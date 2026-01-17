# optimize_dynamic_rsi.py

import optuna
import json
import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.strategies.hybrid_adaptive import HybridAdaptiveStrategy
from typing import Dict

# Paths with underscores
SYMBOL_FILES = {
    'VBL': 'data/raw/NSE_VBL_EQ_1hour.csv',
    'RELIANCE': 'data/raw/NSE_RELIANCE_EQ_1hour.csv',
    'SUNPHARMA': 'data/raw/NSE_SUNPHARMA_EQ_1hour.csv',
    'YESBANK': 'data/raw/NSE_YESBANK_EQ_1hour.csv'
}

def load_baseline():
    """Load baseline metrics for comparison."""
    with open('baseline_metrics.json', 'r') as f:
        return json.load(f)

def objective_dynamic_rsi(trial: optuna.Trial, symbol: str, df: pd.DataFrame, 
                         baseline_params: Dict) -> float:
    """
    Objective function for optimizing dynamic RSI parameters.
    Returns: Weighted score (70% Sharpe, 15% Return, 15% Trade Penalty)
    """
    
    # Start with baseline params
    params = baseline_params.copy()
    
    # Enable dynamic RSI
    params['use_dynamic_rsi'] = True
    
    # Optuna samples these parameters
    params['dynamic_rsi_window'] = trial.suggest_int('dyn_window', 10, 40, step=5)
    params['dynamic_rsi_std'] = trial.suggest_float('dyn_std', 1.3, 2.5, step=0.1)
    
    # Also optimize RSI period (while we're at it)
    params['rsi_period'] = trial.suggest_int('rsi_period', 2, 5)
    
    # Volatility filter (might need adjustment with dynamic bands)
    params['vol_min_pct'] = trial.suggest_float('vol_min_pct', 0.003, 0.012, step=0.001)
    
    # Max hold bars
    params['max_hold_bars'] = trial.suggest_int('max_hold_bars', 4, 12)
    
    try:
        # Run backtest
        strategy = HybridAdaptiveStrategy(params)
        trades, metrics = strategy.backtest(df)
        
        # HARD CONSTRAINTS
        if metrics['total_trades'] < 120:
            # Severe penalty for insufficient trades
            return -1000.0
        
        if metrics['max_drawdown_pct'] > 25.0:
            # Excessive drawdown
            return -500.0
        
        # SCORING
        sharpe = metrics['sharpe_ratio']
        total_return = metrics['total_return_pct']
        trade_count = metrics['total_trades']
        
        # Normalize scores
        sharpe_score = sharpe / 2.0  # Target Sharpe = 2.0
        return_score = total_return / 20.0  # Target Return = 20%
        
        # Trade count bonus/penalty
        if trade_count >= 150:
            trade_score = 0.2  # Bonus for many trades
        elif trade_count >= 130:
            trade_score = 0.1  # Small bonus
        elif trade_count >= 120:
            trade_score = 0.0  # Neutral
        else:
            trade_score = -10.0  # Should never hit this due to hard constraint
        
        # Weighted final score
        final_score = (
            0.70 * sharpe_score +
            0.15 * return_score +
            0.15 * trade_score
        )
        
        return final_score
        
    except Exception as e:
        # print(f"Trial failed: {e}")
        return -1000.0

