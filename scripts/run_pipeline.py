#!/usr/bin/env python
"""
End-to-end trading pipeline execution script.

Usage:
    python scripts/run_pipeline.py --data data/raw/market_data.csv --strategy z_score
    python scripts/run_pipeline.py --data data/raw/market_data.csv --strategy momentum
    python scripts/run_pipeline.py --data data/raw/market_data.csv --strategy obi
    python scripts/run_pipeline.py --data data/raw/test.csv --strategy z_score --eval-mode split
    python scripts/run_pipeline.py --data data/raw/test.csv --strategy z_score --compare-regime-filter

Strategies available:
    - z_score: Mean reversion based on z-score
    - momentum: Moving average crossover
    - mean_reversion: Simple mean reversion
    - obi: Order book imbalance
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

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
from src.signals.regime_based import volatility_regime, should_trade_regime
from src.execution.strategy import Strategy
from src.visualization.plotter import plot_all, print_metrics_table


# Global debug flag
DEBUG = False


# Strategy mapping
STRATEGIES = {
    'z_score': {
        'func': z_score_signal,
        'params': {
            'window': Config.LOOKBACK_WINDOW,
            'entry_z': Config.ENTRY_Z_THRESHOLD,
            'exit_z': Config.EXIT_Z_THRESHOLD
        }
    },
    'momentum': {
        'func': momentum_signal,
        'params': {
            'fast_ma': Config.FAST_MA_WINDOW,
            'slow_ma': Config.SLOW_MA_WINDOW
        }
    },
    'mean_reversion': {
        'func': mean_reversion_signal,
        'params': {
            'window': Config.LOOKBACK_WINDOW,
            'threshold': Config.ENTRY_Z_THRESHOLD
        }
    },
    'obi': {
        'func': obi_signal,
        'params': {
            'threshold': Config.OBI_THRESHOLD
        }
    },
    'microprice': {
        'func': microprice_deviation,
        'params': {
            'window': Config.LOOKBACK_WINDOW,
            'threshold_std': 1.0
        }
    }
}


def debug_log(message: str) -> None:
    """Print message only if DEBUG is enabled."""
    if DEBUG:
        print(f"  [DEBUG] {message}")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Run quantitative trading backtest pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/run_pipeline.py --data data/raw/test.csv --strategy z_score
    python scripts/run_pipeline.py --data data/raw/test.csv --strategy obi --plot
    python scripts/run_pipeline.py --data data/raw/test.csv --strategy z_score --eval-mode split
        """
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
        choices=list(STRATEGIES.keys()),
        help='Trading strategy to use (default: z_score)'
    )
    
    parser.add_argument(
        '--initial-cash',
        type=float,
        default=Config.INITIAL_CASH,
        help=f'Initial cash (default: {Config.INITIAL_CASH})'
    )
    
    parser.add_argument(
        '--max-position',
        type=int,
        default=Config.MAX_POSITION,
        help=f'Maximum position size (default: {Config.MAX_POSITION})'
    )
    
    parser.add_argument(
        '--max-drawdown',
        type=float,
        default=Config.MAX_DRAWDOWN,
        help=f'Maximum drawdown threshold (default: {Config.MAX_DRAWDOWN})'
    )
    
    parser.add_argument(
        '--trade-qty',
        type=int,
        default=1,
        help='Quantity to trade per signal (default: 1)'
    )
    
    parser.add_argument(
        '--plot', '-p',
        action='store_true',
        help='Generate performance plots'
    )
    
    parser.add_argument(
        '--output-dir', '-o',
        type=str,
        default=Config.RESULTS_PATH,
        help=f'Output directory for results (default: {Config.RESULTS_PATH})'
    )
    
    parser.add_argument(
        '--use-regime-filter',
        action='store_true',
        help='Enable volatility regime filter'
    )
    
    # Task 2: Train/Test Split arguments
    parser.add_argument(
        '--eval-mode',
        type=str,
        default='full',
        choices=['full', 'split'],
        help='Evaluation mode: full (all data) or split (train/test)'
    )
    
    parser.add_argument(
        '--train-ratio',
        type=float,
        default=0.7,
        help='Ratio of data for training (default: 0.7)'
    )
    
    # Task 6: Regime Filter Comparison
    parser.add_argument(
        '--compare-regime-filter',
        action='store_true',
        help='Compare performance with and without regime filter'
    )
    
    # Task 7: Debug Mode
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable detailed debug output'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        default=True,
        help='Verbose output'
    )
    
    return parser.parse_args()


