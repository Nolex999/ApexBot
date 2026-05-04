"""APEX BOT - Main Orchestrator (Bot + Web Dashboard)

Architecture anti-ban Binance :
  - WebSocket pour prix + klines temps réel (0 requête REST, push par Binance)
  - Check de sortie (SL/TP) à CHAQUE TICK via WS (on ne loupe aucun mouvement)
  - Analyse stratégique déclenchée par CLÔTURE de bougie (event-driven)
  - Fallback REST polling très rare (4x/h max) si WS down
"""

import sys
import os
import time
import threading
import traceback

# Ajoute le dossier apex_bot au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from data_handler import DataHandler
from strategy import ApexStrategy
from risk_manager import RiskManager
from executor import Executor
from logger import ApexLogger
from dashboard import app, bot_state
from ws_stream import BinanceWSStream
from datetime import datetime


# État partagé entre WS callback, tick loop et analysis loop
_shared = {
    "log": None,
    "dh": None,
    "strat": None,
    "rm": None,
    "ex": None,
    "analyze_lock": threading.Lock(),
}


def on_kline_close(tf: str, kline: dict):
    """
    Callback WS : appelé dès qu'une bougie se clôture.
    C'est le TRIGGER idéal pour lancer l'analyse stratégique
    (plutôt que du polling aveugle).
    """
    log = _shared["log"]
    if not log:
        return

    # On ne ré-analyse que sur clôture du timeframe rapide (évite la duplication)
    if tf != Config.TIMEFRAME_FAST:
        return

    # Éviter les analyses concurrentes
    if not _shared["analyze_lock"].acquire(blocking=False):
        return

    try:
        log.info(f"🕯️ Bougie {tf} clôturée @ ${kline['close']:.2f} → analyse...")
        run_analysis_cycle()
    finally:
        _shared["analyze_lock"].release()


def run_analysis_cycle():
    """Un cycle complet d'analyse : fetch (cache+WS merge), strat, décision"""
    dh = _shared["dh"]
    strat = _shared["strat"]
    rm = _shared["rm"]
    ex = _shared["ex"]
    log = _shared["log"]

    try:
        df_fast = dh.fetch_ohlcv(Config.SYMBOL, Config.TIMEFRAME_FAST, 300)
        df_slow = dh.fetch_ohlcv(Config.SYMBOL, Config.TIMEFRAME_SLOW, 300)

        signal = strat.analyze(df_fast, df_slow)
        log.signal(signal)

        bot_state["last_signal"] = signal
        bot_state["signals_history"].append(
            {**signal, "time": datetime.now().isoformat()}
        )
        if len(bot_state["signals_history"]) > 200:
            bot_state["signals_history"] = bot_state["signals_history"][-200:]

        if signal["signal"] in ("BUY", "SELL") and signal["confidence"] >= 0.66:
            can_trade, reason = rm.can_open_trade()
            if can_trade:
                ex.open_position(signal)
            else:
                log.warn(f"Trade refusé: {reason}")
    except Exception as e:
        log.error(f"Erreur analyse: {e}")
        traceback.print_exc()


