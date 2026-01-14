#!/usr/bin/env python
"""
Pre-submission validation script.

Run all checks before submitting to competition.

Usage:
    python scripts/validate_submission.py
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np


def check_required_files() -> tuple:
    """Check if all required files exist."""
    required_files = [
        'config.py',
        'src/core/backtester.py',
        'src/core/risk_manager.py',
        'src/core/metrics.py',
        'src/data/loader.py',
        'src/data/features.py',
        'src/signals/price_based.py',
        'src/signals/flow_based.py',
        'src/signals/regime_based.py',
        'src/execution/strategy.py',
        'scripts/run_pipeline.py',
        'requirements.txt'
    ]
    
    missing = []
    for f in required_files:
        if not Path(f).exists():
            missing.append(f)
    
    return len(missing) == 0, missing


def check_code_runs() -> tuple:
    """Check if code runs without import errors."""
    try:
        from config import Config
        from src.core.backtester import Backtester
        from src.core.risk_manager import RiskManager
        from src.core.metrics import MetricsCalculator
        from src.data.loader import DataLoader
        from src.data.features import FeatureEngine
        from src.signals.price_based import z_score_signal
        from src.execution.strategy import Strategy
        return True, None
    except ImportError as e:
        return False, str(e)


def check_test_pipeline() -> tuple:
    """Run a test pipeline with synthetic data."""
    try:
        import pandas as pd
        import numpy as np
        
        from src.core.backtester import Backtester
        from src.core.risk_manager import RiskManager
        from src.core.metrics import MetricsCalculator
        from src.signals.price_based import z_score_signal
        from src.execution.strategy import Strategy
        
        # Generate synthetic data
        np.random.seed(42)
        n = 200
        df = pd.DataFrame({
            'timestamp': range(n),
            'bid': 100 + np.random.randn(n).cumsum() * 0.1,
            'ask': 100 + np.random.randn(n).cumsum() * 0.1 + 0.01,
            'bid_qty': np.random.randint(100, 1000, n),
            'ask_qty': np.random.randint(100, 1000, n)
        })
        df['mid'] = (df['bid'] + df['ask']) / 2
        
        # Run backtest
        risk_manager = RiskManager(max_position=10, max_drawdown=0.20)
        strategy = Strategy(
            signal_func=z_score_signal,
            risk_manager=risk_manager,
            signal_params={'window': 20, 'entry_z': 1.5, 'exit_z': 0.5}
        )
        
        backtester = Backtester(
            initial_cash=100000,
            max_position=10,
            max_drawdown=0.20
        )
        
        signals = strategy.precompute_signals(df)
        
        for i, (idx, tick) in enumerate(df.iterrows()):
            signal = strategy.get_signal_at_index(
                index=i,
                current_position=backtester.position,
                current_equity=backtester.cash + backtester.position * tick['mid']
            )
            backtester.process_tick(tick, signal)
        
        results = backtester.get_results()
        metrics = MetricsCalculator.calculate_all(results['equity_curve'])
        
        return True, metrics
        
    except Exception as e:
        return False, str(e)


def check_metrics_valid(metrics: dict) -> tuple:
    """Check if metrics are within reasonable bounds."""
    issues = []
    
    if metrics is None:
        return False, ["No metrics to validate"]
    
    # Check Sharpe ratio
    sharpe = metrics.get('sharpe', 0)
    if not np.isfinite(sharpe):
        issues.append(f"Sharpe ratio is not finite: {sharpe}")
    elif sharpe < -5 or sharpe > 10:
        issues.append(f"Sharpe ratio seems unrealistic: {sharpe:.2f}")
    
    # Check max drawdown
    max_dd = metrics.get('max_dd', 0)
    if not np.isfinite(max_dd):
        issues.append(f"Max drawdown is not finite: {max_dd}")
    elif max_dd > 0:
        issues.append(f"Max drawdown should be negative: {max_dd}")
    elif max_dd < -1:
        issues.append(f"Max drawdown is impossible (<-100%): {max_dd}")
    
    # Check total return
    total_return = metrics.get('total_return', 0)
    if not np.isfinite(total_return):
        issues.append(f"Total return is not finite: {total_return}")
    
    # Check win rate
    win_rate = metrics.get('win_rate', 0)
    if win_rate < 0 or win_rate > 1:
        issues.append(f"Win rate should be between 0 and 1: {win_rate}")
    
    return len(issues) == 0, issues


def check_no_nan_inf(metrics: dict) -> tuple:
    """Check for NaN or Inf values in metrics."""
    if metrics is None:
        return True, []
    
    issues = []
    for key, value in metrics.items():
        if isinstance(value, (int, float)):
            if np.isnan(value):
                issues.append(f"{key}: NaN")
            elif np.isinf(value):
                issues.append(f"{key}: Inf")
    
    return len(issues) == 0, issues


def check_results_dir() -> tuple:
    """Check if results directory has expected files."""
    results_dir = Path('results')
    if not results_dir.exists():
        return False, ["results/ directory does not exist"]
    
    files = list(results_dir.glob('*'))
    if len(files) == 0:
        return False, ["results/ directory is empty"]
    
    return True, [f.name for f in files]


def validate_submission():
    """Run all validation checks."""
    print("\n" + "=" * 60)
    print("PRE-SUBMISSION VALIDATION CHECKLIST")
    print("=" * 60 + "\n")
    
    all_passed = True
    
    # Check 1: Required files
    print("📁 Check 1: Required files...")
    passed, missing = check_required_files()
    if passed:
        print("   ✅ All required files present")
    else:
        print("   ❌ Missing files:")
        for f in missing:
            print(f"      - {f}")
        all_passed = False
    
    # Check 2: Code imports
    print("\n🔧 Check 2: Code imports...")
    passed, error = check_code_runs()
    if passed:
        print("   ✅ All imports successful")
    else:
        print(f"   ❌ Import error: {error}")
        all_passed = False
    
    # Check 3: Test pipeline
    print("\n🔬 Check 3: Test pipeline...")
    passed, result = check_test_pipeline()
    if passed:
        print("   ✅ Test pipeline completed successfully")
        metrics = result
    else:
        print(f"   ❌ Pipeline error: {result}")
        all_passed = False
        metrics = None
    
    # Check 4: Metrics validation
    print("\n📊 Check 4: Metrics validation...")
    if metrics:
        passed, issues = check_metrics_valid(metrics)
        if passed:
            print("   ✅ Metrics are within reasonable bounds")
            print(f"      Sharpe: {metrics['sharpe']:.4f}")
            print(f"      Max DD: {metrics['max_dd']*100:.2f}%")
        else:
            print("   ⚠️  Metrics warnings:")
            for issue in issues:
                print(f"      - {issue}")
    else:
        print("   ⏭️  Skipped (no metrics)")
    
    # Check 5: No NaN/Inf
    print("\n🔢 Check 5: No NaN/Inf values...")
    if metrics:
        passed, issues = check_no_nan_inf(metrics)
        if passed:
            print("   ✅ No NaN or Inf values")
        else:
            print("   ❌ Invalid values found:")
            for issue in issues:
                print(f"      - {issue}")
            all_passed = False
    else:
        print("   ⏭️  Skipped (no metrics)")
    
    # Check 6: Results directory
    print("\n📂 Check 6: Results directory...")
    passed, files_or_error = check_results_dir()
    if passed:
        print(f"   ✅ Results directory has {len(files_or_error)} files")
    else:
        print(f"   ⚠️  {files_or_error[0]}")
    
    # Summary
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL CHECKS PASSED - Ready for submission!")
    else:
        print("❌ SOME CHECKS FAILED - Please fix before submitting")
        print("\nNext steps:")
        print("1. Fix any ❌ errors above")
        print("2. Re-run this validation script")
        print("3. Submit when all checks pass")
    print("=" * 60 + "\n")
    
    return all_passed


if __name__ == '__main__':
    success = validate_submission()
    sys.exit(0 if success else 1)
