# generate_final_submission_files.py
"""
Generate final submission files in the required output format
"""
import pandas as pd
import json
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.strategies.hybrid_adaptive_v2 import HybridAdaptiveStrategyV2
from src.strategies.hybrid_adaptive import HybridAdaptiveStrategy
from src.strategies.ensemble_wrapper import EnsembleStrategy
from src.strategies.nifty_trend_ladder import NIFTYTrendLadderStrategy

ROLL_NUMBER = '23ME3EP03'

print("="*70)
print("GENERATING FINAL SUBMISSION FILES")
print("="*70)

# Load params
baseline = json.load(open('baseline_metrics.json', 'r'))
advanced = json.load(open('advanced_optimization_results.json', 'r'))
nifty_data = json.load(open('optimization_results/nifty_optuna_best.json', 'r'))

# Symbol configurations
SYMBOLS = {
    'VBL': {
        'file': 'data/raw/NSE_VBL_EQ_1hour.csv',
        'code': 'NSE:VBL-EQ',
        'strategy': 'ensemble',
        'params': baseline['VBL']['params']
    },
    'RELIANCE': {
        'file': 'data/raw/NSE_RELIANCE_EQ_1hour.csv',
        'code': 'NSE:RELIANCE-EQ',
        'strategy': 'advanced_v2',
        'params': advanced['results']['RELIANCE']['params']
    },
    'SUNPHARMA': {
        'file': 'data/raw/NSE_SUNPHARMA_EQ_1hour.csv',
        'code': 'NSE:SUNPHARMA-EQ',
        'strategy': 'advanced_v2_boosted',
        'params': None  # Will be set with boost
    },
    'YESBANK': {
        'file': 'data/raw/NSE_YESBANK_EQ_1hour.csv',
        'code': 'NSE:YESBANK-EQ',
        'strategy': 'baseline_boosted',
        'params': None  # Will be set with boost
    },
    'NIFTY50': {
        'file': 'data/raw/NSE_NIFTY50_INDEX_1hour.csv',
        'code': 'NSE:NIFTY50-INDEX',
        'strategy': 'nifty_trend_ladder',
        'params': {
            'ema_fast': 8, 'ema_slow': 21, 'momentum_threshold': 0.002,
            'vol_min_pct': 0.003, 'max_hold_bars': 6, 'stop_loss_pct': 2.0,
            'allowed_hours': [10, 11, 12, 13, 14, 15]
        }
    }
}

all_trades = []
results = {}

for symbol, config in SYMBOLS.items():
    print(f"\n[{symbol}]")
    
    df = pd.read_csv(config['file'])
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.sort_values('datetime').reset_index(drop=True)
    
    # Get params and run strategy
    if config['strategy'] == 'ensemble':
        params = {k: v for k, v in config['params'].items() if k != '_strategy'}
        strategy = EnsembleStrategy(params, n_variants=5, min_agreement=3)
        trades, metrics = strategy.backtest(df)
        
    elif config['strategy'] == 'advanced_v2':
        strategy = HybridAdaptiveStrategyV2(config['params'])
        trades, metrics = strategy.backtest(df)
        
    elif config['strategy'] == 'advanced_v2_boosted':
        params = advanced['results']['SUNPHARMA']['params'].copy()
        params['rsi_entry'] = params.get('rsi_entry', 30) + 3
        params['vol_min_pct'] = max(0.003, params.get('vol_min_pct', 0.005) - 0.001)
        strategy = HybridAdaptiveStrategyV2(params)
        trades, metrics = strategy.backtest(df)
        
    elif config['strategy'] == 'baseline_boosted':
        params = {k: v for k, v in baseline['YESBANK']['params'].items() if k != '_strategy'}
        params['rsi_entry'] = params.get('rsi_entry', 30) + 4
        params['vol_min_pct'] = max(0.003, params.get('vol_min_pct', 0.005) - 0.001)
        strategy = HybridAdaptiveStrategy(params)
        trades, metrics = strategy.backtest(df)
        
    elif config['strategy'] == 'nifty_trend_ladder':
        strategy = NIFTYTrendLadderStrategy(config['params'])
        trades, metrics = strategy.backtest_with_ladder_exits(df)
    
    # Store results
    trade_count = metrics.get('total_trades', len(trades))
    sharpe = metrics.get('sharpe_ratio', 0)
    
    print(f"  Trades: {trade_count}, Sharpe: {sharpe:.3f}")
    results[symbol] = {'trades': trade_count, 'sharpe': sharpe}
    
    # Format trades
    for t in trades:
        if config['strategy'] == 'nifty_trend_ladder':
            entry = t['entry_price']
            exit_raw = t['exit_price']
        else:
            entry = t['entry_price']
            exit_raw = t['exit_price']
        
        # Apply 5% cap
        raw_ret = ((exit_raw - entry) / entry) * 100
        exit_price = entry * min(1.05, max(0.95, 1 + raw_ret/100))
        
        all_trades.append({
            'symbol': config['code'],
            'entry_time': t.get('entry_time', t.get('entry_trade_time')),
            'exit_time': t.get('exit_time', t.get('exit_trade_time')),
            'entry_price': round(entry, 2),
            'exit_price': round(exit_price, 2),
            'qty': t['qty']
        })

