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
    
    # ===== STRATEGY — INDICATORS =====
    EMA_FAST = 21
    EMA_SLOW = 55
    EMA_TREND = 200
    EMA_MACRO_FAST = 50     # pour structure macro 4h
    RSI_PERIOD = 14
    ATR_PERIOD = 14
    
    # ===== STRATEGY — ENTRY FILTERS =====
    # RSI zones
    RSI_PULLBACK_BUY_MAX = 55   # on n'achète QUE si RSI < 55 (anti-FOMO)
    RSI_PULLBACK_BUY_MIN = 30   # mais pas si trop oversold (knife)
    RSI_PULLBACK_SELL_MIN = 45  # miroir pour SHORT
    RSI_PULLBACK_SELL_MAX = 70
    
    # ADX (force de tendance)
    ADX_MIN = 20                # comme avant
    ADX_MAX = 55                # au-delà = tendance épuisée
    
    # Confidence
    MIN_CONFIDENCE = 0.65       # seuil de prise de trade (pondéré désormais)
    
    # ===== STRATEGY — EXECUTION =====
    ATR_STOP_MULTIPLIER = 2.3   # élargi pour éviter wicks
    RR_RATIO = 2.5
    
    # ===== COOLDOWN POST-SL =====
    COOLDOWN_AFTER_SL_MINUTES = 30   # 30min = 2 bougies 15m
    
    # ===== EXECUTION =====
    LOOP_INTERVAL = int(os.getenv("APEX_LOOP_INTERVAL", "300"))
    SLIPPAGE_TOLERANCE = 0.002
