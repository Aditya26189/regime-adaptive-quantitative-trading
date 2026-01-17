"""
Focused NIFTY50 Optimization
Specialized Optuna optimizer for NIFTY50 trend strategy only.
"""

import optuna
from optuna.samplers import TPESampler
import pandas as pd
import numpy as np
import json
import sys
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.strategies.nifty_trend_strategy import generate_nifty_trend_signals


class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NpEncoder, self).default(obj)


def optimize_nifty_optuna(n_trials: int = 200):
    """Optimize NIFTY50 using Optuna with direct Sharpe maximization."""
    
    print("="*70)
    print("NIFTY50 OPTUNA OPTIMIZATION (SHARPE-FOCUSED)")
    print("="*70)
    print(f"Trials: {n_trials}")
    print(f"Started: {datetime.now().strftime('%H:%M:%S')}")
    
    # Load data
    data = pd.read_csv('data/raw/NSE_NIFTY50_INDEX_1hour.csv')
    data['datetime'] = pd.to_datetime(data['datetime'])
    data = data.sort_values('datetime').reset_index(drop=True)
    
    def objective(trial):
        params = {
            'ema_fast': trial.suggest_int('ema_fast', 3, 12),
            'ema_slow': trial.suggest_int('ema_slow', 20, 50),
            'momentum_period': trial.suggest_int('momentum_period', 3, 15),
            'momentum_threshold': trial.suggest_float('momentum_threshold', 0.05, 0.5),
            'ema_diff_threshold': trial.suggest_float('ema_diff_threshold', 0.02, 0.2),
            'vol_min': trial.suggest_float('vol_min', 0.0, 0.2),
            'max_hold': trial.suggest_int('max_hold', 4, 20),
            'vol_period': 14,
            'allowed_hours': [9, 10, 11, 12, 13, 14],
        }
        
        # Ensure fast < slow
        if params['ema_fast'] >= params['ema_slow']:
            return float('-inf')
        
        try:
            trades_df = generate_nifty_trend_signals(data, params)
            
            # Must have >= 120 trades
            if len(trades_df) < 120:
                return float('-inf')
            
            # Calculate Sharpe
            trades_df['return_pct'] = trades_df['pnl'] / 100000 * 100
            total_return = trades_df['pnl'].sum() / 100000 * 100
            
            if trades_df['return_pct'].std() == 0:
                return float('-inf')
            
            sharpe = trades_df['return_pct'].mean() / trades_df['return_pct'].std()
            
            # DIRECTLY optimize Sharpe (no multi-objective complexity)
            return sharpe
            
        except Exception:
            return float('-inf')
    
    # Create study
    sampler = TPESampler(seed=42)
    study = optuna.create_study(
        direction='maximize',
        sampler=sampler,
        study_name='nifty50_sharpe_max'
    )
    
    # Run optimization
    study.optimize(
        objective,
        n_trials=n_trials,
        show_progress_bar=True,
    )
    
    # Get best
    best_params = study.best_params
    best_sharpe = study.best_value
    
    # Add fixed params
    best_params['vol_period'] = 14
    best_params['allowed_hours'] = [9, 10, 11, 12, 13, 14]
    
    # Re-run with best params for full metrics
    trades_df = generate_nifty_trend_signals(data, best_params)
    total_return = trades_df['pnl'].sum() / 100000 * 100
    win_rate = (trades_df['pnl'] > 0).sum() / len(trades_df) * 100
    
    print(f"\n{'='*70}")
    print("OPTIMIZATION RESULTS")
    print(f"{'='*70}")
    print(f"Best Sharpe: {best_sharpe:.4f}")
    print(f"Return: {total_return:+.2f}%")
    print(f"Trades: {len(trades_df)}")
    print(f"Win Rate: {win_rate:.1f}%")
    print(f"\nBest Params:")
    for k, v in best_params.items():
        print(f"  {k}: {v}")
    
    # Compare with current best
    print(f"\n{'='*70}")
    print("COMPARISON")
    print(f"{'='*70}")
    print(f"Current NIFTY Sharpe: -0.020")
    print(f"Optuna NIFTY Sharpe:  {best_sharpe:.4f}")
    if best_sharpe > -0.020:
        print(f"✅ IMPROVEMENT: +{best_sharpe - (-0.020):.4f}")
    else:
        print(f"⚠️ No improvement")
    
    # Save
    result = {
        'params': best_params,
        'metrics': {
            'sharpe': best_sharpe,
            'return': total_return,
            'trades': len(trades_df),
            'win_rate': win_rate,
        }
    }
    
    Path('optimization_results').mkdir(exist_ok=True)
    with open('optimization_results/nifty_optuna_best.json', 'w') as f:
        json.dump(result, f, indent=2, cls=NpEncoder)
    
    print(f"\n✅ Saved to optimization_results/nifty_optuna_best.json")
    
    return result


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--trials', type=int, default=200)
    args = parser.parse_args()
    
    optimize_nifty_optuna(n_trials=args.trials)