def run_backtest_on_data(
    df: pd.DataFrame,
    strategy_name: str,
    args,
    use_regime_filter: bool = False,
    label: str = "Full"
) -> Tuple[Dict[str, Any], Dict[str, float]]:
    """
    Run backtest on given data.
    
    Returns:
        Tuple of (results dict, metrics dict)
    """
    # Get strategy config
    strategy_config = STRATEGIES[strategy_name]
    signal_func = strategy_config['func']
    signal_params = strategy_config['params']
    
    # Initialize risk manager
    risk_manager = RiskManager(
        max_position=args.max_position,
        max_drawdown=args.max_drawdown,
        vol_threshold=Config.VOL_THRESHOLD,
        vol_window=Config.VOL_WINDOW
    )
    
    # Set up regime filter if requested
    regime_filter = should_trade_regime if use_regime_filter else None
    
    # Create strategy
    strategy = Strategy(
        signal_func=signal_func,
        risk_manager=risk_manager,
        regime_filter=regime_filter,
        signal_params=signal_params
    )
    
    # Precompute signals
    signals = strategy.precompute_signals(df)
    
    # Compute regime if using filter
    regimes = None
    if use_regime_filter:
        regimes = volatility_regime(df)
    
    # Initialize backtester
    backtester = Backtester(
        initial_cash=args.initial_cash,
        maker_fee=Config.MAKER_FEE,
        taker_fee=Config.TAKER_FEE,
        max_position=args.max_position,
        max_drawdown=args.max_drawdown
    )
    
    # Run backtest
    for i, (idx, tick) in enumerate(df.iterrows()):
        regime = regimes[i] if regimes else None
        
        signal = strategy.get_signal_at_index(
            index=i,
            current_position=backtester.position,
            current_equity=backtester.cash + backtester.position * tick.get('mid', tick.get('close', 0)),
            regime=regime
        )
        
        debug_log(f"Tick {i}: signal={signal}, pos={backtester.position}")
        
        backtester.process_tick(tick, signal, trade_qty=args.trade_qty)
        
        if len(backtester.equity_curve) > 1:
            curr_return = (backtester.equity_curve[-1] - backtester.equity_curve[-2]) / backtester.equity_curve[-2]
            risk_manager.add_return(curr_return)
    
    # Get results
    results = backtester.get_results()
    
    # Calculate metrics
    metrics = MetricsCalculator.calculate_all(
        results['equity_curve'],
        periods_per_year=Config.PERIODS_PER_YEAR
    )
    
    metrics['total_pnl'] = results['total_pnl']
    metrics['num_trades'] = results['num_trades']
    metrics['final_position'] = results['final_position']
    metrics['was_halted'] = results['was_halted']
    
    return results, metrics


def print_split_comparison(
    train_metrics: Dict[str, float],
    test_metrics: Dict[str, float]
) -> None:
    """Print side-by-side train/test comparison."""
    print("\n" + "=" * 60)
    print("IN-SAMPLE (Training) METRICS")
    print("=" * 60)
    print(f"{'Metric':<20} {'Value':>15}")
    print("-" * 60)
    print(f"{'Sharpe':<20} {train_metrics['sharpe']:>15.4f}")
    print(f"{'Max DD':<20} {train_metrics['max_dd']*100:>14.2f}%")
    print(f"{'Total Return':<20} {train_metrics['total_return']*100:>14.2f}%")
    print(f"{'Num Trades':<20} {train_metrics['num_trades']:>15}")
    print(f"{'Win Rate':<20} {train_metrics['win_rate']*100:>14.1f}%")
    
    print("\n" + "=" * 60)
    print("OUT-OF-SAMPLE (Test) METRICS")
    print("=" * 60)
    
    # Calculate degradation
    if train_metrics['sharpe'] != 0:
        sharpe_deg = (train_metrics['sharpe'] - test_metrics['sharpe']) / abs(train_metrics['sharpe']) * 100
    else:
        sharpe_deg = 0
    
    sharpe_warning = f"  [Warning: {abs(sharpe_deg):.0f}% degradation]" if sharpe_deg > 30 else ""
    
    print(f"{'Metric':<20} {'Value':>15}")
    print("-" * 60)
    print(f"{'Sharpe':<20} {test_metrics['sharpe']:>15.4f}{sharpe_warning}")
    print(f"{'Max DD':<20} {test_metrics['max_dd']*100:>14.2f}%")
    print(f"{'Total Return':<20} {test_metrics['total_return']*100:>14.2f}%")
    print(f"{'Num Trades':<20} {test_metrics['num_trades']:>15}")
    print(f"{'Win Rate':<20} {test_metrics['win_rate']*100:>14.1f}%")
    
    # Overfitting warning
    if sharpe_deg > 30:
        print("\n⚠️  WARNING: Significant performance degradation detected.")
        print("   This may indicate overfitting to training data.")
        print("   Consider using more robust parameters or simpler strategy.")
    elif sharpe_deg > 0:
        print("\n✅ Performance within acceptable range.")
    else:
        print("\n✅ Test performance equal or better than training!")


