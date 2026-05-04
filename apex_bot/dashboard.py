"""APEX BOT - Dashboard Web (Clean Fintech Design with Login & Theme/Currency)"""

from flask import (
    Flask,
    jsonify,
    render_template_string,
    request,
    session,
    redirect,
    url_for,
)
from datetime import datetime
from api_routes import register_routes

app = Flask(__name__)
app.secret_key = "apex_super_secret_key_123"  # Required for sessions

# Shared state between Bot and Dashboard
bot_state = {
    "status": "INITIALIZING",
    "cycle": 0,
    "last_signal": None,
    "signals_history": [],
    "risk_manager": None,
    "data_handler": None,
    "config": None,
    "started_at": datetime.now().isoformat(),
    "last_update": None,
}

# Initializing Extended Features
register_routes(app, bot_state)

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
    <title>APEX — Premium Trading Terminal</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #090a0f; --bg-card: #12141c; --bg-hover: #1a1d29;
            --border: #222632; --border-focus: #4f46e5;
            --text: #ffffff; --text-dim: #94a3b8; --text-muted: #64748b;
            --accent: #6366f1; --accent-dim: rgba(99, 102, 241, 0.1);
            --success: #10b981; --success-dim: rgba(16, 185, 129, 0.1);
            --danger: #ef4444; --danger-dim: rgba(239, 68, 68, 0.1);
            --warning: #f59e0b; --warning-dim: rgba(245, 158, 11, 0.1);
            --radius: 12px;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Plus Jakarta Sans', sans-serif; background: var(--bg); color: var(--text); overflow-x: hidden; }
        .app-container { display: flex; flex-direction: column; min-height: 100vh; max-width: 1600px; margin: 0 auto; }
        
        /* Sidebar/Header Tabs */
        header { display: flex; align-items: center; justify-content: space-between; padding: 1.5rem 2rem; border-bottom: 1px solid var(--border); background: var(--bg); position: sticky; top: 0; z-index: 100; }
        .brand { display: flex; align-items: center; gap: 0.75rem; font-weight: 700; font-size: 1.5rem; letter-spacing: -1px; }
        .brand span { color: var(--accent); }
        
        .nav-tabs { display: flex; gap: 0.5rem; background: var(--bg-card); padding: 0.35rem; border-radius: 10px; border: 1px solid var(--border); }
        .tab-btn { padding: 0.6rem 1.2rem; border-radius: 8px; border: none; background: transparent; color: var(--text-dim); font-weight: 600; font-size: 0.85rem; cursor: pointer; transition: 0.2s; display: flex; align-items: center; gap: 0.5rem; }
        .tab-btn:hover { color: var(--text); background: var(--bg-hover); }
        .tab-btn.active { background: var(--accent); color: white; box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3); }

        .header-actions { display: flex; gap: 1rem; align-items: center; }
        .status-badge { display: flex; align-items: center; gap: 0.5rem; padding: 0.4rem 1rem; border-radius: 20px; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; background: var(--accent-dim); color: var(--accent); border: 1px solid var(--accent-dim); }
        .status-badge.live { background: var(--success-dim); color: var(--success); border-color: var(--success-dim); }
        .status-badge.error { background: var(--danger-dim); color: var(--danger); border-color: var(--danger-dim); }
        .dot { width: 8px; height: 8px; border-radius: 50%; background: currentColor; animation: pulse 2s infinite; }
        @keyframes pulse { 0% { transform: scale(0.9); opacity: 0.8; } 50% { transform: scale(1.1); opacity: 1; } 100% { transform: scale(0.9); opacity: 0.8; } }

        /* Main Content */
        main { padding: 2rem; flex: 1; }
        .tab-content { display: none; animation: fadeIn 0.3s ease; }
        .tab-content.active { display: block; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

        /* Grid System */
        .grid { display: grid; grid-template-columns: repeat(12, 1fr); gap: 1.5rem; }
        .col-3 { grid-column: span 3; } .col-4 { grid-column: span 4; } .col-6 { grid-column: span 6; } .col-8 { grid-column: span 8; } .col-9 { grid-column: span 9; } .col-12 { grid-column: span 12; }

        /* Components */
        .card { background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius); padding: 1.5rem; position: relative; transition: 0.2s; }
        .card:hover { border-color: var(--border-focus); }
        .card-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.25rem; }
        .card-title { font-size: 0.85rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; }
        
        .metric-val { font-size: 2rem; font-weight: 700; margin-bottom: 0.5rem; }
        .metric-sub { font-size: 0.8rem; color: var(--text-muted); }
        .up { color: var(--success); } .dn { color: var(--danger); }

        /* Forms & Inputs */
        .form-group { margin-bottom: 1.5rem; }
        label { display: block; font-size: 0.85rem; font-weight: 600; color: var(--text-dim); margin-bottom: 0.5rem; }
        input, select, textarea { width: 100%; background: var(--bg); border: 1px solid var(--border); border-radius: 8px; padding: 0.75rem 1rem; color: white; font-family: inherit; font-size: 0.9rem; transition: 0.2s; }
        input:focus { outline: none; border-color: var(--accent); box-shadow: 0 0 0 2px var(--accent-dim); }
        
        .btn { padding: 0.75rem 1.5rem; border-radius: 8px; font-weight: 600; cursor: pointer; transition: 0.2s; border: none; display: inline-flex; align-items: center; justify-content: center; gap: 0.5rem; font-size: 0.9rem; }
        .btn-primary { background: var(--accent); color: white; } .btn-primary:hover { background: #4f46e5; }
        .btn-danger { background: var(--danger-dim); color: var(--danger); } .btn-danger:hover { background: var(--danger); color: white; }
        .btn-success { background: var(--success-dim); color: var(--success); } .btn-success:hover { background: var(--success); color: white; }
        .btn-outline { background: transparent; border: 1px solid var(--border); color: var(--text); } .btn-outline:hover { background: var(--bg-hover); }

        /* Tables */
        .table-wrap { overflow-x: auto; margin: -1.5rem; margin-top: 0; }
        table { width: 100%; border-collapse: collapse; }
        th { text-align: left; padding: 1rem 1.5rem; font-size: 0.7rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; border-bottom: 1px solid var(--border); }
        td { padding: 1rem 1.5rem; font-size: 0.85rem; color: var(--text-dim); border-bottom: 1px solid var(--border); }
        tr:last-child td { border-bottom: none; }
        tr:hover td { background: rgba(255,255,255,0.02); }

        .tag { padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.7rem; font-weight: 700; }
        .tag-buy { background: var(--success-dim); color: var(--success); }
        .tag-sell { background: var(--danger-dim); color: var(--danger); }

        /* Alerts & Activity */
        .log-list { display: flex; flex-direction: column; gap: 0.75rem; max-height: 400px; overflow-y: auto; padding-right: 0.5rem; }
        .log-item { display: flex; gap: 1rem; padding: 0.75rem; border-radius: 8px; background: var(--bg); border: 1px solid var(--border); font-size: 0.85rem; }
        .log-time { color: var(--text-muted); font-size: 0.75rem; min-width: 60px; }
        .log-success { border-left: 3px solid var(--success); }
        .log-error { border-left: 3px solid var(--danger); }
        .log-warn { border-left: 3px solid var(--warning); }

        /* Setup Specific */
        .setup-grid { display: flex; flex-direction: column; gap: 2rem; max-width: 600px; margin: 0 auto; }
        .key-info { background: var(--warning-dim); color: var(--warning); padding: 1rem; border-radius: 8px; font-size: 0.85rem; border: 1px solid rgba(245, 158, 11, 0.2); margin-bottom: 1.5rem; }

        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 10px; }
        ::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }
    </style>
