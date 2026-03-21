# Roostoo Autonomous Trading Bot

## Structure

- `bot/`
  - `strategy/` — SVM strategy, indicator functions
  - `execution/` — Roostoo API wrappers and signed order placement
  - `data/` — Binance data interfaces
  - `config/` — config values
  - `logs/` — trade logs
- `tests/` — unit tests
- `requirements.txt`
- `Dockerfile`

## Run

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run bot:
   ```bash
   python bot/main.py
   ```

## Logging
Trades are logged to `bot/logs/trades.csv` with:
- timestamp
- symbol
- side
- price
- quantity
- order_id
- api_response
- pnl
- signal_reason
- strategy_state

## Docker
Build and run:
```bash
docker build -t roostoo-bot .
docker run --rm roostoo-bot
```
