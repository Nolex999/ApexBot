"""APEX BOT - Logger institutionnel"""
from colorama import Fore, Style, init
from datetime import datetime
import json
import os

init(autoreset=True)

class ApexLogger:
    def __init__(self, log_file="apex_journal.json"):
        self.log_file = log_file
        if not os.path.exists(log_file):
            with open(log_file, 'w') as f:
                json.dump([], f)
    
    def _ts(self):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def info(self, msg):
        print(f"{Fore.CYAN}[{self._ts()}] ℹ️  {msg}")
    
    def warn(self, msg):
        print(f"{Fore.YELLOW}[{self._ts()}] ⚠️  {msg}")
    
    def error(self, msg):
        print(f"{Fore.RED}[{self._ts()}] ❌ {msg}")
    
    def success(self, msg):
        print(f"{Fore.GREEN}[{self._ts()}] ✅ {msg}")
    
    def signal(self, sig: dict):
        color = Fore.GREEN if sig['signal'] == "BUY" else (Fore.RED if sig['signal'] == "SELL" else Fore.WHITE)
        print(f"{color}[{self._ts()}] 🎯 SIGNAL: {sig['signal']} | Price: {sig['price']:.2f} | RSI: {sig.get('rsi', 0):.1f} | ADX: {sig.get('adx', 0):.1f}")
    
    def trade_opened(self, t, reasons):
        print(f"{Fore.MAGENTA}[{self._ts()}] 🚀 TRADE OUVERT [{t['mode']}]")
        print(f"   ID: {t['id']} | {t['side']} {t['symbol']}")
        print(f"   Entry: {t['entry']:.2f} | Stop: {t['stop']:.2f} | Target: {t['target']:.2f}")
        print(f"   Size: {t['size']:.6f} | Risk: ${t['risk_amount']:.2f}")
        for r in reasons:
            print(f"   • {r}")
        self._persist({**t, 'event': 'OPEN', 'opened_at': str(t['opened_at'])})
    
    def trade_closed(self, t):
        color = Fore.GREEN if t['pnl'] > 0 else Fore.RED
        print(f"{color}[{self._ts()}] 🏁 TRADE FERMÉ — {t['exit_reason']}")
        print(f"   PnL: ${t['pnl']:.2f} | Exit: {t['exit']:.2f}")
        self._persist({**t, 'event': 'CLOSE', 'opened_at': str(t['opened_at']), 'closed_at': str(t['closed_at'])})
    
    def stats(self, s):
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"{Fore.CYAN}📊 APEX STATS")
        print(f"{Fore.CYAN}{'='*60}")
        print(f"   Capital:    ${s['capital']:.2f}")
        print(f"   PnL Total:  ${s['total_pnl']:.2f} ({s['roi']:+.2f}%)")
        print(f"   Trades:     {s['trades_total']} | Win Rate: {s['win_rate']:.1f}%")
        print(f"   Avg Win:    ${s['avg_win']:.2f} | Avg Loss: ${s['avg_loss']:.2f}")
        print(f"   Open:       {s['open_trades']}")
        print(f"{Fore.CYAN}{'='*60}\n")
    
    def _persist(self, data):
        try:
            with open(self.log_file, 'r') as f:
                logs = json.load(f)
            logs.append(data)
            with open(self.log_file, 'w') as f:
                json.dump(logs, f, indent=2, default=str)
        except Exception as e:
            self.error(f"Persist error: {e}")
