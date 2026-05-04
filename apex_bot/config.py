"""APEX BOT - Configuration centrale"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # ===== MODE =====
    MODE = "PAPER"  # "PAPER" | "LIVE" — NE PASSE EN LIVE QU'APRÈS 100+ trades paper rentables
    
    # ===== EXCHANGE =====
    EXCHANGE = "binance"
    API_KEY = os.getenv("BINANCE_API_KEY", "")
    API_SECRET = os.getenv("BINANCE_API_SECRET", "")
    
    # ===== TRADING =====
    SYMBOL = "BTC/USDT"
    TIMEFRAME_FAST = "15m"   # Timeframe d'entrée
    TIMEFRAME_SLOW = "4h"    # Timeframe de tendance macro
    
    # ===== CAPITAL & RISK (LOIS APEX) =====
    INITIAL_CAPITAL = 1000.0       # USDT (paper)
    RISK_PER_TRADE = 0.01          # 1% max par trade
    MAX_PORTFOLIO_HEAT = 0.06      # 6% exposition max
    MAX_DAILY_LOSS = 0.05          # -5% jour → arrêt
    MAX_WEEKLY_LOSS = 0.10         # -10% semaine → arrêt
    MAX_CONCURRENT_TRADES = 3
    
    # ===== STRATEGY =====
    EMA_FAST = 21
    EMA_SLOW = 55
    EMA_TREND = 200
    RSI_PERIOD = 14
    RSI_OVERSOLD = 35
    RSI_OVERBOUGHT = 65
    ATR_PERIOD = 14
    ATR_STOP_MULTIPLIER = 2.0      # Stop = 2x ATR
    RR_RATIO = 2.5                 # Take profit = 2.5x risk
    
    # ===== EXECUTION =====
    LOOP_INTERVAL = 60             # secondes entre chaque cycle
    SLIPPAGE_TOLERANCE = 0.002     # 0.2%
