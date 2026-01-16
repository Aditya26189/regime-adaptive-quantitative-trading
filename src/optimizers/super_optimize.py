"""
Super-Optimize VBL and SUNPHARMA with Extended Search
Targets: VBL +16-18%, SUNPHARMA +10-12%
"""

import pandas as pd
import numpy as np
import random
import json
import sys
sys.path.insert(0, 'src/utils')
from indicators import calculate_rsi, calculate_volatility

def backtest(df, params):
    """Backtest symbol with given parameters"""
    df = df.copy()
    df['rsi2'] = calculate_rsi(df['close'])
    df['volatility'] = calculate_volatility(df['close'])
    
    trades = []
    capital = 100000
    
    in_position = False
    entry_price = 0
    entry_capital = 0
    entry_qty = 0
    bars_held = 0
    
    for i in range(50, len(df)):
        current_time = df['datetime'].iloc[i]
        current_hour = current_time.hour
        current_minute = current_time.minute
        current_close = df['close'].iloc[i]
        
        prev_rsi = df['rsi2'].iloc[i-1]
        prev_vol = df['volatility'].iloc[i-1]
        
        if pd.isna(prev_rsi) or pd.isna(prev_vol):
            continue
        
        if not in_position:
            if current_hour not in params['allowed_hours']:
                continue
            if current_hour >= 14 and current_minute >= 30:
                continue
            
            if prev_rsi < params['rsi_entry'] and prev_vol > params['vol_min']:
                qty = int((capital - 24) * 0.95 / current_close)
                
                if qty > 0:
                    entry_price = current_close
                    entry_capital = capital
                    entry_qty = qty
                    capital -= 24
                    in_position = True
                    bars_held = 0
        else:
            bars_held += 1
            
            exit_signal = (
                prev_rsi > params['rsi_exit'] or
                bars_held >= params['max_hold'] or
                (current_hour >= 15 and current_minute >= 15)
            )
            
            if exit_signal:
                exit_price = current_close
                gross_pnl = entry_qty * (exit_price - entry_price)
                capital = entry_capital + gross_pnl - 48
                trades.append({'pnl': gross_pnl - 48})
                in_position = False
    
    if len(trades) == 0:
        return 0, 0, 0
    
    trades_df = pd.DataFrame(trades)
    return len(trades_df), (capital - 100000) / 100000 * 100, (trades_df['pnl'] > 0).sum() / len(trades_df) * 100

def super_optimize(symbol, file_path, num_samples=1000):
    """Extended optimization with more samples"""
    print(f"\n{'='*70}")
    print(f"SUPER-OPTIMIZING {symbol} ({num_samples} samples)")
    print(f"{'='*70}")
    
    df = pd.read_csv(file_path)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.sort_values('datetime').reset_index(drop=True)
    
    random.seed(42)
    
    best_return = -999
    best_params = None
    best_trades = 0
    positive_count = 0
    
    hour_choices = [
        [9, 10], [9, 10, 11], [10, 11], [9, 10, 11, 12],
        [10, 11, 12], [9, 10, 11, 12, 13]
    ]
    
    for i in range(num_samples):
        if (i + 1) % 200 == 0:
            print(f"  Progress: {i + 1}/{num_samples}")
        
        params = {
            'rsi_entry': random.randint(30, 45),
            'rsi_exit': random.randint(85, 98),  # High exits for VBL-type
            'vol_min': round(random.uniform(0.005, 0.012), 4),
            'allowed_hours': random.choice(hour_choices),
            'max_hold': random.randint(6, 15)
        }
        
        trades, ret, win_rate = backtest(df, params)
        
        if trades >= 120:
            if ret > 0:
                positive_count += 1
            if ret > best_return:
                best_return = ret
                best_params = params.copy()
                best_trades = trades
                print(f"  🎯 New best: {ret:.2f}% ({trades} trades)")
    
    print(f"\n✅ Found {positive_count} positive configurations")
    print(f"\n🏆 BEST RESULT:")
    print(f"   Trades: {best_trades}")
    print(f"   Return: {best_return:.2f}%")
    print(f"   Params: {best_params}")
    
    return best_params, best_return, best_trades

def main():
    print("="*70)
    print("SUPER-OPTIMIZATION FOR VBL AND SUNPHARMA")
    print("="*70)
    
    # Super-optimize VBL
    vbl_params, vbl_return, vbl_trades = super_optimize(
        'VBL',
        'data/raw/NSE_VBL_EQ_1hour.csv',
        num_samples=1000
    )
    
    # Super-optimize SUNPHARMA with different range
    print(f"\n{'='*70}")
    print(f"SUPER-OPTIMIZING SUNPHARMA (1000 samples)")
    print(f"{'='*70}")
    
    df = pd.read_csv('data/raw/NSE_SUNPHARMA_EQ_1hour.csv')
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.sort_values('datetime').reset_index(drop=True)
    
    random.seed(42)
    
    best_return = -999
    best_params = None
    best_trades = 0
    positive_count = 0
    
    hour_choices = [
        [9, 10], [9, 10, 11], [10, 11], [9, 10, 11, 12],
        [10, 11, 12], [9, 10, 11, 12, 13]
    ]
    
    for i in range(1000):
        if (i + 1) % 200 == 0:
            print(f"  Progress: {i + 1}/1000")
        
        params = {
            'rsi_entry': random.randint(32, 45),  # SUNPHARMA: looser entries
            'rsi_exit': random.randint(48, 70),   # SUNPHARMA: quicker exits
            'vol_min': round(random.uniform(0.003, 0.008), 4),
            'allowed_hours': random.choice(hour_choices),
            'max_hold': random.randint(5, 12)
        }
        
        trades, ret, win_rate = backtest(df, params)
        
        if trades >= 120:
            if ret > 0:
                positive_count += 1
            if ret > best_return:
                best_return = ret
                best_params = params.copy()
                best_trades = trades
                print(f"  🎯 New best: {ret:.2f}% ({trades} trades)")
    
    print(f"\n✅ Found {positive_count} positive configurations")
    print(f"\n🏆 SUNPHARMA BEST:")
    print(f"   Trades: {best_trades}")
    print(f"   Return: {best_return:.2f}%")
    print(f"   Params: {best_params}")
    
    sun_params, sun_return, sun_trades = best_params, best_return, best_trades
    
    # Summary
    print("\n" + "="*70)
    print("SUPER-OPTIMIZATION COMPLETE")
    print("="*70)
    print(f"VBL: {vbl_return:.2f}% ({vbl_trades} trades)")
    print(f"SUNPHARMA: {sun_return:.2f}% ({sun_trades} trades)")
    
    # Save results
    results = {
        'VBL': {'params': vbl_params, 'return': vbl_return, 'trades': vbl_trades},
        'SUNPHARMA': {'params': sun_params, 'return': sun_return, 'trades': sun_trades}
    }
    
    with open('output/super_optimized_params.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Saved to: output/super_optimized_params.json")

if __name__ == "__main__":
    main()
