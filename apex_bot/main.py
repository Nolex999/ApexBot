"""APEX BOT - Main Orchestrator"""
import time
import traceback
from config import Config
from data_handler import DataHandler
from strategy import ApexStrategy
from risk_manager import RiskManager
from executor import Executor
from logger import ApexLogger

def main():
    log = ApexLogger()
    log.info("━" * 60)
    log.info("🚀 APEX TRADING BOT — INITIALIZING")
    log.info(f"   Mode: {Config.MODE} | Symbol: {Config.SYMBOL}")
    log.info(f"   Capital: ${Config.INITIAL_CAPITAL} | Risk/trade: {Config.RISK_PER_TRADE*100}%")
    log.info("━" * 60)
    
    dh = DataHandler()
    strat = ApexStrategy()
    rm = RiskManager(Config.INITIAL_CAPITAL)
    ex = Executor(dh, rm, log)
    
    cycle = 0
    while True:
        try:
            cycle += 1
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
            break
        except Exception as e:
            log.error(f"Erreur cycle: {e}")
            traceback.print_exc()
            time.sleep(30)

if __name__ == "__main__":
    main()
