"""APEX BOT - Dashboard Web"""
from flask import Flask, jsonify, render_template_string
from datetime import datetime

app = Flask(__name__)

# Shared state — will be set by main.py
bot_state = {
    'status': 'INITIALIZING',
    'cycle': 0,
    'last_signal': None,
    'signals_history': [],
    'risk_manager': None,
    'config': None,
    'started_at': datetime.now().isoformat(),
    'last_update': None,
}

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>APEX Trading Bot — Dashboard</title>
    <meta name="description" content="Dashboard temps réel du bot de trading APEX">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        :root {
            --bg-primary: #0a0e17;
            --bg-secondary: #111827;
            --bg-card: rgba(17, 24, 39, 0.7);
            --bg-card-hover: rgba(31, 41, 55, 0.8);
            --border: rgba(75, 85, 99, 0.3);
            --text-primary: #f9fafb;
            --text-secondary: #9ca3af;
            --text-muted: #6b7280;
            --accent-green: #10b981;
            --accent-green-glow: rgba(16, 185, 129, 0.15);
            --accent-red: #ef4444;
            --accent-red-glow: rgba(239, 68, 68, 0.15);
            --accent-blue: #3b82f6;
            --accent-blue-glow: rgba(59, 130, 246, 0.15);
            --accent-purple: #8b5cf6;
            --accent-purple-glow: rgba(139, 92, 246, 0.15);
            --accent-amber: #f59e0b;
            --accent-amber-glow: rgba(245, 158, 11, 0.15);
        }
        
        body {
            font-family: 'Inter', -apple-system, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            overflow-x: hidden;
        }
        
        body::before {
            content: '';
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: 
                radial-gradient(ellipse at 20% 50%, rgba(59, 130, 246, 0.06) 0%, transparent 50%),
                radial-gradient(ellipse at 80% 20%, rgba(139, 92, 246, 0.06) 0%, transparent 50%),
                radial-gradient(ellipse at 50% 80%, rgba(16, 185, 129, 0.04) 0%, transparent 50%);
            pointer-events: none;
            z-index: 0;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 24px;
            position: relative;
            z-index: 1;
        }
        
        /* Header */
        .header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 32px;
            padding-bottom: 24px;
            border-bottom: 1px solid var(--border);
        }
        .header-left { display: flex; align-items: center; gap: 16px; }
        .logo {
            font-size: 28px;
            font-weight: 900;
            background: linear-gradient(135deg, #3b82f6, #8b5cf6, #10b981);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -0.5px;
        }
        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .status-running {
            background: var(--accent-green-glow);
            color: var(--accent-green);
            border: 1px solid rgba(16, 185, 129, 0.3);
        }
        .status-dot {
            width: 8px; height: 8px;
            border-radius: 50%;
            background: var(--accent-green);
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.5; transform: scale(0.8); }
        }
        .header-right {
            display: flex;
            align-items: center;
            gap: 16px;
            color: var(--text-muted);
            font-size: 13px;
            font-family: 'JetBrains Mono', monospace;
        }
        
        /* Stats Grid */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 28px;
        }
        .stat-card {
            background: var(--bg-card);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 20px 24px;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }
        .stat-card::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 2px;
            border-radius: 16px 16px 0 0;
        }
        .stat-card:hover {
            background: var(--bg-card-hover);
            transform: translateY(-2px);
            border-color: rgba(75, 85, 99, 0.5);
        }
        .stat-card.blue::before { background: linear-gradient(90deg, #3b82f6, #60a5fa); }
        .stat-card.green::before { background: linear-gradient(90deg, #10b981, #34d399); }
        .stat-card.purple::before { background: linear-gradient(90deg, #8b5cf6, #a78bfa); }
        .stat-card.amber::before { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
        .stat-card.red::before { background: linear-gradient(90deg, #ef4444, #f87171); }
        
        .stat-label {
            font-size: 12px;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.8px;
            font-weight: 600;
            margin-bottom: 8px;
        }
        .stat-value {
            font-size: 28px;
            font-weight: 800;
            font-family: 'JetBrains Mono', monospace;
            letter-spacing: -0.5px;
        }
        .stat-sub {
            font-size: 12px;
            color: var(--text-muted);
            margin-top: 4px;
            font-family: 'JetBrains Mono', monospace;
        }
        .positive { color: var(--accent-green); }
        .negative { color: var(--accent-red); }
        
        /* Sections Grid */
        .sections-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 28px;
        }
        @media (max-width: 900px) {
            .sections-grid { grid-template-columns: 1fr; }
        }
        
        .section {
            background: var(--bg-card);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border);
            border-radius: 16px;
            overflow: hidden;
        }
        .section-full {
            grid-column: 1 / -1;
        }
        .section-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 16px 24px;
            border-bottom: 1px solid var(--border);
        }
        .section-title {
            font-size: 14px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            color: var(--text-secondary);
        }
        .section-badge {
            font-size: 11px;
            padding: 3px 10px;
            border-radius: 12px;
            font-weight: 600;
            font-family: 'JetBrains Mono', monospace;
        }
        
        /* Table */
        .table-wrap { overflow-x: auto; }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th {
            text-align: left;
            padding: 10px 20px;
            font-size: 11px;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            background: rgba(0,0,0,0.2);
        }
        td {
            padding: 12px 20px;
            font-size: 13px;
            font-family: 'JetBrains Mono', monospace;
            border-bottom: 1px solid rgba(75, 85, 99, 0.15);
            color: var(--text-secondary);
        }
        tr:hover td {
            background: rgba(255,255,255,0.02);
        }
        .tag {
            display: inline-block;
            padding: 2px 10px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.3px;
        }
        .tag-buy { background: var(--accent-green-glow); color: var(--accent-green); }
        .tag-sell { background: var(--accent-red-glow); color: var(--accent-red); }
        .tag-hold { background: rgba(107,114,128,0.15); color: var(--text-muted); }
        .tag-tp { background: var(--accent-green-glow); color: var(--accent-green); }
        .tag-sl { background: var(--accent-red-glow); color: var(--accent-red); }
        
        /* Signal Card */
        .signal-card {
            padding: 24px;
        }
        .signal-main {
            display: flex;
            align-items: center;
            gap: 20px;
            margin-bottom: 16px;
        }
        .signal-type {
            font-size: 32px;
            font-weight: 900;
            font-family: 'JetBrains Mono', monospace;
        }
        .signal-meta {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 12px;
        }
        .signal-meta-item {
            background: rgba(0,0,0,0.2);
            padding: 10px 14px;
            border-radius: 10px;
        }
        .signal-meta-label {
            font-size: 10px;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 4px;
        }
        .signal-meta-value {
            font-size: 16px;
            font-weight: 700;
            font-family: 'JetBrains Mono', monospace;
        }
        
        /* Config */
        .config-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1px;
            background: var(--border);
        }
        .config-item {
            padding: 12px 20px;
            background: var(--bg-secondary);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .config-key {
            font-size: 12px;
            color: var(--text-muted);
        }
        .config-val {
            font-size: 13px;
            font-family: 'JetBrains Mono', monospace;
            font-weight: 600;
            color: var(--text-primary);
        }
        
        .empty-state {
            padding: 40px;
            text-align: center;
            color: var(--text-muted);
            font-size: 13px;
        }
        
        /* Footer */
        .footer {
            text-align: center;
            padding: 24px;
            color: var(--text-muted);
            font-size: 12px;
            border-top: 1px solid var(--border);
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <div class="header-left">
                <div class="logo">⚡ APEX</div>
                <span class="status-badge status-running" id="statusBadge">
                    <span class="status-dot"></span>
                    <span id="statusText">Loading...</span>
                </span>
            </div>
            <div class="header-right">
                <span id="modeTag">—</span>
                <span>|</span>
                <span id="lastUpdate">—</span>
            </div>
        </div>
        
        <!-- Stats -->
        <div class="stats-grid">
            <div class="stat-card blue">
                <div class="stat-label">Capital</div>
                <div class="stat-value" id="capital">—</div>
                <div class="stat-sub" id="capitalInit">Initial: —</div>
            </div>
            <div class="stat-card" id="pnlCard">
                <div class="stat-label">PnL Total</div>
                <div class="stat-value" id="pnl">—</div>
                <div class="stat-sub" id="roi">ROI: —</div>
            </div>
            <div class="stat-card purple">
                <div class="stat-label">Trades</div>
                <div class="stat-value" id="tradesTotal">—</div>
                <div class="stat-sub" id="openTrades">Open: —</div>
            </div>
            <div class="stat-card amber">
                <div class="stat-label">Win Rate</div>
                <div class="stat-value" id="winRate">—</div>
                <div class="stat-sub" id="avgWinLoss">—</div>
            </div>
            <div class="stat-card blue">
                <div class="stat-label">Cycle</div>
                <div class="stat-value" id="cycle">—</div>
                <div class="stat-sub" id="uptime">—</div>
            </div>
        </div>
        
        <!-- Last Signal + Config -->
        <div class="sections-grid">
            <div class="section">
                <div class="section-header">
                    <span class="section-title">🎯 Dernier Signal</span>
                </div>
                <div class="signal-card" id="signalCard">
                    <div class="empty-state">En attente du premier signal...</div>
                </div>
            </div>
            
            <div class="section">
                <div class="section-header">
                    <span class="section-title">⚙️ Configuration</span>
                </div>
                <div class="config-grid" id="configGrid">
                    <div class="empty-state" style="grid-column: 1/-1;">Chargement...</div>
                </div>
            </div>
        </div>
        
        <!-- Open Trades -->
        <div class="sections-grid">
            <div class="section section-full">
                <div class="section-header">
                    <span class="section-title">📈 Positions Ouvertes</span>
                    <span class="section-badge" id="openCount" style="background:var(--accent-blue-glow);color:var(--accent-blue);">0</span>
                </div>
                <div class="table-wrap">
                    <table>
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Side</th>
                                <th>Symbol</th>
                                <th>Entrée</th>
                                <th>Stop</th>
                                <th>Target</th>
                                <th>Taille</th>
                                <th>Risque</th>
                            </tr>
                        </thead>
                        <tbody id="openTradesBody">
                            <tr><td colspan="8" class="empty-state">Aucune position ouverte</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        
        <!-- Closed Trades -->
        <div class="sections-grid">
            <div class="section section-full">
                <div class="section-header">
                    <span class="section-title">📊 Historique des Trades</span>
                    <span class="section-badge" id="closedCount" style="background:var(--accent-purple-glow);color:var(--accent-purple);">0</span>
                </div>
                <div class="table-wrap">
                    <table>
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Side</th>
                                <th>Entrée</th>
                                <th>Sortie</th>
                                <th>PnL</th>
                                <th>Raison</th>
                                <th>Fermé le</th>
                            </tr>
                        </thead>
                        <tbody id="closedTradesBody">
                            <tr><td colspan="7" class="empty-state">Aucun trade clôturé</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        
        <!-- Signals History -->
        <div class="sections-grid">
            <div class="section section-full">
                <div class="section-header">
                    <span class="section-title">📡 Signaux Récents</span>
                </div>
                <div class="table-wrap">
                    <table>
                        <thead>
                            <tr>
                                <th>Heure</th>
                                <th>Signal</th>
                                <th>Prix</th>
                                <th>RSI</th>
                                <th>ADX</th>
                                <th>Confiance</th>
                            </tr>
                        </thead>
                        <tbody id="signalsBody">
                            <tr><td colspan="6" class="empty-state">En attente des signaux...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        
        <div class="footer">
            APEX Trading Bot — Paper Mode — Auto-refresh 10s
        </div>
    </div>
    
    <script>
        async function fetchData() {
            try {
                const res = await fetch('/api/status');
                const d = await res.json();
                
                // Status
                document.getElementById('statusText').textContent = d.status;
                document.getElementById('modeTag').textContent = d.config ? d.config.mode + ' | ' + d.config.symbol : '—';
                document.getElementById('lastUpdate').textContent = d.last_update || '—';
                document.getElementById('cycle').textContent = d.cycle || '0';
                document.getElementById('uptime').textContent = 'Depuis ' + (d.started_at || '—').slice(0, 19);
                
                // Stats
                if (d.stats) {
                    const s = d.stats;
                    document.getElementById('capital').textContent = '$' + s.capital.toFixed(2);
                    document.getElementById('capitalInit').textContent = 'Initial: $' + (d.config ? d.config.initial_capital : '—');
                    
                    const pnlEl = document.getElementById('pnl');
                    const pnlCard = document.getElementById('pnlCard');
                    pnlEl.textContent = (s.total_pnl >= 0 ? '+$' : '-$') + Math.abs(s.total_pnl).toFixed(2);
                    pnlEl.className = 'stat-value ' + (s.total_pnl >= 0 ? 'positive' : 'negative');
                    pnlCard.className = 'stat-card ' + (s.total_pnl >= 0 ? 'green' : 'red');
                    
                    document.getElementById('roi').textContent = 'ROI: ' + (s.roi >= 0 ? '+' : '') + s.roi.toFixed(2) + '%';
                    document.getElementById('roi').className = 'stat-sub ' + (s.roi >= 0 ? 'positive' : 'negative');
                    
                    document.getElementById('tradesTotal').textContent = s.trades_total;
                    document.getElementById('openTrades').textContent = 'Open: ' + s.open_trades;
                    
                    document.getElementById('winRate').textContent = s.win_rate.toFixed(1) + '%';
                    document.getElementById('avgWinLoss').textContent = 'W: $' + s.avg_win.toFixed(2) + ' | L: $' + s.avg_loss.toFixed(2);
                }
                
                // Last Signal
                if (d.last_signal) {
                    const sig = d.last_signal;
                    const sigType = sig.signal;
                    const color = sigType === 'BUY' ? 'var(--accent-green)' : sigType === 'SELL' ? 'var(--accent-red)' : 'var(--text-muted)';
                    document.getElementById('signalCard').innerHTML = `
                        <div class="signal-main">
                            <div class="signal-type" style="color:${color}">${sigType}</div>
                        </div>
                        <div class="signal-meta">
                            <div class="signal-meta-item">
                                <div class="signal-meta-label">Prix</div>
                                <div class="signal-meta-value">$${(sig.price||0).toFixed(2)}</div>
                            </div>
                            <div class="signal-meta-item">
                                <div class="signal-meta-label">RSI</div>
                                <div class="signal-meta-value">${(sig.rsi||0).toFixed(1)}</div>
                            </div>
                            <div class="signal-meta-item">
                                <div class="signal-meta-label">ADX</div>
                                <div class="signal-meta-value">${(sig.adx||0).toFixed(1)}</div>
                            </div>
                            <div class="signal-meta-item">
                                <div class="signal-meta-label">Confiance</div>
                                <div class="signal-meta-value">${((sig.confidence||0)*100).toFixed(0)}%</div>
                            </div>
                        </div>
                    `;
                }
                
                // Config
                if (d.config) {
                    const c = d.config;
                    const items = [
                        ['Mode', c.mode], ['Exchange', c.exchange], ['Symbol', c.symbol],
                        ['Capital', '$'+c.initial_capital], ['Risk/Trade', (c.risk_per_trade*100)+'%'],
                        ['Max Heat', (c.max_heat*100)+'%'], ['TF Fast', c.tf_fast], ['TF Slow', c.tf_slow],
                        ['R:R Ratio', c.rr_ratio], ['Stop ATR x', c.atr_stop_mult],
                        ['Max Daily Loss', (c.max_daily_loss*100)+'%'], ['Loop', c.loop_interval+'s'],
                    ];
                    document.getElementById('configGrid').innerHTML = items.map(([k,v]) =>
                        `<div class="config-item"><span class="config-key">${k}</span><span class="config-val">${v}</span></div>`
                    ).join('');
                }
                
                // Open Trades
                if (d.open_trades && d.open_trades.length > 0) {
                    document.getElementById('openCount').textContent = d.open_trades.length;
                    document.getElementById('openTradesBody').innerHTML = d.open_trades.map(t => `
                        <tr>
                            <td>${t.id}</td>
                            <td><span class="tag ${t.side==='BUY'?'tag-buy':'tag-sell'}">${t.side}</span></td>
                            <td>${t.symbol}</td>
                            <td>$${t.entry.toFixed(2)}</td>
                            <td>$${t.stop.toFixed(2)}</td>
                            <td>$${t.target.toFixed(2)}</td>
                            <td>${t.size.toFixed(6)}</td>
                            <td>$${t.risk_amount.toFixed(2)}</td>
                        </tr>
                    `).join('');
                } else {
                    document.getElementById('openCount').textContent = '0';
                    document.getElementById('openTradesBody').innerHTML = '<tr><td colspan="8" class="empty-state">Aucune position ouverte</td></tr>';
                }
                
                // Closed Trades
                if (d.closed_trades && d.closed_trades.length > 0) {
                    document.getElementById('closedCount').textContent = d.closed_trades.length;
                    document.getElementById('closedTradesBody').innerHTML = d.closed_trades.slice().reverse().map(t => `
                        <tr>
                            <td>${t.id}</td>
                            <td><span class="tag ${t.side==='BUY'?'tag-buy':'tag-sell'}">${t.side}</span></td>
                            <td>$${t.entry.toFixed(2)}</td>
                            <td>$${(t.exit||0).toFixed(2)}</td>
                            <td class="${t.pnl>=0?'positive':'negative'}">${t.pnl>=0?'+':''}$${(t.pnl||0).toFixed(2)}</td>
                            <td><span class="tag ${t.exit_reason==='TAKE_PROFIT'?'tag-tp':'tag-sl'}">${t.exit_reason||'—'}</span></td>
                            <td>${(t.closed_at||'—').slice(0,19)}</td>
                        </tr>
                    `).join('');
                } else {
                    document.getElementById('closedCount').textContent = '0';
                    document.getElementById('closedTradesBody').innerHTML = '<tr><td colspan="7" class="empty-state">Aucun trade clôturé</td></tr>';
                }
                
                // Signals History
                if (d.signals_history && d.signals_history.length > 0) {
                    document.getElementById('signalsBody').innerHTML = d.signals_history.slice().reverse().slice(0, 50).map(s => `
                        <tr>
                            <td>${(s.time||'—').slice(11,19)}</td>
                            <td><span class="tag ${s.signal==='BUY'?'tag-buy':s.signal==='SELL'?'tag-sell':'tag-hold'}">${s.signal}</span></td>
                            <td>$${(s.price||0).toFixed(2)}</td>
                            <td>${(s.rsi||0).toFixed(1)}</td>
                            <td>${(s.adx||0).toFixed(1)}</td>
                            <td>${((s.confidence||0)*100).toFixed(0)}%</td>
                        </tr>
                    `).join('');
                }
                
            } catch (e) {
                console.error('Fetch error:', e);
            }
        }
        
        fetchData();
        setInterval(fetchData, 10000);
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(DASHBOARD_HTML)

@app.route('/api/status')
def api_status():
    from config import Config
    
    stats = {}
    open_trades = []
    closed_trades = []
    
    rm = bot_state.get('risk_manager')
    if rm:
        stats = rm.stats()
        open_trades = [{
            'id': t['id'],
            'symbol': t['symbol'],
            'side': t['side'],
            'entry': t['entry'],
            'stop': t['stop'],
            'target': t['target'],
            'size': t['size'],
            'risk_amount': t['risk_amount'],
            'opened_at': str(t['opened_at']),
        } for t in rm.open_trades]
        closed_trades = [{
            'id': t['id'],
            'side': t['side'],
            'entry': t['entry'],
            'exit': t.get('exit', 0),
            'pnl': t.get('pnl', 0),
            'exit_reason': t.get('exit_reason', ''),
            'closed_at': str(t.get('closed_at', '')),
        } for t in rm.closed_trades]
    
    return jsonify({
        'status': bot_state['status'],
        'cycle': bot_state['cycle'],
        'started_at': bot_state['started_at'],
        'last_update': bot_state['last_update'],
        'last_signal': bot_state['last_signal'],
        'signals_history': bot_state['signals_history'][-100:],
        'stats': stats,
        'open_trades': open_trades,
        'closed_trades': closed_trades,
        'config': {
            'mode': Config.MODE,
            'exchange': Config.EXCHANGE,
            'symbol': Config.SYMBOL,
            'tf_fast': Config.TIMEFRAME_FAST,
            'tf_slow': Config.TIMEFRAME_SLOW,
            'initial_capital': Config.INITIAL_CAPITAL,
            'risk_per_trade': Config.RISK_PER_TRADE,
            'max_heat': Config.MAX_PORTFOLIO_HEAT,
            'max_daily_loss': Config.MAX_DAILY_LOSS,
            'rr_ratio': Config.RR_RATIO,
            'atr_stop_mult': Config.ATR_STOP_MULTIPLIER,
            'loop_interval': Config.LOOP_INTERVAL,
        }
    })

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'cycle': bot_state['cycle']})
