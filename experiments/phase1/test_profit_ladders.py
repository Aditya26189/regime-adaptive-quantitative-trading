
"""
Test profit-taking ladders on existing baseline strategies
Use code from hybrid_adaptive_v2.py (already implemented)
"""

import sys
import os
import pandas as pd
import numpy as np
import json

# Add project root to sys.path to allow imports from src
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '../../'))
sys.path.insert(0, project_root)

from src.strategies.hybrid_adaptive_v2 import HybridAdaptiveStrategyV2

def test_profit_ladders_all_symbols():
    """Test profit ladders on all symbols except SUNPHARMA"""
    
    symbols_to_test = {
        'RELIANCE': 'data/raw/NSE_RELIANCE_EQ_1hour.csv',
        'VBL': 'data/raw/NSE_VBL_EQ_1hour.csv',
        'YESBANK': 'data/raw/NSE_YESBANK_EQ_1hour.csv',
    }
    
    # Profit ladder configurations to test
    ladder_configs = [
        # Conservative (exit early)
        {
            'use_profit_ladder': True,
            'ladder_thresholds': [
                {'rsi_threshold': 55, 'exit_fraction': 0.50, 'reason': 'first_target'},
                {'rsi_threshold': 65, 'exit_fraction': 0.30, 'reason': 'second_target'},
                {'rsi_threshold': 75, 'exit_fraction': 0.20, 'reason': 'peak_target'},
            ]
        },
        
        # Moderate (balanced)
        {
            'use_profit_ladder': True,
            'ladder_thresholds': [
                {'rsi_threshold': 60, 'exit_fraction': 0.50, 'reason': 'first_target'},
                {'rsi_threshold': 70, 'exit_fraction': 0.25, 'reason': 'second_target'},
                {'rsi_threshold': 80, 'exit_fraction': 0.25, 'reason': 'peak_target'},
            ]
        },
        
        # Aggressive (let winners run)
        {
            'use_profit_ladder': True,
            'ladder_thresholds': [
                {'rsi_threshold': 65, 'exit_fraction': 0.33, 'reason': 'first_target'},
                {'rsi_threshold': 75, 'exit_fraction': 0.33, 'reason': 'second_target'},
                {'rsi_threshold': 85, 'exit_fraction': 0.34, 'reason': 'peak_target'},
            ]
        },
    ]
    
    results = {}
    
    for symbol, filepath in symbols_to_test.items():
        print("\n" + "="*70)
        print(f"TESTING PROFIT LADDERS: {symbol}")
        print("="*70)
        
        full_path = os.path.join(project_root, filepath)
        if not os.path.exists(full_path):
             # Try other path
             full_path = full_path.replace('data/raw/', 'data/')

        df = pd.read_csv(full_path)
        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.sort_values('datetime').reset_index(drop=True)
        
        symbol_results = []
        
        # Test baseline (no ladder) vs ladder configs
        for idx, ladder_config in enumerate([{'use_profit_ladder': False}] + ladder_configs):
            config_name = f"ladder_{idx}" if ladder_config['use_profit_ladder'] else "baseline"
            
            # Base parameters (from your current best configs)
            if symbol == 'RELIANCE':
                params = {
                    'ker_period': 10,
                    'rsi_period': 2,
                    'rsi_entry': 30,
                    'rsi_exit': 70,
                    'vol_min_pct': 0.005,
                    'max_hold_bars': 10,
                    'allowed_hours': [10, 11, 12, 13, 14],
                    'max_return_cap': 5.0,
                    'use_adaptive_hold': True
                }
            elif symbol == 'VBL':
                params = {
                    'ker_period': 10,
                    'rsi_period': 2,
                    'rsi_entry': 30,
                    'rsi_exit': 70,
                    'vol_min_pct': 0.005,
                    'max_hold_bars': 10,
                    'allowed_hours': [10, 11, 12, 13, 14],
                    'max_return_cap': 5.0,
                    'use_adaptive_hold': True
                }
            else:  # YESBANK
                params = {
                    'ker_period': 10,
                    'rsi_period': 2,
                    'rsi_entry': 30,
                    'rsi_exit': 70,
                    'vol_min_pct': 0.005,
                    'max_hold_bars': 10,
                    'allowed_hours': [10, 11, 12, 13, 14],
                    'max_return_cap': 5.0,
                    'use_adaptive_hold': True
                }
            
            # Add ladder config
            params.update(ladder_config)
            
            print(f"\n[Test {config_name}] {symbol}")
            
            strategy = HybridAdaptiveStrategyV2(params)
            trades, metrics = strategy.backtest(df)
            
            print(f"  Trades: {metrics['total_trades']}")
            print(f"  Sharpe: {metrics['sharpe_ratio']:.3f}")
            print(f"  Return: {metrics['total_return_pct']:.2f}%")
            print(f"  Win Rate: {metrics['win_rate']:.1f}%")
            
            symbol_results.append({
                'config': config_name,
                'params': params,
                'metrics': metrics
            })
        
        # Find best for this symbol
        valid_results = [r for r in symbol_results if r['metrics']['total_trades'] >= 120]
        
        if valid_results:
            best = max(valid_results, key=lambda x: x['metrics']['sharpe_ratio'])
            results[symbol] = best
            
            baseline_result = next((r for r in symbol_results if r['config'] == "baseline"), None)
            baseline_sharpe = baseline_result['metrics']['sharpe_ratio'] if baseline_result else 0
            
            print(f"\n✅ BEST {symbol}: {best['config']}")
            print(f"  Sharpe: {best['metrics']['sharpe_ratio']:.3f}")
            print(f"  Improvement: {best['metrics']['sharpe_ratio'] - baseline_sharpe:.3f}")
    
    return results

# RUN TEST
if __name__ == "__main__":
    ladder_results = test_profit_ladders_all_symbols()
    
    # Save results
    output_dir = os.path.join(project_root, 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    with open(os.path.join(output_dir, 'phase1_profit_ladders.json'), 'w') as f:
        # Convert to serializable format
        save_data = {}
        for symbol, result in ladder_results.items():
            save_data[symbol] = {
                'config': result['config'],
                'sharpe': result['metrics']['sharpe_ratio'],
                'trades': result['metrics']['total_trades'],
                'return_pct': result['metrics']['total_return_pct'],
                'params': result['params']
            }
        
        json.dump(save_data, f, indent=2)
    
    print("\n✅ Results saved to: output/phase1_profit_ladders.json")
