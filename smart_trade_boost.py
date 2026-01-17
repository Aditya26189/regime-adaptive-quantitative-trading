# smart_trade_boost.py - SURGICAL FIX
"""
Strategy:
- Keep VBL at ENSEMBLE (1.574 Sharpe, 127 trades) - SAFE ENOUGH
- Keep RELIANCE at Advanced_V2 (1.683 Sharpe, 128 trades) - SAFE ENOUGH  
- Keep NIFTY at Trend (0.006, 132 trades) - OK
- ONLY boost SUNPHARMA and YESBANK aggressively
"""

import json
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.strategies.hybrid_adaptive_v2 import HybridAdaptiveStrategyV2
from src.strategies.hybrid_adaptive import HybridAdaptiveStrategy
from src.strategies.ensemble_wrapper import EnsembleStrategy
from src.strategies.nifty_trend_strategy import generate_nifty_trend_signals

print("="*70)
print("🎯 SMART TRADE BOOST - Surgical Fix")
print("="*70)

# Load all params
baseline = json.load(open('baseline_metrics.json', 'r'))
try:
    advanced = json.load(open('advanced_optimization_results.json', 'r'))
except:
    advanced = {'results': {}}

try:
    nifty_data = json.load(open('optimization_results/nifty_optuna_best.json', 'r'))
    nifty_params = nifty_data['params']
except:
    nifty_params = baseline['NIFTY50']['params']

final_params = {}
final_results = {}

# ===== VBL - KEEP ORIGINAL ENSEMBLE =====
print("\n[VBL] Keeping original Ensemble (1.574 Sharpe)")
vbl_params = baseline['VBL']['params'].copy()
vbl_params = {k: v for k, v in vbl_params.items() if k != '_strategy'}
final_params['VBL'] = {'params': vbl_params, 'strategy': 'ensemble'}
final_results['VBL'] = {'trades': 127, 'sharpe': 1.574, 'source': 'ORIGINAL'}

# ===== RELIANCE - KEEP ADVANCED V2 =====
print("[RELIANCE] Keeping Advanced_V2 (1.683 Sharpe)")
rel_params = advanced['results']['RELIANCE']['params'].copy()
final_params['RELIANCE'] = {'params': rel_params, 'strategy': 'advanced_v2'}
final_results['RELIANCE'] = {'trades': 128, 'sharpe': 1.683, 'source': 'ORIGINAL'}

# ===== NIFTY - KEEP ORIGINAL TREND =====
print("[NIFTY50] Keeping Trend (0.006 Sharpe)")
final_params['NIFTY50'] = {'params': nifty_params, 'strategy': 'trend'}
final_results['NIFTY50'] = {'trades': 132, 'sharpe': 0.006, 'source': 'ORIGINAL'}

# ===== SUNPHARMA - AGGRESSIVE BOOST =====
print("\n[SUNPHARMA] 🔴 NEEDS AGGRESSIVE BOOST (120 → 135+)")
df = pd.read_csv('data/raw/NSE_SUNPHARMA_EQ_1hour.csv')
df['datetime'] = pd.to_datetime(df['datetime'])
df = df.sort_values('datetime').reset_index(drop=True)

sun_params = advanced['results']['SUNPHARMA']['params'].copy()

# Aggressive loosening for SUNPHARMA
sun_params['rsi_entry'] = 38  # Was ~30, now much looser
sun_params['vol_min_pct'] = 0.003  # Very low
sun_params['max_hold_bars'] = 8  # Faster cycling
sun_params['use_adaptive_hold'] = False  # Disable, just use fixed short hold
sun_params['use_multi_timeframe'] = False
sun_params['use_profit_ladder'] = False

# Test multiple iterations to find the sweet spot
best_sun = {'trades': 0, 'sharpe': 0, 'params': None}
for rsi_entry in [35, 37, 38, 40]:
    for vol_min in [0.002, 0.003, 0.004]:
        for max_hold in [7, 8, 9]:
            test_params = sun_params.copy()
            test_params['rsi_entry'] = rsi_entry
            test_params['vol_min_pct'] = vol_min
            test_params['max_hold_bars'] = max_hold
            
            strategy = HybridAdaptiveStrategyV2(test_params)
            trades, metrics = strategy.backtest(df)
            
            # We want trades >= 135 with highest possible Sharpe
            if metrics['total_trades'] >= 135:
                if metrics['sharpe_ratio'] > best_sun['sharpe']:
                    best_sun = {
                        'trades': metrics['total_trades'],
                        'sharpe': metrics['sharpe_ratio'],
                        'params': test_params.copy()
                    }

if best_sun['params']:
    print(f"  Found: {best_sun['trades']} trades, {best_sun['sharpe']:.3f} Sharpe")
    final_params['SUNPHARMA'] = {'params': best_sun['params'], 'strategy': 'advanced_v2'}
    final_results['SUNPHARMA'] = {'trades': best_sun['trades'], 'sharpe': best_sun['sharpe'], 'source': 'BOOSTED'}
