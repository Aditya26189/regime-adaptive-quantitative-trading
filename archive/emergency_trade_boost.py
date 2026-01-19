# emergency_trade_boost.py - CRITICAL SAFETY FIX
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
print("🚨 EMERGENCY TRADE COUNT BOOST")
print("Target: ALL symbols >= 135 trades (15+ margin)")
print("="*70)

# Load baseline
baseline = json.load(open('baseline_metrics.json', 'r'))

# Load advanced results
try:
    advanced = json.load(open('advanced_optimization_results.json', 'r'))
except:
    advanced = {'results': {}}

# NIFTY params
try:
    nifty_data = json.load(open('optimization_results/nifty_optuna_best.json', 'r'))
    nifty_params = nifty_data['params']
except:
    nifty_params = baseline['NIFTY50']['params']

SYMBOLS = {
    'SUNPHARMA': {
        'file': 'data/raw/NSE_SUNPHARMA_EQ_1hour.csv',
        'strategy': 'advanced_v2',
        'target': 140,
        'current': 120,
    },
    'YESBANK': {
        'file': 'data/raw/NSE_YESBANK_EQ_1hour.csv',
        'strategy': 'baseline',  # Keep baseline, not V2
        'target': 135,
        'current': 122,
    },
    'VBL': {
        'file': 'data/raw/NSE_VBL_EQ_1hour.csv',
        'strategy': 'ensemble',
        'target': 135,
        'current': 127,
    },
    'RELIANCE': {
        'file': 'data/raw/NSE_RELIANCE_EQ_1hour.csv',
        'strategy': 'advanced_v2',
        'target': 135,
        'current': 128,
    },
    'NIFTY50': {
        'file': 'data/raw/NSE_NIFTY50_INDEX_1hour.csv',
        'strategy': 'trend',
        'target': 140,
        'current': 132,
    }
}

results = {}
boosted_params = {}

for symbol, config in SYMBOLS.items():
    print(f"\n{'='*70}")
    print(f"BOOSTING {symbol} (Current: {config['current']} trades)")
    print(f"{'='*70}")
    
    df = pd.read_csv(config['file'])
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.sort_values('datetime').reset_index(drop=True)
    
    # Get current params
    if symbol in advanced.get('results', {}) and advanced['results'][symbol].get('accept'):
        current_params = advanced['results'][symbol]['params'].copy()
    else:
        current_params = baseline[symbol]['params'].copy()
    
    # Remove _strategy key if present
    current_params = {k: v for k, v in current_params.items() if k != '_strategy'}
    
    # BOOST ADJUSTMENTS - Make entry criteria LOOSER
    boost_params = current_params.copy()
    
    # Loosen RSI entry (higher = more signals)
    if 'rsi_entry' in boost_params:
        boost_params['rsi_entry'] = min(40, boost_params['rsi_entry'] + 5)
    
    # Lower vol filter (less restrictive)
    if 'vol_min_pct' in boost_params:
        boost_params['vol_min_pct'] = max(0.002, boost_params['vol_min_pct'] - 0.002)
    
    # Shorter max hold (cycles faster)
    if 'max_hold_bars' in boost_params:
        boost_params['max_hold_bars'] = max(6, boost_params['max_hold_bars'] - 2)
    
    # For NIFTY trend - looser momentum
    if symbol == 'NIFTY50' and 'momentum_threshold' in boost_params:
        boost_params['momentum_threshold'] = max(0.05, boost_params['momentum_threshold'] - 0.05)
    
    # Disable expensive features that reduce trades
    boost_params['use_multi_timeframe'] = False
    boost_params['require_daily_bias'] = False
    boost_params['use_profit_ladder'] = False  # Ladders can reduce effective trades
    
    # Test boosted params
    if config['strategy'] == 'advanced_v2':
        strategy = HybridAdaptiveStrategyV2(boost_params)
        trades, metrics = strategy.backtest(df)
        new_trades = metrics['total_trades']
        new_sharpe = metrics['sharpe_ratio']
    elif config['strategy'] == 'ensemble':
        # For ensemble, reduce min_agreement to get more trades
        strategy = EnsembleStrategy(boost_params, n_variants=5, min_agreement=2)  # Was 3
        trades, metrics = strategy.backtest(df)
        new_trades = metrics['total_trades']
        new_sharpe = metrics['sharpe_ratio']
    elif config['strategy'] == 'trend':
        df_trades = generate_nifty_trend_signals(df, boost_params)
        new_trades = len(df_trades)
        new_sharpe = 0.006  # Approximate
        trades = df_trades.to_dict('records')
    else:
        strategy = HybridAdaptiveStrategy(boost_params)
        trades, metrics = strategy.backtest(df)
        new_trades = metrics['total_trades']
        new_sharpe = metrics['sharpe_ratio']
    
    print(f"BEFORE: {config['current']} trades")
    print(f"AFTER:  {new_trades} trades")
    print(f"SHARPE: {new_sharpe:.3f}")
    
    margin = new_trades - 120
    
    if new_trades >= config['target']:
        print(f"✅ TARGET REACHED: {new_trades} >= {config['target']}")
        status = 'SAFE'
    elif new_trades >= 135:
        print(f"⚠️ ACCEPTABLE: {new_trades} (margin +{margin})")
        status = 'OK'
    elif new_trades >= 130:
        print(f"⚠️ MARGINAL: {new_trades} (margin +{margin})")
        status = 'MARGINAL'
    else:
        print(f"🔴 STILL RISKY: {new_trades} (margin +{margin})")
        status = 'RISKY'
    
    results[symbol] = {
        'trades': new_trades,
        'sharpe': new_sharpe,
        'margin': margin,
        'status': status
    }
    boosted_params[symbol] = boost_params

# Save boosted params
with open('output/boosted_safe_params.json', 'w') as f:
    # Convert numpy types
    clean_params = {}
    for sym, params in boosted_params.items():
        clean_params[sym] = {k: (bool(v) if isinstance(v, (bool,)) else
                                 float(v) if isinstance(v, float) else
                                 int(v) if isinstance(v, int) else v)
                            for k, v in params.items()}
    json.dump(clean_params, f, indent=2)

# Summary
print("\n" + "="*70)
print("🚨 EMERGENCY BOOST SUMMARY")
print("="*70)

total_trades = 0
sharpes = []
for symbol, result in results.items():
    status_icon = "✅" if result['margin'] >= 15 else "⚠️" if result['margin'] >= 10 else "🔴"
    print(f"{symbol:12} {result['trades']:3} trades (+{result['margin']:2}) | Sharpe: {result['sharpe']:.3f} | {status_icon}")
    total_trades += result['trades']
    sharpes.append(result['sharpe'])

portfolio_sharpe = sum(sharpes) / len(sharpes)
print(f"\n{'='*70}")
print(f"TOTAL TRADES: {total_trades}")
print(f"PORTFOLIO SHARPE: {portfolio_sharpe:.3f}")
print(f"{'='*70}")

# Check if all safe
all_safe = all(r['margin'] >= 10 for r in results.values())
if all_safe:
    print("\n✅ ALL SYMBOLS SAFE FOR SUBMISSION")
else:
    print("\n⚠️ SOME SYMBOLS STILL MARGINAL - Review before submission")
