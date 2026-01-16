"""
RSI(2) V6 - 9AM Focus + Looser RSI to Boost Trade Count
=========================================================
9AM is the only profitable hour.
Try combining 9AM focus with much looser RSI thresholds.
"""

import pandas as pd
import numpy as np


def calculate_rsi(close, period=2):
    delta = close.diff()
    gains = delta.where(delta > 0, 0.0)
    losses = (-delta).where(delta < 0, 0.0)
    alpha = 1.0 / period
    avg_gain = gains.ewm(alpha=alpha, min_periods=period, adjust=False).mean()
    avg_loss = losses.ewm(alpha=alpha, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-10)
    return 100.0 - (100.0 / (1.0 + rs))


def calculate_volatility(close, period=14):
    rolling_max = close.rolling(window=period, min_periods=period).max()
    rolling_min = close.rolling(window=period, min_periods=period).min()
    return (rolling_max - rolling_min) / close


def backtest(df, params, initial_capital=100000):
    df = df.copy()
    df['rsi2'] = calculate_rsi(df['close'], period=2)
    df['volatility'] = calculate_volatility(df['close'], period=14)
    
    if df['datetime'].dtype == 'object':
        df['datetime_parsed'] = pd.to_datetime(df['datetime'])
    else:
        df['datetime_parsed'] = df['datetime']
    df['hour'] = df['datetime_parsed'].dt.hour
    
    rsi_entry = params['RSI_ENTRY']
    rsi_exit = params['RSI_EXIT']
    allowed_hours = params.get('ALLOWED_HOURS', [9, 10, 11, 12, 13, 14])
    vol_min = params.get('VOL_MIN', 0.001)
    max_hold = params.get('MAX_HOLD', 12)
    
    warmup = 50
    capital = initial_capital
    position = 0
    entry_price = 0
    bars_held = 0
    trades = []
    
    for i in range(warmup, len(df)):
        prev_rsi = df['rsi2'].iloc[i-1]
        prev_vol = df['volatility'].iloc[i-1]
        current_price = df['close'].iloc[i]
        current_hour = df['hour'].iloc[i]
        
        if pd.isna(prev_rsi) or pd.isna(prev_vol):
            continue
        
        if position > 0:
            bars_held += 1
            if prev_rsi > rsi_exit or bars_held >= max_hold or current_hour >= 15:
                pnl_pct = (current_price - entry_price) / entry_price
                net_pnl = (current_price - entry_price) * position - 48
                capital += (position * current_price) - 24
                trades.append({'pnl': pnl_pct, 'net': net_pnl})
                position = 0
                bars_held = 0
                continue
        
        if position == 0:
            if prev_rsi < rsi_entry and prev_vol > vol_min and current_hour in allowed_hours:
                available = capital - 24
                qty = int(available / current_price)
                if qty > 0:
                    position = qty
                    entry_price = current_price
                    capital -= (qty * current_price) + 24
                    bars_held = 0
    
    if not trades:
        return {'trades': 0, 'return': 0, 'sharpe': 0, 'win_rate': 0}
    
    returns = np.array([t['pnl'] for t in trades])
    total_return = (capital - initial_capital) / initial_capital * 100
    win_rate = sum(1 for r in returns if r > 0) / len(returns) * 100
    sharpe = np.mean(returns) / np.std(returns) * np.sqrt(250*7) if np.std(returns) > 0 else 0
    
    return {
        'trades': len(trades),
        'return': round(total_return, 2),
        'sharpe': round(sharpe, 2),
        'win_rate': round(win_rate, 2)
    }


def main():
    symbols = [
        ("NIFTY50", "fyers_data/NSE_NIFTY50_INDEX_1hour.csv"),
        ("RELIANCE", "fyers_data/NSE_RELIANCE_EQ_1hour.csv"),
        ("VBL", "fyers_data/NSE_VBL_EQ_1hour.csv"),
        ("YESBANK", "fyers_data/NSE_YESBANK_EQ_1hour.csv"),
        ("SUNPHARMA", "fyers_data/NSE_SUNPHARMA_EQ_1hour.csv"),
    ]
    
    # Variants: combine 9AM (+ maybe 10AM) with different RSI thresholds
    variants = [
        {
            "name": "9AM + RSI<40",
            "RSI_ENTRY": 40,
            "RSI_EXIT": 70,
            "ALLOWED_HOURS": [9],
            "VOL_MIN": 0.001,
            "MAX_HOLD": 8,
        },
        {
            "name": "9AM + RSI<50",
            "RSI_ENTRY": 50,
            "RSI_EXIT": 65,
            "ALLOWED_HOURS": [9],
            "VOL_MIN": 0.001,
            "MAX_HOLD": 6,
        },
        {
            "name": "9-10AM + RSI<30",
            "RSI_ENTRY": 30,
            "RSI_EXIT": 75,
            "ALLOWED_HOURS": [9, 10],
            "VOL_MIN": 0.001,
            "MAX_HOLD": 10,
        },
        {
            "name": "9-10AM + RSI<35",
            "RSI_ENTRY": 35,
            "RSI_EXIT": 70,
            "ALLOWED_HOURS": [9, 10],
            "VOL_MIN": 0.001,
            "MAX_HOLD": 8,
        },
        {
            "name": "9-10AM + RSI<40",
            "RSI_ENTRY": 40,
            "RSI_EXIT": 65,
            "ALLOWED_HOURS": [9, 10],
            "VOL_MIN": 0.001,
            "MAX_HOLD": 6,
        },
        {
            "name": "Baseline (all hours)",
            "RSI_ENTRY": 20,
            "RSI_EXIT": 90,
            "ALLOWED_HOURS": [9, 10, 11, 12, 13, 14],
            "VOL_MIN": 0.002,
            "MAX_HOLD": 12,
        },
    ]
    
    print("="*90)
    print("9AM FOCUS WITH LOOSER RSI - FINDING OPTIMAL COMBINATION")
    print("="*90)
    
    for v in variants:
        print(f"\n{'='*70}")
        print(f"VARIANT: {v['name']}")
        print(f"Hours: {v['ALLOWED_HOURS']}, RSI<{v['RSI_ENTRY']}, Exit>{v['RSI_EXIT']}")
        print(f"{'='*70}")
        
        total_trades = 0
        total_return = 0
        passed = 0
        positive = 0
        
        for symbol, fp in symbols:
            df = pd.read_csv(fp)
            r = backtest(df, v)
            
            status = "✅" if r['trades'] >= 120 and r['return'] > 0 else \
                     "⚠️" if r['trades'] >= 120 else "❌"
            
            print(f"{status} {symbol:12} | T:{r['trades']:3} | Ret:{r['return']:>+7.2f}% | Win:{r['win_rate']:5.1f}%")
            
            total_trades += r['trades']
            total_return += r['return']
            if r['trades'] >= 120:
                passed += 1
            if r['return'] > 0:
                positive += 1
        
        print(f"\nSummary: Avg T={total_trades/5:.0f}, Avg Ret={total_return/5:+.2f}%, "
              f"Pass120: {passed}/5, Positive: {positive}/5")
    
    print("\n" + "="*90)


if __name__ == "__main__":
    main()
