"""APEX BOT - Stratégie Multi-Timeframe Hybrid v2"""
from indicators import Indicators
from config import Config
import pandas as pd


class ApexStrategy:
    """
    Stratégie Hybride APEX v2:

    PHILOSOPHIE:
    - Trade dans le sens de la tendance MACRO 4h (structure EMA50 vs EMA200)
    - Entrée sur PULLBACK 15m (pas en momentum haut)
    - Filtres anti-pièges : RSI bornes, ADX bornes, structure cohérente
    - Scoring pondéré -> confidence réelle

    SCORING (total = 1.0):
    - Structure macro 4h coherente .......... 0.30
    - EMAs 15m alignées ..................... 0.20
    - RSI dans zone pullback (pas extreme) .. 0.20
    - Prix en pullback (pas en momentum) .... 0.15
    - ADX dans zone saine (20-55) ........... 0.15
    """

    def __init__(self):
        self.cfg = Config

    def analyze(self, df_fast: pd.DataFrame, df_slow: pd.DataFrame) -> dict:
        # ===== MACRO 4h - Structure complete =====
        df_slow = df_slow.copy()
        df_slow['ema_macro_fast'] = Indicators.ema(df_slow['close'], self.cfg.EMA_MACRO_FAST)
        df_slow['ema_trend'] = Indicators.ema(df_slow['close'], self.cfg.EMA_TREND)

        slow_last = df_slow.iloc[-1]
        # Structure haussiere forte : prix > EMA50 > EMA200
        macro_strong_up = (slow_last['close'] > slow_last['ema_macro_fast'] > slow_last['ema_trend'])
        # Structure baissiere forte : prix < EMA50 < EMA200
        macro_strong_down = (slow_last['close'] < slow_last['ema_macro_fast'] < slow_last['ema_trend'])

        # ===== MICRO 15m - Indicateurs =====
        df = df_fast.copy()
        df['ema_fast'] = Indicators.ema(df['close'], self.cfg.EMA_FAST)
        df['ema_slow'] = Indicators.ema(df['close'], self.cfg.EMA_SLOW)
        df['rsi'] = Indicators.rsi(df['close'], self.cfg.RSI_PERIOD)
        df['atr'] = Indicators.atr(df, self.cfg.ATR_PERIOD)
        df['adx'] = Indicators.adx(df, 14)

        last = df.iloc[-1]
        prev = df.iloc[-2]

        # Base output
        out = {
            'signal': 'HOLD',
            'confidence': 0.0,
            'reasons': [],
            'price': float(last['close']),
            'atr': float(last['atr']),
            'rsi': float(last['rsi']),
            'adx': float(last['adx'])
        }

        # ===== HARD FILTERS (rejet immediat) =====
        # 1) ADX hors zone saine
        if last['adx'] < self.cfg.ADX_MIN:
            out['reasons'] = [f"ADX {last['adx']:.1f} < {self.cfg.ADX_MIN} (pas de tendance)"]
            return out
        if last['adx'] > self.cfg.ADX_MAX:
            out['reasons'] = [f"ADX {last['adx']:.1f} > {self.cfg.ADX_MAX} (tendance epuisee, retournement probable)"]
            return out

        # 2) Aucune structure macro claire
        if not (macro_strong_up or macro_strong_down):
            out['reasons'] = ["Pas de structure macro 4h claire (range)"]
            return out

        # ===== LONG SETUP (uptrend confirme) =====
        if macro_strong_up:
            # Filtre dur anti-FOMO
            if last['rsi'] > self.cfg.RSI_PULLBACK_BUY_MAX:
                out['reasons'] = [f"RSI {last['rsi']:.1f} > {self.cfg.RSI_PULLBACK_BUY_MAX} (surachat - pas de chase)"]
                return out
            if last['rsi'] < self.cfg.RSI_PULLBACK_BUY_MIN:
                out['reasons'] = [f"RSI {last['rsi']:.1f} < {self.cfg.RSI_PULLBACK_BUY_MIN} (falling knife)"]
                return out

            # Scoring pondere
            score = 0.0
            reasons = []

            # Structure macro (deja validee si on est la)
            score += 0.30
            reasons.append(f"Macro 4h strong up (close>EMA50>EMA200)")

            # EMAs 15m alignees haussier
            if last['ema_fast'] > last['ema_slow']:
                score += 0.20
                reasons.append(f"EMA21>EMA55 (micro aligne)")
            else:
                reasons.append(f"EMA21<EMA55 (micro divergent)")

            # RSI en zone pullback saine (30-55)
            # Bonus si RSI remonte (momentum reprend)
            if last['rsi'] > prev['rsi']:
                score += 0.20
                reasons.append(f"RSI={last['rsi']:.1f} reprend (prev {prev['rsi']:.1f})")
            else:
                score += 0.10
                reasons.append(f"RSI={last['rsi']:.1f} encore en baisse")

            # Prix en PULLBACK : proche ou sous EMA21 (pas etire au-dessus)
            distance_pct = (last['close'] - last['ema_fast']) / last['ema_fast'] * 100
            if -1.5 < distance_pct < 0.5:  # zone pullback ideale
                score += 0.15
                reasons.append(f"Prix en pullback (dist EMA21: {distance_pct:+.2f}%)")
            elif distance_pct >= 0.5:
                reasons.append(f"Prix etire au-dessus EMA21 ({distance_pct:+.2f}% - FOMO)")
            else:
                score += 0.05
                reasons.append(f"Prix loin sous EMA21 ({distance_pct:+.2f}%)")

            # ADX en zone saine (deja validee si on est la)
            score += 0.15
            reasons.append(f"ADX={last['adx']:.1f} (zone saine)")

            out['signal'] = 'BUY' if score >= self.cfg.MIN_CONFIDENCE else 'HOLD'
            out['confidence'] = round(score, 3)
            out['reasons'] = reasons
            return out

        # ===== SHORT SETUP (downtrend confirme) =====
        if macro_strong_down:
            if last['rsi'] < self.cfg.RSI_PULLBACK_SELL_MIN:
                out['reasons'] = [f"RSI {last['rsi']:.1f} < {self.cfg.RSI_PULLBACK_SELL_MIN} (deja oversold - pas de chase)"]
                return out
            if last['rsi'] > self.cfg.RSI_PULLBACK_SELL_MAX:
                out['reasons'] = [f"RSI {last['rsi']:.1f} > {self.cfg.RSI_PULLBACK_SELL_MAX} (rebond trop fort, attendre)"]
                return out

            score = 0.0
            reasons = []

            score += 0.30
            reasons.append(f"Macro 4h strong down (close<EMA50<EMA200)")

            if last['ema_fast'] < last['ema_slow']:
                score += 0.20
                reasons.append(f"EMA21<EMA55 (micro aligne)")
            else:
                reasons.append(f"EMA21>EMA55 (micro divergent)")

            if last['rsi'] < prev['rsi']:
                score += 0.20
                reasons.append(f"RSI={last['rsi']:.1f} redescend (prev {prev['rsi']:.1f})")
            else:
                score += 0.10
                reasons.append(f"RSI={last['rsi']:.1f} encore en hausse")

            distance_pct = (last['close'] - last['ema_fast']) / last['ema_fast'] * 100
            if -0.5 < distance_pct < 1.5:
                score += 0.15
                reasons.append(f"Prix en rebond vers EMA21 ({distance_pct:+.2f}%)")
            elif distance_pct <= -0.5:
                reasons.append(f"Prix deja etire sous EMA21 ({distance_pct:+.2f}%)")
            else:
                score += 0.05
                reasons.append(f"Prix loin au-dessus EMA21 ({distance_pct:+.2f}%)")

            score += 0.15
            reasons.append(f"ADX={last['adx']:.1f} (zone saine)")

            out['signal'] = 'SELL' if score >= self.cfg.MIN_CONFIDENCE else 'HOLD'
            out['confidence'] = round(score, 3)
            out['reasons'] = reasons
            return out

        return out
