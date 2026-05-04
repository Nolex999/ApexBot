"""APEX BOT - Main Orchestrator (Bot + Web Dashboard)"""
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
from datetime import datetime


def bot_loop(dh, strat, rm, ex, log):
    """Boucle de trading qui tourne en background thread"""
    cycle = 0
    bot_state['status'] = 'RUNNING'
    
    while True:
        try:
            cycle += 1
            bot_state['cycle'] = cycle
            bot_state['last_update'] = datetime.now().isoformat()
            log.info(f"--- Cycle #{cycle} ---")
            
            # 1. Fetch data
            df_fast = dh.fetch_ohlcv(Config.SYMBOL, Config.TIMEFRAME_FAST, 300)
            df_slow = dh.fetch_ohlcv(Config.SYMBOL, Config.TIMEFRAME_SLOW, 300)
            current_price = dh.fetch_price(Config.SYMBOL)
            
            # 2. Check existing positions
            ex.check_exits(current_price)
            
            # 3. Analyze for new signal
            signal = strat.analyze(df_fast, df_slow)
            log.signal(signal)
            
            # Update dashboard state
            bot_state['last_signal'] = signal
            bot_state['signals_history'].append({
                **signal,
                'time': datetime.now().isoformat()
            })
            # Keep only last 200 signals in memory
            if len(bot_state['signals_history']) > 200:
                bot_state['signals_history'] = bot_state['signals_history'][-200:]
            
            # 4. Trade decision
            if signal['signal'] in ("BUY", "SELL") and signal['confidence'] >= 0.66:
                can_trade, reason = rm.can_open_trade()
                if can_trade:
                    ex.open_position(signal)
                else:
                    log.warn(f"Trade refusé: {reason}")
            
            # 5. Stats every 10 cycles
            if cycle % 10 == 0:
                log.stats(rm.stats())
            
            time.sleep(Config.LOOP_INTERVAL)
        
        except KeyboardInterrupt:
            log.warn("Arrêt manuel demandé")
            log.stats(rm.stats())
            bot_state['status'] = 'STOPPED'
            break
        except Exception as e:
            log.error(f"Erreur cycle: {e}")
            traceback.print_exc()
            bot_state['status'] = 'ERROR'
            time.sleep(30)
            bot_state['status'] = 'RUNNING'


def main():
    log = ApexLogger()
    log.info("━" * 60)
    log.info("🚀 APEX TRADING BOT — INITIALIZING")
    log.info(f"   Mode: {Config.MODE} | Symbol: {Config.SYMBOL}")
    log.info(f"   Capital: ${Config.INITIAL_CAPITAL} | Risk/trade: {Config.RISK_PER_TRADE*100}%")
    log.info(f"   Exchange: {Config.EXCHANGE}")
    log.info(f"   Dashboard: http://0.0.0.0:{os.getenv('PORT', '8080')}")
    log.info("━" * 60)
    
    dh = DataHandler()
    strat = ApexStrategy()
    rm = RiskManager(Config.INITIAL_CAPITAL)
    ex = Executor(dh, rm, log)
    
    # Share risk_manager with dashboard
    bot_state['risk_manager'] = rm
    bot_state['config'] = Config
    
    # Start bot loop in background thread
    bot_thread = threading.Thread(target=bot_loop, args=(dh, strat, rm, ex, log), daemon=True)
    bot_thread.start()
    log.success("Bot thread démarré")
    
    # Start Flask web dashboard (main thread)
    port = int(os.getenv('PORT', 8080))
    log.success(f"Dashboard web démarré sur le port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)


if __name__ == "__main__":
    main()