</head>
<body>
    <div class="app-container">
        <header>
            <div class="brand"><span>A</span>PEX</div>
            
            <nav class="nav-tabs">
                <button class="tab-btn active" onclick="showTab('dashboard')">📊 Dashboard</button>
                <button class="tab-btn" onclick="showTab('controls')">🎮 Controls</button>
                <button class="tab-btn" onclick="showTab('risk')">⚖️ Risk</button>
                <button class="tab-btn" onclick="showTab('alerts')">🔔 Alerts</button>
                <button class="tab-btn" onclick="showTab('journal')">📖 Journal</button>
                <button class="tab-btn" onclick="showTab('setup')">⚙️ Setup</button>
            </nav>

            <div class="header-actions">
                <div class="status-badge" id="botStatusBadge"><span class="dot"></span> <span id="botStatusText">LOADING</span></div>
                <button class="btn btn-outline" style="padding: 0.5rem" onclick="location.reload()">🔄</button>
                <a href="/logout" class="btn btn-outline" style="font-size: 0.8rem">Logout</a>
            </div>
        </header>

        <main>
            <!-- DASHBOARD TAB -->
            <div id="dashboard" class="tab-content active">
                <div class="grid">
                    <div class="col-3">
                        <div class="card">
                            <div class="card-title">Balance Totale</div>
                            <div class="metric-val" id="capVal">$0.00</div>
                            <div class="metric-sub" id="capInit">Initial: $0.00</div>
                        </div>
                    </div>
                    <div class="col-3">
                        <div class="card">
                            <div class="card-title">Profit / Perte</div>
                            <div class="metric-val" id="pnlVal">$0.00</div>
                            <div class="metric-sub" id="roiVal">ROI: 0.00%</div>
                        </div>
                    </div>
                    <div class="col-3">
                        <div class="card">
                            <div class="card-title">Win Rate</div>
                            <div class="metric-val" id="wrVal">0%</div>
                            <div class="metric-sub" id="avgWinLoss">W: $0 | L: $0</div>
                        </div>
                    </div>
                    <div class="col-3">
                        <div class="card">
                            <div class="card-title">Uptime</div>
                            <div class="metric-val" id="cycleVal">0</div>
                            <div class="metric-sub" id="uptimeVal">Since --/--</div>
                        </div>
                    </div>

                    <div class="col-8">
                        <div class="card" style="height: 400px;">
                            <div class="card-header"><div class="card-title">Equity Curve</div></div>
                            <canvas id="equityChart" style="width: 100%; height: 300px;"></canvas>
                        </div>
                    </div>

                    <div class="col-4">
                        <div class="card" style="height: 400px;">
                            <div class="card-header"><div class="card-title">Dernier Signal</div></div>
                            <div id="lastSignalBox" style="display: flex; flex-direction: column; gap: 1rem; height: 100%; justify-content: center; text-align: center;">
                                <div class="metric-sub">En attente de données...</div>
                            </div>
                        </div>
                    </div>

                    <!-- Binance API Health Monitor -->
                    <div class="col-12">
                        <div class="card">
                            <div class="card-header">
                                <div class="card-title">🛡️ Binance API Health (Anti-Ban Monitor)</div>
                                <span class="tag" id="wsStatusTag" style="background: var(--success-dim); color: var(--success)">WS ●</span>
                            </div>
                            <div class="grid" style="gap: 1rem;">
                                <div class="col-3">
                                    <div class="metric-sub">WebSocket Stream</div>
                                    <div id="wsStatus" style="font-weight: 700; font-size: 1.1rem;">—</div>
                                    <div class="metric-sub" id="wsMsgs">0 msgs</div>
                                </div>
                                <div class="col-3">
                                    <div class="metric-sub">Binance Weight (1m)</div>
                                    <div id="binanceWeight" style="font-weight: 700; font-size: 1.1rem;">0 / 1200</div>
                                    <div style="background: var(--border); border-radius: 4px; height: 6px; margin-top: 4px; overflow: hidden;">
                                        <div id="weightBar" style="height: 100%; background: var(--success); width: 0%; transition: 0.3s;"></div>
                                    </div>
                                </div>
                                <div class="col-3">
                                    <div class="metric-sub">Rate Limit Local</div>
                                    <div id="bucketUsage" style="font-weight: 700; font-size: 1.1rem;">0 / 200</div>
                                    <div style="background: var(--border); border-radius: 4px; height: 6px; margin-top: 4px; overflow: hidden;">
                                        <div id="bucketBar" style="height: 100%; background: var(--accent); width: 0%; transition: 0.3s;"></div>
                                    </div>
                                </div>
                                <div class="col-3">
                                    <div class="metric-sub">Statut IP</div>
                                    <div id="banStatus" class="up" style="font-weight: 700; font-size: 1.1rem;">✅ Clean</div>
                                    <div class="metric-sub" id="restCount">0 REST reqs</div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="col-12">
                        <div class="card">
                            <div class="card-header">
                                <div class="card-title">Positions Ouvertes</div>
                                <span class="tag" style="background: var(--accent-dim); color: var(--accent)" id="openPosCount">0</span>
                            </div>
                            <div class="table-wrap">
                                <table>
                                    <thead><tr><th>ID</th><th>Side</th><th>Pair</th><th>Entry</th><th>SL / TP</th><th>Size</th><th>PnL Live</th><th>Action</th></tr></thead>
                                    <tbody id="openPosTable"></tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- CONTROLS TAB -->
            <div id="controls" class="tab-content">
                <div class="grid">
                    <div class="col-6">
                        <div class="card">
                            <div class="card-header"><div class="card-title">Bot Master Controls</div></div>
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
                                <button class="btn btn-primary" id="btnResume" onclick="botAction('resume')">▶️ Resume Bot</button>
                                <button class="btn btn-outline" id="btnPause" onclick="botAction('pause')">⏸️ Pause Bot</button>
                                <button class="btn btn-danger" style="grid-column: span 2;" onclick="if(confirm('Tout fermer ?')) botAction('close-all')">🚨 EMERGENCY CLOSE ALL</button>
                            </div>
                            <hr style="border: 0; border-top: 1px solid var(--border); margin: 1.5rem 0;">
                            <div class="form-group" style="display: flex; align-items: center; justify-content: space-between;">
                                <div>
                                    <div style="font-weight: 600;">Auto-Trading System</div>
                                    <div class="metric-sub">Le bot exécute les ordres automatiquement</div>
                                </div>
                                <button class="btn btn-outline" id="btnToggleAuto" onclick="botAction('toggle-auto')">Désactiver</button>
                            </div>
                        </div>
                    </div>
                    <div class="col-6">
                        <div class="card">
                            <div class="card-header"><div class="card-title">Manual Order</div></div>
                            <div class="grid" style="gap: 1rem;">
                                <div class="col-6"><label>Symbol</label><input type="text" id="manSymbol" value="BTC/USDT"></div>
                                <div class="col-6"><label>Side</label><select id="manSide"><option value="BUY">BUY / LONG</option><option value="SELL">SELL / SHORT</option></select></div>
                                <div class="col-12"><label>Taille (USDT)</label><input type="number" id="manSize" placeholder="100.00"></div>
                                <div class="col-12"><button class="btn btn-success" style="width: 100%" onclick="alert('Feature live bientôt !')">Exécuter Ordre Manuel</button></div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- RISK TAB -->
            <div id="risk" class="tab-content">
                <div class="card" style="max-width: 800px; margin: 0 auto;">
                    <div class="card-header"><div class="card-title">Configuration des Risques (Lois Apex)</div></div>
                    <form id="riskForm" onsubmit="event.preventDefault(); updateRisk();">
                        <div class="grid" style="gap: 1.5rem;">
                            <div class="col-6"><label>Risque par Trade (%)</label><input type="number" step="0.1" name="risk_per_trade" id="r_risk"></div>
                            <div class="col-6"><label>Max Heat Portefeuille (%)</label><input type="number" step="0.1" name="max_heat" id="r_heat"></div>
                            <div class="col-6"><label>Max Trades Simultanés</label><input type="number" name="max_trades" id="r_max_trades"></div>
                            <div class="col-6"><label>Ratio Risk:Reward</label><input type="number" step="0.1" name="rr_ratio" id="r_rr"></div>
                            <div class="col-6"><label>Stop Loss ATR Mult.</label><input type="number" step="0.1" name="atr_stop_mult" id="r_atr"></div>
                            <div class="col-6"><label>Max Daily Loss (%)</label><input type="number" step="0.1" name="max_daily_loss" id="r_loss"></div>
                            <div class="col-12"><button type="submit" class="btn btn-primary" style="width: 100%">Sauvegarder les Paramètres</button></div>
                        </div>
                    </form>
                </div>
            </div>

            <!-- ALERTS TAB -->
            <div id="alerts" class="tab-content">
                <div class="grid">
                    <div class="col-4">
                        <div class="card">
                            <div class="card-header"><div class="card-title">Nouvelle Alerte Prix</div></div>
                            <div class="form-group"><label>Symbol</label><input type="text" id="aSymbol" value="BTC/USDT"></div>
                            <div class="form-group"><label>Condition</label><select id="aCond"><option value="above">Prix > (Supérieur)</option><option value="below">Prix < (Inférieur)</option></select></div>
                            <div class="form-group"><label>Prix Target</label><input type="number" step="0.01" id="aPrice" placeholder="0.00"></div>
                            <button class="btn btn-primary" style="width: 100%" onclick="addAlert()">Créer l'Alerte</button>
                        </div>
                    </div>
                    <div class="col-8">
                        <div class="card">
                            <div class="card-header"><div class="card-title">Alertes Actives</div></div>
                            <div class="table-wrap">
                                <table>
                                    <thead><tr><th>Symbol</th><th>Condition</th><th>Cible</th><th>Actions</th></tr></thead>
                                    <tbody id="alertsTable"></tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- JOURNAL TAB -->
            <div id="journal" class="tab-content">
                <div class="grid">
                    <div class="col-7">
                        <div class="card">
                            <div class="card-header"><div class="card-title">Activity Log</div></div>
                            <div class="log-list" id="activityLog"></div>
                        </div>
                    </div>
                    <div class="col-5">
                        <div class="card">
                            <div class="card-header"><div class="card-title">Notes de Trading</div></div>
                            <div class="form-group"><textarea id="noteText" placeholder="Prendre une note..." rows="3"></textarea></div>
                            <button class="btn btn-outline" style="width: 100%; margin-bottom: 1.5rem;" onclick="addNote()">Ajouter Note</button>
                            <div id="notesList" style="display: flex; flex-direction: column; gap: 1rem;"></div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- SETUP TAB -->
            <div id="setup" class="tab-content">
                <div class="setup-grid">
                    <div class="card">
                        <div class="card-header"><div class="card-title">Binance API Connectivity</div></div>
                        <div class="key-info">Les clés sont stockées en mémoire et dans le fichier .env localement. Elles sont utilisées pour le mode LIVE et pour récupérer les soldes réels.</div>
                        <div class="form-group"><label>Binance API Key</label><input type="text" id="apiKey" placeholder="Saisir votre clé..."></div>
                        <div class="form-group"><label>Binance Secret Key</label><input type="password" id="apiSecret" placeholder="••••••••••••••••"></div>
                        <button class="btn btn-primary" style="width: 100%" onclick="saveKeys()">Mettre à jour les Clés</button>
                        <div id="keyStatus" class="metric-sub" style="margin-top: 1rem; text-align: center;">Vérification du statut...</div>
                    </div>
                    
                    <div class="card">
                        <div class="card-header"><div class="card-title">Performance Avancée</div></div>
                        <div class="grid">
                            <div class="col-6"><div class="metric-sub">Profit Factor</div><div id="perfPF" style="font-weight: 700;">--</div></div>
                            <div class="col-6"><div class="metric-sub">Max Drawdown</div><div id="perfDD" class="dn" style="font-weight: 700;">--</div></div>
                            <div class="col-6"><div class="metric-sub">Plus gros gain</div><div id="perfBest" class="up" style="font-weight: 700;">--</div></div>
                            <div class="col-6"><div class="metric-sub">Série actuelle</div><div id="perfStreak" style="font-weight: 700;">--</div></div>
                        </div>
                    </div>
                </div>
            </div>
        </main>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
        // Tab System
        function showTab(id) {
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.getElementById(id).classList.add('active');
            event.currentTarget.classList.add('active');
            localStorage.setItem('apex_last_tab', id);
        }
        
        // Restore last tab
        const lastTab = localStorage.getItem('apex_last_tab');
        if(lastTab) {
            const btn = Array.from(document.querySelectorAll('.tab-btn')).find(b => b.textContent.toLowerCase().includes(lastTab));
            if(btn) btn.click();
        }

        let chart = null;
        function drawChart(data) {
            const ctx = document.getElementById('equityChart').getContext('2d');
            if (chart) chart.destroy();
            chart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.map((_, i) => i),
                    datasets: [{
                        label: 'Portfolio Value',
                        data: data,
                        borderColor: '#6366f1',
                        backgroundColor: 'rgba(99, 102, 241, 0.1)',
                        fill: true,
                        tension: 0.4,
                        borderWidth: 2,
                        pointRadius: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { grid: { color: '#222632' }, ticks: { color: '#94a3b8', font: { size: 10 } } },
                        x: { display: false }
                    }
                }
            });
        }

        async function fetchData() {
            try {
                const [statusRes, extRes, logsRes] = await Promise.all([
                    fetch('/api/status'),
                    fetch('/api/extended-status'),
                    fetch('/api/logs')
                ]);
                
                const d = await statusRes.json();
                const e = await extRes.json();
                const l = await logsRes.json();

                // Dashboard Header
                const st = d.status.toUpperCase();
                document.getElementById('botStatusText').textContent = d.status;
                document.getElementById('botStatusBadge').className = 'status-badge ' + 
                    (st === 'RUNNING' ? 'live' : (st.includes('ERROR') || st.includes('BANNED') ? 'error' : ''));

                // Metrics
                if(d.stats) {
                    const s = d.stats;
                    document.getElementById('capVal').textContent = '$' + s.capital.toFixed(2);
                    document.getElementById('capInit').textContent = 'Initial: $' + d.config.initial_capital.toFixed(2);
                    document.getElementById('pnlVal').textContent = (s.total_pnl >= 0 ? '+$' : '-$') + Math.abs(s.total_pnl).toFixed(2);
                    document.getElementById('pnlVal').className = 'metric-val ' + (s.total_pnl >= 0 ? 'up' : 'dn');
                    document.getElementById('roiVal').textContent = 'ROI: ' + s.roi.toFixed(2) + '%';
                    document.getElementById('roiVal').className = 'metric-sub ' + (s.roi >= 0 ? 'up' : 'dn');
                    document.getElementById('wrVal').textContent = s.win_rate.toFixed(0) + '%';
                    document.getElementById('avgWinLoss').textContent = 'W: $' + s.avg_win.toFixed(0) + ' | L: $' + s.avg_loss.toFixed(0);
                    document.getElementById('cycleVal').textContent = d.cycle;
                    document.getElementById('uptimeVal').textContent = 'Since ' + new Date(d.started_at).toLocaleDateString();
                    
                    // Chart (simulate history for now)
                    drawChart([d.config.initial_capital, s.capital]);
                }

                // Last Signal
                if(d.last_signal) {
                    const ls = d.last_signal;
                    const color = ls.signal === 'BUY' ? 'var(--success)' : (ls.signal === 'SELL' ? 'var(--danger)' : 'var(--text)');
                    document.getElementById('lastSignalBox').innerHTML = `
                        <div style="font-size: 2.5rem; font-weight: 800; color: ${color}">${ls.signal}</div>
                        <div style="font-size: 1.2rem; font-weight: 600;">$${ls.price.toFixed(2)}</div>
                        <div class="metric-sub">Confidence: ${(ls.confidence*100).toFixed(0)}%</div>
                        <div style="font-size: 0.75rem; text-align: left; margin-top: 1rem;">
                            ${ls.reasons.map(r => `• ${r}`).join('<br>')}
                        </div>
                    `;
                }

                // Open Positions
                document.getElementById('openPosCount').textContent = d.open_trades.length;
                document.getElementById('openPosTable').innerHTML = d.open_trades.map(t => `
                    <tr>
                        <td>${t.id.slice(-6)}</td>
                        <td><span class="tag ${t.side==='BUY'?'tag-buy':'tag-sell'}">${t.side}</span></td>
                        <td>${t.symbol}</td>
                        <td>$${t.entry.toFixed(2)}</td>
                        <td>$${t.stop.toFixed(2)} / $${t.target.toFixed(2)}</td>
                        <td>${t.size.toFixed(5)}</td>
                        <td class="up">+$0.00</td>
                        <td><button class="btn btn-outline" style="padding: 0.2rem 0.5rem; font-size: 0.7rem">Fermer</button></td>
                    </tr>
                `).join('') || '<tr><td colspan="8" style="text-align:center; padding: 2rem; color: var(--text-muted)">Aucune position active</td></tr>';

                // Extended Status (Risk & Perf)
                if(e.risk_config) {
                    const rc = e.risk_config;
                    document.getElementById('r_risk').value = (rc.risk_per_trade * 100).toFixed(1);
                    document.getElementById('r_heat').value = (rc.max_heat * 100).toFixed(1);
                    document.getElementById('r_max_trades').value = rc.max_trades;
                    document.getElementById('r_rr').value = rc.rr_ratio;
                    document.getElementById('r_atr').value = rc.atr_stop_mult;
                    document.getElementById('r_loss').value = (rc.max_daily_loss * 100).toFixed(1);
                }
                
                // ===== API Health Monitor =====
                if(e.data_handler) {
                    const dh = e.data_handler;
                    const wsStats = dh.ws_stats || {};
                    const wsOk = dh.ws_connected;
                    
                    document.getElementById('wsStatus').textContent = wsOk ? '✅ Connected' : '❌ Disconnected';
                    document.getElementById('wsStatus').className = wsOk ? 'up' : 'dn';
                    document.getElementById('wsStatusTag').textContent = wsOk ? 'WS LIVE ●' : 'WS DOWN';
                    document.getElementById('wsStatusTag').style.background = wsOk ? 'var(--success-dim)' : 'var(--danger-dim)';
                    document.getElementById('wsStatusTag').style.color = wsOk ? 'var(--success)' : 'var(--danger)';
                    document.getElementById('wsMsgs').textContent = (wsStats.msg_count || 0) + ' msgs reçus';
                    
                    const wPct = dh.binance_weight_pct || 0;
                    document.getElementById('binanceWeight').textContent = (dh.binance_weight_1m||0) + ' / 1200';
                    document.getElementById('weightBar').style.width = Math.min(100, wPct) + '%';
                    document.getElementById('weightBar').style.background = wPct > 75 ? 'var(--danger)' : wPct > 50 ? 'var(--warning)' : 'var(--success)';
                    
                    const bPct = dh.bucket_pct || 0;
                    document.getElementById('bucketUsage').textContent = (dh.bucket_used||0) + ' / ' + (dh.bucket_max||200);
                    document.getElementById('bucketBar').style.width = Math.min(100, bPct) + '%';
                    document.getElementById('bucketBar').style.background = bPct > 75 ? 'var(--danger)' : bPct > 50 ? 'var(--warning)' : 'var(--accent)';
                    
                    if(dh.is_banned) {
                        document.getElementById('banStatus').textContent = '🚫 BANNED (' + Math.round(dh.ban_remaining) + 's)';
                        document.getElementById('banStatus').className = 'dn';
                    } else {
                        document.getElementById('banStatus').textContent = '✅ Clean';
                        document.getElementById('banStatus').className = 'up';
                    }
                    document.getElementById('restCount').textContent = (dh.request_count||0) + ' REST reqs';
                }

                document.getElementById('perfPF').textContent = e.performance.profit_factor.toFixed(2);
                document.getElementById('perfDD').textContent = '$' + Math.abs(e.performance.max_drawdown).toFixed(2);
                document.getElementById('perfBest').textContent = '+$' + e.performance.best_trade.toFixed(2);
                document.getElementById('perfStreak').textContent = e.performance.streak + ' wins';
                
                document.getElementById('keyStatus').textContent = e.keys_configured ? '✅ Clés Configurées' : '❌ Clés Manquantes';
                document.getElementById('btnToggleAuto').textContent = e.bot_control.auto_trade ? 'Désactiver Auto' : 'Activer Auto';
                document.getElementById('btnToggleAuto').className = e.bot_control.auto_trade ? 'btn btn-outline' : 'btn btn-primary';

                // Logs
                document.getElementById('activityLog').innerHTML = l.logs.map(log => `
                    <div class="log-item log-${log.level}">
                        <div class="log-time">${new Date(log.time).toLocaleTimeString()}</div>
                        <div>${log.msg}</div>
                    </div>
                `).join('');

            } catch(err) { console.error(err); }
        }

        // Actions
        async function botAction(action) {
            let url = '/api/bot/' + action;
            if(action === 'toggle-auto') url = '/api/bot/toggle-auto';
            const res = await fetch(url, { method: 'POST' });
            if(res.ok) fetchData();
        }

        async function saveKeys() {
            const api_key = document.getElementById('apiKey').value;
            const api_secret = document.getElementById('apiSecret').value;
            const res = await fetch('/api/setup/keys', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ api_key, api_secret })
            });
            if(res.ok) {
                alert('Clés mises à jour !');
                document.getElementById('apiKey').value = '';
                document.getElementById('apiSecret').value = '';
                fetchData();
            }
        }

        async function updateRisk() {
            const formData = new FormData(document.getElementById('riskForm'));
            const data = {};
            formData.forEach((v, k) => {
                if(['risk_per_trade', 'max_heat', 'max_daily_loss'].includes(k)) data[k] = parseFloat(v) / 100;
                else data[k] = parseFloat(v);
            });
            const res = await fetch('/api/risk/update', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            if(res.ok) alert('Risque mis à jour !');
        }

        async function addNote() {
            const text = document.getElementById('noteText').value;
            if(!text) return;
            await fetch('/api/notes', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text })
            });
            document.getElementById('noteText').value = '';
            loadNotes();
        }

        async function loadNotes() {
            const res = await fetch('/api/notes');
            const data = await res.json();
            document.getElementById('notesList').innerHTML = data.notes.map(n => `
                <div class="card" style="padding: 1rem; font-size: 0.85rem;">
                    <div class="metric-sub" style="margin-bottom: 0.5rem;">${new Date(n.time).toLocaleString()}</div>
                    ${n.text}
                </div>
            `).join('');
        }

        fetchData();
        loadNotes();
        setInterval(fetchData, 5000);
    </script>
