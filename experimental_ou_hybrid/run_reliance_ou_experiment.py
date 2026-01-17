"""
RELIANCE OU EXPERIMENT RUNNER
Compares baseline RELIANCE strategy vs experimental OU-Hybrid strategy.
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime

# Add project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from experimental_ou_hybrid.hybrid_strategy_reliance import HybridOURelianceStrategy
from src.strategies.hybrid_adaptive_v2 import HybridAdaptiveStrategyV2


# Config
DATA_PATH = 'data/raw/NSE_RELIANCE_EQ_1hour.csv'
CAPITAL = 2000000.0
TRAIN_RATIO = 0.75

# Load Data
print("="*70)
print("RELIANCE OU-HYBRID EXPERIMENT")
print("="*70)

df = pd.read_csv(DATA_PATH)
df['datetime'] = pd.to_datetime(df['datetime'])
df = df.sort_values('datetime').reset_index(drop=True)

# Train/Test Split
train_len = int(len(df) * TRAIN_RATIO)
train_df = df.iloc[:train_len].copy()
test_df = df.iloc[train_len:].copy()

print(f"Data: {len(df)} bars | Train: {len(train_df)} | Test: {len(test_df)}")

# ----- BASELINE STRATEGY -----
print("\n[1/2] Running Baseline Strategy (HybridAdaptiveStrategyV2)...")

baseline_params = {
    "strategy_type": "HYBRID",
    "ker_period": 10,
    "ker_threshold_meanrev": 0.28,
    "ker_threshold_trend": 0.5,
    "rsi_period": 2,
    "rsi_entry_range": 29,
    "rsi_exit_range": 90,
    "vol_min_pct": 0.008,
    "ema_fast": 5,
    "ema_slow": 21,
    "allowed_hours": [9, 10, 11, 12],
    "max_hold_bars": 8,
    "use_dynamic_sizing": False,
    "use_multi_timeframe": True,
    "daily_ema_period": 50,
    "require_daily_bias": False,
    "use_profit_ladder": False,
    "use_adaptive_hold": True,
    "use_dynamic_rsi": False
}

# Train
baseline_train = HybridAdaptiveStrategyV2(baseline_params)
_, baseline_train_metrics = baseline_train.backtest(train_df, initial_capital=CAPITAL)

# Test
baseline_test = HybridAdaptiveStrategyV2(baseline_params)
_, baseline_test_metrics = baseline_test.backtest(test_df, initial_capital=CAPITAL)

print(f"  Train Sharpe: {baseline_train_metrics.get('sharpe_ratio', 0):.2f}")
print(f"  Test Sharpe:  {baseline_test_metrics.get('sharpe_ratio', 0):.2f}")
print(f"  Train Trades: {baseline_train_metrics.get('total_trades', 0)}")
print(f"  Test Trades:  {baseline_test_metrics.get('total_trades', 0)}")


# ----- OU-HYBRID STRATEGY -----
print("\n[2/2] Running OU-Hybrid Strategy...")

ou_params = {
    'ou_window': 200,
    's_entry': 1.8,  # Relaxed for more trades
    's_exit': 0.3,
    's_stop': 4.0,
    'sma_period': 50,
    'atr_period': 14,
    'atr_mult': 2.0,
    'max_hold_bars': 12
}

# Train
ou_train = HybridOURelianceStrategy(ou_params)
ou_train_trades, ou_train_metrics = ou_train.backtest(train_df, initial_capital=CAPITAL)

# Test
ou_test = HybridOURelianceStrategy(ou_params)
ou_test_trades, ou_test_metrics = ou_test.backtest(test_df, initial_capital=CAPITAL)

print(f"  Train Sharpe: {ou_train_metrics.get('sharpe_ratio', 0):.2f}")
print(f"  Test Sharpe:  {ou_test_metrics.get('sharpe_ratio', 0):.2f}")
print(f"  Train Trades: {ou_train_metrics.get('total_trades', 0)}")
print(f"  Test Trades:  {ou_test_metrics.get('total_trades', 0)}")

if 'regime_breakdown' in ou_train_metrics:
    print(f"  Regime Breakdown (Train): {ou_train_metrics['regime_breakdown']}")

# ----- ANALYSIS -----
print("\n" + "="*70)
print("EXPERIMENT ANALYSIS")
print("="*70)

baseline_train_sharpe = baseline_train_metrics.get('sharpe_ratio', 0)
baseline_test_sharpe = baseline_test_metrics.get('sharpe_ratio', 0)
ou_train_sharpe = ou_train_metrics.get('sharpe_ratio', 0)
ou_test_sharpe = ou_test_metrics.get('sharpe_ratio', 0)

baseline_degradation = (baseline_train_sharpe - baseline_test_sharpe) / max(baseline_train_sharpe, 0.01) * 100
ou_degradation = (ou_train_sharpe - ou_test_sharpe) / max(ou_train_sharpe, 0.01) * 100

ou_total_trades = ou_train_metrics.get('total_trades', 0) + ou_test_metrics.get('total_trades', 0)
baseline_total_trades = baseline_train_metrics.get('total_trades', 0) + baseline_test_metrics.get('total_trades', 0)

print(f"Baseline Degradation: {baseline_degradation:.1f}%")
print(f"OU-Hybrid Degradation: {ou_degradation:.1f}%")
print(f"Baseline Total Trades: {baseline_total_trades}")
print(f"OU-Hybrid Total Trades: {ou_total_trades}")

# Decision Logic
USE_OU = (
    ou_test_sharpe >= baseline_test_sharpe - 0.1 and
    ou_test_sharpe >= 1.5 and
    ou_total_trades >= 120 and
    ou_degradation <= 40
)

print("\n" + "="*70)
print("DECISION")
print("="*70)

if USE_OU:
    print("✅ OU-HYBRID STRATEGY APPROVED FOR EXTRA SUBMISSION")
    print("   Preparing submission_ou_variant/ folder...")
    
    # Create folder
    os.makedirs('submission_ou_variant', exist_ok=True)
    
    # Copy existing 4 CSVs
    import shutil
    for symbol in ['NIFTY50', 'SUNPHARMA', 'VBL', 'YESBANK']:
        src = f"submission_new/STRATEGY5_NSE_{symbol.replace('50', '50-INDEX')}-EQ_trades.csv"
        if symbol == 'NIFTY50':
            src = "submission_new/STRATEGY5_NSE_NIFTY50-INDEX_trades.csv"
        dst = f"submission_ou_variant/STRATEGY5_NSE_{symbol.replace('50', '50-INDEX')}-EQ_trades.csv"
        if symbol == 'NIFTY50':
            dst = "submission_ou_variant/STRATEGY5_NSE_NIFTY50-INDEX_trades.csv"
            
        if os.path.exists(src):
            shutil.copy(src, dst)
            print(f"   Copied {symbol}")
            
    # Generate new RELIANCE CSV
    full_ou = HybridOURelianceStrategy(ou_params)
    full_trades, full_metrics = full_ou.backtest(df, initial_capital=CAPITAL)
    
    # Format for submission
    # ... (would need to match exact format)
    print(f"   OU RELIANCE Full-Year Trades: {full_metrics.get('total_trades', 0)}")
    print(f"   OU RELIANCE Full-Year Sharpe: {full_metrics.get('sharpe_ratio', 0):.2f}")
    
else:
    print("❌ OU-HYBRID NOT STRONG ENOUGH FOR SUBMISSION")
    print("   Baseline strategy remains preferred.")
    print(f"   Reasons:")
    if ou_test_sharpe < baseline_test_sharpe - 0.1:
        print(f"   - Test Sharpe ({ou_test_sharpe:.2f}) < Baseline ({baseline_test_sharpe:.2f}) - 0.1")
    if ou_test_sharpe < 1.5:
        print(f"   - Test Sharpe ({ou_test_sharpe:.2f}) < 1.5 threshold")
    if ou_total_trades < 120:
        print(f"   - Total trades ({ou_total_trades}) < 120 minimum")
    if ou_degradation > 40:
        print(f"   - Degradation ({ou_degradation:.1f}%) > 40% threshold")

# ----- SAVE REPORT -----
report = f"""# RELIANCE OU-HYBRID EXPERIMENT RESULTS

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Baseline Strategy (HybridAdaptiveStrategyV2)
- Train Sharpe: {baseline_train_sharpe:.2f}
- Test Sharpe: {baseline_test_sharpe:.2f}
- Total Trades: {baseline_total_trades}
- Degradation: {baseline_degradation:.1f}%

## OU-Hybrid Strategy (Experimental)
- Train Sharpe: {ou_train_sharpe:.2f}
- Test Sharpe: {ou_test_sharpe:.2f}
- Total Trades: {ou_total_trades}
- Degradation: {ou_degradation:.1f}%

## Constraint Checks
- OU trades >= 120? {'Yes' if ou_total_trades >= 120 else 'No'} ({ou_total_trades})
- Test Sharpe >= 1.5? {'Yes' if ou_test_sharpe >= 1.5 else 'No'} ({ou_test_sharpe:.2f})
- Degradation <= 40%? {'Yes' if ou_degradation <= 40 else 'No'} ({ou_degradation:.1f}%)

## Recommendation
{'USE FOR EXTRA SUBMISSION' if USE_OU else 'TOO RISKY, KEEP BASELINE'}
"""

os.makedirs('output', exist_ok=True)
with open('output/RELIANCE_OU_EXPERIMENT.md', 'w') as f:
    f.write(report)

print(f"\nReport saved to: output/RELIANCE_OU_EXPERIMENT.md")
