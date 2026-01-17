
"""
Walk-Forward Validation: Prevent overfitting via time-series cross-validation
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Callable
import json
import os
import sys

# Add project root to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '../../'))
sys.path.insert(0, project_root)

from src.strategies.hybrid_adaptive import HybridAdaptiveStrategy

class WalkForwardValidator:
    """
    Time-series cross-validation for trading strategies
    """
    
    def __init__(self, train_days=120, test_days=30, step_days=20):
        """
        Args:
            train_days: Training window (in trading days)
            test_days: Test window (in trading days)
            step_days: Step size for rolling window
        """
        # Convert days to hours (assuming 6 trading hours per day)
        self.train_window = train_days * 6
        self.test_window = test_days * 6
        self.step_size = step_days * 6
    
    def validate(self, df, strategy_class, param_grid, optimize_func):
        """
        Run walk-forward validation
        """
        
        results = []
        
        n_periods = (len(df) - self.train_window - self.test_window) // self.step_size
        
        print(f"\n{'='*70}")
        print(f"WALK-FORWARD VALIDATION")
        print(f"{'='*70}")
        print(f"Train window: {self.train_window // 6} days ({self.train_window} bars)")
        print(f"Test window: {self.test_window // 6} days ({self.test_window} bars)")
        print(f"Step size: {self.step_size // 6} days ({self.step_size} bars)")
        print(f"Total periods: {n_periods}")
        
        for period_idx in range(n_periods):
            start_idx = period_idx * self.step_size
            train_end = start_idx + self.train_window
            test_end = train_end + self.test_window
            
            if test_end > len(df):
                break
            
            # Split data
            train_data = df.iloc[start_idx:train_end].copy()
            test_data = df.iloc[train_end:test_end].copy()
            
            # print(f"\n[Period {period_idx+1}/{n_periods}]")
            # print(f"  Train: {train_data['datetime'].iloc[0]} to {train_data['datetime'].iloc[-1]}")
            # print(f"  Test:  {test_data['datetime'].iloc[0]} to {test_data['datetime'].iloc[-1]}")
            
            # Train on param_grid
            train_results = []
            for params in param_grid:
                strategy = strategy_class(params)
                try:
                    trades, metrics = strategy.backtest(train_data)
                    train_results.append({
                        'params': params,
                        'metrics': metrics,
                        'trades': trades
                    })
                except Exception as e:
                    pass
                    # print(f"    Error with params {params}: {e}")
            
            # Select best params using optimize_func
            if len(train_results) == 0:
                print(f"  ❌ No valid training results")
                continue
            
            best_train = optimize_func(train_results)
            
            if best_train is None:
                # print(f"  ❌ No valid configurations found")
                continue
            
            # print(f"  Train Sharpe: {best_train['metrics']['sharpe_ratio']:.3f} (Trades: {best_train['metrics']['total_trades']})")
            
            # Test on out-of-sample data
            test_strategy = strategy_class(best_train['params'])
            try:
                test_trades, test_metrics = test_strategy.backtest(test_data)
                
                # print(f"  Test Sharpe:  {test_metrics['sharpe_ratio']:.3f} (Trades: {test_metrics['total_trades']})")
                
                # Calculate degradation
                degradation = best_train['metrics']['sharpe_ratio'] - test_metrics['sharpe_ratio']
                # print(f"  Degradation:  {degradation:+.3f}")
                
                results.append({
                    'period': period_idx,
                    'train_sharpe': best_train['metrics']['sharpe_ratio'],
                    'test_sharpe': test_metrics['sharpe_ratio'],
                    'degradation': degradation,
                    'params': best_train['params'],
                    'train_trades': best_train['metrics']['total_trades'],
                    'test_trades': test_metrics['total_trades'],
                    'train_start': train_data['datetime'].iloc[0],
                    'test_end': test_data['datetime'].iloc[-1]
                })
                
            except Exception as e:
                print(f"  ❌ Test error: {e}")
        
        # Analyze results
        if len(results) == 0:
            print("\n❌ NO VALID WALK-FORWARD RESULTS")
            return results, None
        
        results_df = pd.DataFrame(results)
        
        # Filter for stable parameters (degradation < 0.3)
        stable = results_df[results_df['degradation'].abs() < 0.3]
        
        print(f"\n{'='*70}")
        print(f"WALK-FORWARD SUMMARY")
        print(f"{'='*70}")
        print(f"Total periods: {len(results_df)}")
        print(f"Stable periods (|degradation| < 0.3): {len(stable)}")
        print(f"Avg train Sharpe: {results_df['train_sharpe'].mean():.3f}")
        print(f"Avg test Sharpe:  {results_df['test_sharpe'].mean():.3f}")
        print(f"Avg degradation:  {results_df['degradation'].mean():+.3f}")
        
        if len(stable) > 0:
            print(f"\n✅ STABLE PERFORMANCE:")
            print(f"  Avg test Sharpe (stable): {stable['test_sharpe'].mean():.3f}")
            print(f"  Std test Sharpe (stable): {stable['test_sharpe'].std():.3f}")
            
            # Return most frequently selected params
            # Or params from period with highest test sharpe
            best_stable = stable.loc[stable['test_sharpe'].idxmax()]
            stable_params = best_stable['params']
            
            return results, stable_params
        else:
            print(f"\n⚠️ NO STABLE PARAMETERS FOUND (all degrade >0.3)")
            # Return params with lowest degradation
            least_bad = results_df.loc[results_df['degradation'].abs().idxmin()]
            return results, least_bad['params']


def select_best_train_params(train_results, min_trades=30):
    """
    Select best parameters from training results
    """
    valid = [r for r in train_results if r['metrics']['total_trades'] >= min_trades]
    
    if len(valid) == 0:
        return None
    
    best = max(valid, key=lambda x: x['metrics']['sharpe_ratio'])
    return best


# TESTING SCRIPT
def test_walk_forward_validation():
    """Test walk-forward validation on YESBANK"""
    
    print("\n" + "="*70)
    print("WALK-FORWARD VALIDATION TEST: YESBANK")
    print("="*70)
    
    filepath = 'data/raw/NSE_YESBANK_EQ_1hour.csv'
    full_path = os.path.join(project_root, filepath)
    if not os.path.exists(full_path):
            full_path = full_path.replace('data/raw/', 'data/')

    df = pd.read_csv(full_path)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.sort_values('datetime').reset_index(drop=True)
    
    # Parameter grid to test
    param_grid = [
        {
            'ker_period': 10,
            'rsi_period': 2,
            'rsi_entry': 25,
            'rsi_exit': 75,
            'vol_min_pct': 0.005,
            'max_hold_bars': 8,
            'allowed_hours': [10, 11, 12, 13, 14],
            'max_return_cap': 5.0,
            'ker_threshold_meanrev': 0.30,
            'ker_threshold_trend': 0.50,
            'ema_fast': 8,
            'ema_slow': 21,
            'trend_pulse_mult': 0.4,
        },
        {
            'ker_period': 10,
            'rsi_period': 2,
            'rsi_entry': 28,
            'rsi_exit': 72,
            'vol_min_pct': 0.005,
            'max_hold_bars': 10,
            'allowed_hours': [10, 11, 12, 13, 14],
            'max_return_cap': 5.0,
            'ker_threshold_meanrev': 0.30,
            'ker_threshold_trend': 0.50,
            'ema_fast': 8,
            'ema_slow': 21,
            'trend_pulse_mult': 0.4,
        },
        {
            'ker_period': 10,
            'rsi_period': 2,
            'rsi_entry': 30,
            'rsi_exit': 70,
            'vol_min_pct': 0.005,
            'max_hold_bars': 10,
            'allowed_hours': [10, 11, 12, 13, 14],
            'max_return_cap': 5.0,
            'ker_threshold_meanrev': 0.30,
            'ker_threshold_trend': 0.50,
            'ema_fast': 8,
            'ema_slow': 21,
            'trend_pulse_mult': 0.4,
        },
    ]
    
    # Run walk-forward validation
    validator = WalkForwardValidator(train_days=120, test_days=30, step_days=20)
    
    wf_results, stable_params = validator.validate(
        df=df,
        strategy_class=HybridAdaptiveStrategy,
        param_grid=param_grid,
        optimize_func=select_best_train_params
    )
    
    # Save results
    output_dir = os.path.join(project_root, 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    save_data = {
        'stable_params': stable_params,
        'walk_forward_periods': [
            {
                'period': r['period'],
                'train_sharpe': r['train_sharpe'],
                'test_sharpe': r['test_sharpe'],
                'degradation': r['degradation'],
            }
            for r in wf_results
        ],
        'avg_test_sharpe': np.mean([r['test_sharpe'] for r in wf_results]) if wf_results else 0,
    }
    
    with open(os.path.join(output_dir, 'phase2_walk_forward.json'), 'w') as f:
        json.dump(save_data, f, indent=2, default=str)
    
    print("\n✅ Results saved to: output/phase2_walk_forward.json")
    
    return wf_results, stable_params

if __name__ == "__main__":
    wf_results, stable_params = test_walk_forward_validation()
