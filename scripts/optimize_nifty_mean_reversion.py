"""
NIFTY50 Mean Reversion Optimization using Optuna
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

from src.strategies.nifty_mean_reversion import generate_nifty_mean_reversion_signals


class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NpEncoder, self).default(obj)


def optimize_nifty_mean_reversion(n_trials: int = 300):
    """Optimize NIFTY50 using mean reversion with Optuna."""
    
    print("="*70)
    print("NIFTY50 MEAN REVERSION OPTIMIZATION (SHARPE-FOCUSED)")
    print("="*70)
    print(f"Trials: {n_trials}")
    print(f"Started: {datetime.now().strftime('%H:%M:%S')}")
    
    # Load data
    data = pd.read_csv('data/raw/NSE_NIFTY50_INDEX_1hour.csv')
    data['datetime'] = pd.to_datetime(data['datetime'])
    data = data.sort_values('datetime').reset_index(drop=True)
    
    def objective(trial):
        params = {
            'rsi_period': 2,  # Fixed - RSI(2) works best
            'rsi_entry': trial.suggest_int('rsi_entry', 10, 35),
            'rsi_exit': trial.suggest_int('rsi_exit', 65, 90),
            'ker_period': trial.suggest_int('ker_period', 8, 15),
            'ker_max': trial.suggest_float('ker_max', 0.2, 0.5),
            'vol_min': trial.suggest_float('vol_min', 0.0, 0.1),
            'max_hold': trial.suggest_int('max_hold', 6, 20),
            'position_size': trial.suggest_float('position_size', 0.85, 0.95),
            'vol_period': 14,
            'allowed_hours': [9, 10, 11, 12, 13, 14],
        }
        
        # Ensure entry < exit
        if params['rsi_entry'] >= params['rsi_exit']:
            return float('-inf')
        
        try:
            trades_df = generate_nifty_mean_reversion_signals(data, params)
            
            # Must have >= 120 trades
            if len(trades_df) < 120:
                return float('-inf')
            
            # Calculate Sharpe
            trades_df['return_pct'] = trades_df['pnl'] / 100000 * 100
            
            if trades_df['return_pct'].std() == 0:
                return float('-inf')
            
            sharpe = trades_df['return_pct'].mean() / trades_df['return_pct'].std()
            
            # Directly optimize Sharpe
            return sharpe
            
        except Exception:
            return float('-inf')
    
    # Create study
    sampler = TPESampler(seed=42)
    study = optuna.create_study(
        direction='maximize',
        sampler=sampler,
        study_name='nifty50_mean_reversion'
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
    best_params['rsi_period'] = 2
    best_params['vol_period'] = 14
    best_params['allowed_hours'] = [9, 10, 11, 12, 13, 14]
    
    # Re-run with best params for full metrics
    trades_df = generate_nifty_mean_reversion_signals(data, best_params)
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
    
    # Compare with current
    print(f"\n{'='*70}")
    print("COMPARISON")
    print(f"{'='*70}")
    print(f"Current NIFTY (Trend): -0.020 Sharpe")
    print(f"New NIFTY (Mean Rev):  {best_sharpe:.4f} Sharpe")
    if best_sharpe > 0:
        print(f"✅ SUCCESS: Positive Sharpe achieved!")
    else:
        print(f"⚠️ Still negative, but may be improvement")
    
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
    with open('optimization_results/nifty_mean_reversion_best.json', 'w') as f:
        json.dump(result, f, indent=2, cls=NpEncoder)
    
    print(f"\n✅ Saved to optimization_results/nifty_mean_reversion_best.json")
    
    return result


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--trials', type=int, default=300)
    args = parser.parse_args()
    
    optimize_nifty_mean_reversion(n_trials=args.trials)
