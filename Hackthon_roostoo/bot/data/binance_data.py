import requests
from typing import List, Any

BINANCE_API_BASE = 'https://api.binance.com'


def fetch_klines(symbol: str = 'BTCUSDT', interval: str = '1d', limit: int = 200) -> List[List[Any]]:
    r = requests.get(f"{BINANCE_API_BASE}/api/v3/klines", params={"symbol": symbol, "interval": interval, "limit": limit})
    r.raise_for_status()
    return r.json()


def closes_from_klines(klines: List[List[Any]]) -> List[float]:
    return [float(k[4]) for k in klines]
