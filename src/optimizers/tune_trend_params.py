"""
Trend Parameter Tuning Script
Tests different EMA combinations and pulse multipliers to find positive returns
"""

import pandas as pd
import numpy as np
import sys
sys.path.insert(0, 'src/strategies')

from strategy_trend import backtest_trend_strategy, TrendConfig, Indicators

def test_params(symbol_name, file_path, symbol_code):
    """Test multiple parameter combinations"""
    print(f"\n{'='*70}")
    print(f"TUNING {symbol_name}")
    print(f"{'='*70}")
    
    df = pd.read_csv(file_path)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.sort_values('datetime').reset_index(drop=True)
    
    # Parameter combinations to test
    param_sets = [
        # Conservative (fewer trades, higher quality)
        {'ema_fast': 10, 'ema_slow': 30, 'pulse_mult': 0.5, 'max_hold': 25, 'desc': 'Conservative'},
        # Balanced
        {'ema_fast': 8, 'ema_slow': 21, 'pulse_mult': 0.4, 'max_hold': 20, 'desc': 'Balanced'},
        # Aggressive (more trades)
        {'ema_fast': 5, 'ema_slow': 15, 'pulse_mult': 0.3, 'max_hold': 15, 'desc': 'Aggressive'},
        # Very Aggressive
        {'ema_fast': 3, 'ema_slow': 10, 'pulse_mult': 0.2, 'max_hold': 10, 'desc': 'VeryAggressive'},
        # Morning only
        {'ema_fast': 8, 'ema_slow': 21, 'pulse_mult': 0.35, 'max_hold': 15, 'allowed_hours': [9, 10, 11], 'desc': 'MorningOnly'},
        # Longer trends
        {'ema_fast': 12, 'ema_slow': 34, 'pulse_mult': 0.6, 'max_hold': 30, 'desc': 'LongerTrends'},
    ]
    
    results = []
    
    for params in param_sets:
        desc = params.pop('desc')
        params['symbol'] = symbol_code
        params['timeframe'] = '60'
        if 'allowed_hours' not in params:
            params['allowed_hours'] = [9, 10, 11, 12, 13]
        
        trades, metrics = backtest_trend_strategy(df, params, TrendConfig())
        
        results.append({
            'desc': desc,
            'trades': metrics['trades'],
            'return': metrics['return'],
            'win_rate': metrics['win_rate'],
            'params': params.copy()
        })
        
        status = "✅" if metrics['trades'] >= 120 and metrics['return'] > 0 else "⚠️" if metrics['trades'] >= 120 else "❌"
        print(f"{status} {desc:15} | Trades: {metrics['trades']:3} | Return: {metrics['return']:>7.2f}% | Win: {metrics['win_rate']:.1f}%")
    
    # Find best valid result
    valid = [r for r in results if r['trades'] >= 120]
    if valid:
        best = max(valid, key=lambda x: x['return'])
        print(f"\n🏆 BEST for {symbol_name}: {best['desc']} ({best['trades']} trades, {best['return']:.2f}%)")
        return best
    else:
        print(f"\n❌ No valid results (all < 120 trades)")
        return None

def main():
    print("="*70)
    print("TREND PARAMETER TUNING")
    print("="*70)
    
    # Test NIFTY50
    nifty_best = test_params(
        'NIFTY50',
        'data/raw/NSE_NIFTY50_INDEX_1hour.csv',
        'NSE:NIFTY50-INDEX'
    )
    
    # Test YESBANK
    yesbank_best = test_params(
        'YESBANK',
        'data/raw/NSE_YESBANK_EQ_1hour.csv',
        'NSE:YESBANK-EQ'
    )
    
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    if nifty_best:
        print(f"NIFTY50: {nifty_best['return']:.2f}% ({nifty_best['trades']} trades)")
    if yesbank_best:
        print(f"YESBANK: {yesbank_best['return']:.2f}% ({yesbank_best['trades']} trades)")

if __name__ == "__main__":
    main()
