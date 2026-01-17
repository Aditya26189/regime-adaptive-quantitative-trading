
"""
Final hyperparameter tuning using Optuna on Phase 2 best strategies
"""

import optuna
import pandas as pd
import numpy as np
import sys
import os
import json

# Add project root to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '../../'))
sys.path.insert(0, project_root)

from src.strategies.hybrid_adaptive import HybridAdaptiveStrategy

def objective_yesbank(trial):
    """Optuna objective for YESBANK fine-tuning"""
    
    filepath = 'data/raw/NSE_YESBANK_EQ_1hour.csv'
    full_path = os.path.join(project_root, filepath)
    if not os.path.exists(full_path):
            full_path = full_path.replace('data/raw/', 'data/')
            
    df = pd.read_csv(full_path)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.sort_values('datetime').reset_index(drop=True)
    
    # Narrow parameter ranges (fine-tuning only)
    params = {
        'ker_period': 10,  # Fixed
        'rsi_period': trial.suggest_int('rsi_period', 2, 3),
        'rsi_entry': trial.suggest_int('rsi_entry', 24, 32),
        'rsi_exit': trial.suggest_int('rsi_exit', 68, 78),
        'vol_min_pct': trial.suggest_float('vol_min_pct', 0.004, 0.007),
        'max_hold_bars': trial.suggest_int('max_hold_bars', 8, 12),
        'allowed_hours': [10, 11, 12, 13, 14],
        'max_return_cap': 5.0,
        'ker_threshold_meanrev': 0.30,
        'ker_threshold_trend': 0.50,
        'ema_fast': 8,
        'ema_slow': 21,
        'trend_pulse_mult': 0.4,
    }
    
    strategy = HybridAdaptiveStrategy(params)
    
    try:
        trades, metrics = strategy.backtest(df)
        
        # Penalize if trade count < 120
        if metrics['total_trades'] < 120:
            return -999
        
        return metrics['sharpe_ratio']
    
    except Exception as e:
        return -999


def fine_tune_phase2():
    """Fine-tune parameters for Phase 2 strategies"""
    
    print("\n" + "="*70)
    print("PHASE 2 FINAL FINE-TUNING (OPTUNA)")
    print("="*70)
    
    # Fine-tune YESBANK
    print("\n🔧 Fine-tuning YESBANK...")
    
    # Use optuna logging verbosity control
    optuna.logging.set_verbosity(optuna.logging.WARNING)

    study = optuna.create_study(direction='maximize', study_name='yesbank_finetune')
    # Limit number of trials to keep it fast
    study.optimize(objective_yesbank, n_trials=50, show_progress_bar=True)
    
    best_params = study.best_params
    best_sharpe = study.best_value
    
    print(f"\n✅ BEST YESBANK (FINE-TUNED):")
    print(f"  Sharpe: {best_sharpe:.3f}")
    print(f"  Params: {best_params}")
    
    # Save
    output_dir = os.path.join(project_root, 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    with open(os.path.join(output_dir, 'phase2_finetuned.json'), 'w') as f:
        json.dump({
            'YESBANK': {
                'sharpe': best_sharpe,
                'params': best_params
            }
        }, f, indent=2)
    
    print("\n✅ Results saved to: output/phase2_finetuned.json")

if __name__ == "__main__":
    fine_tune_phase2()
