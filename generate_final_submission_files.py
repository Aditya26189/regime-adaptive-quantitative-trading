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
from src.strategies.regime_switching_strategy import RegimeSwitchingStrategy

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
        'strategy': 'regime_switching',
        'params': {
            'rsi_period': 2,
            'allowed_hours': [10, 11, 12, 13, 14, 15]
        }
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
# Capital per symbol (from Phase 3 Optimization 2.559 Sharpe)
CAPITAL_PER_SYMBOL = 2000000

# ==============================================================================
# 2. RUN BACKTESTS
# ==============================================================================

print("\n" + "="*70)
print("GENERATING FINAL SUBMISSION FILES")
print("="*70)

final_rows = []
total_trades = 0
results = {}

for symbol, config in SYMBOLS.items():
    print(f"\n[{symbol}]")
    
    # Load data
    if not os.path.exists(config['file']):
        # Try local path
        config['file'] = config['file'].replace('data/raw/', 'data/')
        
    df = pd.read_csv(config['file'])
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.sort_values('datetime').reset_index(drop=True)
    
    # Get params and run strategy
    if config['strategy'] == 'regime_switching':
        # VBL: Switched to Hybrid Baseline for Safety
        # Final Push for 120 trades: Fast Scalping
        params = {
            "ker_period": 14,
            "rsi_period": 14,
            "rsi_entry": 45, # Maximum Aggression
            "rsi_exit": 55,  # Maximum Turnover
            "vol_min_pct": 0.0, # NO Filter
            "max_hold_bars": 3, # Hyper Scalping
            "allowed_hours": [9, 10, 11, 12, 13, 14, 15],
            "max_return_cap": 5.0,
            "ker_threshold_meanrev": 0.3,
            "ker_threshold_trend": 0.5,
            "ema_fast": 9,
            "ema_slow": 21,
            "trend_pulse_mult": 0.4
        }
        strategy = HybridAdaptiveStrategy(params)
        trades, metrics = strategy.backtest(df, initial_capital=CAPITAL_PER_SYMBOL)

    elif config['strategy'] == 'ensemble':
        params = {k: v for k, v in config['params'].items() if k != '_strategy'}
        strategy = EnsembleStrategy(params, n_variants=5, min_agreement=3)
        trades, metrics = strategy.backtest(df, initial_capital=CAPITAL_PER_SYMBOL)
        
    elif config['strategy'] == 'advanced_v2':
        # RELIANCE V2 (Phase 3)
        params = {
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
        strategy = HybridAdaptiveStrategyV2(params)
        trades, metrics = strategy.backtest(df, initial_capital=CAPITAL_PER_SYMBOL)
        
    elif config['strategy'] == 'advanced_v2_boosted':
        # SUNPHARMA V2 Boosted (Phase 3)
        params = {
            "ker_period": 15,
            "rsi_period": 4,
            "vol_lookback": 14,
            "max_return_cap": 5.0,
            "ker_threshold_meanrev": 0.38224215306531234,
            "ker_threshold_trend": 0.6094140658792518,
            "rsi_entry": 41,  # Boosted 38+3
            "rsi_exit": 52,
            "vol_min_pct": 0.004,  # Boosted 0.005-0.001
            "ema_fast": 8,
            "ema_slow": 21,
            "trend_pulse_mult": 0.45596263377414287,
            "allowed_hours": [9, 10, 11],
            "max_hold_bars": 6,
            "use_dynamic_sizing": False,
            "use_multi_timeframe": False,
            "use_profit_ladder": True,
            "ladder_rsi_1": 65,
            "ladder_rsi_2": 73,
            "ladder_frac_1": 0.35,
            "use_adaptive_hold": True,
            "use_dynamic_rsi": False
        }
        strategy = HybridAdaptiveStrategyV2(params)
        trades, metrics = strategy.backtest(df, initial_capital=CAPITAL_PER_SYMBOL)
        
    elif config['strategy'] == 'baseline_boosted':
        # YESBANK Optimized (Rescue Tuned 3)
        # Final Push for 120 trades
        params = {
            "ker_period": 10,
            "rsi_period": 4,
            "rsi_entry": 40, # High Entry
            "rsi_exit": 60, # Tighter Exit
            "vol_min_pct": 0.001, # Almost no filter
            "max_hold_bars": 4, # Very fast turnover
            "ker_threshold_meanrev": 0.21,
            "ker_threshold_trend": 0.57,
            "ema_fast": 8,
            "ema_slow": 21,
            "trend_pulse_mult": 0.4,
            "allowed_hours": [9, 10, 11, 12, 13, 14, 15],
            "max_return_cap": 5.0
        }
        strategy = HybridAdaptiveStrategy(params)
        trades, metrics = strategy.backtest(df, initial_capital=CAPITAL_PER_SYMBOL)
        
    elif config['strategy'] == 'nifty_trend_ladder':
        # Relaxed Nifty Params for Trade Count
        p = config['params'].copy()
        p['momentum_threshold'] = 0.0015 # Lowered from 0.002
        p['vol_min_pct'] = 0.0025 # Lowered from 0.003
        strategy = NIFTYTrendLadderStrategy(p)
        trades, metrics = strategy.backtest_with_ladder_exits(df, initial_capital=CAPITAL_PER_SYMBOL)
    
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

# Global accumulator (for rough check, but files will be independent)
capital_global = 2000000.0 * 5 # Portfolio total
final_rows = []

for t in sorted(all_trades, key=lambda x: (x['symbol'], str(x['entry_time']))):
    pnl = (t['exit_price'] - t['entry_price']) * t['qty'] - 48
    capital_global += pnl
    
    final_rows.append({
        'student_roll_number': ROLL_NUMBER,
        'strategy_submission_number': 5, # Submission 5
        'symbol': t['symbol'],
        'timeframe': '60',
        'entry_trade_time': t['entry_time'],
        'exit_trade_time': t['exit_time'],
        'entry_trade_price': t['entry_price'],
        'exit_trade_price': t['exit_price'],
        'qty': t['qty'],
        'fees': 48,
        'cumulative_capital_after_trade': 0.0 # Will calculate per symbol
    })

# Save combined result (Portfolio View)
submission_df = pd.DataFrame(final_rows)
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
combined_file = f"submission_5/FINAL_PORTFOLIO_TRACKER_{timestamp}.csv"
submission_df.to_csv(combined_file, index=False)

print(f"\n✅ Combined: {combined_file}")

# Split by symbol and Calculate Independent Capital
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
    
    # Calculate independent capital path
    current_cap = CAPITAL_PER_SYMBOL
    cap_series = []
    
    for idx, row in symbol_df.iterrows():
        pnl = (row['exit_trade_price'] - row['entry_trade_price']) * row['qty'] - row['fees']
        current_cap += pnl
        cap_series.append(round(current_cap, 2))
        
    symbol_df['cumulative_capital_after_trade'] = cap_series
    
    filename = f"submission_5/STRATEGY5_{symbol_code.replace(':', '_')}_trades.csv"
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
print(f"FINAL CAPITAL: ₹{capital_global:,.2f}")
print("="*70)
