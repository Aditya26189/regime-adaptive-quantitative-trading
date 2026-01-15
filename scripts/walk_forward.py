#!/usr/bin/env python
"""
Walk-forward optimization engine for detecting overfitting.

Validates strategy on rolling time windows to ensure parameters work
across multiple market regimes in different time periods.

Usage:
    python scripts/walk_forward.py --data data/raw/test.csv --strategy z_score
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple
import itertools

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd

from config import Config
from src.core.backtester import Backtester
from src.core.risk_manager import RiskManager
from src.core.metrics import MetricsCalculator
from src.data.loader import DataLoader
from src.data.features import FeatureEngine
from src.signals.price_based import z_score_signal, momentum_signal, mean_reversion_signal
from src.signals.flow_based import obi_signal, microprice_deviation
from src.execution.strategy import Strategy


# Strategy configs for grid search
STRATEGY_CONFIGS = {
    'z_score': {
        'func': z_score_signal,
        'param_grid': {
            'window': [10, 20, 30],
            'entry_z': [1.5, 2.0, 2.5],
            'exit_z': [0.3, 0.5]
        }
    },
    'momentum': {
        'func': momentum_signal,
        'param_grid': {
            'fast_ma': [3, 5, 10],
            'slow_ma': [15, 20, 30]
        }
    },
    'obi': {
        'func': obi_signal,
        'param_grid': {
            'threshold': [0.2, 0.3, 0.4, 0.5]
        }
    },
    'mean_reversion': {
        'func': mean_reversion_signal,
        'param_grid': {
            'window': [10, 20, 30],
            'threshold': [1.5, 2.0, 2.5]
        }
    }
}


def backtest_with_params(
    data: pd.DataFrame,
    signal_func,
    params: Dict[str, Any],
    initial_cash: float = 100000
) -> Dict[str, float]:
    """
    Run a single backtest with given parameters.
    
    Returns:
        Dict with 'sharpe', 'max_dd', 'total_return', 'num_trades'
    """
    # Initialize components
    risk_manager = RiskManager(
        max_position=Config.MAX_POSITION,
        max_drawdown=Config.MAX_DRAWDOWN,
        vol_threshold=Config.VOL_THRESHOLD,
        vol_window=Config.VOL_WINDOW
    )
    
    strategy = Strategy(
        signal_func=signal_func,
        risk_manager=risk_manager,
        signal_params=params
    )
    
    backtester = Backtester(
        initial_cash=initial_cash,
        maker_fee=Config.MAKER_FEE,
        taker_fee=Config.TAKER_FEE,
        max_position=Config.MAX_POSITION,
        max_drawdown=Config.MAX_DRAWDOWN
    )
    
    # Precompute signals
    signals = strategy.precompute_signals(data)
    
    # Run backtest
    for i, (idx, tick) in enumerate(data.iterrows()):
        signal = strategy.get_signal_at_index(
            index=i,
            current_position=backtester.position,
            current_equity=backtester.cash + backtester.position * tick.get('mid', 0)
        )
        backtester.process_tick(tick, signal, trade_qty=1)
    
    # Get results
    results = backtester.get_results()
    metrics = MetricsCalculator.calculate_all(results['equity_curve'])
    
    return {
        'sharpe': metrics['sharpe'],
        'max_dd': metrics['max_dd'],
        'total_return': results['total_return'],
        'num_trades': results['num_trades']
    }


def grid_search_on_fold(
    data: pd.DataFrame,
    strategy_name: str
) -> Tuple[Dict[str, Any], float]:
    """
    Run grid search on a fold's training data.
    
    Returns:
        (best_params, best_sharpe)
    """
    config = STRATEGY_CONFIGS[strategy_name]
    signal_func = config['func']
    param_grid = config['param_grid']
    
    # Generate all combinations
    param_names = list(param_grid.keys())
    param_values = list(param_grid.values())
    combinations = list(itertools.product(*param_values))
    
    best_sharpe = -np.inf
    best_params = None
    
    for combo in combinations:
        params = dict(zip(param_names, combo))
        
        # Skip invalid combinations
        if strategy_name == 'momentum':
            if params['fast_ma'] >= params['slow_ma']:
                continue
        
        try:
            metrics = backtest_with_params(data, signal_func, params)
            
            if metrics['sharpe'] > best_sharpe:
                best_sharpe = metrics['sharpe']
                best_params = params
                
        except Exception:
            continue
    
    return best_params, best_sharpe


def walk_forward_optimize(
    data: pd.DataFrame,
    strategy_name: str,
    train_window: int = 500,
    test_window: int = 100,
    step: int = 100,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Rolling window optimization and out-of-sample testing.
    
    Args:
        data: DataFrame with market data (already cleaned & featured)
        strategy_name: 'z_score', 'momentum', 'obi', etc.
        train_window: Number of rows for training
        test_window: Number of rows for testing
        step: Step size between folds
        verbose: Print progress
        
    Returns:
        {
            'n_folds': int,
            'avg_train_sharpe': float,
            'avg_test_sharpe': float,
            'std_test_sharpe': float,
            'degradation_pct': float,
            'fold_results': [...]
        }
    """
    if strategy_name not in STRATEGY_CONFIGS:
        raise ValueError(f"Unknown strategy: {strategy_name}")
    
    config = STRATEGY_CONFIGS[strategy_name]
    signal_func = config['func']
    
    fold_results = []
    fold_num = 0
    
    # Calculate number of folds possible
    max_folds = (len(data) - train_window - test_window) // step + 1
    
    if verbose:
        print(f"\nWalk-forward optimization: {strategy_name}")
        print(f"Data length: {len(data)}")
        print(f"Train window: {train_window}, Test window: {test_window}, Step: {step}")
        print(f"Expected folds: ~{max_folds}")
        print("-" * 60)
    
    for start_idx in range(0, len(data) - train_window - test_window + 1, step):
        train_end = start_idx + train_window
        test_end = train_end + test_window
        
        # Get data slices
        train_data = data.iloc[start_idx:train_end].copy().reset_index(drop=True)
        test_data = data.iloc[train_end:test_end].copy().reset_index(drop=True)
        
        if len(train_data) < train_window * 0.8 or len(test_data) < test_window * 0.5:
            continue
        
        fold_num += 1
        
        # Grid search on training data
        best_params, _ = grid_search_on_fold(train_data, strategy_name)
        
        if best_params is None:
            continue
        
        # Backtest on training data (in-sample)
        train_metrics = backtest_with_params(train_data, signal_func, best_params)
        
        # Backtest on test data (out-of-sample)
        test_metrics = backtest_with_params(test_data, signal_func, best_params)
        
        # Calculate degradation
        if train_metrics['sharpe'] != 0:
            degradation = (train_metrics['sharpe'] - test_metrics['sharpe']) / abs(train_metrics['sharpe']) * 100
        else:
            degradation = 0
        
        fold_result = {
            'fold': fold_num,
            'train_start': start_idx,
            'train_end': train_end,
            'test_end': test_end,
            'best_params': best_params,
            'train_sharpe': train_metrics['sharpe'],
            'test_sharpe': test_metrics['sharpe'],
            'train_max_dd': train_metrics['max_dd'],
            'test_max_dd': test_metrics['max_dd'],
            'train_trades': train_metrics['num_trades'],
            'test_trades': test_metrics['num_trades'],
            'degradation_pct': degradation
        }
        
        fold_results.append(fold_result)
        
        if verbose:
            print(f"Fold {fold_num}: Train Sharpe={train_metrics['sharpe']:.3f}, "
                  f"Test Sharpe={test_metrics['sharpe']:.3f}, Deg={degradation:.1f}%")
    
    if not fold_results:
        return {
            'n_folds': 0,
            'avg_train_sharpe': 0,
            'avg_test_sharpe': 0,
            'std_test_sharpe': 0,
            'degradation_pct': 0,
            'fold_results': []
        }
    
    # Aggregate results
    train_sharpes = [f['train_sharpe'] for f in fold_results]
    test_sharpes = [f['test_sharpe'] for f in fold_results]
    
    avg_train = np.mean(train_sharpes)
    avg_test = np.mean(test_sharpes)
    std_test = np.std(test_sharpes)
    
    if avg_train != 0:
        overall_degradation = (avg_train - avg_test) / abs(avg_train) * 100
    else:
        overall_degradation = 0
    
    return {
        'n_folds': len(fold_results),
        'avg_train_sharpe': avg_train,
        'avg_test_sharpe': avg_test,
        'std_test_sharpe': std_test,
        'degradation_pct': overall_degradation,
        'fold_results': fold_results
    }


