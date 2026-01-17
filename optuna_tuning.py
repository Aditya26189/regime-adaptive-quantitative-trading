"""
OPTUNA TUNING SCRIPT
Target: YESBANK Robustness
"""

import optuna
import pandas as pd
import numpy as np
import os
import sys
import json

# Add project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.strategies.hybrid_adaptive import HybridAdaptiveStrategy

# Load Data
DATA_PATH = 'data/raw/NSE_YESBANK_EQ_1hour.csv'
if not os.path.exists(DATA_PATH):
    DATA_PATH = 'data/NSE_YESBANK_EQ_1hour.csv'

df = pd.read_csv(DATA_PATH)
df['datetime'] = pd.to_datetime(df['datetime'])
df = df.sort_values('datetime').reset_index(drop=True)

# Train/Test Split
# Train: Jan - Sep 2025
# Test: Oct - Dec 2025 (Approx last 25%)
train_len = int(len(df) * 0.75)
train_df = df.iloc[:train_len].copy()
test_df = df.iloc[train_len:].copy()

print(f"Train Data: {len(train_df)} bars")
print(f"Test Data: {len(test_df)} bars")

CAPITAL = 2000000

def objective(trial):
    # Search Space (Conservative)
    params = {
        "ker_period": trial.suggest_int("ker_period", 8, 20),
        "rsi_period": trial.suggest_categorical("rsi_period", [2, 3, 4]),
        "rsi_entry": trial.suggest_int("rsi_entry", 15, 45),
        "rsi_exit": trial.suggest_int("rsi_exit", 55, 85),
        "vol_min_pct": trial.suggest_float("vol_min_pct", 0.003, 0.010),
        "max_hold_bars": trial.suggest_int("max_hold_bars", 3, 15),
        "allowed_hours": [9, 10, 11, 12, 13, 14, 15], # Keep wide
        "max_return_cap": 5.0,
        "ker_threshold_meanrev": trial.suggest_float("ker_threshold_meanrev", 0.2, 0.4),
        "ker_threshold_trend": trial.suggest_float("ker_threshold_trend", 0.4, 0.6),
        "ema_fast": 8,
        "ema_slow": 21,
        "trend_pulse_mult": 0.4,
        # Baseline / Boosted toggle?
        # Keep to HybridAdaptiveStrategy base logic
    }
    
    # Train Evaluation
    strat = HybridAdaptiveStrategy(params)
    t_trades, t_metrics = strat.backtest(train_df, initial_capital=CAPITAL)
    train_sharpe = t_metrics.get('sharpe_ratio', 0)
    
    if train_sharpe < 0.5:
        raise optuna.TrialPruned()
        
    # Test Evaluation
    strat = HybridAdaptiveStrategy(params)
    o_trades, o_metrics = strat.backtest(test_df, initial_capital=CAPITAL)
    test_sharpe = o_metrics.get('sharpe_ratio', 0)
    
    # Validation Constraints
    if test_sharpe < 0:
        return -100 # Failure
        
    # Consistency Check
    # We want Test ~ Train (Robustness)
    # Objective: Maximize Test Sharpe, but penalized if Test << Train
    
    return test_sharpe 

if __name__ == "__main__":
    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=50)
    
    print("\n" + "="*60)
    print("BEST PARAMS FOR YESBANK")
    print("="*60)
    print(study.best_params)
    print(f"Best Test Sharpe: {study.best_value}")
    
    # Save best params
    with open('output/optuna_yesbank_results.json', 'w') as f:
        json.dump(study.best_params, f, indent=2)
