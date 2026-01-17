
"""
Last-minute fine-tuning: Quick parameter sweep on weakest symbols
"""

import pandas as pd
import numpy as np
import json
import sys
import os

# Add project root to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '../../'))
sys.path.insert(0, project_root)

def quick_parameter_sweep_yesbank():
    """Ultra-fast parameter sweep on YESBANK (weakest link)"""
    from src.strategies.hybrid_adaptive import HybridAdaptiveStrategy
    
    print("\n⚡ LAST-MINUTE PARAMETER SWEEP: YESBANK")
    
    filepath = 'data/raw/NSE_YESBANK_EQ_1hour.csv'
    full_path = os.path.join(project_root, filepath)
    if not os.path.exists(full_path):
         full_path = full_path.replace('data/raw/', 'data/')
    
    df = pd.read_csv(full_path)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.sort_values('datetime').reset_index(drop=True)
    
    # Ultra-focused grid (only test ±2 around current best)
    # Current best from Phase 2/1 logic: 30/70
    
    param_variants = [
        {'rsi_entry': 29, 'rsi_exit': 71},
        {'rsi_entry': 30, 'rsi_exit': 70},  # Current best
        {'rsi_entry': 31, 'rsi_exit': 69},
    ]
    
    best_sharpe = 0
    best_params = None
    
    for variant in param_variants:
        params = {
            'ker_period': 10,
            'rsi_period': 2,
            'rsi_entry': variant['rsi_entry'],
            'rsi_exit': variant['rsi_exit'],
            'vol_min_pct': 0.005,
            'max_hold_bars': 10,
            'allowed_hours': [10, 11, 12, 13, 14, 15],
            'max_return_cap': 5.0,
            'ker_threshold_meanrev': 0.30,
            'ker_threshold_trend': 0.50,
            'ema_fast': 8,
            'ema_slow': 21,
            'trend_pulse_mult': 0.4,
        }
        
        strategy = HybridAdaptiveStrategy(params)
        trades, metrics = strategy.backtest(df)
        
        if metrics['total_trades'] >= 120 and metrics['sharpe_ratio'] > best_sharpe:
            best_sharpe = metrics['sharpe_ratio']
            best_params = variant
            print(f"  ✨ New best: {variant} → Sharpe {best_sharpe:.3f}")
    
    print(f"\n✅ Final best: {best_params} → Sharpe {best_sharpe:.3f}")
    
    return best_params, best_sharpe

if __name__ == "__main__":
    best_params, best_sharpe = quick_parameter_sweep_yesbank()
