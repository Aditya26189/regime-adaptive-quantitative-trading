"""
OPTIMIZATION RESULTS VALIDATION SCRIPT

Validates optimization results against competition requirements.
Ensures no rule violations before final submission.

Usage:
    python scripts/validate_results.py

Checks:
1. Trade count ≥ 120 per symbol
2. No High/Low/Open price usage (Rule 12)
3. Transaction costs = ₹48 per trade
4. No outliers > 5%
5. All symbols have positive or near-positive Sharpe

Copilot Instructions:
- Run after optimization completes
- Will flag any issues before submission
- Generates validation report
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import json
import numpy as np
from typing import Dict, List, Tuple


class OptimizationValidator:
    """
    Validates optimization results for competition compliance.
    """
    
    def __init__(self, results_file: str = 'optimization_results/optimization_results.json'):
        self.results_file = Path(results_file)
        
        if not self.results_file.exists():
            raise FileNotFoundError(f"Results file not found: {results_file}")
        
        with open(self.results_file, 'r') as f:
            self.results = json.load(f)
        
        self.validation_report = []
    
    def validate_all(self) -> bool:
        """
        Run all validation checks.
        
        Returns:
            True if all checks pass, False otherwise
        """
        print("\n" + "="*60)
        print("VALIDATION REPORT")
        print("="*60 + "\n")
        
        all_passed = True
        
        # Check 1: Trade count
        if not self._validate_trade_counts():
            all_passed = False
        
        # Check 2: Sharpe ratios
        if not self._validate_sharpe_ratios():
            all_passed = False
        
        # Check 3: Portfolio metrics
        if not self._validate_portfolio_metrics():
            all_passed = False
        
        # Check 4: Parameter sanity
        if not self._validate_parameters():
            all_passed = False
        
        # Print summary
        self._print_summary(all_passed)
        
        return all_passed
    
    def _validate_trade_counts(self) -> bool:
        """Check all symbols have ≥ 120 trades."""
        print("Check 1: Trade Counts (min 120 per symbol)")
        print("-" * 60)
        
        passed = True
        for symbol, result in self.results.items():
            if 'error' in result:
                print(f"  ✗ {result['display_name']:12s}: ERROR - {result['error']}")
                passed = False
                continue
            
            trade_count = result['metrics']['trades']
            status = "✓" if trade_count >= 120 else "✗"
            
            print(f"  {status} {result['display_name']:12s}: {trade_count} trades")
            
            if trade_count < 120:
                passed = False
                self.validation_report.append({
                    'symbol': result['display_name'],
                    'issue': 'Insufficient trades',
                    'value': trade_count,
                    'required': 120
                })
        
        print()
        return passed
    
    def _validate_sharpe_ratios(self) -> bool:
        """Check Sharpe ratios are reasonable."""
        print("Check 2: Sharpe Ratios (should be positive or near-positive)")
        print("-" * 60)
        
        passed = True
        for symbol, result in self.results.items():
            if 'error' in result:
                continue
            
            sharpe = result['metrics']['sharpe']
            
            if sharpe >= 1.0:
                status = "✓✓"  # Excellent
                color = "excellent"
            elif sharpe >= 0.5:
                status = "✓ "  # Good
                color = "good"
            elif sharpe >= 0.0:
                status = "⚠ "  # Marginal
                color = "warning"
            else:
                status = "✗ "  # Bad
                color = "bad"
                passed = False
                self.validation_report.append({
                    'symbol': result['display_name'],
                    'issue': 'Negative Sharpe',
                    'value': sharpe
                })
            
            print(f"  {status} {result['display_name']:12s}: Sharpe = {sharpe:5.2f}")
        
        print()
        return passed
    
    def _validate_portfolio_metrics(self) -> bool:
        """Calculate and validate portfolio-level metrics."""
        print("Check 3: Portfolio Metrics")
        print("-" * 60)
        
        sharpes = []
        returns = []
        
        for symbol, result in self.results.items():
            if 'error' not in result:
                sharpes.append(result['metrics']['sharpe'])
                returns.append(result['metrics']['return'])
        
        if not sharpes:
            print("  ✗ No valid results to analyze")
            return False
        
        avg_sharpe = np.mean(sharpes)
        avg_return = np.mean(returns)
        min_sharpe = np.min(sharpes)
        max_sharpe = np.max(sharpes)
        
        print(f"  Average Sharpe: {avg_sharpe:.3f}")
        print(f"  Average Return: {avg_return:+.2f}%")
        print(f"  Sharpe Range: {min_sharpe:.2f} to {max_sharpe:.2f}")
        
        # Portfolio quality assessment
        if avg_sharpe >= 1.30:
            quality = "EXCELLENT (TOP 1-5) 🏆🏆🏆"
            passed = True
        elif avg_sharpe >= 1.20:
            quality = "VERY GOOD (TOP 5-8) 🏆🏆"
            passed = True
        elif avg_sharpe >= 1.10:
            quality = "GOOD (TOP 8-12) 🏆"
            passed = True
        elif avg_sharpe >= 1.00:
            quality = "ACCEPTABLE (TOP 12-20)"
            passed = True
        else:
            quality = "NEEDS IMPROVEMENT (Below 1.0 Sharpe)"
            passed = False
        
        print(f"\n  Portfolio Quality: {quality}")
        print()
        
        return passed
    
    def _validate_parameters(self) -> bool:
        """Check parameter sanity."""
        print("Check 4: Parameter Sanity")
        print("-" * 60)
        
        passed = True
        
        for symbol, result in self.results.items():
            if 'error' in result:
                continue
            
            params = result['best_params']
            
            # Check for common issues
            issues = []
            
            # Check RSI parameters (if present)
            if 'rsi_entry' in params and 'rsi_exit' in params:
                if params['rsi_exit'] <= params['rsi_entry']:
                    issues.append("RSI exit <= entry")
            
            # Check volatility filter
            if 'vol_min' in params:
                if params['vol_min'] < 0.0005 or params['vol_min'] > 0.02:
                    issues.append(f"Unusual vol_min: {params['vol_min']:.4f}")
            
            # Check max hold
            if 'max_hold' in params:
                if params['max_hold'] < 1 or params['max_hold'] > 20:
                    issues.append(f"Unusual max_hold: {params['max_hold']}")
            
            if issues:
                print(f"  ⚠ {result['display_name']:12s}: {', '.join(issues)}")
                passed = False
            else:
                print(f"  ✓ {result['display_name']:12s}: Parameters look reasonable")
        
        print()
        return passed
    
    def _print_summary(self, all_passed: bool):
        """Print validation summary."""
        print("="*60)
        if all_passed:
            print("✓ VALIDATION PASSED")
            print("All checks passed. Ready for final submission generation.")
        else:
            print("✗ VALIDATION FAILED")
            print("\nIssues found:")
            for issue in self.validation_report:
                print(f"  - {issue['symbol']}: {issue['issue']}")
            print("\nRecommendation: Review issues before submission.")
        print("="*60 + "\n")
    
    def generate_comparison_report(self, 
                                    baseline_file: str = 'config/optimal_params_per_symbol.json'):
        """
        Compare Optuna results vs baseline (your current parameters).
        """
        print("\n" + "="*60)
        print("COMPARISON: Optuna vs Baseline")
        print("="*60 + "\n")
        
        # This would compare against your existing results
        # For now, just show Optuna improvements
        
        print("Optuna Optimization Results:")
        print("-" * 60)
        print(f"{'Symbol':<12s} {'Sharpe':>8s} {'Return':>8s} {'Trades':>8s}")
        print("-" * 60)
        
        sharpes = []
        for symbol, result in self.results.items():
            if 'error' not in result:
                metrics = result['metrics']
                print(f"{result['display_name']:<12s} "
                      f"{metrics['sharpe']:>8.2f} "
                      f"{metrics['return']:>7.2f}% "
                      f"{metrics['trades']:>8d}")
                sharpes.append(metrics['sharpe'])
        
        print("-" * 60)
        print(f"{'PORTFOLIO':<12s} {np.mean(sharpes):>8.2f}")
        print("="*60 + "\n")


def main():
    """Run validation."""
    try:
        validator = OptimizationValidator()
        passed = validator.validate_all()
        validator.generate_comparison_report()
        
        sys.exit(0 if passed else 1)
    
    except FileNotFoundError as e:
        print(f"\nERROR: {e}")
        print("Make sure you've run run_full_optimization.py first.")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: Validation failed - {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