def print_walk_forward_report(results: Dict[str, Any]) -> None:
    """Pretty-print walk-forward results."""
    print("\n" + "=" * 70)
    print("WALK-FORWARD OPTIMIZATION REPORT")
    print("=" * 70)
    
    if results['n_folds'] == 0:
        print("\n⚠️  No folds completed. Data may be too short for walk-forward.")
        print("   Try reducing train_window and test_window.")
        return
    
    # Print per-fold results
    print(f"\n{'FOLD RESULTS':^70}")
    print("-" * 70)
    print(f"{'Fold':>6} {'Train Sharpe':>14} {'Test Sharpe':>14} {'Degradation':>12} {'Trades':>10}")
    print("-" * 70)
    
    for fold in results['fold_results']:
        deg_str = f"{fold['degradation_pct']:+.1f}%" if fold['degradation_pct'] != 0 else "0.0%"
        print(f"{fold['fold']:>6} "
              f"{fold['train_sharpe']:>14.4f} "
              f"{fold['test_sharpe']:>14.4f} "
              f"{deg_str:>12} "
              f"{fold['test_trades']:>10}")
    
    # Print summary
    print("\n" + "=" * 70)
    print(f"{'SUMMARY':^70}")
    print("=" * 70)
    print(f"  Number of folds:        {results['n_folds']}")
    print(f"  Avg Train Sharpe:       {results['avg_train_sharpe']:.4f}")
    print(f"  Avg Test Sharpe:        {results['avg_test_sharpe']:.4f} ± {results['std_test_sharpe']:.4f}")
    print(f"  Overall Degradation:    {results['degradation_pct']:.1f}%")
    print("=" * 70)
    
    # Interpretation
    print("\nINTERPRETATION:")
    if results['degradation_pct'] < 20:
        print("  ✅ EXCELLENT - Minimal overfitting detected")
        print("     Strategy parameters are robust across time periods.")
    elif results['degradation_pct'] < 35:
        print("  ⚠️  ACCEPTABLE - Moderate overfitting")
        print("     Monitor performance closely on live data.")
    else:
        print("  ❌ WARNING - High overfitting detected!")
        print("     Consider:")
        print("       - Reducing model complexity (simpler parameters)")
        print("       - Using longer lookback windows")
        print("       - Adding regularization or constraints")
        print("       - Using simpler signal types")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Walk-forward optimization for overfitting detection'
    )
    
    parser.add_argument(
        '--data', '-d',
        type=str,
        required=True,
        help='Path to market data CSV'
    )
    
    parser.add_argument(
        '--strategy', '-s',
        type=str,
        default='z_score',
        choices=list(STRATEGY_CONFIGS.keys()),
        help='Strategy to optimize (default: z_score)'
    )
    
    parser.add_argument(
        '--train-window',
        type=int,
        default=500,
        help='Training window size (default: 500)'
    )
    
    parser.add_argument(
        '--test-window',
        type=int,
        default=100,
        help='Test window size (default: 100)'
    )
    
    parser.add_argument(
        '--step',
        type=int,
        default=100,
        help='Step size between folds (default: 100)'
    )
    
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()
    
    print("\n" + "=" * 70)
    print("WALK-FORWARD OPTIMIZATION")
    print("=" * 70)
    
    # Load and prepare data
    print(f"\nLoading data from {args.data}...")
    loader = DataLoader(verbose=False)
    df = loader.load_csv(args.data)
    df = loader.add_mid_price(df)
    
    engine = FeatureEngine(verbose=False)
    df = engine.add_all(df)
    df = engine.fill_missing(df)
    
    print(f"  ✓ Loaded {len(df)} rows")
    
    # Run walk-forward
    results = walk_forward_optimize(
        df,
        args.strategy,
        args.train_window,
        args.test_window,
        args.step
    )
    
    # Print report
    print_walk_forward_report(results)


if __name__ == '__main__':
    main()