def optimize_symbol_dynamic_rsi(symbol: str, n_trials: int = 50) -> Dict:
    """
    Optimize dynamic RSI parameters for a single symbol.
    Reduced trials to 50 for speed in this agent session.
    """
    print(f"\n{'='*70}")
    print(f"OPTIMIZING DYNAMIC RSI: {symbol}")
    print(f"{'='*70}")
    
    # Load data
    baseline = load_baseline()
    
    df = pd.read_csv(SYMBOL_FILES[symbol])
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.sort_values('datetime').reset_index(drop=True)
    
    baseline_params = baseline[symbol]['params']
    baseline_sharpe = baseline[symbol]['sharpe']
    baseline_trades = baseline[symbol]['trades']
    
    print(f"Baseline: Sharpe={baseline_sharpe:.3f}, Trades={baseline_trades}")
    
    # Create Optuna study
    study = optuna.create_study(
        direction='maximize',
        sampler=optuna.samplers.TPESampler(seed=42),
        pruner=optuna.pruners.MedianPruner(n_warmup_steps=10)
    )
    
    # Optimize
    study.optimize(
        lambda trial: objective_dynamic_rsi(trial, symbol, df, baseline_params),
        n_trials=n_trials,
        n_jobs=1,
        show_progress_bar=True
    )
    
    # Get best params
    best_params = baseline_params.copy()
    best_params['use_dynamic_rsi'] = True
    best_params.update(study.best_params)
    
    # Validate best params
    strategy = HybridAdaptiveStrategy(best_params)
    trades, metrics = strategy.backtest(df)
    
    print(f"\n{'='*70}")
    print(f"RESULTS: {symbol}")
    print(f"{'='*70}")
    print(f"Baseline:  Sharpe={baseline_sharpe:.3f}, Trades={baseline_trades}")
    print(f"Optimized: Sharpe={metrics['sharpe_ratio']:.3f}, Trades={metrics['total_trades']}")
    print(f"Change:    Sharpe={metrics['sharpe_ratio']-baseline_sharpe:+.3f}, Trades={metrics['total_trades']-baseline_trades:+d}")
    print(f"\nBest Params: {study.best_params}")
    
    # Decision logic
    improvement = metrics['sharpe_ratio'] - baseline_sharpe
    trade_ok = metrics['total_trades'] >= 120
    
    accept = False
    if improvement > 0.05 and trade_ok:
        print(f"✅ ACCEPT: Significant improvement (+{improvement:.3f} Sharpe)")
        accept = True
    elif improvement > 0.0 and trade_ok:
        print(f"⚠️  MARGINAL: Small improvement (+{improvement:.3f} Sharpe)")
        accept = True
    else:
        print(f"❌ REJECT: No improvement or trade count violation")
        
    return {
        'symbol': symbol,
        'accept': accept,
        'params': best_params if accept else baseline_params,
        'metrics': {
            'sharpe': metrics['sharpe_ratio'] if accept else baseline_sharpe,
            'trades': metrics['total_trades'] if accept else baseline_trades,
            'return': metrics['total_return_pct'] if accept else 0.0, # Baseline return not saved in metric
            'maxdd': metrics['max_drawdown_pct'] if accept else 0.0
        }
    }

def run_phase1_optimization():
    """Run dynamic RSI optimization on all stock symbols."""
    stocks = ['VBL', 'RELIANCE', 'SUNPHARMA', 'YESBANK']
    
    results = {}
    
    for symbol in stocks:
        result = optimize_symbol_dynamic_rsi(symbol, n_trials=50) # Low trials for quick check
        results[symbol] = result
        
        # Save intermediate results
        with open(f'phase1_results_{symbol}.json', 'w') as f:
            json.dump(result, f, indent=2)
    
    # Summary
    print(f"\n{'='*70}")
    print("PHASE 1 SUMMARY: DYNAMIC RSI")
    print(f"{'='*70}")
    
    accepted = [s for s in stocks if results[s]['accept']]
    
    # Calculate new portfolio Sharpe
    baseline = load_baseline()
    # Baseline portfolio sharpe
    old_portfolio = baseline['PORTFOLIO']['sharpe']
    
    new_sharpes = [results[s]['metrics']['sharpe'] for s in stocks] + [baseline['NIFTY50']['sharpe']]
    new_portfolio = sum(new_sharpes) / 5
    
    print(f"\nPortfolio Sharpe:")
    print(f"  Before: {old_portfolio:.3f}")
    print(f"  After:  {new_portfolio:.3f}")
    print(f"  Change: {new_portfolio - old_portfolio:+.3f}")
    
    # Save final results
    phase1_output = {
        'results': results,
        'portfolio_sharpe': {
            'before': old_portfolio,
            'after': new_portfolio,
            'change': new_portfolio - old_portfolio
        }
    }
    
    with open('phase1_dynamic_rsi_results.json', 'w') as f:
        json.dump(phase1_output, f, indent=2)
    
    # Update params file
    # Load fallback or create new structure
    try:
        with open('output/sharpe_optimized_params.json', 'r') as f:
            params = json.load(f)
    except:
        params = {}
    
    for symbol in stocks:
        if results[symbol]['accept']:
            params[symbol] = results[symbol]['params']
    
    with open('output/sharpe_optimized_params_phase1.json', 'w') as f:
        json.dump(params, f, indent=2)
    
    print(f"\n💾 Updated params saved to: output/sharpe_optimized_params_phase1.json")

if __name__ == "__main__":
    run_phase1_optimization()