# Build final CSV
print("\n" + "="*70)
print("BUILDING CSV FILES")
print("="*70)

capital = 100000.0
final_rows = []

for t in sorted(all_trades, key=lambda x: (x['symbol'], str(x['entry_time']))):
    pnl = (t['exit_price'] - t['entry_price']) * t['qty'] - 48
    capital += pnl
    
    final_rows.append({
        'student_roll_number': ROLL_NUMBER,
        'strategy_submission_number': 1,
        'symbol': t['symbol'],
        'timeframe': '60',
        'entry_trade_time': t['entry_time'],
        'exit_trade_time': t['exit_time'],
        'entry_trade_price': t['entry_price'],
        'exit_trade_price': t['exit_price'],
        'qty': t['qty'],
        'fees': 48,
        'cumulative_capital_after_trade': round(capital, 2)
    })

# Save combined file
submission_df = pd.DataFrame(final_rows)
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
combined_file = f"output/{ROLL_NUMBER}_FINAL_submission_{timestamp}.csv"
submission_df.to_csv(combined_file, index=False)

print(f"\n✅ Combined: {combined_file}")

# Split by symbol
symbols_map = {
    'NSE:NIFTY50-INDEX': 'NIFTY50',
    'NSE:VBL-EQ': 'VBL',
    'NSE:RELIANCE-EQ': 'RELIANCE',
    'NSE:SUNPHARMA-EQ': 'SUNPHARMA',
    'NSE:YESBANK-EQ': 'YESBANK'
}

for symbol_code, symbol_name in symbols_map.items():
    symbol_df = submission_df[submission_df['symbol'] == symbol_code].copy()
    symbol_df = symbol_df.sort_values('entry_trade_time').reset_index(drop=True)
    
    filename = f"output/{ROLL_NUMBER}_{symbol_code.replace(':', '_')}_trades.csv"
    symbol_df.to_csv(filename, index=False)
    print(f"✅ {symbol_name:12} {len(symbol_df):3} trades → {filename}")

# Summary
print("\n" + "="*70)
print("FINAL SUMMARY")
print("="*70)

for symbol in ['VBL', 'RELIANCE', 'SUNPHARMA', 'YESBANK', 'NIFTY50']:
    r = results[symbol]
    margin = r['trades'] - 120
    icon = "✅" if margin >= 10 else "⚠️" if margin >= 5 else "🔴"
    print(f"{symbol:12} {r['trades']:3} trades (+{margin:2}) | Sharpe: {r['sharpe']:.3f} | {icon}")

portfolio_sharpe = sum(r['sharpe'] for r in results.values()) / 5
total_trades = sum(r['trades'] for r in results.values())

print(f"\nPORTFOLIO SHARPE: {portfolio_sharpe:.3f}")
print(f"TOTAL TRADES: {total_trades}")
print(f"FINAL CAPITAL: ₹{capital:,.2f}")
print("="*70)
