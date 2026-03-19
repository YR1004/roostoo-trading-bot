#!/usr/bin/env python3
import time
import traceback
from datetime import datetime

from bot.config.config import (
    PAIR, SYMBOL, MAX_CYCLES, INTERVAL_SECONDS,
    MIN_ORDER_USD, RISK_PER_TRADE, SVM_RETRAIN_INTERVAL
)
from bot.execution.roostoo_api import get_ticker, get_balance, place_market_order, parse_balance
from bot.data.binance_data import fetch_klines, closes_from_klines
from bot.strategy.svm_strategy import build_sma_features, train_svm, predict_signal
from bot.logs.logger import log_trade, log_error, log_performance


# ── helpers ──────────────────────────────────────────────────────────────────

def safe_order_response(resp):
  
    try:
        api_status = resp.status_code
        if api_status == 200:
            return resp.json().get('order_id', ''), api_status, True
        else:
            return '', api_status, False
    except Exception as e:
        return '', 'PARSE_ERROR', False


def compute_portfolio_value(usd: float, btc: float, price: float) -> float:
    """Total portfolio value in USD terms."""
    return usd + btc * price


def compute_metrics(portfolio_values: list, cycle_returns: list) -> dict:

    if len(portfolio_values) < 2 or len(cycle_returns) < 2:
        return {}

    import math

    initial = portfolio_values[0]
    final = portfolio_values[-1]
    port_return = (final - initial) / initial if initial > 0 else 0.0

    returns = cycle_returns
    avg_return = sum(returns) / len(returns)
    std_return = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5

    # Sharpe 
    cycles_per_year = (365 * 24 * 3600) / INTERVAL_SECONDS
    sharpe = (avg_return / std_return * (cycles_per_year ** 0.5)) if std_return > 0 else 0.0

    # Sortino (only penalises downside volatility)
    downside = [r for r in returns if r < 0]
    downside_std = (sum(r ** 2 for r in downside) / len(downside)) ** 0.5 if downside else 0.0
    sortino = (avg_return / downside_std * (cycles_per_year ** 0.5)) if downside_std > 0 else 0.0

    # Max drawdown
    peak = portfolio_values[0]
    max_dd = 0.0
    for v in portfolio_values:
        peak = max(peak, v)
        dd = (peak - v) / peak if peak > 0 else 0.0
        max_dd = max(max_dd, dd)

    # Calmar
    annualised_return = port_return * (cycles_per_year / len(returns))
    calmar = (annualised_return / max_dd) if max_dd > 0 else 0.0

    return {
        'portfolio_return_pct': round(port_return * 100, 4),
        'sharpe_ratio': round(sharpe, 4),
        'sortino_ratio': round(sortino, 4),
        'calmar_ratio': round(calmar, 4),
        'max_drawdown_pct': round(max_dd * 100, 4),
        'initial_value_usd': round(initial, 2),
        'final_value_usd': round(final, 2),
    }


# ── main loop ─────────────────────────────────────────────────────────────────

