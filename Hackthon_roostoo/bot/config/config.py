import os

# Roostoo credentials (Hardcoded for this demo; use env vars in production)
ROOSTOO_API_KEY = os.getenv('ROOSTOO_API_KEY', 'UtVJC6TZId4MTPuaVoXLM2RqpNPhcxTGrYqoNbpYNp2AslIpsPmYnh1HyQ2rgUna')
ROOSTOO_SECRET = os.getenv('ROOSTOO_SECRET', 'Rtb0bcdgRWBfxzew9apfs1XpiWLJZMXK3gIUAtrCwJSLrDvrxQVM8O8LBVX4wH04')
BASE_URL = os.getenv('ROOSTOO_BASE_URL', 'https://mock-api.roostoo.com')
PAIR = os.getenv('PAIR', 'BTC/USD')
SYMBOL = os.getenv('SYMBOL', 'BTCUSDT')

# Strategy / execution
MIN_ORDER_USD = float(os.getenv('MIN_ORDER_USD', '10'))
RISK_PER_TRADE = float(os.getenv('RISK_PER_TRADE', '0.02'))
INTERVAL_SECONDS = float(os.getenv('INTERVAL_SECONDS', '10.0'))
MAX_CYCLES = int(os.getenv('MAX_CYCLES', '500'))

# SVM
SVM_RETRAIN_INTERVAL = int(os.getenv('SVM_RETRAIN_INTERVAL', '5'))

# Logging
LOG_PATH = os.getenv('LOG_PATH', 'bot/logs/trades.log')
CSV_LOG_PATH = os.getenv('CSV_LOG_PATH', 'bot/logs/trades.csv')
