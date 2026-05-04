"""APEX BOT - Stratégie Multi-Timeframe Hybrid"""
from indicators import Indicators
from config import Config
import pandas as pd

class ApexStrategy:
    """
    Stratégie Hybride APEX:
    1. Identifie la tendance macro sur TF lent (4h) via EMA200
    2. Cherche pullbacks sur TF rapide (15m) dans le sens de la tendance
    3. Confirme avec RSI (oversold en uptrend, overbought en downtrend)
    4. Filtre par ADX > 20 (évite les marchés sans tendance)
    5. Stop dynamique basé sur ATR
    """
    
    def __init__(self):
        self.cfg = Config
    
    def analyze(self, df_fast: pd.DataFrame, df_slow: pd.DataFrame) -> dict:
        # === MACRO TREND (TF lent) ===
        df_slow['ema_trend'] = Indicators.ema(df_slow['close'], self.cfg.EMA_TREND)
        macro_uptrend = df_slow['close'].iloc[-1] > df_slow['ema_trend'].iloc[-1]
        macro_downtrend = df_slow['close'].iloc[-1] < df_slow['ema_trend'].iloc[-1]
        
        # === MICRO SETUP (TF rapide) ===
        df = df_fast.copy()
        df['ema_fast'] = Indicators.ema(df['close'], self.cfg.EMA_FAST)
        df['ema_slow'] = Indicators.ema(df['close'], self.cfg.EMA_SLOW)
        df['rsi'] = Indicators.rsi(df['close'], self.cfg.RSI_PERIOD)
        df['atr'] = Indicators.atr(df, self.cfg.ATR_PERIOD)
        df['adx'] = Indicators.adx(df, 14)
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        # === SIGNAL LOGIC ===
        signal = "HOLD"
        confidence = 0.0
        reasons = []
        
        # Filtre ADX (force de tendance)
        if last['adx'] < 20:
            return {
                'signal': 'HOLD',
                'confidence': 0,
                'reason': 'ADX trop faible (marché sans tendance)',
                'price': last['close'],
                'atr': last['atr']
            }
        
        # === LONG SETUP ===
        if macro_uptrend:
            cond_ema = last['ema_fast'] > last['ema_slow']
            cond_rsi_pullback = prev['rsi'] < self.cfg.RSI_OVERSOLD and last['rsi'] > prev['rsi']
            cond_price_above_fast = last['close'] > last['ema_fast']
            
            score = sum([cond_ema, cond_rsi_pullback, cond_price_above_fast])
            
            if score >= 2:
                signal = "BUY"
                confidence = score / 3
                reasons = [
                    f"Macro uptrend (4h close > EMA200)",
                    f"EMA21 > EMA55: {cond_ema}",
                    f"RSI pullback recovery: {cond_rsi_pullback}",
                    f"ADX={last['adx']:.1f} (trend confirmé)"
                ]
        
        # === SHORT SETUP ===
        elif macro_downtrend:
            cond_ema = last['ema_fast'] < last['ema_slow']
            cond_rsi_pullback = prev['rsi'] > self.cfg.RSI_OVERBOUGHT and last['rsi'] < prev['rsi']
            cond_price_below_fast = last['close'] < last['ema_fast']
            
            score = sum([cond_ema, cond_rsi_pullback, cond_price_below_fast])
            
            if score >= 2:
                signal = "SELL"
                confidence = score / 3
                reasons = [
                    f"Macro downtrend (4h close < EMA200)",
                    f"EMA21 < EMA55: {cond_ema}",
                    f"RSI pullback rejection: {cond_rsi_pullback}",
                    f"ADX={last['adx']:.1f} (trend confirmé)"
                ]
        
        return {
            'signal': signal,
            'confidence': confidence,
            'reasons': reasons,
            'price': last['close'],
            'atr': last['atr'],
            'rsi': last['rsi'],
            'adx': last['adx']
        }
