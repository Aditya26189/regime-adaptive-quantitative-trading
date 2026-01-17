# optimize_advanced_techniques.py - FIXED
"""
Optuna Optimizer for Advanced Techniques
CRITICAL: VBL stays with ENSEMBLE (1.574) - Don't touch it!
Apply advanced techniques to: RELIANCE, SUNPHARMA, YESBANK only
"""

import optuna
import json
import pandas as pd
import numpy as np
import sys
import os
from typing import Dict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.strategies.hybrid_adaptive_v2 import HybridAdaptiveStrategyV2

# ONLY optimize these symbols (VBL stays with Ensemble at 1.574)
SYMBOL_FILES = {
    'RELIANCE': 'data/raw/NSE_RELIANCE_EQ_1hour.csv',
    'SUNPHARMA': 'data/raw/NSE_SUNPHARMA_EQ_1hour.csv',
    'YESBANK': 'data/raw/NSE_YESBANK_EQ_1hour.csv',
}

def load_baseline():
    with open('baseline_metrics.json', 'r') as f:
        return json.load(f)

def get_advanced_params(trial: optuna.Trial, baseline_params: Dict) -> Dict:
    """Sample advanced parameters."""
    params = {}
    for k, v in baseline_params.items():
        if k != '_strategy':
            params[k] = v
    
    # Technique 1: Dynamic Position Sizing
    params['use_dynamic_sizing'] = trial.suggest_categorical('use_dynamic_sizing', [True, False])
    if params['use_dynamic_sizing']:
        params['kelly_fraction'] = trial.suggest_float('kelly_fraction', 0.3, 0.6, step=0.1)
        params['max_risk_pct'] = trial.suggest_float('max_risk_pct', 1.5, 3.0, step=0.5)
    
    # Technique 2: Multi-Timeframe
    params['use_multi_timeframe'] = trial.suggest_categorical('use_mtf', [True, False])
    if params['use_multi_timeframe']:
        params['daily_ema_period'] = trial.suggest_int('daily_ema', 30, 60, step=10)
        params['require_daily_bias'] = trial.suggest_categorical('require_bias', [True, False])
    
    # Technique 3: Profit Ladders
    params['use_profit_ladder'] = trial.suggest_categorical('use_ladder', [True, False])
    if params['use_profit_ladder']:
        params['ladder_rsi_1'] = trial.suggest_int('ladder_rsi_1', 55, 65)
        params['ladder_rsi_2'] = trial.suggest_int('ladder_rsi_2', 70, 80)
        params['ladder_frac_1'] = trial.suggest_float('ladder_frac_1', 0.25, 0.40, step=0.05)
    
    # Technique 4: Adaptive Hold
    params['use_adaptive_hold'] = trial.suggest_categorical('use_adaptive_hold', [True, False])
    
    # Technique 5: Dynamic RSI
    params['use_dynamic_rsi'] = trial.suggest_categorical('use_dynamic_rsi', [True, False])
    if params['use_dynamic_rsi']:
        params['dynamic_rsi_window'] = trial.suggest_int('dyn_rsi_window', 15, 30, step=5)
        params['dynamic_rsi_std'] = trial.suggest_float('dyn_rsi_std', 1.5, 2.5, step=0.25)
    
    # Base parameters
    params['rsi_period'] = trial.suggest_int('rsi_period', 2, 4)
    params['max_hold_bars'] = trial.suggest_int('max_hold_bars', 6, 14, step=2)
    params['vol_min_pct'] = trial.suggest_float('vol_min_pct', 0.003, 0.010, step=0.001)
    
    return params

def objective(trial: optuna.Trial, symbol: str, df: pd.DataFrame, 
              baseline_params: Dict, baseline_sharpe: float) -> float:
    """Objective function."""
    
    params = get_advanced_params(trial, baseline_params)
    
    try:
        strategy = HybridAdaptiveStrategyV2(params)
        trades, metrics = strategy.backtest(df)
        
        # HARD CONSTRAINTS
        if metrics['total_trades'] < 120:
            return -1000.0
        
        if metrics['max_drawdown_pct'] < -25.0:
            return -500.0
        
        sharpe = metrics['sharpe_ratio']
        
        # Must improve or stay close
        if sharpe < baseline_sharpe - 0.2:
            return -100.0  # Reject big regressions
        
        # Score: Direct Sharpe (simple is better)
        return float(sharpe)
        
    except Exception as e:
        return -1000.0