def run_autobot(max_cycles: int = MAX_CYCLES):
    print(f"[{datetime.utcnow().isoformat()}] Starting autonomous trader for {PAIR}, max_cycles={max_cycles}")

    svm_model = None
    position_qty = 0.0
    entry_price = 0.0
    stop_loss = 0.0
    take_profit = 0.0

    portfolio_values = []
    cycle_returns = []
    prev_portfolio_value = None

    for cycle in range(max_cycles):
        try:
            # ── price ──────────────────────────────────────────────────────
            ticker = get_ticker(PAIR)
            price = float(ticker.get('lastPrice', 0.0))
            if price <= 0:
                print(f"[{datetime.utcnow().isoformat()}] Invalid price: {ticker}")
                time.sleep(INTERVAL_SECONDS)
                continue

            # ── market data & features ─────────────────────────────────────
            klines = fetch_klines(symbol=SYMBOL, interval='1d', limit=200)
            closes = closes_from_klines(klines)
            features, labels = build_sma_features(closes)

            if len(features) < 10:
                print("Not enough data for SVM training, holding")
                time.sleep(INTERVAL_SECONDS)
                continue

            if cycle % SVM_RETRAIN_INTERVAL == 0 or svm_model is None:
                svm_model = train_svm(features, labels)
                print(f"[{datetime.utcnow().isoformat()}] SVM model retrained at cycle {cycle+1}")

            current_feature = [
                sum(closes[-3:]) / 3.0,
                sum(closes[-10:]) / 10.0,
                (closes[-1] - closes[-2]) / closes[-2] if len(closes) > 1 else 0.0,
            ]
            signal = predict_signal(svm_model, current_feature)
            strategy_state = {
                'sma3': current_feature[0],
                'sma10': current_feature[1],
                'momentum': current_feature[2],
            }
            signal_reason = 'SVM prediction based on SMA features'

            # ── balance ────────────────────────────────────────────────────
            bal = parse_balance(get_balance())
            usd = bal.get('USD', bal.get('USDT', 0.0))
            btc = bal.get('BTC', 0.0)

            # ── portfolio tracking ─────────────────────────────────────────
            portfolio_value = compute_portfolio_value(usd, btc, price)
            portfolio_values.append(portfolio_value)
            if prev_portfolio_value is not None and prev_portfolio_value > 0:
                cycle_returns.append((portfolio_value - prev_portfolio_value) / prev_portfolio_value)
            prev_portfolio_value = portfolio_value

            # ── trade logic ────────────────────────────────────────────────
            side = 'HOLD'
            qty = 0.0
            order_id = ''
            api_response = ''
            api_status = ''
            api_success = True
            pnl = ''

            # ── Exit 1: SVM bearish signal closes open position ───────────
            # The SVM returning SELL means the model predicts price will fall.
            # We act on this immediately rather than waiting for TP/SL levels
            if position_qty > 0 and signal == 'SELL':
                print(f"[{datetime.utcnow().isoformat()}] SVM SELL signal — closing position at {price:.2f}, entry={entry_price:.2f}")
                resp = place_market_order(PAIR, 'SELL', position_qty)
                api_response = resp.text
                order_id, api_status, api_success = safe_order_response(resp)
                if api_success:
                    realized = (price - entry_price) * position_qty
                    pnl = round(realized, 6)
                    side = 'SELL'
                    qty = position_qty
                    position_qty = 0.0
                    entry_price = 0.0
                    stop_loss = 0.0
                    take_profit = 0.0
                    signal_reason = 'SVM SELL signal — bearish prediction'
                else:
                    print(f"[{datetime.utcnow().isoformat()}] SVM SELL order failed, status={api_status}, body={api_response}")

            # ── Exit 2: TP/SL hard stop (only if still in position) ───────
            # This fires if the SVM SELL above failed OR if the model said BUY/HOLD
            # but price hit a hard risk limit anyway.
            if position_qty > 0 and (price <= stop_loss or price >= take_profit):
                reason = 'take-profit' if price >= take_profit else 'stop-loss'
                print(f"[{datetime.utcnow().isoformat()}] {reason.upper()} hit at {price:.2f}, entry={entry_price:.2f}")
                resp = place_market_order(PAIR, 'SELL', position_qty)
                api_response = resp.text
                order_id, api_status, api_success = safe_order_response(resp)
                if api_success:
                    realized = (price - entry_price) * position_qty
                    pnl = round(realized, 6)
                    side = 'SELL'
                    qty = position_qty
                    position_qty = 0.0
                    entry_price = 0.0
                    stop_loss = 0.0
                    take_profit = 0.0
                    signal_reason = f'SVM SELL signal — {reason} triggered'
                else:
                    print(f"[{datetime.utcnow().isoformat()}] TP/SL SELL order failed, status={api_status}, body={api_response}")


            if side != 'SELL' and position_qty == 0 and signal == 'BUY' and usd > MIN_ORDER_USD:
                qty = round((usd * RISK_PER_TRADE) / price, 8)
                if qty > 0:
                    resp = place_market_order(PAIR, 'BUY', qty)
                    api_response = resp.text
                    order_id, api_status, api_success = safe_order_response(resp)
                    if api_success:
                        side = 'BUY'
                        position_qty = qty
                        entry_price = price
                        risk = 0.01 * entry_price
                        stop_loss = entry_price - risk
                        take_profit = entry_price + 2 * risk
                        pnl = 0.0
                    else:
                        print(f"[{datetime.utcnow().isoformat()}] BUY order failed, status={api_status}, body={api_response}")
                        side = 'HOLD'
                        qty = 0.0

            # ── log trade ──────────────────────────────────────────────────
            log_trade({
                'timestamp': datetime.utcnow().isoformat(),  
                'symbol': PAIR,
                'side': side,
                'price': price,
                'quantity': qty,
                'order_id': order_id,
                'api_status': api_status,          
                'api_success': api_success,      
                'api_response': api_response,
                'pnl': pnl,
                'portfolio_value_usd': round(portfolio_value, 2),  # NEW
                'signal_reason': signal_reason,
                'strategy_state': str({
                    **strategy_state,
                    'entry': entry_price,
                    'sl': stop_loss,
                    'tp': take_profit,
                    'pos': position_qty,
                }),
            })

            print(
                f"Cycle {cycle+1}: price={price:.2f}, signal={signal}, side={side}, "
                f"qty={qty}, pos={position_qty:.6f}, sl={stop_loss:.2f}, tp={take_profit:.2f}, "
                f"portfolio=${portfolio_value:.2f}"
            )

            # ── periodic performance snapshot (every 50 cycles) ───────────
            if (cycle + 1) % 50 == 0:
                metrics = compute_metrics(portfolio_values, cycle_returns)
                if metrics:
                    log_performance({**metrics, 'cycle': cycle + 1})
                    print(f"[METRICS] {metrics}")

            time.sleep(INTERVAL_SECONDS)

        except Exception as e:
            tb = traceback.format_exc()
            print(f"[{datetime.utcnow().isoformat()}] Error in cycle {cycle+1}: {e}")
            log_error({'cycle': cycle + 1, 'error': str(e), 'traceback': tb})
            time.sleep(INTERVAL_SECONDS)

    # ── final metrics on completion ────────────────────────────────────────
    metrics = compute_metrics(portfolio_values, cycle_returns)
    if metrics:
        log_performance({**metrics, 'cycle': max_cycles, 'final': True})
        print(f"\n=== FINAL PERFORMANCE ===")
        for k, v in metrics.items():
            print(f"  {k}: {v}")

    print("Autobot finished cleanly after max cycles.")


if __name__ == '__main__':
    run_autobot()