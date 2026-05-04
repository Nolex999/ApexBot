"""APEX BOT - Binance WebSocket Streamer

Flux temps réel GRATUIT et ILLIMITÉ (aucun rate-limit, aucun risque de ban).
Binance pousse les données vers nous en push — au lieu du polling REST.

Streams utilisés:
  - <symbol>@trade     : chaque trade exécuté (prix live ms)
  - <symbol>@kline_1m  : bougie 1m qui se met à jour en temps réel
  - <symbol>@kline_15m : bougie 15m (TIMEFRAME_FAST)
  - <symbol>@kline_4h  : bougie 4h (TIMEFRAME_SLOW)

→ Le bot connaît le prix et la structure des bougies à CHAQUE MS, sans jamais
  toucher à l'API REST de Binance.
"""

import json
import threading
import time
import logging
from collections import deque
import websocket  # websocket-client

logger = logging.getLogger("APEX")

BINANCE_WS_BASE = "wss://stream.binance.com:9443/stream"


class BinanceWSStream:
    """
    WebSocket multi-stream Binance Spot.
    Thread-safe. Reconnexion automatique avec backoff exponentiel.
    """

    def __init__(
        self, symbol: str, timeframes=("1m", "15m", "4h"), on_kline_close=None
    ):
        # Binance WS utilise les symboles en lowercase sans le /
        self.symbol_pair = symbol.replace("/", "").lower()  # ex: btcusdt
        self.symbol = symbol
        self.timeframes = timeframes
        self.on_kline_close_cb = on_kline_close

        # --- État live ---
        self._lock = threading.RLock()
        self._last_price = None
        self._last_price_ts = 0
        self._last_trade_qty = 0

        # Klines: {tf: {"open":..., "high":..., "low":..., "close":..., "volume":..., "t":..., "closed": bool}}
        self._live_kline: dict = {tf: None for tf in timeframes}

        # Historique récent des trades (pour détection de mouvement)
        self._recent_trades = deque(maxlen=500)

        # --- Connexion ---
        self._ws = None
        self._thread = None
        self._running = False
        self._reconnect_delay = 1  # backoff exponentiel
        self._connected_at = 0
        self._msg_count = 0
        self._last_msg_ts = 0

    # ================================================================
    # API publique (thread-safe)
    # ================================================================
    def start(self):
        """Démarre la connexion WS dans un thread background"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._run_forever, daemon=True, name="BinanceWS"
        )
        self._thread.start()
        logger.info(
            f"🔌 WebSocket stream démarré pour {self.symbol} (TFs: {self.timeframes})"
        )

    def stop(self):
        self._running = False
        try:
            if self._ws:
                self._ws.close()
        except Exception:
            pass

    def get_price(self) -> float | None:
        """Dernier prix reçu en temps réel (ms-level)"""
        with self._lock:
            return self._last_price

    def get_live_kline(self, timeframe: str) -> dict | None:
        """Bougie en cours pour un timeframe donné (mise à jour en live)"""
        with self._lock:
            k = self._live_kline.get(timeframe)
            return dict(k) if k else None

    def is_connected(self) -> bool:
        if not self._last_msg_ts:
            return False
        # Considéré connecté si on a reçu un message dans les 30 dernières secondes
        return (time.time() - self._last_msg_ts) < 30

    def get_stats(self) -> dict:
        with self._lock:
            return {
                "connected": self.is_connected(),
                "msg_count": self._msg_count,
                "last_price": self._last_price,
                "last_msg_age_s": round(time.time() - self._last_msg_ts, 1)
                if self._last_msg_ts
                else None,
                "uptime_s": round(time.time() - self._connected_at, 0)
                if self._connected_at
                else 0,
                "recent_trades": len(self._recent_trades),
            }

    # ================================================================
    # WS internals
    # ================================================================
    def _build_url(self) -> str:
        streams = [f"{self.symbol_pair}@trade"]
        for tf in self.timeframes:
            streams.append(f"{self.symbol_pair}@kline_{tf}")
        return f"{BINANCE_WS_BASE}?streams={'/'.join(streams)}"

    def _run_forever(self):
        """Boucle de (re)connexion avec backoff"""
        while self._running:
            try:
                url = self._build_url()
                logger.info(f"🔌 WS connecting → {url}")
                self._ws = websocket.WebSocketApp(
                    url,
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close,
                )
                # ping_interval pour maintenir la co (Binance déconnecte après 24h)
                self._ws.run_forever(ping_interval=180, ping_timeout=10, reconnect=0)
            except Exception as e:
                logger.error(f"❌ WS exception: {e}")

            if not self._running:
                break

            # Backoff exponentiel plafonné à 60s
            logger.warning(
                f"⚠️ WS déconnecté — reconnexion dans {self._reconnect_delay}s"
            )
            time.sleep(self._reconnect_delay)
            self._reconnect_delay = min(self._reconnect_delay * 2, 60)

    def _on_open(self, ws):
        logger.info(f"✅ WS connecté ({self.symbol})")
        self._connected_at = time.time()
        self._reconnect_delay = 1  # reset backoff

    def _on_close(self, ws, code, msg):
        logger.warning(f"🔌 WS fermé (code={code}, msg={msg})")

    def _on_error(self, ws, error):
        logger.error(f"❌ WS error: {error}")

    def _on_message(self, ws, message):
        try:
            self._msg_count += 1
            self._last_msg_ts = time.time()

            payload = json.loads(message)
            stream = payload.get("stream", "")
            data = payload.get("data", {})

            if "@trade" in stream:
                self._handle_trade(data)
            elif "@kline_" in stream:
                self._handle_kline(data)
        except Exception as e:
            logger.error(f"❌ WS message parse error: {e}")

    def _handle_trade(self, d: dict):
        """Événement trade (prix live à chaque trade exécuté sur Binance)"""
        try:
            price = float(d["p"])
            qty = float(d["q"])
            ts = int(d["T"])
            with self._lock:
                self._last_price = price
                self._last_price_ts = ts
                self._last_trade_qty = qty
                self._recent_trades.append((ts, price, qty))
        except (KeyError, ValueError) as e:
            logger.debug(f"Trade parse error: {e}")

    def _handle_kline(self, d: dict):
        """Événement kline (bougie qui se met à jour en live, plusieurs fois/sec)"""
        try:
            k = d["k"]
            tf = k["i"]  # interval (1m, 15m, 4h, ...)
            kline = {
                "open": float(k["o"]),
                "high": float(k["h"]),
                "low": float(k["l"]),
                "close": float(k["c"]),
                "volume": float(k["v"]),
                "t": int(k["t"]),  # open time (ms)
                "T": int(k["T"]),  # close time (ms)
                "closed": bool(k["x"]),  # True quand la bougie se clôture
            }
            with self._lock:
                self._live_kline[tf] = kline
                # Le close dans kline est le prix live — on met à jour aussi
                if (
                    self._last_price is None
                    or (time.time() - self._last_price_ts / 1000) > 5
                ):
                    self._last_price = kline["close"]

            # Callback sur clôture de bougie (trigger analyse stratégie)
            if kline["closed"] and self.on_kline_close_cb:
                try:
                    self.on_kline_close_cb(tf, kline)
                except Exception as e:
                    logger.error(f"❌ on_kline_close callback error: {e}")
        except (KeyError, ValueError) as e:
            logger.debug(f"Kline parse error: {e}")
