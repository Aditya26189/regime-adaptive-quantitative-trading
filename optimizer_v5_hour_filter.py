"""
RSI(2) Optimizer V5 - 9 AM Only Trading
=========================================
Based on time-of-day analysis, 9 AM entries are the only profitable ones.
Test if restricting to 9 AM only meets trade count requirements.
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass


@dataclass
class Result:
    trades: int
    total_return: float
    sharpe: float
    win_rate: float


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


def backtest_with_hour_filter(df, allowed_hours, rsi_entry=20, rsi_exit=90, initial_capital=100000):
    """Backtest with entry restricted to specific hours."""
    
    df = df.copy()
    df['rsi2'] = calculate_rsi(df['close'], period=2)
    df['volatility'] = calculate_volatility(df['close'], period=14)
    
    if df['datetime'].dtype == 'object':
        df['datetime_parsed'] = pd.to_datetime(df['datetime'])
    else:
        df['datetime_parsed'] = df['datetime']
    
    df['hour'] = df['datetime_parsed'].dt.hour
    
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
        
        # EXIT
        if position > 0:
            bars_held += 1
            exit_rsi = prev_rsi > rsi_exit
            exit_time = bars_held >= 12
            exit_eod = current_hour >= 15
            
            if exit_rsi or exit_time or exit_eod:
                pnl_pct = (current_price - entry_price) / entry_price
                net_pnl = (current_price - entry_price) * position - 48
                capital += (position * current_price) - 24
                trades.append({'pnl_pct': pnl_pct, 'net_pnl': net_pnl})
                position = 0
                entry_price = 0
                bars_held = 0
                continue
        
        # ENTRY - only during allowed hours
        if position == 0:
            cond_rsi = prev_rsi < rsi_entry
            cond_vol = prev_vol > 0.002
            cond_hour = current_hour in allowed_hours  # HOUR FILTER
            
            if cond_rsi and cond_vol and cond_hour:
                available = capital - 24
                qty = int(available / current_price)
                if qty > 0:
                    position = qty
                    entry_price = current_price
                    capital -= (qty * current_price) + 24
                    bars_held = 0
    
    if not trades:
        return Result(0, 0, 0, 0)
    
    returns = np.array([t['pnl_pct'] for t in trades])
    total_return = (capital - initial_capital) / initial_capital * 100
    win_rate = sum(1 for r in returns if r > 0) / len(returns) * 100
    
    if len(returns) > 1 and np.std(returns) > 0:
        sharpe = np.mean(returns) / np.std(returns) * np.sqrt(250 * 7)
    else:
        sharpe = 0
    
    return Result(len(trades), round(total_return, 2), round(sharpe, 2), round(win_rate, 2))


def main():
    symbols = [
        ("NIFTY50", "fyers_data/NSE_NIFTY50_INDEX_1hour.csv"),
        ("RELIANCE", "fyers_data/NSE_RELIANCE_EQ_1hour.csv"),
        ("VBL", "fyers_data/NSE_VBL_EQ_1hour.csv"),
        ("YESBANK", "fyers_data/NSE_YESBANK_EQ_1hour.csv"),
        ("SUNPHARMA", "fyers_data/NSE_SUNPHARMA_EQ_1hour.csv"),
    ]
    
    # Test different hour combinations
    hour_filters = [
        ("All hours (baseline)", [9, 10, 11, 12, 13, 14]),
        ("9 AM only", [9]),
        ("9-10 AM", [9, 10]),
        ("9-11 AM", [9, 10, 11]),
        ("9 AM + 13-14 PM", [9, 13, 14]),
    ]
    
    print("="*90)
    print("TIME-OF-DAY FILTER TESTING")
    print("="*90)
    
    for filter_name, hours in hour_filters:
        print(f"\n{'='*70}")
        print(f"FILTER: {filter_name}")
        print(f"{'='*70}")
        
        total_trades = 0
        total_return = 0
        all_pass = True
        
        for symbol, fp in symbols:
            df = pd.read_csv(fp)
            result = backtest_with_hour_filter(df, hours)
            
            status = "✅" if result.trades >= 120 and result.total_return > 0 else \
                     "⚠️" if result.trades >= 120 else "❌"
            
            print(f"{status} {symbol:15} | Trades: {result.trades:3} | "
                  f"Return: {result.total_return:>+7.2f}% | Win: {result.win_rate:5.1f}%")
            
            total_trades += result.trades
            total_return += result.total_return
            if result.trades < 120:
                all_pass = False
        
        avg_trades = total_trades / 5
        avg_return = total_return / 5
        
        print(f"\nAverage: Trades={avg_trades:.0f}, Return={avg_return:+.2f}%")
        print(f"Passes 120 trade minimum: {'YES' if all_pass else 'NO'}")
    
    print("\n" + "="*90)
    print("CONCLUSION:")
    print("- 9 AM only has best returns but likely insufficient trades")
    print("- Need to balance profitable hours with trade count requirement")
    print("="*90)


if __name__ == "__main__":
    main()
