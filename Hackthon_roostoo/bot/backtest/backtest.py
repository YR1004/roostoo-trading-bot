from bot.data.binance_data import fetch_klines, closes_from_klines


def backtest_sma_crossover(symbol='BTCUSDT', interval='1d', lookback=240, initial_cash=10000.0, risk_pct=0.1, commission=0.0006):
    klines = fetch_klines(symbol=symbol, interval=interval, limit=lookback)
    closes = closes_from_klines(klines)
    if len(closes) < 50:
        raise ValueError('Need at least 50 candles')
    sma3 = [sum(closes[i-3:i]) / 3 for i in range(3, len(closes)+1)]
    sma10 = [sum(closes[i-10:i]) / 10 for i in range(10, len(closes)+1)]

    cash = initial_cash
    position = 0.0
    trades = []
    equity_curve = []

    # offset: sma3 starts at idx2 (3rd close), sma10 at idx9
    for i in range(10, len(closes)):
        price = closes[i]
        ma3 = sma3[i-2]
        ma10 = sma10[i-9]
        signal = 'HOLD'
        if ma3 > ma10 and position == 0:
            signal = 'BUY'
        elif ma3 < ma10 and position > 0:
            signal = 'SELL'

        if signal == 'BUY':
            qty = (cash * risk_pct) / price
            cost = qty * price * (1 + commission)
            if cost <= cash:
                cash -= cost
                position += qty
                trades.append({'day': i, 'signal': 'BUY', 'price': price, 'qty': qty})
        elif signal == 'SELL' and position > 0:
            proceeds = position * price * (1 - commission)
            cash += proceeds
            trades.append({'day': i, 'signal': 'SELL', 'price': price, 'qty': position})
            position = 0.0

        equity_curve.append(cash + position * price)

    final_value = cash + position * closes[-1]
    pnl = final_value - initial_cash
    wins = 0
    total_pairs = 0
    for j in range(1, len(trades), 2):
        b = trades[j-1]
        s = trades[j]
        if s['price'] > b['price']:
            wins += 1
        total_pairs += 1
    win_rate = (wins / total_pairs * 100) if total_pairs else 0

    return {
        'initial_cash': initial_cash,
        'final_value': final_value,
        'pnl': pnl,
        'return_pct': pnl / initial_cash * 100,
        'n_trades': len(trades),
        'win_rate': win_rate,
        'equity_curve': equity_curve,
        'trades': trades,
    }


if __name__ == '__main__':
    res = backtest_sma_crossover()
    print('SMA Crossover Backtest results:')
    print(f"Initial cash: {res['initial_cash']}")
    print(f"Final value: {res['final_value']:.2f}")
    print(f"PnL: {res['pnl']:.2f} ({res['return_pct']:.2f}%)")
    print(f"Trades: {res['n_trades']}, Win rate: {res['win_rate']:.2f}%")
    print('Last equity:', res['equity_curve'][-5:])
    print('First 10 trades:', res['trades'][:10])