def tick_loop():
    """
    Boucle rapide (1s) — surveille chaque tick de prix via WS.
    Role :
      - Vérifier SL/TP en temps réel (on ne loupe aucune sortie)
      - Mettre à jour le dashboard
      - Déclencher une analyse si WS déconnecté trop longtemps (fallback)
    """
    log = _shared["log"]
    dh = _shared["dh"]
    ex = _shared["ex"]
    rm = _shared["rm"]

    cycle = 0
    last_fallback_analysis = 0
    last_heartbeat = 0

    while True:
        try:
            cycle += 1
            bot_state["cycle"] = cycle
            bot_state["last_update"] = datetime.now().isoformat()

            # Ban check
            if dh._is_banned():
                remaining = dh._ban_until - time.time()
                bot_state["status"] = f"BANNED ({remaining / 60:.0f}min)"
                time.sleep(5)
                continue

            # Prix live depuis le WS (0 requête REST)
            try:
                current_price = dh.fetch_price(Config.SYMBOL)
            except Exception as e:
                log.warn(f"Prix indisponible: {e}")
                time.sleep(2)
                continue

            # ===== Check SL/TP à CHAQUE TICK =====
            # C'est critique : les exits doivent être instantanés pour ne pas
            # louper un mouvement. Grâce au WS, on a le prix à la ms.
            if rm.open_trades:
                ex.check_exits(current_price)

            # ===== Statut =====
            ws_ok = dh.ws.is_connected() if dh.ws else False
            if ws_ok:
                bot_state["status"] = "RUNNING (WS live)"
            else:
                bot_state["status"] = "RUNNING (REST fallback)"

            # ===== Fallback analyse si WS down trop longtemps =====
            # Si le WS est déco depuis >5min, on force une analyse REST
            # (pour ne pas rester aveugle)
            now = time.time()
            if not ws_ok and (now - last_fallback_analysis) > 300:
                log.warn("⚠️ WS down depuis >5min — analyse REST de secours")
                if _shared["analyze_lock"].acquire(blocking=False):
                    try:
                        run_analysis_cycle()
                        last_fallback_analysis = now
                    finally:
                        _shared["analyze_lock"].release()

            # ===== Heartbeat stats toutes les 2min =====
            if (now - last_heartbeat) > 120:
                ws_stats = dh.ws.get_stats() if dh.ws else {}
                dh_stats = dh.get_stats()
                log.info(
                    f"💓 price=${current_price:.2f} | "
                    f"WS={'✅' if ws_ok else '❌'} msgs={ws_stats.get('msg_count', 0)} | "
                    f"REST={dh_stats['request_count']} reqs, weight={dh_stats['binance_weight_1m']}/1200 | "
                    f"bucket={dh_stats['bucket_used']}/{dh_stats['bucket_max']}"
                )
                last_heartbeat = now

            time.sleep(1)  # tick rapide grâce au WS (pas d'appel REST)

        except KeyboardInterrupt:
            log.warn("Arrêt manuel")
            bot_state["status"] = "STOPPED"
            break
        except Exception as e:
            log.error(f"Erreur tick loop: {e}")
            traceback.print_exc()
            bot_state["status"] = "ERROR"
            time.sleep(5)


def initial_warmup():
    """
    Préchauffe le cache avec 1 fetch par timeframe au démarrage.
    Après ça, le WS prend le relais pour les données live.
    """
    log = _shared["log"]
    dh = _shared["dh"]
    log.info("🔥 Warmup cache (1 fetch par TF)...")
    try:
        dh.fetch_ohlcv(Config.SYMBOL, Config.TIMEFRAME_FAST, 300)
        dh.fetch_ohlcv(Config.SYMBOL, Config.TIMEFRAME_SLOW, 300)
        log.success("Warmup terminé")

        # Analyse initiale
        if _shared["analyze_lock"].acquire(blocking=False):
            try:
                run_analysis_cycle()
            finally:
                _shared["analyze_lock"].release()
    except Exception as e:
        log.error(f"Warmup échoué: {e}")


def main():
    log = ApexLogger()
    log.info("━" * 60)
    log.info("🚀 APEX TRADING BOT — INITIALIZING")
    log.info(f"   Mode: {Config.MODE} | Symbol: {Config.SYMBOL}")
    log.info(
        f"   Capital: ${Config.INITIAL_CAPITAL} | Risk/trade: {Config.RISK_PER_TRADE * 100}%"
    )
    log.info(f"   Exchange: {Config.EXCHANGE}")
    log.info(f"   Dashboard: http://0.0.0.0:{os.getenv('PORT', '8080')}")
    log.info(f"   Architecture: WebSocket (anti-ban) + REST fallback")
    log.info("━" * 60)

    # --- WebSocket stream (prix + klines temps réel, 0 rate-limit) ---
    ws = BinanceWSStream(
        symbol=Config.SYMBOL,
        timeframes=("1m", Config.TIMEFRAME_FAST, Config.TIMEFRAME_SLOW),
        on_kline_close=on_kline_close,
    )
    ws.start()

    # --- Composants bot ---
    dh = DataHandler(ws_stream=ws)
    strat = ApexStrategy()
    rm = RiskManager(Config.INITIAL_CAPITAL)
    ex = Executor(dh, rm, log)

    # Partage entre threads
    _shared.update({"log": log, "dh": dh, "strat": strat, "rm": rm, "ex": ex})

    # Partage dashboard
    bot_state["risk_manager"] = rm
    bot_state["data_handler"] = dh
    bot_state["config"] = Config
    bot_state["status"] = "STARTING"

    # Attend 2s que le WS se connecte avant le warmup
    time.sleep(2)
    initial_warmup()

    # --- Tick loop en background ---
    threading.Thread(target=tick_loop, daemon=True, name="TickLoop").start()
    log.success("Tick loop démarré (1s via WS)")
    log.success("Event-driven analysis activé (déclenché par clôture de bougie)")

    # --- Dashboard Flask (main thread) ---
    port = int(os.getenv("PORT", 8080))
    log.success(f"Dashboard web sur port {port}")

    import logging

    logging.getLogger("werkzeug").setLevel(logging.ERROR)

    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    main()