def print_regime_comparison(
    no_filter_metrics: Dict[str, float],
    with_filter_metrics: Dict[str, float]
) -> None:
    """Print regime filter comparison."""
    print("\n" + "=" * 60)
    print("REGIME FILTER COMPARISON")
    print("=" * 60)
    
    def calc_improvement(no_filter, with_filter, higher_is_better=True):
        if no_filter == 0:
            return 0
        change = (with_filter - no_filter) / abs(no_filter) * 100
        if not higher_is_better:
            change = -change
        return change
    
    metrics_to_compare = [
        ('Sharpe', 'sharpe', True),
        ('Max DD', 'max_dd', False),  # Less negative is better
        ('Num Trades', 'num_trades', False),  # Neutral
        ('Win Rate', 'win_rate', True),
        ('Total Return', 'total_return', True),
    ]
    
    print(f"{'Metric':<15} {'No Filter':>12} {'With Filter':>12} {'Change':>12}")
    print("-" * 60)
    
    total_improvement = 0
    for label, key, higher_better in metrics_to_compare:
        nf = no_filter_metrics[key]
        wf = with_filter_metrics[key]
        
        if key == 'max_dd':
            nf_str = f"{nf*100:.2f}%"
            wf_str = f"{wf*100:.2f}%"
        elif key in ['win_rate', 'total_return']:
            nf_str = f"{nf*100:.1f}%"
            wf_str = f"{wf*100:.1f}%"
        elif key == 'num_trades':
            nf_str = f"{nf}"
            wf_str = f"{wf}"
        else:
            nf_str = f"{nf:.4f}"
            wf_str = f"{wf:.4f}"
        
        improvement = calc_improvement(nf, wf, higher_better)
        
        if key in ['sharpe', 'max_dd']:
            total_improvement += improvement
        
        sign = "+" if improvement > 0 else ""
        print(f"{label:<15} {nf_str:>12} {wf_str:>12} {sign}{improvement:>10.0f}%")
    
    print("-" * 60)
    
    # Recommendation
    if total_improvement > 20:
        print("\n✅ Recommendation: USE REGIME FILTER")
    elif total_improvement < -20:
        print("\n❌ Recommendation: DO NOT USE REGIME FILTER")
    else:
        print("\n⚠️  Recommendation: MARGINAL DIFFERENCE - test further")


