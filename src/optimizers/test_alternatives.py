"""
Alternative Strategy Test for NIFTY50 and YESBANK
Testing both mean-reversion and trend to find best approach
"""

import pandas as pd
import numpy as np
import sys
sys.path.insert(0, 'src/strategies')
sys.path.insert(0, 'src/utils')

from indicators import calculate_rsi, calculate_volatility

def backtest_meanrev(df, params):
    """Mean reversion backtest"""
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
        return {'trades': 0, 'return': 0}
    
    trades_df = pd.DataFrame(trades)
    total_return = (capital - 100000) / 100000 * 100
    win_rate = (trades_df['pnl'] > 0).sum() / len(trades_df) * 100
    
    return {'trades': len(trades_df), 'return': total_return, 'win_rate': win_rate}

def test_symbol(symbol, file_path):
    """Test various parameter combinations"""
    print(f"\n{'='*70}")
    print(f"TESTING {symbol}")
    print(f"{'='*70}")
    
    df = pd.read_csv(file_path)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.sort_values('datetime').reset_index(drop=True)
    
    # Mean reversion parameter sets
    param_sets = [
        # Current best (from fast_optimizer)
        {'rsi_entry': 31, 'rsi_exit': 66, 'vol_min': 0.0084, 'allowed_hours': [10, 11, 12, 13], 'max_hold': 1, 'desc': 'Current'},
        # Looser entry
        {'rsi_entry': 35, 'rsi_exit': 60, 'vol_min': 0.005, 'allowed_hours': [9, 10, 11, 12, 13], 'max_hold': 3, 'desc': 'Looser'},
        # Very loose
        {'rsi_entry': 40, 'rsi_exit': 55, 'vol_min': 0.003, 'allowed_hours': [9, 10, 11, 12, 13], 'max_hold': 5, 'desc': 'VeryLoose'},
        # Morning focused
        {'rsi_entry': 35, 'rsi_exit': 65, 'vol_min': 0.004, 'allowed_hours': [9, 10, 11], 'max_hold': 4, 'desc': 'Morning'},
        # Extended hours
        {'rsi_entry': 38, 'rsi_exit': 58, 'vol_min': 0.004, 'allowed_hours': [9, 10, 11, 12, 13, 14], 'max_hold': 4, 'desc': 'Extended'},
        # Short hold
        {'rsi_entry': 32, 'rsi_exit': 55, 'vol_min': 0.005, 'allowed_hours': [9, 10, 11, 12], 'max_hold': 2, 'desc': 'ShortHold'},
    ]
    
    results = []
    
    for params in param_sets:
        desc = params.pop('desc')
        result = backtest_meanrev(df, params)
        
        status = "✅" if result['trades'] >= 120 and result['return'] > 0 else "⚠️" if result['trades'] >= 120 else "❌"
        print(f"{status} {desc:12} | Trades: {result['trades']:3} | Return: {result['return']:>7.2f}% | Win: {result.get('win_rate', 0):.1f}%")
        
        results.append({
            'desc': desc,
            'trades': result['trades'],
            'return': result['return'],
            'params': params.copy()
        })
    
    # Find best valid result
    valid = [r for r in results if r['trades'] >= 120]
    if valid:
        best = max(valid, key=lambda x: x['return'])
        print(f"\n🏆 BEST: {best['desc']} ({best['trades']} trades, {best['return']:.2f}%)")
        return best
    return None

def main():
    print("="*70)
    print("ALTERNATIVE STRATEGY TESTING")
    print("="*70)
    
    nifty = test_symbol('NIFTY50', 'data/raw/NSE_NIFTY50_INDEX_1hour.csv')
    yesbank = test_symbol('YESBANK', 'data/raw/NSE_YESBANK_EQ_1hour.csv')
    
    print("\n" + "="*70)
    print("FINAL RESULTS")
    print("="*70)
    
    if nifty:
        print(f"NIFTY50: {nifty['return']:.2f}% ({nifty['trades']} trades)")
    if yesbank:
        print(f"YESBANK: {yesbank['return']:.2f}% ({yesbank['trades']} trades)")

if __name__ == "__main__":
    main()
