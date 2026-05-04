"""APEX BOT - Extended API Routes"""
import os, json, time
from flask import jsonify, request, session
from datetime import datetime

# Shared state for new features
extended_state = {
    'api_keys': {'key': '', 'secret': '', 'configured': False, 'last_updated': None},
    'bot_control': {'paused': False, 'auto_trade': True},
    'alerts': [],
    'triggered_alerts': [],
    'activity_log': [],
    'risk_overrides': {},
    'notes': [],
    'favorite_pairs': ['BTC/USDT', 'ETH/USDT', 'SOL/USDT'],
}

MAX_LOG = 200

def add_log(msg, level='info'):
    extended_state['activity_log'].insert(0, {
        'time': datetime.now().isoformat(), 'msg': msg, 'level': level
    })
    if len(extended_state['activity_log']) > MAX_LOG:
        extended_state['activity_log'] = extended_state['activity_log'][:MAX_LOG]

def register_routes(app, bot_state):
    """Register all extended API routes on the Flask app."""

    def _auth():
        return session.get('logged_in')

    # ── Setup: Save Binance API Keys ──
    @app.route('/api/setup/keys', methods=['POST'])
    def save_keys():
        if not _auth(): return jsonify({'error': 'Unauthorized'}), 401
        data = request.json or {}
        key = data.get('api_key', '').strip()
        secret = data.get('api_secret', '').strip()
        if not key or not secret:
            return jsonify({'ok': False, 'error': 'Clé et secret requis'}), 400

        # Update Config class at runtime
        from config import Config
        Config.API_KEY = key
        Config.API_SECRET = secret

        # Also set env vars for any future re-init
        os.environ['BINANCE_API_KEY'] = key
        os.environ['BINANCE_API_SECRET'] = secret

        # Reinit exchange in data_handler if available
        dh = bot_state.get('data_handler')
        if dh:
            import ccxt
            dh.exchange = getattr(ccxt, Config.EXCHANGE)({
                'apiKey': key, 'secret': secret,
                'enableRateLimit': True,
                'options': {'defaultType': 'spot'}
            })

        extended_state['api_keys'] = {
            'key': key[:8] + '...' + key[-4:] if len(key) > 12 else '***',
            'secret': '••••••••' + secret[-4:] if len(secret) > 4 else '***',
            'configured': True,
            'last_updated': datetime.now().isoformat()
        }
        add_log('🔑 Clés API Binance mises à jour', 'success')
        return jsonify({'ok': True, 'keys': extended_state['api_keys']})

    @app.route('/api/setup/keys', methods=['GET'])
    def get_keys():
        if not _auth(): return jsonify({'error': 'Unauthorized'}), 401
        from config import Config
        has_key = bool(Config.API_KEY)
        info = extended_state['api_keys'].copy()
        if not info['configured'] and has_key:
            info['configured'] = True
            k = Config.API_KEY
            info['key'] = k[:8] + '...' + k[-4:] if len(k) > 12 else '***'
            info['secret'] = '••••••••'
        return jsonify(info)

    # ── Bot Controls ──
    @app.route('/api/bot/pause', methods=['POST'])
    def pause_bot():
        if not _auth(): return jsonify({'error': 'Unauthorized'}), 401
        extended_state['bot_control']['paused'] = True
        bot_state['status'] = 'PAUSED'
        add_log('⏸️ Bot mis en pause', 'warn')
        return jsonify({'ok': True, 'paused': True})

    @app.route('/api/bot/resume', methods=['POST'])
    def resume_bot():
        if not _auth(): return jsonify({'error': 'Unauthorized'}), 401
        extended_state['bot_control']['paused'] = False
        bot_state['status'] = 'RUNNING'
        add_log('▶️ Bot repris', 'success')
        return jsonify({'ok': True, 'paused': False})

    @app.route('/api/bot/close-all', methods=['POST'])
    def close_all():
        if not _auth(): return jsonify({'error': 'Unauthorized'}), 401
        rm = bot_state.get('risk_manager')
        closed = 0
        if rm:
            for t in list(rm.open_trades):
                rm.close_trade(t, t['entry'], 'MANUAL_CLOSE')
                closed += 1
        add_log(f'🚨 Fermeture d\'urgence: {closed} positions fermées', 'error')
        return jsonify({'ok': True, 'closed': closed})

    @app.route('/api/bot/toggle-auto', methods=['POST'])
    def toggle_auto():
        if not _auth(): return jsonify({'error': 'Unauthorized'}), 401
        extended_state['bot_control']['auto_trade'] = not extended_state['bot_control']['auto_trade']
        state = extended_state['bot_control']['auto_trade']
        add_log(f'{"🤖" if state else "🖐️"} Auto-trade {"activé" if state else "désactivé"}', 'info')
        return jsonify({'ok': True, 'auto_trade': state})

    # ── Risk Overrides ──
    @app.route('/api/risk/update', methods=['POST'])
    def update_risk():
        if not _auth(): return jsonify({'error': 'Unauthorized'}), 401
        data = request.json or {}
        from config import Config
        mapping = {
            'risk_per_trade': ('RISK_PER_TRADE', float),
            'max_heat': ('MAX_PORTFOLIO_HEAT', float),
            'max_daily_loss': ('MAX_DAILY_LOSS', float),
            'rr_ratio': ('RR_RATIO', float),
            'atr_stop_mult': ('ATR_STOP_MULTIPLIER', float),
            'loop_interval': ('LOOP_INTERVAL', int),
            'max_trades': ('MAX_CONCURRENT_TRADES', int),
        }
        changed = []
        for k, (attr, typ) in mapping.items():
            if k in data:
                val = typ(data[k])
                setattr(Config, attr, val)
                changed.append(f'{k}={val}')
        if changed:
            add_log(f'⚙️ Risk params mis à jour: {", ".join(changed)}', 'warn')
        return jsonify({'ok': True, 'changed': changed})

    # ── Alerts ──
    @app.route('/api/alerts', methods=['GET'])
    def get_alerts():
        if not _auth(): return jsonify({'error': 'Unauthorized'}), 401
        return jsonify({'alerts': extended_state['alerts'], 'triggered': extended_state['triggered_alerts'][-20:]})

    @app.route('/api/alerts', methods=['POST'])
    def add_alert():
        if not _auth(): return jsonify({'error': 'Unauthorized'}), 401
        data = request.json or {}
        alert = {
            'id': int(time.time() * 1000),
            'symbol': data.get('symbol', 'BTC/USDT'),
            'condition': data.get('condition', 'above'),
            'price': float(data.get('price', 0)),
            'active': True,
            'created': datetime.now().isoformat()
        }
        extended_state['alerts'].append(alert)
        add_log(f'🔔 Alerte créée: {alert["symbol"]} {alert["condition"]} {alert["price"]}', 'info')
        return jsonify({'ok': True, 'alert': alert})

    @app.route('/api/alerts/<int:alert_id>', methods=['DELETE'])
    def delete_alert(alert_id):
        if not _auth(): return jsonify({'error': 'Unauthorized'}), 401
        extended_state['alerts'] = [a for a in extended_state['alerts'] if a['id'] != alert_id]
        return jsonify({'ok': True})

    # ── Activity Log ──
    @app.route('/api/logs')
    def get_logs():
        if not _auth(): return jsonify({'error': 'Unauthorized'}), 401
        return jsonify({'logs': extended_state['activity_log'][:100]})

    # ── Notes / Journal ──
    @app.route('/api/notes', methods=['GET'])
    def get_notes():
        if not _auth(): return jsonify({'error': 'Unauthorized'}), 401
        return jsonify({'notes': extended_state['notes']})

    @app.route('/api/notes', methods=['POST'])
    def add_note():
        if not _auth(): return jsonify({'error': 'Unauthorized'}), 401
        data = request.json or {}
        note = {'id': int(time.time()*1000), 'text': data.get('text',''), 'time': datetime.now().isoformat()}
        extended_state['notes'].insert(0, note)
        if len(extended_state['notes']) > 50:
            extended_state['notes'] = extended_state['notes'][:50]
        return jsonify({'ok': True})

    @app.route('/api/notes/<int:note_id>', methods=['DELETE'])
    def delete_note(note_id):
        if not _auth(): return jsonify({'error': 'Unauthorized'}), 401
        extended_state['notes'] = [n for n in extended_state['notes'] if n['id'] != note_id]
        return jsonify({'ok': True})

    # ── Extended Status ──
    @app.route('/api/extended-status')
    def extended_status():
        if not _auth(): return jsonify({'error': 'Unauthorized'}), 401
        from config import Config
        rm = bot_state.get('risk_manager')
        dh = bot_state.get('data_handler')

        # Performance metrics
        perf = {}
        if rm:
            trades = rm.closed_trades
            if trades:
                pnls = [t.get('pnl', 0) for t in trades]
                wins = [p for p in pnls if p > 0]
                losses = [p for p in pnls if p <= 0]
                perf['profit_factor'] = sum(wins) / abs(sum(losses)) if losses and sum(losses) != 0 else 0
                perf['max_drawdown'] = min(pnls) if pnls else 0
                perf['best_trade'] = max(pnls) if pnls else 0
                perf['worst_trade'] = min(pnls) if pnls else 0
                perf['total_fees'] = 0
                perf['streak'] = 0
                streak = 0
                for p in reversed(pnls):
                    if p > 0: streak += 1
                    else: break
                perf['streak'] = streak
            else:
                perf = {'profit_factor':0,'max_drawdown':0,'best_trade':0,'worst_trade':0,'total_fees':0,'streak':0}

        dh_stats = {}
        if dh:
            dh_stats = dh.get_stats()

        return jsonify({
            'bot_control': extended_state['bot_control'],
            'keys_configured': extended_state['api_keys']['configured'] or bool(Config.API_KEY),
            'performance': perf,
            'data_handler': dh_stats,
            'risk_config': {
                'risk_per_trade': Config.RISK_PER_TRADE,
                'max_heat': Config.MAX_PORTFOLIO_HEAT,
                'max_daily_loss': Config.MAX_DAILY_LOSS,
                'rr_ratio': Config.RR_RATIO,
                'atr_stop_mult': Config.ATR_STOP_MULTIPLIER,
                'loop_interval': Config.LOOP_INTERVAL,
                'max_trades': Config.MAX_CONCURRENT_TRADES,
            },
            'alerts_count': len([a for a in extended_state['alerts'] if a['active']]),
            'logs_count': len(extended_state['activity_log']),
        })

    add_log('🚀 Dashboard APEX démarré', 'success')
