"""
Trace NIFTY Logic with Loose Parameters
"""
import pandas as pd
from src.strategies.nifty_trend_strategy import generate_nifty_trend_signals

data = pd.read_csv('data/raw/NSE_NIFTY50_INDEX_1hour.csv')

# LOOSE params
params = {
    'ema_fast': 5,
    'ema_slow': 15, # Closer means more crossovers
    'momentum_period': 3,
    'momentum_threshold': 0.1, # Very low
    'ema_diff_threshold': 0.02, # Very low
    'vol_min': 0.01, # Effective OFF
    'allowed_hours': [9, 10, 11, 12, 13, 14],
    'max_hold': 5,
    'vol_period': 14
}

print("Testing Loose Parameters:")
for k,v in params.items():
    print(f"  {k}: {v}")

trades = generate_nifty_trend_signals(data, params)
print(f"\nTrades generated: {len(trades)}")

if len(trades) > 0:
    df = trades
    total_ret = df['pnl'].sum() / 100000 * 100
    win_rate = (df['pnl'] > 0).sum() / len(df) * 100
    print(f"Return: {total_ret:.2f}%")
    print(f"Win Rate: {win_rate:.1f}%")
