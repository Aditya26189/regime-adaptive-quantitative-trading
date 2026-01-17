"""
NIFTY50 Regime Fix - Stricter Parameters for Trend Mode
Target: -2.84% → 0% to +1%
"""

import pandas as pd
import numpy as np
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from strategies.hybrid_adaptive import HybridAdaptiveStrategy


def test_nifty50_params(params: dict, description: str):
    """Test NIFTY50 with given parameters."""
    df = pd.read_csv('data/raw/NSE_NIFTY50_INDEX_1hour.csv')
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.sort_values('datetime').reset_index(drop=True)
    
    strategy = HybridAdaptiveStrategy(params)
    trades, metrics = strategy.backtest(df)
    
    print(f"\n{description}:")
    print(f"  Return: {metrics['total_return_pct']:+.2f}%")
    print(f"  Sharpe: {metrics['sharpe_ratio']:.3f}")
    print(f"  Trades: {metrics['total_trades']}")
    print(f"  MeanRev: {metrics['meanrev_trades']}, Trend: {metrics['trend_trades']}")
    
    return metrics


def optimize_nifty50():
    """Try different parameter combinations to fix NIFTY50."""
    print("="*70)
    print("NIFTY50 REGIME FIX - Testing Parameter Variations")
    print("="*70)
    
    # Current params (baseline)
    current_params = {
        'ker_period': 8,
        'rsi_period': 2,
        'vol_lookback': 14,
        'max_return_cap': 5.0,
        'ker_threshold_meanrev': 0.1674,
        'ker_threshold_trend': 0.2808,
        'rsi_entry': 33,
        'rsi_exit': 69,
        'vol_min_pct': 0.0072,
        'ema_fast': 5,
        'ema_slow': 18,
        'trend_pulse_mult': 0.4647,
        'allowed_hours': [9, 10, 11, 12, 13, 14],
        'max_hold_bars': 8,
    }
    
    baseline = test_nifty50_params(current_params, "BASELINE (Current)")
    
    # Variation 1: Lower KER threshold for trend mode
    v1_params = current_params.copy()
    v1_params['ker_threshold_trend'] = 0.20  # Was 0.28
    v1_params['ker_threshold_meanrev'] = 0.12  # Rarely use mean rev
    v1 = test_nifty50_params(v1_params, "V1: Lower KER for trend (0.20)")
    
    # Variation 2: Skip afternoon hours
    v2_params = current_params.copy()
    v2_params['allowed_hours'] = [9, 10, 11]  # Morning only
    v2 = test_nifty50_params(v2_params, "V2: Morning only [9,10,11]")
    
    # Variation 3: Combined - lower KER + morning only
    v3_params = current_params.copy()
    v3_params['ker_threshold_trend'] = 0.22
    v3_params['ker_threshold_meanrev'] = 0.10
    v3_params['allowed_hours'] = [9, 10, 11, 12]
    v3_params['max_hold_bars'] = 5  # Faster exit
    v3 = test_nifty50_params(v3_params, "V3: Lower KER + Skip afternoon + Faster exit")
    
    # Variation 4: Very aggressive trend mode
    v4_params = current_params.copy()
    v4_params['ker_threshold_trend'] = 0.18  # Very low
    v4_params['ker_threshold_meanrev'] = 0.08  # Almost never mean rev
    v4_params['rsi_entry'] = 28  # More aggressive entry
    v4_params['rsi_exit'] = 60  # Faster exit
    v4_params['allowed_hours'] = [9, 10, 11, 12, 13]
    v4_params['max_hold_bars'] = 4
    v4 = test_nifty50_params(v4_params, "V4: Aggressive trend mode")
    
    # Pick best
    results = [
        ('BASELINE', baseline, current_params),
        ('V1', v1, v1_params),
        ('V2', v2, v2_params),
        ('V3', v3, v3_params),
        ('V4', v4, v4_params),
    ]
    
    # Filter valid (>= 120 trades)
    valid = [(n, m, p) for n, m, p in results if m['total_trades'] >= 120]
    
    if not valid:
        print("\n⚠️ No valid configs with >= 120 trades!")
        # Fall back to best return regardless of trade count
        best = max(results, key=lambda x: x[1]['total_return_pct'])
    else:
        # Pick by best Sharpe among valid
        best = max(valid, key=lambda x: x[1]['sharpe_ratio'])
    
    print(f"\n{'='*70}")
    print(f"BEST CONFIG: {best[0]}")
    print(f"{'='*70}")
    print(f"Return: {best[1]['total_return_pct']:+.2f}%")
    print(f"Sharpe: {best[1]['sharpe_ratio']:.3f}")
    print(f"Trades: {best[1]['total_trades']}")
    
    improvement = best[1]['total_return_pct'] - baseline['total_return_pct']
    print(f"\nImprovement vs Baseline: {improvement:+.2f}%")
    
    return best[0], best[1], best[2]


if __name__ == "__main__":
    best_name, best_metrics, best_params = optimize_nifty50()
    
    # Save best params
    print(f"\n{'='*70}")
    print("BEST NIFTY50 PARAMS:")
    print(json.dumps(best_params, indent=2))