def run_pipeline(args):
    """Execute the complete trading pipeline."""
    global DEBUG
    DEBUG = args.debug
    
    print("\n" + "=" * 60)
    print("QUANTITATIVE TRADING PIPELINE")
    print("=" * 60 + "\n")
    
    if DEBUG:
        print("🔧 DEBUG MODE ENABLED\n")
    
    # ===== 1. Load Data =====
    print("STEP 1: Loading data...")
    loader = DataLoader(verbose=args.verbose)
    
    try:
        df = loader.load_csv(args.data)
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return None, None
    
    print(f"  ✓ Loaded {len(df)} rows\n")
    
    # Detect schema
    schema = loader.detect_schema(df)
    print(f"  ✓ Detected schema: {schema}\n")
    
    # ===== 2. Feature Engineering =====
    print("STEP 2: Adding features...")
    engine = FeatureEngine(verbose=args.verbose)
    
    # Add mid price if needed
    df = loader.add_mid_price(df)
    
    # Add all features
    df = engine.add_all(df)
    
    # Fill missing values (from rolling calculations)
    df = engine.fill_missing(df, method='ffill')
    
    feature_cols = [c for c in df.columns if c not in ['timestamp']]
    print(f"  ✓ Added {len(feature_cols)} features\n")
    
    # ===== Handle Regime Filter Comparison =====
    if args.compare_regime_filter:
        print("STEP 3: Running regime filter comparison...")
        
        # Run without filter
        print("\n  Running WITHOUT regime filter...")
        _, no_filter_metrics = run_backtest_on_data(
            df, args.strategy, args, 
            use_regime_filter=False, 
            label="No Filter"
        )
        
        # Run with filter
        print("  Running WITH regime filter...")
        _, with_filter_metrics = run_backtest_on_data(
            df, args.strategy, args,
            use_regime_filter=True,
            label="With Filter"
        )
        
        # Print comparison
        print_regime_comparison(no_filter_metrics, with_filter_metrics)
        
        print("\n" + "=" * 60)
        print("COMPARISON COMPLETE")
        print("=" * 60 + "\n")
        
        return None, {'no_filter': no_filter_metrics, 'with_filter': with_filter_metrics}
    
    # ===== Handle Train/Test Split =====
    if args.eval_mode == 'split':
        print("STEP 3: Running train/test split evaluation...")
        
        # Split data
        split_idx = int(len(df) * args.train_ratio)
        train_df = df.iloc[:split_idx].copy().reset_index(drop=True)
        test_df = df.iloc[split_idx:].copy().reset_index(drop=True)
        
        print(f"  ✓ Training set: {len(train_df)} rows (0-{split_idx-1})")
        print(f"  ✓ Test set: {len(test_df)} rows ({split_idx}-{len(df)-1})")
        
        # Run on training data
        print("\n  Running on TRAINING data...")
        _, train_metrics = run_backtest_on_data(
            train_df, args.strategy, args,
            use_regime_filter=args.use_regime_filter,
            label="Training"
        )
        
        # Run on test data
        print("  Running on TEST data...")
        _, test_metrics = run_backtest_on_data(
            test_df, args.strategy, args,
            use_regime_filter=args.use_regime_filter,
            label="Test"
        )
        
        # Print comparison
        print_split_comparison(train_metrics, test_metrics)
        
        print("\n" + "=" * 60)
        print("SPLIT EVALUATION COMPLETE")
        print("=" * 60 + "\n")
        
        return None, {'train': train_metrics, 'test': test_metrics}
    
    # ===== Standard Full Pipeline =====
    print("STEP 3: Initializing strategy...")
    
    # Get strategy config
    strategy_config = STRATEGIES[args.strategy]
    signal_func = strategy_config['func']
    signal_params = strategy_config['params']
    
    print(f"  ✓ Strategy: {args.strategy}")
    print(f"  ✓ Parameters: {signal_params}")
    
    # Initialize risk manager
    risk_manager = RiskManager(
        max_position=args.max_position,
        max_drawdown=args.max_drawdown,
        vol_threshold=Config.VOL_THRESHOLD,
        vol_window=Config.VOL_WINDOW
    )
    
    # Set up regime filter if requested
    regime_filter = should_trade_regime if args.use_regime_filter else None
    
    # Create strategy
    strategy = Strategy(
        signal_func=signal_func,
        risk_manager=risk_manager,
        regime_filter=regime_filter,
        signal_params=signal_params
    )
    
    print(f"  ✓ Risk manager initialized (max_pos={args.max_position}, max_dd={args.max_drawdown})")
    if args.use_regime_filter:
        print("  ✓ Volatility regime filter enabled")
    print()
    
    # ===== 4. Precompute Signals =====
    print("STEP 4: Generating signals...")
    signals = strategy.precompute_signals(df)
    
    # Count signals
    buy_count = sum(1 for s in signals if s == 'BUY')
    sell_count = sum(1 for s in signals if s == 'SELL')
    close_count = sum(1 for s in signals if s == 'CLOSE')
    
    print(f"  ✓ Generated {buy_count + sell_count + close_count} signals")
    print(f"    - BUY: {buy_count}")
    print(f"    - SELL: {sell_count}")
    print(f"    - CLOSE: {close_count}\n")
    
    # Compute regime if using filter
    regimes = None
    if args.use_regime_filter:
        regimes = volatility_regime(df)
    
    # ===== 5. Run Backtest =====
    print("STEP 5: Running backtest...")
    
    backtester = Backtester(
        initial_cash=args.initial_cash,
        maker_fee=Config.MAKER_FEE,
        taker_fee=Config.TAKER_FEE,
        max_position=args.max_position,
        max_drawdown=args.max_drawdown
    )
    
    # Track progress
    n_rows = len(df)
    progress_interval = max(1, n_rows // 10)
    
    for i, (idx, tick) in enumerate(df.iterrows()):
        # Get regime if using filter
        regime = regimes[i] if regimes else None
        
        # Get signal through strategy (with risk checks)
        signal = strategy.get_signal_at_index(
            index=i,
            current_position=backtester.position,
            current_equity=backtester.cash + backtester.position * tick.get('mid', tick.get('close', 0)),
            regime=regime
        )
        
        debug_log(f"Tick {i}: price={tick.get('mid', 0):.4f}, signal={signal}, pos={backtester.position}")
        
        # Process tick
        backtester.process_tick(tick, signal, trade_qty=args.trade_qty)
        
        # Update risk manager returns history
        if len(backtester.equity_curve) > 1:
            curr_return = (backtester.equity_curve[-1] - backtester.equity_curve[-2]) / backtester.equity_curve[-2]
            risk_manager.add_return(curr_return)
        
        # Progress update
        if (i + 1) % progress_interval == 0:
            pct = (i + 1) / n_rows * 100
            print(f"  ... {pct:.0f}% complete ({i + 1}/{n_rows} ticks)")
    
    print(f"  ✓ Completed {len(backtester.trades)} trades\n")
    
    # Check if halted
    if backtester.is_halted:
        print("  ⚠ WARNING: Circuit breaker was triggered (max drawdown exceeded)\n")
    
    # ===== 6. Get Results =====
    print("STEP 6: Calculating metrics...")
    results = backtester.get_results()
    
    # Calculate comprehensive metrics
    metrics = MetricsCalculator.calculate_all(
        results['equity_curve'],
        periods_per_year=Config.PERIODS_PER_YEAR
    )
    
    # Add additional metrics from backtest
    metrics['total_pnl'] = results['total_pnl']
    metrics['num_trades'] = results['num_trades']
    metrics['final_position'] = results['final_position']
    metrics['was_halted'] = results['was_halted']
    
    # Print results
    print_metrics_table(metrics)
    
    # ===== 7. Generate Plots =====
    if args.plot:
        print("\nSTEP 7: Generating plots...")
        
        # Ensure output directory exists
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate combined dashboard
        plot_path = output_dir / f'dashboard_{args.strategy}.png'
        plot_all(results, str(plot_path))
    
    # ===== 8. Save Results =====
    print("\nSTEP 8: Saving results...")
    
    # Ensure output directory exists
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save metrics to CSV
    metrics_df = pd.DataFrame([metrics])
    metrics_path = output_dir / f'metrics_{args.strategy}.csv'
    metrics_df.to_csv(metrics_path, index=False)
    print(f"  ✓ Saved metrics to {metrics_path}")
    
    # Save trades using the new method
    if results['trades']:
        trades_path = output_dir / f'trades_{args.strategy}.csv'
        backtester.save_trades(str(trades_path))
    
    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60 + "\n")
    
    return results, metrics


def main():
    """Main entry point."""
    args = parse_args()
    
    try:
        results, metrics = run_pipeline(args)
        
        # Exit with appropriate code
        if results is None and metrics is None:
            sys.exit(1)
        elif isinstance(metrics, dict) and metrics.get('was_halted', False):
            sys.exit(2)  # Warning - circuit breaker triggered
        else:
            sys.exit(0)
            
    except KeyboardInterrupt:
        print("\n\n⚠ Pipeline interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Pipeline failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
