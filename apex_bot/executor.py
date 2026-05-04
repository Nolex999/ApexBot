"""APEX BOT - Order Executor"""
from config import Config
from datetime import datetime

class Executor:
    def __init__(self, data_handler, risk_manager, logger):
        self.dh = data_handler
        self.rm = risk_manager
        self.log = logger
        self.cfg = Config
    
    def open_position(self, signal: dict) -> dict:
        side = signal['signal']
        entry = signal['price']
        atr = signal['atr']
        
        # Stop & target dynamiques (ATR-based)
        if side == "BUY":
            stop = entry - (atr * self.cfg.ATR_STOP_MULTIPLIER)
            target = entry + (atr * self.cfg.ATR_STOP_MULTIPLIER * self.cfg.RR_RATIO)
        else:
            stop = entry + (atr * self.cfg.ATR_STOP_MULTIPLIER)
            target = entry - (atr * self.cfg.ATR_STOP_MULTIPLIER * self.cfg.RR_RATIO)
        
        size = self.rm.calculate_position_size(entry, stop)
        if size <= 0:
            self.log.warn("Taille de position nulle — trade annulé")
            return None
        
        risk_amount = abs(entry - stop) * size
        
        trade = {
            'id': datetime.now().strftime("%Y%m%d%H%M%S"),
            'symbol': self.cfg.SYMBOL,
            'side': side,
            'entry': entry,
            'stop': stop,
            'target': target,
            'size': size,
            'risk_amount': risk_amount,
            'opened_at': datetime.now(),
            'mode': self.cfg.MODE
        }
        
        if self.cfg.MODE == "LIVE":
            # ICI : implémenter ordre réel via ccxt
            # order = self.dh.exchange.create_market_order(...)
            self.log.warn("LIVE mode pas activé dans cette version — passe en PAPER")
        
        self.rm.register_trade(trade)
        self.log.trade_opened(trade, signal['reasons'])
        return trade
    
    def check_exits(self, current_price: float):
        for trade in list(self.rm.open_trades):
            if trade['side'] == "BUY":
                if current_price <= trade['stop']:
                    self.rm.close_trade(trade, current_price, "STOP_LOSS")
                    self.log.trade_closed(trade)
                elif current_price >= trade['target']:
                    self.rm.close_trade(trade, current_price, "TAKE_PROFIT")
                    self.log.trade_closed(trade)
            else:
                if current_price >= trade['stop']:
                    self.rm.close_trade(trade, current_price, "STOP_LOSS")
                    self.log.trade_closed(trade)
                elif current_price <= trade['target']:
                    self.rm.close_trade(trade, current_price, "TAKE_PROFIT")
                    self.log.trade_closed(trade)
