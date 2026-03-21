import csv
import os
from datetime import datetime
from typing import Dict, Any
 
from bot.config.config import CSV_LOG_PATH
 
# ── path setup ────────────────────────────────────────────────────────────────
LOG_DIR = os.path.dirname(CSV_LOG_PATH)
os.makedirs(LOG_DIR, exist_ok=True)
 
ERROR_LOG_PATH = os.path.join(LOG_DIR, 'errors.csv')
PERFORMANCE_LOG_PATH = os.path.join(LOG_DIR, 'performance.csv')
 
# ── field definitions ─────────────────────────────────────────────────────────
 
TRADE_FIELDS = [
    'timestamp', 'symbol', 'side', 'price', 'quantity',
    'order_id', 'api_status', 'api_success', 'api_response',
    'pnl', 'portfolio_value_usd', 'signal_reason', 'strategy_state',
]
 
ERROR_FIELDS = ['timestamp', 'cycle', 'error', 'traceback']
 
PERFORMANCE_FIELDS = [
    'timestamp', 'cycle', 'portfolio_return_pct', 'sharpe_ratio',
    'sortino_ratio', 'calmar_ratio', 'max_drawdown_pct',
    'initial_value_usd', 'final_value_usd', 'final',
]
 
# ── generic init/append ───────────────────────────────────────────────────────
 
def _init_log(path: str, fields: list) -> None:
    if not os.path.exists(path):
        with open(path, 'w', newline='') as f:
            csv.DictWriter(f, fieldnames=fields).writeheader()
 
 
def _append_log(path: str, fields: list, entry: Dict[str, Any]) -> None:
    _init_log(path, fields)
    row = {f: entry.get(f, '') for f in fields}  # safe: missing keys → ''
    with open(path, 'a', newline='') as f:
        csv.DictWriter(f, fieldnames=fields).writerow(row)
 
 
# ── public API ────────────────────────────────────────────────────────────────
 
def log_trade(entry: Dict[str, Any]) -> None:
    entry_copy = entry.copy()
    entry_copy.setdefault('timestamp', datetime.utcnow().isoformat())
    _append_log(CSV_LOG_PATH, TRADE_FIELDS, entry_copy)
 
 
def log_error(entry: Dict[str, Any]) -> None:
    entry_copy = entry.copy()
    entry_copy.setdefault('timestamp', datetime.utcnow().isoformat())
    _append_log(ERROR_LOG_PATH, ERROR_FIELDS, entry_copy)
 
 
def log_performance(entry: Dict[str, Any]) -> None:
    entry_copy = entry.copy()
    entry_copy.setdefault('timestamp', datetime.utcnow().isoformat())
    entry_copy.setdefault('final', False)
    _append_log(PERFORMANCE_LOG_PATH, PERFORMANCE_FIELDS, entry_copy)
