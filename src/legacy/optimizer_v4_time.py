"""
RSI(2) Optimizer V4 - Time-of-Day Analysis
============================================
Analyze which hours have best mean reversion performance.
Maybe certain hours are more profitable.
"""

import pandas as pd
import numpy as np
from collections import defaultdict


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


def analyze_by_hour(df, rsi_entry=20, rsi_exit=90):
    """Analyze trade performance by entry hour."""
    
    df = df.copy()
    df['rsi2'] = calculate_rsi(df['close'], period=2)
    df['volatility'] = calculate_volatility(df['close'], period=14)
    
    if df['datetime'].dtype == 'object':
        df['datetime_parsed'] = pd.to_datetime(df['datetime'])
    else:
        df['datetime_parsed'] = df['datetime']
    
    df['hour'] = df['datetime_parsed'].dt.hour
    
    warmup = 50
    trades_by_hour = defaultdict(list)
    
    position = 0
    entry_price = 0
    entry_hour = 0
    bars_held = 0
    
    for i in range(warmup, len(df)):
        prev_rsi = df['rsi2'].iloc[i-1]
        prev_vol = df['volatility'].iloc[i-1]
        
        current_price = df['close'].iloc[i]
        current_hour = df['hour'].iloc[i]
        
        if pd.isna(prev_rsi) or pd.isna(prev_vol):
            continue
        
        # EXIT
        if position > 0:
            bars_held += 1
            exit_rsi = prev_rsi > rsi_exit
            exit_time = bars_held >= 12
            exit_eod = current_hour >= 15
            
            if exit_rsi or exit_time or exit_eod:
                pnl_pct = (current_price - entry_price) / entry_price
                trades_by_hour[entry_hour].append(pnl_pct)
                position = 0
                entry_price = 0
                bars_held = 0
                continue
        
        # ENTRY
        if position == 0:
            cond_rsi = prev_rsi < rsi_entry
            cond_vol = prev_vol > 0.002
            cond_time = current_hour < 15
            
            if cond_rsi and cond_vol and cond_time:
                position = 1
                entry_price = current_price
                entry_hour = current_hour
                bars_held = 0
    
    return trades_by_hour


def main():
    symbols = [
        ("NIFTY50", "fyers_data/NSE_NIFTY50_INDEX_1hour.csv"),
        ("RELIANCE", "fyers_data/NSE_RELIANCE_EQ_1hour.csv"),
        ("VBL", "fyers_data/NSE_VBL_EQ_1hour.csv"),
        ("YESBANK", "fyers_data/NSE_YESBANK_EQ_1hour.csv"),
        ("SUNPHARMA", "fyers_data/NSE_SUNPHARMA_EQ_1hour.csv"),
    ]
    
    print("="*80)
    print("TIME-OF-DAY ANALYSIS - Mean Reversion Performance by Entry Hour")
    print("="*80)
    
    all_by_hour = defaultdict(list)
    
    for symbol, fp in symbols:
        print(f"\n{symbol}:")
        print("-"*60)
        
        df = pd.read_csv(fp)
        trades_by_hour = analyze_by_hour(df)
        
        print(f"{'Hour':<6} {'Trades':<8} {'Avg Return':<12} {'Win Rate':<10} {'Net Gain'}")
        
        for hour in sorted(trades_by_hour.keys()):
            returns = trades_by_hour[hour]
            count = len(returns)
            avg_ret = np.mean(returns) * 100
            win_rate = sum(1 for r in returns if r > 0) / count * 100
            net = sum(returns) * 100
            
            all_by_hour[hour].extend(returns)
            
            indicator = "✅" if avg_ret > 0 else "❌"
            print(f"{hour:02d}:00  {count:<8} {avg_ret:>+10.2f}%   {win_rate:>6.1f}%   {net:>+10.2f}% {indicator}")
    
    print("\n" + "="*80)
    print("AGGREGATE ACROSS ALL SYMBOLS")
    print("="*80)
    print(f"{'Hour':<6} {'Trades':<8} {'Avg Return':<12} {'Win Rate':<10}")
    
    best_hours = []
    for hour in sorted(all_by_hour.keys()):
        returns = all_by_hour[hour]
        count = len(returns)
        avg_ret = np.mean(returns) * 100
        win_rate = sum(1 for r in returns if r > 0) / count * 100
        
        indicator = "✅" if avg_ret > 0 else "  "
        print(f"{hour:02d}:00  {count:<8} {avg_ret:>+10.3f}%   {win_rate:>6.1f}% {indicator}")
        
        if avg_ret > 0:
            best_hours.append(hour)
    
    print("\n" + "="*80)
    if best_hours:
        print(f"PROFITABLE HOURS: {best_hours}")
        print("Consider restricting entries to these hours only")
    else:
        print("NO CONSISTENTLY PROFITABLE HOURS FOUND")
    print("="*80)


if __name__ == "__main__":
    main()
