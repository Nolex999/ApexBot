"""APEX BOT - Dashboard Web (Clean Fintech Design with Login & Theme/Currency)"""
from flask import Flask, jsonify, render_template_string, request, session, redirect, url_for
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'apex_super_secret_key_123'  # Required for sessions

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

LOGIN_HTML = r"""
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>APEX — Login</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', system-ui, sans-serif; background: #0c0d12; color: #e8e9ed; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
        .box { background: #15161e; padding: 40px; border-radius: 12px; border: 1px solid #23252f; width: 100%; max-width: 340px; text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
        .logo { font-size: 24px; font-weight: 700; margin-bottom: 24px; letter-spacing: -0.5px; }
        .logo span { color: #6366f1; margin-right: 2px; }
        input { width: 100%; padding: 12px 14px; margin-bottom: 16px; background: #0c0d12; border: 1px solid #2a2c38; color: white; border-radius: 8px; box-sizing: border-box; font-family: 'Inter'; font-size: 14px; transition: border-color 0.2s; }
        input:focus { outline: none; border-color: #6366f1; }
        button { width: 100%; padding: 12px; background: #6366f1; border: none; color: white; font-weight: 600; border-radius: 8px; cursor: pointer; font-family: 'Inter'; font-size: 14px; transition: background 0.2s; }
        button:hover { background: #4f46e5; }
        .err { color: #ef4444; font-size: 13px; margin-bottom: 16px; background: rgba(239, 68, 68, 0.1); padding: 8px; border-radius: 6px; }
    </style>
</head>
<body>
    <div class="box">
        <div class="logo"><span>A</span>APEX</div>
        {% if error %}<div class="err">{{ error }}</div>{% endif %}
        <form method="POST">
            <input type="text" name="username" placeholder="Identifiant" required autofocus>
            <input type="password" name="password" placeholder="Mot de passe" required>
            <button type="submit">Connexion</button>
        </form>
    </div>
</body>
</html>
"""

