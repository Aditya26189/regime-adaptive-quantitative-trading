"""
Quick test of NIFTY50 trend strategy (5-minute validation)
"""

import pandas as pd
from src.strategies.nifty_trend_strategy import optimize_nifty_trend_parameters

print("="*60)
print("NIFTY50 TREND STRATEGY - QUICK TEST")
print("="*60)

# Load data
data = pd.read_csv('data/raw/NSE_NIFTY50_INDEX_1hour.csv')
print(f"Data loaded: {len(data)} rows")

# Quick optimization (100 iterations, ~5 minutes)
print("\nRunning quick optimization (100 iterations)...")
params, trades_df = optimize_nifty_trend_parameters(data, n_iterations=100, verbose=True)

# Validate results
if params is None or len(trades_df) == 0:
    print("\n❌ FAILED: No valid strategy found!")
    print("Debug needed. Check:")
    print("  1. Data file has 'datetime' and 'close' columns")
    print("  2. Date range is 2025-01-01 to 2025-12-31")
    exit(1)

# Calculate metrics
total_return = trades_df['pnl'].sum() / 100000 * 100
trades_df['return_pct'] = trades_df['pnl'] / 100000 * 100
sharpe = trades_df['return_pct'].mean() / trades_df['return_pct'].std()

print(f"\n{'='*60}")
print(f"QUICK TEST RESULTS")
print(f"{'='*60}")
print(f"Return: {total_return:+.2f}% (was -2.84%)")
print(f"Sharpe: {sharpe:.3f} (was -1.14)")
print(f"Trades: {len(trades_df)} (min 120)")
print(f"Win Rate: {(trades_df['pnl'] > 0).sum() / len(trades_df) * 100:.1f}%")

# Validation checkpoints
checkpoints = []
checkpoints.append(("Return > 0%", total_return > 0))
checkpoints.append(("Sharpe > 0.5", sharpe > 0.5))
checkpoints.append(("Trades >= 120", len(trades_df) >= 120))

print(f"\nCheckpoints:")
all_passed = True
for check_name, passed in checkpoints:
    status = "✓" if passed else "❌"
    print(f"  {status} {check_name}")
    if not passed:
        all_passed = False

if all_passed:
    print(f"\n✅ SUCCESS! Ready for full optimization.")
    print(f"Expected after 500 iterations: Sharpe 1.2-1.5, Return +4-6%")
else:
    print(f"\n⚠️ PARTIAL SUCCESS. Review parameters and retry.")

# Save quick test params
import json
with open('output/nifty_quick_test_params.json', 'w') as f:
    json.dump(params, f, indent=2)
    
print(f"\n✓ Parameters saved: output/nifty_quick_test_params.json")
