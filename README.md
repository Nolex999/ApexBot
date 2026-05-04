# 🚀 APEX Trading Bot

Bot de trading algorithmique modulaire — Multi-Timeframe Trend Following + Mean Reversion Hybrid avec Risk Management institutionnel.

## Architecture

```
apex_bot/
├── config.py           # Configuration centrale (env vars)
├── data_handler.py     # Récupération données marché (ccxt)
├── indicators.py       # Indicateurs techniques (EMA, RSI, ATR, MACD, ADX)
├── strategy.py         # Logique de trading multi-timeframe
├── risk_manager.py     # Gestion du risque + circuit breakers
├── executor.py         # Exécution des ordres (paper/live)
├── logger.py           # Journalisation avec persistence JSON
└── main.py             # Orchestrateur principal
```

## Déploiement Railway

1. Connecte ce repo à [Railway](https://railway.app)
2. Ajoute les variables d'environnement dans le dashboard :

| Variable | Default | Description |
|---|---|---|
| `APEX_MODE` | `PAPER` | Mode de trading (`PAPER` / `LIVE`) |
| `APEX_SYMBOL` | `BTC/USDT` | Paire à trader |
| `APEX_CAPITAL` | `1000` | Capital initial (USDT) |
| `APEX_EXCHANGE` | `binance` | Exchange à utiliser |
| `BINANCE_API_KEY` | _(vide)_ | Clé API Binance (optionnel en paper) |
| `BINANCE_API_SECRET` | _(vide)_ | Secret API Binance (optionnel en paper) |

3. Railway détecte automatiquement le `Procfile` et lance le bot comme **worker**

## Local

```bash
cd apex_bot
python -m venv venv && source venv/bin/activate
pip install -r ../requirements.txt
python main.py
```

## Stratégie

- **Trend-following** confirmé par macro 4h + entrée sur pullback 15m
- **Risk management** institutionnel (1% par trade, circuit breakers daily/weekly)
- **Position sizing** dynamique basé sur ATR
- **R:R minimum 2.5:1**
- **Filtre ADX** — ne trade pas dans les marchés sans tendance

## ⚠️ Disclaimer

Code éducatif. Aucune garantie de profit. Le trading algo comporte des risques substantiels.