DASHBOARD_HTML = r"""
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>APEX — Trading Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        :root{
            --bg:#0c0d12;--bg-raised:#15161e;--bg-hover:#1c1d28;
            --border:#23252f;--border-light:#2a2c38;
            --text:#e8e9ed;--text-2:#9395a1;--text-3:#5f6170;
            --green:#22c55e;--green-dim:#16321f;
            --red:#ef4444;--red-dim:#3b1515;
            --blue:#6366f1;--blue-dim:#1e1b4b;
            --amber:#eab308;--amber-dim:#332e0a;
            --radius:10px;
        }
        :root.light-theme {
            --bg:#f8fafc;--bg-raised:#ffffff;--bg-hover:#f1f5f9;
            --border:#e2e8f0;--border-light:#cbd5e1;
            --text:#0f172a;--text-2:#475569;--text-3:#94a3b8;
            --green:#059669;--green-dim:#d1fae5;
            --red:#dc2626;--red-dim:#fee2e2;
            --blue:#2563eb;--blue-dim:#dbeafe;
            --amber:#d97706;--amber-dim:#fef3c7;
        }
        body{font-family:'Inter',system-ui,sans-serif;background:var(--bg);color:var(--text);min-height:100vh;-webkit-font-smoothing:antialiased;transition:background 0.3s, color 0.3s;}

        .wrap{max-width:1320px;margin:0 auto;padding:20px 24px}

        /* ── Header ── */
        .hdr{display:flex;align-items:center;justify-content:space-between;padding:12px 0 20px;border-bottom:1px solid var(--border);margin-bottom:24px}
        .hdr-left{display:flex;align-items:center;gap:14px}
        .logo{font-size:18px;font-weight:700;letter-spacing:-.3px;color:var(--text)}
        .logo span{color:var(--blue);margin-right:2px}
        .pill{display:inline-flex;align-items:center;gap:6px;padding:4px 12px;border-radius:20px;font-size:11px;font-weight:600}
        .pill-live{background:var(--green-dim);color:var(--green);border:1px solid var(--green-dim)}
        .pill-err{background:var(--red-dim);color:var(--red);border:1px solid var(--red-dim)}
        .pill-init{background:var(--blue-dim);color:var(--blue);border:1px solid var(--blue-dim)}
        .dot{width:6px;height:6px;border-radius:50%;background:currentColor;animation:blink 2s infinite}
        @keyframes blink{0%,100%{opacity:1}50%{opacity:.35}}
        
        .hdr-right{display:flex;align-items:center;gap:16px;font-size:12px;color:var(--text-3)}
        .hdr-right b{color:var(--text-2);font-weight:500}
        .btn-icon { background: var(--bg-raised); border: 1px solid var(--border); color: var(--text); padding: 4px 8px; border-radius: 6px; cursor: pointer; font-size: 13px; transition: 0.2s; text-decoration: none;}
        .btn-icon:hover { background: var(--bg-hover); }

        /* ── Metric Cards ── */
        .metrics{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-bottom:20px}
        @media(max-width:900px){.metrics{grid-template-columns:repeat(2,1fr)}}
        @media(max-width:520px){.metrics{grid-template-columns:1fr}}
        .m-card{background:var(--bg-raised);border:1px solid var(--border);border-radius:var(--radius);padding:16px 20px;transition:border-color .2s}
        .m-card:hover{border-color:var(--border-light)}
        .m-label{font-size:11px;color:var(--text-3);font-weight:600;text-transform:uppercase;letter-spacing:.6px;margin-bottom:6px}
        .m-val{font-size:24px;font-weight:700;letter-spacing:-.5px;line-height:1.1}
        .m-sub{font-size:11px;color:var(--text-3);margin-top:4px}
        .up{color:var(--green)}.dn{color:var(--red)}

        /* ── Equity Chart ── */
        .chart-box{background:var(--bg-raised);border:1px solid var(--border);border-radius:var(--radius);margin-bottom:20px;padding:16px 20px 12px}
        .chart-title{font-size:12px;font-weight:600;color:var(--text-2);margin-bottom:12px;text-transform:uppercase;letter-spacing:.5px}
        canvas{width:100%;height:140px;display:block}

        /* ── Grid ── */
        .grid-2{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:20px}
        @media(max-width:800px){.grid-2{grid-template-columns:1fr}}
        .full{grid-column:1/-1}

        /* ── Section ── */
        .sec{background:var(--bg-raised);border:1px solid var(--border);border-radius:var(--radius);overflow:hidden}
        .sec-hdr{display:flex;align-items:center;justify-content:space-between;padding:14px 20px;border-bottom:1px solid var(--border)}
        .sec-t{font-size:12px;font-weight:600;color:var(--text-2);text-transform:uppercase;letter-spacing:.5px}
        .badge{font-size:11px;padding:2px 8px;border-radius:6px;font-weight:600;background:var(--blue-dim);color:var(--blue)}

        /* ── Tables ── */
        .tw{overflow-x:auto}
        table{width:100%;border-collapse:collapse}
        th{text-align:left;padding:8px 20px;font-size:10px;font-weight:600;color:var(--text-3);text-transform:uppercase;letter-spacing:.5px;background:rgba(0,0,0,.05)}
        td{padding:10px 20px;font-size:12px;color:var(--text-2);border-bottom:1px solid var(--border)}
        tr:last-child td{border-bottom:none}
        tr:hover td{background:rgba(128,128,128,.05)}
        .tag{display:inline-block;padding:2px 8px;border-radius:4px;font-size:10px;font-weight:700;letter-spacing:.3px}
        .t-buy{background:var(--green-dim);color:var(--green)}
        .t-sell{background:var(--red-dim);color:var(--red)}
        .t-hold{background:var(--border);color:var(--text-3)}
        .t-tp{background:var(--green-dim);color:var(--green)}
        .t-sl{background:var(--red-dim);color:var(--red)}

        /* ── Signal Card ── */
        .sig-body{padding:20px}
        .sig-row{display:flex;align-items:center;gap:16px;margin-bottom:14px}
        .sig-type{font-size:22px;font-weight:700}
        .sig-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(100px,1fr));gap:8px}
        .sg-item{background:rgba(128,128,128,.08);padding:10px 12px;border-radius:8px}
        .sg-label{font-size:9px;color:var(--text-3);text-transform:uppercase;letter-spacing:.5px;margin-bottom:3px}
        .sg-val{font-size:14px;font-weight:600}

        /* ── Config ── */
        .cfg-grid{display:grid;grid-template-columns:1fr 1fr}
        .cfg-row{padding:10px 20px;display:flex;justify-content:space-between;border-bottom:1px solid var(--border)}
        .cfg-row:last-child,.cfg-row:nth-last-child(2){border-bottom:none}
        .cfg-k{font-size:11px;color:var(--text-3)}
        .cfg-v{font-size:12px;font-weight:600;color:var(--text)}

        .empty{padding:32px;text-align:center;color:var(--text-3);font-size:12px}

        .foot{text-align:center;padding:20px;color:var(--text-3);font-size:11px;border-top:1px solid var(--border);margin-top:16px}
    </style>
</head>
<body>
<div class="wrap">
    <!-- Header -->
    <div class="hdr">
        <div class="hdr-left">
            <div class="logo"><span>A</span>APEX</div>
            <div class="pill pill-init" id="statusPill"><span class="dot"></span><span id="statusText">Initializing</span></div>
        </div>
        <div class="hdr-right">
            <button id="currencyToggle" class="btn-icon" title="Toggle Currency">€</button>
            <button id="themeToggle" class="btn-icon" title="Toggle Theme">☀️</button>
            <span><b id="modeTag">—</b></span>
            <span id="lastUpdate">—</span>
            <a href="/logout" class="btn-icon">Logout</a>
        </div>
    </div>

    <!-- Metrics -->
    <div class="metrics">
        <div class="m-card"><div class="m-label">Capital</div><div class="m-val" id="capital">—</div><div class="m-sub" id="capitalInit">Initial: —</div></div>
        <div class="m-card"><div class="m-label">PnL Total</div><div class="m-val" id="pnl">—</div><div class="m-sub" id="roi">ROI: —</div></div>
        <div class="m-card"><div class="m-label">Trades</div><div class="m-val" id="tradesTotal">—</div><div class="m-sub" id="openTrades">Open: —</div></div>
        <div class="m-card"><div class="m-label">Win Rate</div><div class="m-val" id="winRate">—</div><div class="m-sub" id="avgWinLoss">—</div></div>
        <div class="m-card"><div class="m-label">Cycle</div><div class="m-val" id="cycle">—</div><div class="m-sub" id="uptime">—</div></div>
    </div>

    <!-- Equity Curve -->
    <div class="chart-box">
        <div class="chart-title">Equity Curve</div>
        <canvas id="equityCanvas" height="140"></canvas>
    </div>

    <!-- Signal + Config -->
    <div class="grid-2">
        <div class="sec">
            <div class="sec-hdr"><span class="sec-t">Last Signal</span></div>
            <div class="sig-body" id="signalCard"><div class="empty">Waiting for first signal…</div></div>
        </div>
        <div class="sec">
            <div class="sec-hdr"><span class="sec-t">Configuration</span></div>
            <div class="cfg-grid" id="configGrid"><div class="empty" style="grid-column:1/-1">Loading…</div></div>
        </div>
    </div>

    <!-- Open Positions -->
    <div class="grid-2" style="margin-bottom:20px">
        <div class="sec full">
            <div class="sec-hdr"><span class="sec-t">Open Positions</span><span class="badge" id="openCount">0</span></div>
            <div class="tw"><table><thead><tr><th>ID</th><th>Side</th><th>Symbol</th><th>Entry</th><th>Stop</th><th>Target</th><th>Size</th><th>Risk</th></tr></thead><tbody id="openTradesBody"><tr><td colspan="8" class="empty">No open positions</td></tr></tbody></table></div>
        </div>
    </div>

    <!-- Trade History -->
    <div class="grid-2" style="margin-bottom:20px">
        <div class="sec full">
            <div class="sec-hdr"><span class="sec-t">Trade History</span><span class="badge" id="closedCount">0</span></div>
            <div class="tw"><table><thead><tr><th>ID</th><th>Side</th><th>Entry</th><th>Exit</th><th>PnL</th><th>Result</th><th>Closed</th></tr></thead><tbody id="closedTradesBody"><tr><td colspan="7" class="empty">No closed trades</td></tr></tbody></table></div>
        </div>
    </div>

    <!-- Recent Signals -->
    <div class="grid-2">
        <div class="sec full">
            <div class="sec-hdr"><span class="sec-t">Recent Signals</span></div>
            <div class="tw"><table><thead><tr><th>Time</th><th>Signal</th><th>Price</th><th>RSI</th><th>ADX</th><th>Confidence</th></tr></thead><tbody id="signalsBody"><tr><td colspan="6" class="empty">Waiting for signals…</td></tr></tbody></table></div>
        </div>
    </div>

    <div class="foot">APEX Trading Bot &middot; Auto-refresh 10s</div>
</div>

<script>
// Format Utils
function formatTime(isoString) {
    if (!isoString || isoString === '—') return '—';
    const dt = new Date(isoString.endsWith('Z') ? isoString : isoString + 'Z');
    return dt.toLocaleTimeString('fr-FR', { timeZone: 'Europe/Paris', hour: '2-digit', minute: '2-digit', second: '2-digit' });
}
function formatDate(isoString) {
    if (!isoString || isoString === '—') return '—';
    const dt = new Date(isoString.endsWith('Z') ? isoString : isoString + 'Z');
    return dt.toLocaleDateString('fr-FR', { timeZone: 'Europe/Paris', year: 'numeric', month: '2-digit', day: '2-digit' });
}

// State toggles
let isLight = localStorage.getItem('apex_theme') === 'light';
let isEuro = localStorage.getItem('apex_currency') === 'EUR';
const EUR_RATE = 0.92; // Fixed exchange rate for display

// Initialize Theme
if (isLight) document.documentElement.classList.add('light-theme');
document.getElementById('themeToggle').textContent = isLight ? '🌙' : '☀️';
document.getElementById('currencyToggle').textContent = isEuro ? '$' : '€';

document.getElementById('themeToggle').addEventListener('click', () => {
    isLight = !isLight;
    if (isLight) {
        document.documentElement.classList.add('light-theme');
        localStorage.setItem('apex_theme', 'light');
    } else {
        document.documentElement.classList.remove('light-theme');
        localStorage.setItem('apex_theme', 'dark');
    }
    document.getElementById('themeToggle').textContent = isLight ? '🌙' : '☀️';
    if (equityData.length) drawEquity(equityData); // Redraw chart with new colors
});

let lastFetchedData = null;
document.getElementById('currencyToggle').addEventListener('click', () => {
    isEuro = !isEuro;
    localStorage.setItem('apex_currency', isEuro ? 'EUR' : 'USD');
    document.getElementById('currencyToggle').textContent = isEuro ? '$' : '€';
    if (lastFetchedData) renderData(lastFetchedData);
});

function formatMoney(value) {
    if (typeof value !== 'number') return '—';
    if (isEuro) {
        return '€' + (value * EUR_RATE).toFixed(2);
    }
    return '$' + value.toFixed(2);
}

let equityData = [];

function drawEquity(data) {
    const c = document.getElementById('equityCanvas');
    const ctx = c.getContext('2d');
    c.width = c.clientWidth * 2;
    c.height = 280;
    ctx.scale(2, 2);
    const W = c.clientWidth, H = 140;
    ctx.clearRect(0, 0, W, H);
    
    // Get colors from CSS vars
    const style = getComputedStyle(document.body);
    const gridColor = style.getPropertyValue('--border').trim() || '#23252f';
    const textColor = style.getPropertyValue('--text-3').trim() || '#5f6170';

    if (data.length < 2) {
        ctx.fillStyle = textColor;
        ctx.font = '12px Inter, system-ui';
        ctx.textAlign = 'center';
        ctx.fillText('Not enough data', W/2, H/2);
        return;
    }
    const min = Math.min(...data) * 0.999;
    const max = Math.max(...data) * 1.001;
    const range = max - min || 1;
    const px = (i) => (i / (data.length - 1)) * (W - 40) + 20;
    const py = (v) => H - 16 - ((v - min) / range) * (H - 32);

    // Grid lines
    ctx.strokeStyle = gridColor;
    ctx.lineWidth = 0.5;
    for (let i = 0; i < 4; i++) {
        const y = 16 + i * ((H - 32) / 3);
        ctx.beginPath(); ctx.moveTo(20, y); ctx.lineTo(W - 20, y); ctx.stroke();
        const val = max - (i / 3) * range;
        ctx.fillStyle = textColor;
        ctx.font = '9px Inter';
        ctx.textAlign = 'right';
        ctx.fillText(formatMoney(val).replace('.00', ''), W - 4, y + 3);
    }

    // Fill
    const lastVal = data[data.length - 1];
    const firstVal = data[0];
    const isUp = lastVal >= firstVal;
    
    const colorUp = style.getPropertyValue('--green').trim() || '#22c55e';
    const colorDn = style.getPropertyValue('--red').trim() || '#ef4444';
    const color = isUp ? colorUp : colorDn;
    
    // Create subtle gradient fill
    const fillStyle = isUp ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)';
    if (isLight) {
        ctx.fillStyle = isUp ? 'rgba(5,150,105,0.08)' : 'rgba(220,38,38,0.08)';
    } else {
        ctx.fillStyle = fillStyle;
    }

    ctx.beginPath();
    ctx.moveTo(px(0), py(data[0]));
    for (let i = 1; i < data.length; i++) ctx.lineTo(px(i), py(data[i]));
    ctx.lineTo(px(data.length - 1), H - 16);
    ctx.lineTo(px(0), H - 16);
    ctx.closePath();
    ctx.fill();

    // Line
    ctx.beginPath();
    ctx.moveTo(px(0), py(data[0]));
    for (let i = 1; i < data.length; i++) ctx.lineTo(px(i), py(data[i]));
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // Last point
    ctx.beginPath();
    ctx.arc(px(data.length - 1), py(lastVal), 3, 0, Math.PI * 2);
    ctx.fillStyle = color;
    ctx.fill();
}

function renderData(d) {
    // Status
    const pill = document.getElementById('statusPill');
    const st = (d.status || '').toUpperCase();
    document.getElementById('statusText').textContent = d.status;
    pill.className = 'pill ' + (st === 'RUNNING' ? 'pill-live' : st.includes('ERROR') || st.includes('BAN') ? 'pill-err' : 'pill-init');
    document.getElementById('modeTag').textContent = d.config ? d.config.mode + ' · ' + d.config.symbol : '—';
    document.getElementById('lastUpdate').textContent = d.last_update ? formatTime(d.last_update) : '—';
    document.getElementById('cycle').textContent = d.cycle || '0';
    document.getElementById('uptime').textContent = 'Since ' + (d.started_at ? formatDate(d.started_at) : '—');

    // Stats
    if (d.stats) {
        const s = d.stats;
        document.getElementById('capital').textContent = formatMoney(s.capital);
        document.getElementById('capitalInit').textContent = 'Initial: ' + (d.config ? formatMoney(d.config.initial_capital) : '—');
        
        const pE = document.getElementById('pnl');
        pE.textContent = (s.total_pnl >= 0 ? '+' : '') + formatMoney(Math.abs(s.total_pnl));
        pE.className = 'm-val ' + (s.total_pnl >= 0 ? 'up' : 'dn');
        
        const rE = document.getElementById('roi');
        rE.textContent = 'ROI: ' + (s.roi >= 0 ? '+' : '') + s.roi.toFixed(2) + '%';
        rE.className = 'm-sub ' + (s.roi >= 0 ? 'up' : 'dn');
        
        document.getElementById('tradesTotal').textContent = s.trades_total;
        document.getElementById('openTrades').textContent = 'Open: ' + s.open_trades;
        document.getElementById('winRate').textContent = s.win_rate.toFixed(1) + '%';
        document.getElementById('avgWinLoss').textContent = 'W: ' + formatMoney(s.avg_win) + ' · L: ' + formatMoney(s.avg_loss);

        // Equity
        equityData = [];
        if (s.capital) {
            equityData.push(d.config ? d.config.initial_capital : s.capital);
            equityData.push(s.capital);
        }
        drawEquity(equityData);
    }

    // Signal
    if (d.last_signal) {
        const sig = d.last_signal;
        const st = sig.signal;
        const cl = st === 'BUY' ? 'up' : st === 'SELL' ? 'dn' : '';
        document.getElementById('signalCard').innerHTML = `
            <div class="sig-row">
                <div class="sig-type ${cl}">${st}</div>
                <div class="tag ${st==='BUY'?'t-buy':st==='SELL'?'t-sell':'t-hold'}">${((sig.confidence||0)*100).toFixed(0)}% confidence</div>
            </div>
            <div class="sig-grid">
                <div class="sg-item"><div class="sg-label">Price</div><div class="sg-val">${formatMoney(sig.price||0)}</div></div>
                <div class="sg-item"><div class="sg-label">RSI</div><div class="sg-val">${(sig.rsi||0).toFixed(1)}</div></div>
                <div class="sg-item"><div class="sg-label">ADX</div><div class="sg-val">${(sig.adx||0).toFixed(1)}</div></div>
                <div class="sg-item"><div class="sg-label">ATR</div><div class="sg-val">${formatMoney(sig.atr||0)}</div></div>
            </div>`;
    }

    // Config
    if (d.config) {
        const c = d.config;
        const items = [
            ['Mode', c.mode], ['Exchange', c.exchange], ['Symbol', c.symbol], ['Capital', formatMoney(c.initial_capital)],
            ['Risk/Trade', (c.risk_per_trade*100)+'%'], ['Max Heat', (c.max_heat*100)+'%'],
            ['TF Fast', c.tf_fast], ['TF Slow', c.tf_slow],
            ['R:R', c.rr_ratio], ['Stop ATR ×', c.atr_stop_mult],
            ['Max Daily Loss', (c.max_daily_loss*100)+'%'], ['Loop', c.loop_interval+'s'],
        ];
        document.getElementById('configGrid').innerHTML = items.map(([k,v]) =>
            `<div class="cfg-row"><span class="cfg-k">${k}</span><span class="cfg-v">${v}</span></div>`
        ).join('');
    }

    // Open Trades
    if (d.open_trades && d.open_trades.length > 0) {
        document.getElementById('openCount').textContent = d.open_trades.length;
        document.getElementById('openTradesBody').innerHTML = d.open_trades.map(t => `
            <tr>
                <td>${t.id}</td>
                <td><span class="tag ${t.side==='BUY'?'t-buy':'t-sell'}">${t.side}</span></td>
                <td>${t.symbol}</td>
                <td>${formatMoney(t.entry)}</td>
                <td>${formatMoney(t.stop)}</td>
                <td>${formatMoney(t.target)}</td>
                <td>${t.size.toFixed(6)}</td>
                <td>${formatMoney(t.risk_amount)}</td>
            </tr>`).join('');
    } else {
        document.getElementById('openCount').textContent = '0';
        document.getElementById('openTradesBody').innerHTML = '<tr><td colspan="8" class="empty">No open positions</td></tr>';
    }

    // Closed Trades
    if (d.closed_trades && d.closed_trades.length > 0) {
        document.getElementById('closedCount').textContent = d.closed_trades.length;
        document.getElementById('closedTradesBody').innerHTML = d.closed_trades.slice().reverse().map(t => `
            <tr>
                <td>${t.id}</td>
                <td><span class="tag ${t.side==='BUY'?'t-buy':'t-sell'}">${t.side}</span></td>
                <td>${formatMoney(t.entry)}</td>
                <td>${formatMoney(t.exit||0)}</td>
                <td class="${t.pnl>=0?'up':'dn'}">${t.pnl>=0?'+':''}${formatMoney(Math.abs(t.pnl||0))}</td>
                <td><span class="tag ${t.exit_reason==='TAKE_PROFIT'?'t-tp':'t-sl'}">${t.exit_reason||'—'}</span></td>
                <td>${t.closed_at ? formatDate(t.closed_at) + ' ' + formatTime(t.closed_at) : '—'}</td>
            </tr>`).join('');
    } else {
        document.getElementById('closedCount').textContent = '0';
        document.getElementById('closedTradesBody').innerHTML = '<tr><td colspan="7" class="empty">No closed trades</td></tr>';
    }

    // Signals
    if (d.signals_history && d.signals_history.length > 0) {
        document.getElementById('signalsBody').innerHTML = d.signals_history.slice().reverse().slice(0, 50).map(s => `
            <tr>
                <td>${formatTime(s.time)}</td>
                <td><span class="tag ${s.signal==='BUY'?'t-buy':s.signal==='SELL'?'t-sell':'t-hold'}">${s.signal}</span></td>
                <td>${formatMoney(s.price||0)}</td>
                <td>${(s.rsi||0).toFixed(1)}</td>
                <td>${(s.adx||0).toFixed(1)}</td>
                <td>${((s.confidence||0)*100).toFixed(0)}%</td>
            </tr>`).join('');
    }
}

async function fetchData() {
    try {
        const res = await fetch('/api/status');
        if (res.status === 401) {
            window.location.href = '/login';
            return;
        }
        const d = await res.json();
        lastFetchedData = d;
        renderData(d);
    } catch (e) { console.error('Fetch error:', e); }
}

fetchData();
setInterval(fetchData, 10000);
window.addEventListener('resize', () => { if (equityData.length) drawEquity(equityData); });
</script>
</body>
</html>
"""

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        # Simple hardcoded credentials as requested
        if request.form.get('username') == 'nolex' and request.form.get('password') == 'apexbot':
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            error = 'Identifiants ou mot de passe incorrects.'
    return render_template_string(LOGIN_HTML, error=error)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template_string(DASHBOARD_HTML)

@app.route('/api/status')
def api_status():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
        
    from config import Config

    stats = {}
    open_trades = []
    closed_trades = []

    rm = bot_state.get('risk_manager')
    if rm:
        stats = rm.stats()
        open_trades = [{
            'id': t['id'], 'symbol': t['symbol'], 'side': t['side'],
            'entry': t['entry'], 'stop': t['stop'], 'target': t['target'],
            'size': t['size'], 'risk_amount': t['risk_amount'],
            'opened_at': str(t['opened_at']),
        } for t in rm.open_trades]
        closed_trades = [{
            'id': t['id'], 'side': t['side'], 'entry': t['entry'],
            'exit': t.get('exit', 0), 'pnl': t.get('pnl', 0),
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