def optimize_symbol(symbol: str, n_trials: int = 100) -> Dict:
    """Optimize a single symbol."""
    print(f"\n{'='*70}")
    print(f"OPTIMIZING: {symbol}")
    print(f"{'='*70}")
    
    baseline = load_baseline()
    
    df = pd.read_csv(SYMBOL_FILES[symbol])
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.sort_values('datetime').reset_index(drop=True)
    
    baseline_params = baseline[symbol]['params']
    baseline_sharpe = baseline[symbol]['sharpe']
    
    print(f"Baseline: Sharpe={baseline_sharpe:.3f}")
    
    study = optuna.create_study(
        direction='maximize',
        sampler=optuna.samplers.TPESampler(seed=42)
    )
    
    study.optimize(
        lambda trial: objective(trial, symbol, df, baseline_params, baseline_sharpe),
        n_trials=n_trials,
        n_jobs=1,
        show_progress_bar=True
    )
    
    # Best params
    best_trial_params = study.best_params
    best_params = get_advanced_params_from_study(best_trial_params, baseline_params)
    
    # Validate
    strategy = HybridAdaptiveStrategyV2(best_params)
    trades, metrics = strategy.backtest(df)
    
    improvement = metrics['sharpe_ratio'] - baseline_sharpe
    
    print(f"\nRESULTS:")
    print(f"Baseline:  Sharpe={baseline_sharpe:.3f}")
    print(f"Optimized: Sharpe={metrics['sharpe_ratio']:.3f}, Trades={metrics['total_trades']}")
    print(f"Change:    {improvement:+.3f}")
    
    print(f"\nBest Features:")
    for feat in ['use_dynamic_sizing', 'use_multi_timeframe', 'use_profit_ladder', 
                 'use_adaptive_hold', 'use_dynamic_rsi']:
        print(f"  {feat}: {best_params.get(feat, False)}")
    
    # Accept if improvement or minimal regression
    accept = (metrics['total_trades'] >= 120) and (metrics['sharpe_ratio'] >= baseline_sharpe - 0.05)
    
    # Convert numpy types to native Python
    result = {
        'symbol': symbol,
        'accept': bool(accept),
        'params': {k: (bool(v) if isinstance(v, (np.bool_, bool)) else 
                       float(v) if isinstance(v, (np.floating, float)) else
                       int(v) if isinstance(v, (np.integer, int)) else v)
                  for k, v in best_params.items()},
        'metrics': {
            'sharpe': float(metrics['sharpe_ratio']),
            'trades': int(metrics['total_trades']),
            'return': float(metrics['total_return_pct']),
            'win_rate': float(metrics['win_rate']),
            'max_dd': float(metrics['max_drawdown_pct'])
        },
        'improvement': float(improvement)
    }
    
    return result

def get_advanced_params_from_study(best_trial_params: Dict, baseline_params: Dict) -> Dict:
    """Reconstruct params from trial."""
    params = {k: v for k, v in baseline_params.items() if k != '_strategy'}
    
    params['use_dynamic_sizing'] = best_trial_params.get('use_dynamic_sizing', False)
    if params['use_dynamic_sizing']:
        params['kelly_fraction'] = best_trial_params.get('kelly_fraction', 0.5)
        params['max_risk_pct'] = best_trial_params.get('max_risk_pct', 2.0)
    
    params['use_multi_timeframe'] = best_trial_params.get('use_mtf', False)
    if params['use_multi_timeframe']:
        params['daily_ema_period'] = best_trial_params.get('daily_ema', 50)
        params['require_daily_bias'] = best_trial_params.get('require_bias', False)
    
    params['use_profit_ladder'] = best_trial_params.get('use_ladder', False)
    if params['use_profit_ladder']:
        params['ladder_rsi_1'] = best_trial_params.get('ladder_rsi_1', 60)
        params['ladder_rsi_2'] = best_trial_params.get('ladder_rsi_2', 75)
        params['ladder_frac_1'] = best_trial_params.get('ladder_frac_1', 0.33)
    
    params['use_adaptive_hold'] = best_trial_params.get('use_adaptive_hold', False)
    
    params['use_dynamic_rsi'] = best_trial_params.get('use_dynamic_rsi', False)
    if params['use_dynamic_rsi']:
        params['dynamic_rsi_window'] = best_trial_params.get('dyn_rsi_window', 20)
        params['dynamic_rsi_std'] = best_trial_params.get('dyn_rsi_std', 2.0)
    
    params['rsi_period'] = best_trial_params.get('rsi_period', 2)
    params['max_hold_bars'] = best_trial_params.get('max_hold_bars', 10)
    params['vol_min_pct'] = best_trial_params.get('vol_min_pct', 0.005)
    
    return params

def run_full_optimization():
    """Run optimization (VBL excluded - kept at Ensemble 1.574)."""
    symbols = ['RELIANCE', 'SUNPHARMA', 'YESBANK']
    
    results = {}
    
    for symbol in symbols:
        result = optimize_symbol(symbol, n_trials=80)
        results[symbol] = result
        
        with open(f'advanced_results_{symbol}.json', 'w') as f:
            json.dump(result, f, indent=2)
    
    # Summary
    print(f"\n{'='*70}")
    print("ADVANCED OPTIMIZATION SUMMARY")
    print(f"{'='*70}")
    
    baseline = load_baseline()
    
    # VBL stays at 1.574 (Ensemble)
    vbl_sharpe = baseline['VBL']['sharpe']  # 1.574
    nifty_sharpe = baseline['NIFTY50']['sharpe']  # 0.006
    
    old_sharpes = [baseline[s]['sharpe'] for s in symbols] + [vbl_sharpe, nifty_sharpe]
    old_portfolio = sum(old_sharpes) / 5
    
    new_sharpes = [results[s]['metrics']['sharpe'] for s in symbols] + [vbl_sharpe, nifty_sharpe]
    new_portfolio = sum(new_sharpes) / 5
    
    print(f"\nPer-Symbol:")
    print(f"  VBL: {vbl_sharpe:.3f} (ENSEMBLE - unchanged)")
    for s in symbols:
        old = baseline[s]['sharpe']
        new = results[s]['metrics']['sharpe']
        print(f"  {s}: {old:.3f} → {new:.3f} ({new-old:+.3f})")
    print(f"  NIFTY50: {nifty_sharpe:.3f} (unchanged)")
    
    print(f"\nPortfolio Sharpe:")
    print(f"  Before: {old_portfolio:.3f}")
    print(f"  After:  {new_portfolio:.3f}")
    print(f"  Change: {new_portfolio - old_portfolio:+.3f}")
    
    # Save results
    with open('advanced_optimization_results.json', 'w') as f:
        json.dump({
            'results': results,
            'vbl_ensemble': vbl_sharpe,
            'nifty_trend': nifty_sharpe,
            'portfolio': {
                'before': old_portfolio,
                'after': new_portfolio,
                'change': new_portfolio - old_portfolio
            }
        }, f, indent=2)
    
    print(f"\n💾 Results saved to advanced_optimization_results.json")

if __name__ == "__main__":
    run_full_optimization()
