#!/usr/bin/env python
"""
Parameter grid search script for optimizing strategy parameters.

Usage:
    python scripts/grid_search.py --data data/raw/test.csv --strategy z_score
"""

import argparse
import itertools
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

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


# Default parameter grids for each strategy
DEFAULT_PARAM_GRIDS = {
    'z_score': {
        'window': [10, 20, 30, 50],
        'entry_z': [1.5, 2.0, 2.5, 3.0],
        'exit_z': [0.3, 0.5, 0.7]
    },
    'momentum': {
        'fast_ma': [3, 5, 10],
        'slow_ma': [15, 20, 30, 50]
    },
    'mean_reversion': {
        'window': [10, 20, 30, 50],
        'threshold': [1.5, 2.0, 2.5, 3.0]
    },
    'obi': {
        'threshold': [0.1, 0.2, 0.3, 0.4, 0.5]
    },
    'microprice': {
        'window': [10, 20, 30],
        'threshold_std': [0.5, 1.0, 1.5, 2.0]
    }
}

# Strategy function mapping
STRATEGY_FUNCS = {
    'z_score': z_score_signal,
    'momentum': momentum_signal,
    'mean_reversion': mean_reversion_signal,
    'obi': obi_signal,
    'microprice': microprice_deviation
}


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Grid search for optimal strategy parameters'
    )
    
    parser.add_argument(
        '--data', '-d',
        type=str,
        required=True,
        help='Path to market data CSV file'
    )
    
    parser.add_argument(
        '--strategy', '-s',
        type=str,
        default='z_score',
        choices=list(STRATEGY_FUNCS.keys()),
        help='Trading strategy to optimize (default: z_score)'
    )
    
    parser.add_argument(
        '--max-position',
        type=int,
        default=Config.MAX_POSITION,
        help=f'Maximum position size (default: {Config.MAX_POSITION})'
    )
    
    parser.add_argument(
        '--top-n',
        type=int,
        default=5,
        help='Number of top results to display (default: 5)'
    )
    
    parser.add_argument(
        '--output-dir', '-o',
        type=str,
        default=Config.RESULTS_PATH,
        help=f'Output directory for results (default: {Config.RESULTS_PATH})'
    )
    
    return parser.parse_args()


def run_single_backtest(
    data: pd.DataFrame,
    signal_func,
    signal_params: Dict[str, Any],
    max_position: int
) -> Dict[str, float]:
    """
    Run a single backtest with given parameters.
    
    Returns:
        Dictionary with sharpe, max_dd, num_trades, total_return
    """
    # Initialize components
    risk_manager = RiskManager(
        max_position=max_position,
        max_drawdown=Config.MAX_DRAWDOWN,
        vol_threshold=Config.VOL_THRESHOLD,
        vol_window=Config.VOL_WINDOW
    )
    
    strategy = Strategy(
        signal_func=signal_func,
        risk_manager=risk_manager,
        signal_params=signal_params
    )
    
    backtester = Backtester(
        initial_cash=Config.INITIAL_CASH,
        maker_fee=Config.MAKER_FEE,
        taker_fee=Config.TAKER_FEE,
        max_position=max_position,
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
        'num_trades': results['num_trades'],
        'total_return': results['total_return'],
        'win_rate': metrics['win_rate']
    }


def grid_search(
    data: pd.DataFrame,
    strategy_name: str,
    param_grid: Dict[str, List],
    max_position: int
) -> pd.DataFrame:
    """
    Test all parameter combinations and rank by Sharpe ratio.
    
    Args:
        data: DataFrame with market data
        strategy_name: Name of strategy
        param_grid: Dictionary of parameter lists
        max_position: Maximum position size
        
    Returns:
        DataFrame with results sorted by Sharpe descending
    """
    signal_func = STRATEGY_FUNCS[strategy_name]
    
    # Generate all parameter combinations
    param_names = list(param_grid.keys())
    param_values = list(param_grid.values())
    combinations = list(itertools.product(*param_values))
    
    print(f"\n📊 Grid Search: {strategy_name}")
    print(f"   Parameters: {param_names}")
    print(f"   Total combinations: {len(combinations)}")
    print("-" * 50)
    
    results = []
    
    for i, combo in enumerate(combinations):
        # Build parameter dict
        params = dict(zip(param_names, combo))
        
        # Skip invalid combinations (e.g., fast_ma >= slow_ma for momentum)
        if strategy_name == 'momentum':
            if params['fast_ma'] >= params['slow_ma']:
                continue
        
        try:
            # Run backtest
            metrics = run_single_backtest(data, signal_func, params, max_position)
            
            result = {
                'params': str(params),
                **params,
                **metrics
            }
            results.append(result)
            
            # Progress update
            if (i + 1) % 10 == 0 or i == len(combinations) - 1:
                print(f"   Progress: {i + 1}/{len(combinations)} ({(i+1)/len(combinations)*100:.0f}%)")
                
        except Exception as e:
            print(f"   ⚠ Error with {params}: {e}")
            continue
    
    # Create DataFrame and sort
    df = pd.DataFrame(results)
    if len(df) > 0:
        df = df.sort_values('sharpe', ascending=False).reset_index(drop=True)
    
    return df


def print_top_results(df: pd.DataFrame, top_n: int = 5):
    """Print top N results."""
    print("\n" + "=" * 60)
    print(f"TOP {top_n} PARAMETER COMBINATIONS")
    print("=" * 60)
    
    if len(df) == 0:
        print("No valid results found.")
        return
    
    for i, row in df.head(top_n).iterrows():
        print(f"\n#{i + 1}")
        print(f"   Parameters: {row['params']}")
        print(f"   Sharpe:     {row['sharpe']:.4f}")
        print(f"   Max DD:     {row['max_dd']*100:.2f}%")
        print(f"   Num Trades: {row['num_trades']}")
        print(f"   Return:     {row['total_return']*100:.2f}%")
        print(f"   Win Rate:   {row['win_rate']*100:.1f}%")
    
    print("\n" + "=" * 60)
    
    # Print recommendation
    if len(df) > 0:
        best = df.iloc[0]
        print("\n✅ RECOMMENDED PARAMETERS:")
        print(f"   {best['params']}")


def main():
    """Main entry point."""
    args = parse_args()
    
    print("\n" + "=" * 60)
    print("PARAMETER GRID SEARCH")
    print("=" * 60)
    
    # Load data
    print("\n📁 Loading data...")
    loader = DataLoader(verbose=False)
    df = loader.load_csv(args.data)
    df = loader.add_mid_price(df)
    
    engine = FeatureEngine(verbose=False)
    df = engine.add_all(df)
    df = engine.fill_missing(df)
    
    print(f"   ✓ Loaded {len(df)} rows")
    
    # Get param grid
    param_grid = DEFAULT_PARAM_GRIDS.get(args.strategy, {})
    
    if not param_grid:
        print(f"❌ No default parameter grid for strategy: {args.strategy}")
        return
    
    # Run grid search
    results_df = grid_search(df, args.strategy, param_grid, args.max_position)
    
    # Print results
    print_top_results(results_df, args.top_n)
    
    # Save results
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f'grid_search_{args.strategy}_{timestamp}.csv'
    results_df.to_csv(output_path, index=False)
    print(f"\n💾 Full results saved to: {output_path}")


if __name__ == '__main__':
    main()
