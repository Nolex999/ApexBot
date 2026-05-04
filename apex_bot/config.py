"""APEX BOT - Configuration centrale"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # ===== MODE =====
    MODE = os.getenv("APEX_MODE", "PAPER")  # "PAPER" | "LIVE"
    
    # ===== EXCHANGE =====
    EXCHANGE = os.getenv("APEX_EXCHANGE", "binance")
    API_KEY = os.getenv("BINANCE_API_KEY", "")
    API_SECRET = os.getenv("BINANCE_API_SECRET", "")
    
    # ===== TRADING =====
    SYMBOL = os.getenv("APEX_SYMBOL", "BTC/USDT")
    TIMEFRAME_FAST = os.getenv("APEX_TF_FAST", "15m")
    TIMEFRAME_SLOW = os.getenv("APEX_TF_SLOW", "4h")
    
    # ===== CAPITAL & RISK (LOIS APEX) =====
    INITIAL_CAPITAL = float(os.getenv("APEX_CAPITAL", "1000.0"))
    RISK_PER_TRADE = float(os.getenv("APEX_RISK_PER_TRADE", "0.01"))
    MAX_PORTFOLIO_HEAT = float(os.getenv("APEX_MAX_HEAT", "0.06"))
    MAX_DAILY_LOSS = float(os.getenv("APEX_MAX_DAILY_LOSS", "0.05"))
    MAX_WEEKLY_LOSS = float(os.getenv("APEX_MAX_WEEKLY_LOSS", "0.10"))
    MAX_CONCURRENT_TRADES = int(os.getenv("APEX_MAX_TRADES", "3"))
    
    # ===== STRATEGY =====
    EMA_FAST = 21
    EMA_SLOW = 55
    EMA_TREND = 200
    RSI_PERIOD = 14
    RSI_OVERSOLD = 35
    RSI_OVERBOUGHT = 65
    ATR_PERIOD = 14
    ATR_STOP_MULTIPLIER = 2.0
    RR_RATIO = 2.5
    
    # ===== EXECUTION =====
    LOOP_INTERVAL = int(os.getenv("APEX_LOOP_INTERVAL", "300"))  # 5min — anti rate-limit
    SLIPPAGE_TOLERANCE = 0.002
