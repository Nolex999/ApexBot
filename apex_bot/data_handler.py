"""APEX BOT - Data Handler

Conçu pour ne JAMAIS se faire ban par Binance :
  1. WebSocket en priorité (prix live + kline live) → 0 requête REST
  2. Cache agressif sur les OHLCV historiques (TTL adapté par timeframe)
  3. Token bucket rate-limiter local (bien en-dessous des limites Binance)
  4. Tracking du header X-MBX-USED-WEIGHT-* renvoyé par Binance
  5. Backoff exponentiel + respect du "Retry-After" / "banned until"
  6. Jitter aléatoire pour éviter les patterns de requêtes réguliers
  7. Fallback sur cache stale si API indispo (on ne plante jamais)

Limites officielles Binance Spot (par IP) :
  - 1200 weight-points par minute (fenêtre glissante)
  - 6000 requêtes brutes par 5 min
  Un fetch_ohlcv = 1 weight, fetch_ticker = 1 weight → on est très large.
"""

import ccxt
import pandas as pd
import time
import random
import logging
import re
import threading
from collections import deque
from config import Config

logger = logging.getLogger("APEX")


# ====================================================================
# Token Bucket Rate Limiter
# ====================================================================
class TokenBucket:
    """
    Rate limiter local : autorise au plus N requêtes par fenêtre glissante.
    Thread-safe. Conservateur par défaut (bien en-deçà des limites Binance).
    """

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window = window_seconds
        self._calls = deque()
        self._lock = threading.Lock()

    def acquire(self, block: bool = True, timeout: float = 30.0) -> bool:
        """Essaie de consommer un token. Bloque si nécessaire (jusqu'à timeout)."""
        start = time.time()
        while True:
            with self._lock:
                now = time.time()
                # Nettoie les appels hors fenêtre
                while self._calls and now - self._calls[0] > self.window:
                    self._calls.popleft()

                if len(self._calls) < self.max_requests:
                    self._calls.append(now)
                    return True

                # Temps à attendre avant la prochaine autorisation
                wait = self.window - (now - self._calls[0]) + 0.05

            if not block:
                return False
            if time.time() - start + wait > timeout:
                return False
            time.sleep(min(wait, 1.0))

    def usage(self) -> dict:
        with self._lock:
            now = time.time()
            while self._calls and now - self._calls[0] > self.window:
                self._calls.popleft()
            return {
                "used": len(self._calls),
                "max": self.max_requests,
                "window_s": self.window,
                "pct": round(100 * len(self._calls) / self.max_requests, 1),
            }


