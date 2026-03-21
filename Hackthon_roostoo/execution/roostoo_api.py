import time
import hashlib
import hmac
import requests
from typing import Dict, Any, Optional
from bot.config.config import ROOSTOO_API_KEY, ROOSTOO_SECRET, BASE_URL


def make_signature(params: Dict[str, Any]) -> str:
    payload = '&'.join(f"{k}={params[k]}" for k in sorted(params.keys()))
    return hmac.new(ROOSTOO_SECRET.encode('utf-8'), payload.encode('utf-8'), hashlib.sha256).hexdigest()


def signed_get(path: str, params: Optional[Dict[str, Any]] = None) -> requests.Response:
    if params is None:
        params = {}
    params['timestamp'] = int(time.time() * 1000)
    headers = {
        'RST-API-KEY': ROOSTOO_API_KEY,
        'MSG-SIGNATURE': make_signature(params),
    }
    return requests.get(BASE_URL + path, params=params, headers=headers)


def signed_post(path: str, data: Optional[Dict[str, Any]] = None) -> requests.Response:
    if data is None:
        data = {}
    data['timestamp'] = int(time.time() * 1000)
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'RST-API-KEY': ROOSTOO_API_KEY,
        'MSG-SIGNATURE': make_signature(data),
    }
    return requests.post(BASE_URL + path, data=data, headers=headers)


def get_ticker(pair: str = 'BTC/USD') -> Dict[str, Any]:
    payload = {'pair': pair, 'timestamp': int(time.time() * 1000)}
    r = requests.get(BASE_URL + '/v3/ticker', params=payload)
    r.raise_for_status()
    js = r.json()
    if isinstance(js, dict):
        data = js.get('Data') or js.get('data')
        if isinstance(data, dict):
            pair_data = data.get(pair) or next(iter(data.values()), None)
            if isinstance(pair_data, dict):
                price = pair_data.get('LastPrice') or pair_data.get('lastPrice') or pair_data.get('price')
                if price is not None:
                    return {'lastPrice': float(price), 'raw': js}
    if 'lastPrice' in js:
        return {'lastPrice': float(js['lastPrice']), 'raw': js}
    return {'lastPrice': 0.0, 'raw': js}


def get_balance() -> Dict[str, Any]:
    r = signed_get('/v3/balance')
    r.raise_for_status()
    return r.json()


def place_market_order(pair: str, side: str, quantity: float) -> requests.Response:
    data = {'pair': pair, 'side': side, 'type': 'MARKET', 'quantity': quantity}
    return signed_post('/v3/place_order', data=data)


def parse_balance(resp: Dict[str, Any]) -> Dict[str, float]:
    if isinstance(resp, dict) and 'balance' in resp:
        balances = resp['balance']
    elif isinstance(resp, dict) and 'data' in resp:
        balances = resp['data']
    else:
        balances = resp
    out: Dict[str, float] = {}
    for item in balances:
        try:
            asset = item.get('asset', item.get('symbol', 'UNKNOWN'))
            out[asset] = float(item.get('free', item.get('available', 0)))
        except Exception:
            continue
    return out
