"""
Debug NIFTY50 Trend Strategy
"""
import pandas as pd
import numpy as np
from src.strategies.nifty_trend_strategy import generate_nifty_trend_signals

# Load data
data = pd.read_csv('data/raw/NSE_NIFTY50_INDEX_1hour.csv')
print(f"Data loaded: {len(data)} rows")

# Default params
params = {
    'ema_fast': 8,
    'ema_slow': 21,
    'momentum_period': 5,
    'momentum_threshold': 0.4,
    'ema_diff_threshold': 0.1, # Lowered for debug
    'vol_min': 0.005,
    'allowed_hours': [9, 10, 11, 12, 13, 14], # All hours
    'max_hold': 8,
    'vol_period': 14
}

trades = generate_nifty_trend_signals(data, params)
print(f"Trades found: {len(trades)}")

# Inspect indicators manually to see ranges
df = data.copy()
df['timestamp'] = pd.to_datetime(df['datetime'])
df['ema_fast'] = df['close'].ewm(span=params['ema_fast'], adjust=False).mean()
df['ema_slow'] = df['close'].ewm(span=params['ema_slow'], adjust=False).mean()
df['ema_diff'] = (df['ema_fast'] - df['ema_slow']) / df['ema_slow'] * 100
df['momentum'] = df['close'].pct_change(params['momentum_period']) * 100
df['volatility'] = df['close'].pct_change().rolling(14).std() * 100

print("\nIndicator Stats:")
print(f"EMA Diff Max: {df['ema_diff'].max():.4f}")
print(f"EMA Diff Min: {df['ema_diff'].min():.4f}")
print(f"EMA Diff Mean: {df['ema_diff'].mean():.4f}")
print(f"Momentum Max: {df['momentum'].max():.4f}")
print(f"Volatility Max: {df['volatility'].max():.4f}")
print(f"Volatility Mean: {df['volatility'].mean():.4f}")

# Check conditions count
cond_uptrend = (df['ema_diff'] > params['ema_diff_threshold']).sum()
cond_momentum = (df['momentum'] > params['momentum_threshold']).sum()
cond_vol = (df['volatility'] > params['vol_min']).sum()

print(f"\nConditions met (rows):")
print(f"Uptrend (> {params['ema_diff_threshold']}): {cond_uptrend}")
print(f"Momentum (> {params['momentum_threshold']}): {cond_momentum}")
print(f"Volatility (> {params['vol_min']}): {cond_vol}")
