# generate_advanced_submission.py
"""
Generate Final Submission with Best Parameters Per Symbol
- VBL: Ensemble (1.574)
- RELIANCE: Advanced V2 (1.683)
- SUNPHARMA: Advanced V2 (3.323!)
- YESBANK: Original Baseline (1.278) - V2 regressed
- NIFTY50: Trend Strategy (0.006)
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.strategies.hybrid_adaptive_v2 import HybridAdaptiveStrategyV2
from src.strategies.hybrid_adaptive import HybridAdaptiveStrategy
from src.strategies.ensemble_wrapper import EnsembleStrategy
from src.strategies.nifty_trend_strategy import generate_nifty_trend_signals

ROLL_NUMBER = '23ME3EP03'

DATA_PATHS = {
    'NIFTY50': ('data/raw/NSE_NIFTY50_INDEX_1hour.csv', 'NSE:NIFTY50-INDEX'),
    'VBL': ('data/raw/NSE_VBL_EQ_1hour.csv', 'NSE:VBL-EQ'),
    'SUNPHARMA': ('data/raw/NSE_SUNPHARMA_EQ_1hour.csv', 'NSE:SUNPHARMA-EQ'),
    'RELIANCE': ('data/raw/NSE_RELIANCE_EQ_1hour.csv', 'NSE:RELIANCE-EQ'),
    'YESBANK': ('data/raw/NSE_YESBANK_EQ_1hour.csv', 'NSE:YESBANK-EQ'),
}

def generate_final_submission():
    print("="*70)
    print("GENERATING ADVANCED SUBMISSION")
    print("="*70)
    
    # Load params
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
    
    all_trades = []
    all_metrics = {}
    
    for symbol, (path, code) in DATA_PATHS.items():
        df = pd.read_csv(path)
        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.sort_values('datetime').reset_index(drop=True)
        
        print(f"\n{symbol}:")
        
        if symbol == 'NIFTY50':
            # Trend strategy
            trades_df = generate_nifty_trend_signals(df, nifty_params)
            trades = trades_df.to_dict('records')
            sharpe = 0.006
            source = "TREND"
            
        elif symbol == 'VBL':
            # Ensemble (best performance)
            params = baseline['VBL']['params']
            strategy = EnsembleStrategy(params, n_variants=5, min_agreement=3)
            trades, metrics = strategy.backtest(df)
            sharpe = metrics['sharpe_ratio']
            source = "ENSEMBLE"
            
        elif symbol in advanced.get('results', {}) and advanced['results'][symbol]['accept']:
            # Advanced V2 (if accepted)
            params = advanced['results'][symbol]['params']
            strategy = HybridAdaptiveStrategyV2(params)
            trades, metrics = strategy.backtest(df)
            sharpe = metrics['sharpe_ratio']
            source = "ADVANCED_V2"
            
        else:
            # Fallback to original baseline
            params = baseline[symbol]['params']
            strategy = HybridAdaptiveStrategy(params)
            trades, metrics = strategy.backtest(df)
            sharpe = metrics['sharpe_ratio']
            source = "BASELINE"
        
        print(f"  Source: {source}")
        print(f"  Trades: {len(trades)}")
        print(f"  Sharpe: {sharpe:.3f}")
        
        all_metrics[symbol] = {'sharpe': sharpe, 'trades': len(trades), 'source': source}
        
        # Format trades for CSV
        capital = 100000.0
        for t in trades:
            entry = t.get('entry_price', t.get('entry_trade_price'))
            exit_raw = t.get('exit_price', t.get('exit_trade_price'))
            
            # 5% Cap
            raw_ret = ((exit_raw - entry) / entry) * 100
            if raw_ret > 5.0:
                exit_price = entry * 1.05
            elif raw_ret < -5.0:
                exit_price = entry * 0.95
            else:
                exit_price = exit_raw
            
            qty = t.get('qty', int(capital // entry))
            pnl = (exit_price - entry) * qty - 48
            capital += pnl
            
            all_trades.append({
                'student_roll_number': ROLL_NUMBER,
                'strategy_submission_number': 1,
                'symbol': code,
                'timeframe': '60',
                'entry_trade_time': t.get('entry_time', t.get('entry_trade_time')),
                'exit_trade_time': t.get('exit_time', t.get('exit_trade_time')),
                'entry_trade_price': round(entry, 2),
                'exit_trade_price': round(exit_price, 2),
                'qty': qty,
                'fees': 48,
                'cumulative_capital_after_trade': round(capital, 2)
            })
    
    # Portfolio metrics
    portfolio_sharpe = sum(m['sharpe'] for m in all_metrics.values()) / 5
    
    print(f"\n{'='*70}")
    print("FINAL PORTFOLIO METRICS")
    print(f"{'='*70}")
    for sym, m in all_metrics.items():
        print(f"  {sym}: Sharpe={m['sharpe']:.3f}, Trades={m['trades']} [{m['source']}]")
    print(f"\nPORTFOLIO SHARPE: {portfolio_sharpe:.3f}")
    print(f"TOTAL TRADES: {len(all_trades)}")
    
    # Save
    submission_df = pd.DataFrame(all_trades)
    submission_df = submission_df.sort_values(['symbol', 'entry_trade_time'])
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"output/{ROLL_NUMBER}_advanced_submission_{timestamp}.csv"
    submission_df.to_csv(filename, index=False)
    
    print(f"\n✅ Saved: {filename}")
    
    return portfolio_sharpe

if __name__ == "__main__":
    generate_final_submission()