</body>
</html>
"""


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        # Simple hardcoded credentials as requested
        if (
            request.form.get("username") == "nolex"
            and request.form.get("password") == "apexbot"
        ):
            session["logged_in"] = True
            return redirect(url_for("index"))
        else:
            error = "Identifiants ou mot de passe incorrects."
    return render_template_string(LOGIN_HTML, error=error)


@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    return redirect(url_for("login"))


@app.route("/")
def index():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    return render_template_string(DASHBOARD_HTML)


@app.route("/api/status")
def api_status():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401

    from config import Config

    stats = {}
    open_trades = []
    closed_trades = []

    rm = bot_state.get("risk_manager")
    if rm:
        stats = rm.stats()
        open_trades = [
            {
                "id": t["id"],
                "symbol": t["symbol"],
                "side": t["side"],
                "entry": t["entry"],
                "stop": t["stop"],
                "target": t["target"],
                "size": t["size"],
                "risk_amount": t["risk_amount"],
                "opened_at": str(t["opened_at"]),
            }
            for t in rm.open_trades
        ]
        closed_trades = [
            {
                "id": t["id"],
                "side": t["side"],
                "entry": t["entry"],
                "exit": t.get("exit", 0),
                "pnl": t.get("pnl", 0),
                "exit_reason": t.get("exit_reason", ""),
                "closed_at": str(t.get("closed_at", "")),
            }
            for t in rm.closed_trades
        ]

    return jsonify(
        {
            "status": bot_state["status"],
            "cycle": bot_state["cycle"],
            "started_at": bot_state["started_at"],
            "last_update": bot_state["last_update"],
            "last_signal": bot_state["last_signal"],
            "signals_history": bot_state["signals_history"][-100:],
            "stats": stats,
            "open_trades": open_trades,
            "closed_trades": closed_trades,
            "config": {
                "mode": Config.MODE,
                "exchange": Config.EXCHANGE,
                "symbol": Config.SYMBOL,
                "tf_fast": Config.TIMEFRAME_FAST,
                "tf_slow": Config.TIMEFRAME_SLOW,
                "initial_capital": Config.INITIAL_CAPITAL,
                "risk_per_trade": Config.RISK_PER_TRADE,
                "max_heat": Config.MAX_PORTFOLIO_HEAT,
                "max_daily_loss": Config.MAX_DAILY_LOSS,
                "rr_ratio": Config.RR_RATIO,
                "atr_stop_mult": Config.ATR_STOP_MULTIPLIER,
                "loop_interval": Config.LOOP_INTERVAL,
            },
        }
    )


@app.route("/health")
def health():
    return jsonify({"status": "ok", "cycle": bot_state["cycle"]})