# ====================================================================
# DataHandler
# ====================================================================
class DataHandler:
    def __init__(self, ws_stream=None):
        self.exchange = getattr(ccxt, Config.EXCHANGE)(
            {
                "apiKey": Config.API_KEY,
                "secret": Config.API_SECRET,
                "enableRateLimit": True,  # throttle interne ccxt
                "rateLimit": 250,  # min 250ms entre requêtes (conservateur)
                "options": {
                    "defaultType": "spot",
                    "adjustForTimeDifference": True,
                },
            }
        )

        # Source temps réel (WebSocket) — optionnelle mais recommandée
        self.ws = ws_stream

        # ========= Cache OHLCV =========
        self._cache: dict = {}
        # TTL ≥ durée de la bougie → on ne requête que sur clôture effective
        self._cache_ttl = {
            "1m": 55,  # bougie 1m
            "5m": 290,  # bougie 5m
            "15m": 890,  # bougie 15m — presque toute la durée de la bougie
            "1h": 3590,
            "4h": 14390,
            "1d": 86390,
        }
        self._cache_lock = threading.RLock()

        # ========= Cache Prix =========
        self._price_cache: dict = {}
        self._price_cache_ttl = 5  # fallback REST: 5s (vs. WS live = ms)

        # ========= Rate limiter =========
        # Max 200 req/min côté bot (Binance autorise 1200 weight/min, on prend x6 de marge)
        self._bucket = TokenBucket(max_requests=200, window_seconds=60)

        # ========= Tracking weight Binance =========
        self._used_weight_1m = 0  # dernière valeur X-MBX-USED-WEIGHT-1M
        self._weight_updated_at = 0
        self._request_count = 0
        self._last_request_at = 0

        # ========= Ban tracking =========
        self._ban_until = 0
        self._consecutive_errors = 0

        # Monkey-patch la méthode de ccxt pour capturer les headers
        self._install_weight_tracker()

    # ------------------------------------------------------------------
    # Header tracking (Binance renvoie X-MBX-USED-WEIGHT-1M dans chaque réponse)
    # ------------------------------------------------------------------
    def _install_weight_tracker(self):
        exchange = self.exchange
        original_fetch = exchange.fetch

        def fetch_with_tracking(*args, **kwargs):
            result = original_fetch(*args, **kwargs)
            try:
                last_headers = getattr(exchange, "last_response_headers", None) or {}
                # Les clés peuvent être lowercase selon l'implémentation
                for k, v in last_headers.items():
                    if k.lower() == "x-mbx-used-weight-1m":
                        self._used_weight_1m = int(v)
                        self._weight_updated_at = time.time()
                        if self._used_weight_1m > 1000:
                            logger.warning(
                                f"⚠️ Weight Binance élevé: {self._used_weight_1m}/1200 — ralentir !"
                            )
                        break
            except Exception:
                pass
            return result

        try:
            exchange.fetch = fetch_with_tracking
        except Exception as e:
            logger.debug(f"Weight tracker not installed: {e}")

    # ------------------------------------------------------------------
    # Ban detection
    # ------------------------------------------------------------------
    def _is_banned(self) -> bool:
        if time.time() < self._ban_until:
            return True
        return False

    def _handle_rate_error(self, e):
        error_str = str(e)
        now = time.time()
        self._consecutive_errors += 1

        # Cas 1 : message contient "banned until <timestamp ms>"
        m = re.search(r"banned until (\d+)", error_str.lower())
        if m:
            ban_ts = int(m.group(1)) / 1000
            self._ban_until = ban_ts
            remaining = max(0, ban_ts - now)
            logger.error(
                f"🚫 IP BANNED — libération dans {remaining:.0f}s ({remaining / 60:.1f}min)"
            )
            return

        # Cas 2 : header Retry-After
        try:
            headers = getattr(self.exchange, "last_response_headers", None) or {}
            for k, v in headers.items():
                if k.lower() == "retry-after":
                    wait = int(v)
                    self._ban_until = now + wait
                    logger.error(f"🚫 Retry-After reçu: {wait}s")
                    return
        except Exception:
            pass

        # Cas 3 : backoff exponentiel basé sur le nombre d'erreurs consécutives
        backoff = min(60 * (2**self._consecutive_errors), 3600)  # max 1h
        jitter = random.uniform(0, backoff * 0.1)
        self._ban_until = now + backoff + jitter
        logger.error(f"🚫 Rate limited — backoff {backoff + jitter:.0f}s")

    # ------------------------------------------------------------------
    # Wrapper safe pour toute requête REST
    # ------------------------------------------------------------------
    def _safe_request(self, func, *args, **kwargs):
        if self._is_banned():
            remaining = self._ban_until - time.time()
            logger.warning(
                f"⛔ Ban actif ({remaining:.0f}s) — requête bloquée côté client"
            )
            return None

        # Rate-limit local (token bucket)
        if not self._bucket.acquire(block=True, timeout=30):
            logger.warning("⚠️ Token bucket saturé — requête abandonnée")
            return None

        # Jitter anti-pattern (0 à 200ms)
        time.sleep(random.uniform(0, 0.2))

        max_retries = 3
        for attempt in range(max_retries):
            try:
                self._request_count += 1
                self._last_request_at = time.time()
                result = func(*args, **kwargs)
                self._consecutive_errors = 0  # reset sur succès
                return result

            except (ccxt.RateLimitExceeded, ccxt.DDoSProtection) as e:
                self._handle_rate_error(e)
                return None

            except ccxt.ExchangeNotAvailable as e:
                err = str(e)
                if "418" in err or "teapot" in err.lower() or "429" in err:
                    self._handle_rate_error(e)
                    return None
                wait = (attempt + 1) * 10 + random.uniform(0, 5)
                logger.warning(f"⚠️ Exchange indispo, retry dans {wait:.0f}s... ({e})")
                time.sleep(wait)

            except ccxt.NetworkError as e:
                wait = (attempt + 1) * 5 + random.uniform(0, 3)
                logger.warning(f"⚠️ Network error, retry dans {wait:.0f}s... ({e})")
                time.sleep(wait)

            except Exception as e:
                logger.error(f"❌ API error inattendu: {e}")
                if attempt < max_retries - 1:
                    time.sleep(5)
                else:
                    return None

        return None

    # ------------------------------------------------------------------
    # Fetch OHLCV (avec cache + fusion bougie live via WS)
    # ------------------------------------------------------------------
    def fetch_ohlcv(
        self, symbol: str, timeframe: str, limit: int = 300
    ) -> pd.DataFrame:
        cache_key = f"{symbol}_{timeframe}_{limit}"
        now = time.time()

        with self._cache_lock:
            cached = self._cache.get(cache_key)

        # Cache hit
        if cached:
            data, cached_at = cached
            ttl = self._cache_ttl.get(timeframe, 60)
            if now - cached_at < ttl:
                logger.debug(f"📦 Cache hit: {cache_key} (age {now - cached_at:.0f}s)")
                return self._merge_live_kline(data, symbol, timeframe)

        # Cache miss → requête REST
        raw = self._safe_request(
            self.exchange.fetch_ohlcv, symbol, timeframe, limit=limit
        )

        if raw is None:
            # Fallback : retourne le cache stale plutôt que planter
            if cached:
                logger.warning(f"⚠️ Utilisation cache stale pour {cache_key}")
                return self._merge_live_kline(cached[0], symbol, timeframe)
            raise Exception(
                f"Impossible de récupérer {cache_key} et pas de cache dispo"
            )

        df = pd.DataFrame(
            raw, columns=["timestamp", "open", "high", "low", "close", "volume"]
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)

        with self._cache_lock:
            self._cache[cache_key] = (df, now)
        logger.debug(f"✅ Fetched & cached: {cache_key} ({len(df)} bougies)")

        return self._merge_live_kline(df, symbol, timeframe)

    def _merge_live_kline(
        self, df: pd.DataFrame, symbol: str, timeframe: str
    ) -> pd.DataFrame:
        """
        Fusionne la dernière bougie live du WebSocket pour avoir des données
        à jour à la milliseconde près sans refaire de requête REST.
        """
        if not self.ws or self.ws.symbol != symbol:
            return df

        live = self.ws.get_live_kline(timeframe)
        if not live:
            return df

        try:
            live_ts = pd.to_datetime(live["t"], unit="ms")
            df = df.copy()
            new_row = pd.DataFrame(
                [
                    {
                        "open": live["open"],
                        "high": live["high"],
                        "low": live["low"],
                        "close": live["close"],
                        "volume": live["volume"],
                    }
                ],
                index=[live_ts],
            )

            if len(df) and df.index[-1] == live_ts:
                # Remplace la dernière bougie par la version live
                df.iloc[-1] = new_row.iloc[0]
            else:
                # Ajoute la bougie en formation
                df = pd.concat([df, new_row])
        except Exception as e:
            logger.debug(f"Live kline merge skipped: {e}")

        return df

    # ------------------------------------------------------------------
    # Fetch prix
    # ------------------------------------------------------------------
    def fetch_price(self, symbol: str) -> float:
        # 1. Priorité absolue : WebSocket (prix live à la ms)
        if self.ws and self.ws.symbol == symbol:
            ws_price = self.ws.get_price()
            if ws_price is not None and self.ws.is_connected():
                return ws_price

        # 2. Fallback REST avec cache
        now = time.time()
        cached = self._price_cache.get(symbol)
        if cached:
            price, cached_at = cached
            if now - cached_at < self._price_cache_ttl:
                return price

        ticker = self._safe_request(self.exchange.fetch_ticker, symbol)

        if ticker is None:
            if cached:
                logger.warning(f"⚠️ Utilisation prix stale pour {symbol}")
                return cached[0]
            raise Exception(f"Impossible de récupérer le prix {symbol}")

        price = ticker["last"]
        self._price_cache[symbol] = (price, now)
        return price

    # ------------------------------------------------------------------
    # Stats (dashboard)
    # ------------------------------------------------------------------
    def get_stats(self) -> dict:
        bucket = self._bucket.usage()
        return {
            "request_count": self._request_count,
            "cache_entries": len(self._cache),
            "is_banned": self._is_banned(),
            "ban_remaining": max(0, self._ban_until - time.time()),
            "bucket_used": bucket["used"],
            "bucket_max": bucket["max"],
            "bucket_pct": bucket["pct"],
            "binance_weight_1m": self._used_weight_1m,
            "binance_weight_max": 1200,
            "binance_weight_pct": round(100 * self._used_weight_1m / 1200, 1)
            if self._used_weight_1m
            else 0,
            "weight_updated_at": self._weight_updated_at,
            "ws_connected": self.ws.is_connected() if self.ws else False,
            "ws_stats": self.ws.get_stats() if self.ws else None,
        }
