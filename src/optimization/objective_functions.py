"""
MULTI-OBJECTIVE OPTIMIZATION FUNCTIONS

Defines how to score each parameter combination.
Uses weighted combination of multiple metrics to avoid overfitting to single objective.

Weights:
1. Sharpe Ratio (70%) - Primary objective
2. Total Return (10%) - Secondary objective
3. Drawdown Control (10%) - Risk control
4. Win Rate (10%) - Consistency
"""

import pandas as pd
import numpy as np
import sys
from pathlib import Path
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.strategies.hybrid_adaptive import HybridAdaptiveStrategy
from src.strategies.ensemble_wrapper import EnsembleStrategy
from src.strategies.nifty_trend_strategy import generate_nifty_trend_signals


def compute_weighted_score(metrics: Dict[str, float]) -> float:
    """
    Compute weighted multi-objective score.
    Returns float('-inf') if constraints are violated.
    """
    # 1. HARD CONSTRAINTS
    if metrics['trades'] < 120:
        return float('-inf')
    
    if metrics['max_drawdown'] > 20.0:  # Allow up to 20% DD temporarily
        return float('-inf')

    # 2. NORMALIZE METRICS
    # Scale Sharpe: target 2.0 = 1.0 (uncapped)
    sharpe_score = metrics['sharpe'] / 2.0
    
    # Scale Return: target 15% = 1.0
    return_score = metrics['return'] / 15.0
    
    # Scale Drawdown: 0% = 1.0, 20% = 0.0
    dd_score = max(0, 1.0 - (metrics['max_drawdown'] / 20.0))
    
    # Scale Win Rate: 60% = 1.0
    wr_score = metrics['win_rate'] / 60.0
    
    # 3. WEIGHTED SUM
    # Weights: Sharpe=0.7, Return=0.1, DD=0.1, WR=0.1
    final_score = (
        0.70 * sharpe_score +
        0.10 * return_score +
        0.10 * dd_score +
        0.10 * wr_score
    )
    
    return final_score


def calculate_metrics(trades_df: pd.DataFrame, capital: float = 100000) -> Dict[str, float]:
    """Calculate comprehensive metrics from trades DataFrame."""
    if len(trades_df) == 0:
        return {'sharpe': -999, 'return': -999, 'trades': 0, 'max_drawdown': 100, 'win_rate': 0}
        
    # PnL Analysis
    trades_df['return_pct'] = trades_df['pnl'] / capital * 100
    total_return = trades_df['pnl'].sum() / capital * 100
    
    # Sharpe
    std_dev = trades_df['return_pct'].std()
    sharpe = (trades_df['return_pct'].mean() / std_dev) if std_dev > 0 else 0
    
    # Drawdown
    trades_df['cumulative'] = trades_df['pnl'].cumsum()
    peak = trades_df['cumulative'].expanding().max()
    dd = (peak - trades_df['cumulative']) / capital * 100
    max_dd = dd.max() if len(dd) > 0 else 0
    
    # Win Rate
    win_rate = (trades_df['pnl'] > 0).mean() * 100
    
    return {
        'sharpe': sharpe,
        'return': total_return,
        'trades': len(trades_df),
        'max_drawdown': max_dd,
        'win_rate': win_rate
    }


def objective_function(trial, symbol: str, data: pd.DataFrame) -> float:
    """Generic objective function that dispatches to specific strategies."""
    from src.optimization.parameter_space import SYMBOL_PARAM_FUNCTIONS
    
    # Get parameters from search space
    params = SYMBOL_PARAM_FUNCTIONS[symbol](trial)
    
    try:
        # NIFTY SPECIAL CASE (Trend Strategy)
        if symbol == 'NIFTY50':
            if params['ema_fast'] >= params['ema_slow']:
                return float('-inf')  # Invalid param combination
                
            trades_df = generate_nifty_trend_signals(data, params)
            metrics = calculate_metrics(trades_df)
            return compute_weighted_score(metrics)
            
        # STOCKS (Hybrid/Ensemble)
        else:
            if symbol == 'VBL' and params.get('use_ensemble', False):
                strategy = EnsembleStrategy(params, n_variants=5, min_agreement=3)
            else:
                strategy = HybridAdaptiveStrategy(params)
                
            trades, strat_metrics = strategy.backtest(data)
            
            # Convert strategy metrics to our format
            metrics = {
                'sharpe': strat_metrics['sharpe_ratio'],
                'return': strat_metrics['total_return_pct'],
                'trades': strat_metrics['total_trades'],
                'max_drawdown': strat_metrics['max_drawdown'],
                'win_rate': strat_metrics['win_rate']
            }
            return compute_weighted_score(metrics)
            
    except Exception:
        return float('-inf')