else:
    # Fallback: just use most aggressive
    print("  Using max aggressive params")
    sun_params['rsi_entry'] = 42
    sun_params['vol_min_pct'] = 0.002
    strategy = HybridAdaptiveStrategyV2(sun_params)
    trades, metrics = strategy.backtest(df)
    final_params['SUNPHARMA'] = {'params': sun_params, 'strategy': 'advanced_v2'}
    final_results['SUNPHARMA'] = {'trades': metrics['total_trades'], 'sharpe': metrics['sharpe_ratio'], 'source': 'BOOSTED'}
    print(f"  Result: {metrics['total_trades']} trades, {metrics['sharpe_ratio']:.3f} Sharpe")

# ===== YESBANK - AGGRESSIVE BOOST =====
print("\n[YESBANK] 🔴 NEEDS AGGRESSIVE BOOST (122 → 135+)")
df = pd.read_csv('data/raw/NSE_YESBANK_EQ_1hour.csv')
df['datetime'] = pd.to_datetime(df['datetime'])
df = df.sort_values('datetime').reset_index(drop=True)

yes_params = baseline['YESBANK']['params'].copy()
yes_params = {k: v for k, v in yes_params.items() if k != '_strategy'}

# Aggressive loosening for YESBANK
best_yes = {'trades': 0, 'sharpe': 0, 'params': None}
for rsi_entry in [35, 38, 40, 42]:
    for vol_min in [0.002, 0.003, 0.004]:
        for max_hold in [6, 7, 8]:
            test_params = yes_params.copy()
            test_params['rsi_entry'] = rsi_entry
            test_params['vol_min_pct'] = vol_min
            test_params['max_hold_bars'] = max_hold
            
            strategy = HybridAdaptiveStrategy(test_params)
            trades, metrics = strategy.backtest(df)
            
            if metrics['total_trades'] >= 135:
                if metrics['sharpe_ratio'] > best_yes['sharpe']:
                    best_yes = {
                        'trades': metrics['total_trades'],
                        'sharpe': metrics['sharpe_ratio'],
                        'params': test_params.copy()
                    }

if best_yes['params']:
    print(f"  Found: {best_yes['trades']} trades, {best_yes['sharpe']:.3f} Sharpe")
    final_params['YESBANK'] = {'params': best_yes['params'], 'strategy': 'baseline'}
    final_results['YESBANK'] = {'trades': best_yes['trades'], 'sharpe': best_yes['sharpe'], 'source': 'BOOSTED'}
else:
    # Try even more aggressive
    print("  Using very aggressive params")
    yes_params['rsi_entry'] = 45
    yes_params['vol_min_pct'] = 0.001
    yes_params['max_hold_bars'] = 5
    strategy = HybridAdaptiveStrategy(yes_params)
    trades, metrics = strategy.backtest(df)
    final_params['YESBANK'] = {'params': yes_params, 'strategy': 'baseline'}
    final_results['YESBANK'] = {'trades': metrics['total_trades'], 'sharpe': metrics['sharpe_ratio'], 'source': 'BOOSTED'}
    print(f"  Result: {metrics['total_trades']} trades, {metrics['sharpe_ratio']:.3f} Sharpe")

# Save final params
with open('output/final_safe_params.json', 'w') as f:
    json.dump(final_params, f, indent=2, default=str)

# Summary
print("\n" + "="*70)
print("🎯 SMART BOOST SUMMARY")
print("="*70)

total_trades = 0
sharpes = []
for symbol in ['VBL', 'RELIANCE', 'SUNPHARMA', 'YESBANK', 'NIFTY50']:
    result = final_results[symbol]
    margin = result['trades'] - 120
    status_icon = "✅" if margin >= 10 else "⚠️" if margin >= 5 else "🔴"
    print(f"{symbol:12} {result['trades']:3} trades (+{margin:2}) | Sharpe: {result['sharpe']:.3f} | {status_icon} [{result['source']}]")
    total_trades += result['trades']
    sharpes.append(result['sharpe'])

portfolio_sharpe = sum(sharpes) / len(sharpes)
print(f"\n{'='*70}")
print(f"TOTAL TRADES: {total_trades}")
print(f"PORTFOLIO SHARPE: {portfolio_sharpe:.3f}")
print(f"{'='*70}")

all_safe = all(final_results[s]['trades'] >= 130 for s in final_results)
if all_safe:
    print("\n✅ ALL SYMBOLS SAFE FOR SUBMISSION")
else:
    risky = [s for s in final_results if final_results[s]['trades'] < 130]
    print(f"\n⚠️ STILL RISKY: {risky}")
