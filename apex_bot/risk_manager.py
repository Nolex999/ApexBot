"""APEX BOT - Risk Manager (le plus important du système)"""
from config import Config
from datetime import datetime, timedelta

class RiskManager:
    def __init__(self, initial_capital: float):
        self.cfg = Config
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.open_trades = []
        self.closed_trades = []
        self.daily_pnl = 0.0
        self.weekly_pnl = 0.0
        self.last_reset_day = datetime.now().date()
        self.last_reset_week = datetime.now().isocalendar()[1]
        self.trading_halted = False
    
    def calculate_position_size(self, entry_price: float, stop_price: float) -> float:
        """Calcule la taille de position basée sur le risk % du capital"""
        risk_amount = self.current_capital * self.cfg.RISK_PER_TRADE
        risk_per_unit = abs(entry_price - stop_price)
        if risk_per_unit == 0:
            return 0
        position_size = risk_amount / risk_per_unit
        # Safety cap: jamais plus de 30% du capital sur une seule position
        max_size = (self.current_capital * 0.30) / entry_price
        return min(position_size, max_size)
    
    def can_open_trade(self) -> tuple[bool, str]:
        self._check_resets()
        
        if self.trading_halted:
            return False, "🛑 TRADING HALTED — Circuit breaker activé"
        
        if len(self.open_trades) >= self.cfg.MAX_CONCURRENT_TRADES:
            return False, f"Max trades simultanés atteint ({self.cfg.MAX_CONCURRENT_TRADES})"
        
        # Heat portfolio
        total_risk = sum(t['risk_amount'] for t in self.open_trades)
        heat = total_risk / self.current_capital
        if heat >= self.cfg.MAX_PORTFOLIO_HEAT:
            return False, f"Heat portefeuille max atteint ({heat*100:.1f}%)"
        
        # Daily loss circuit breaker
        if self.daily_pnl <= -self.cfg.MAX_DAILY_LOSS * self.initial_capital:
            self.trading_halted = True
            return False, f"🛑 Perte journalière max atteinte"
        
        # Weekly loss circuit breaker
        if self.weekly_pnl <= -self.cfg.MAX_WEEKLY_LOSS * self.initial_capital:
            self.trading_halted = True
            return False, f"🛑 Perte hebdomadaire max atteinte"
        
        return True, "OK"
    
    def register_trade(self, trade: dict):
        self.open_trades.append(trade)
    
    def close_trade(self, trade: dict, exit_price: float, reason: str):
        if trade['side'] == 'BUY':
            pnl = (exit_price - trade['entry']) * trade['size']
        else:
            pnl = (trade['entry'] - exit_price) * trade['size']
        
        trade['exit'] = exit_price
        trade['pnl'] = pnl
        trade['exit_reason'] = reason
        trade['closed_at'] = datetime.now()
        
        self.current_capital += pnl
        self.daily_pnl += pnl
        self.weekly_pnl += pnl
        
        self.open_trades.remove(trade)
        self.closed_trades.append(trade)
        return trade
    
    def _check_resets(self):
        today = datetime.now().date()
        week = datetime.now().isocalendar()[1]
        if today != self.last_reset_day:
            self.daily_pnl = 0.0
            self.last_reset_day = today
        if week != self.last_reset_week:
            self.weekly_pnl = 0.0
            self.last_reset_week = week
            self.trading_halted = False  # Reset hebdo
    
    def stats(self) -> dict:
        wins = [t for t in self.closed_trades if t['pnl'] > 0]
        losses = [t for t in self.closed_trades if t['pnl'] <= 0]
        win_rate = len(wins) / len(self.closed_trades) if self.closed_trades else 0
        avg_win = sum(t['pnl'] for t in wins) / len(wins) if wins else 0
        avg_loss = sum(t['pnl'] for t in losses) / len(losses) if losses else 0
        return {
            'capital': self.current_capital,
            'total_pnl': self.current_capital - self.initial_capital,
            'roi': (self.current_capital / self.initial_capital - 1) * 100,
            'trades_total': len(self.closed_trades),
            'win_rate': win_rate * 100,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'open_trades': len(self.open_trades)
        }
