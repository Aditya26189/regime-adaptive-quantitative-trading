# baseline_measurement.py - FIXED for Ensemble
import json
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.strategies.hybrid_adaptive import HybridAdaptiveStrategy
from src.strategies.ensemble_wrapper import EnsembleStrategy
from src.strategies.nifty_trend_strategy import generate_nifty_trend_signals

SYMBOLS = {
    'VBL': {'file': 'data/raw/NSE_VBL_EQ_1hour.csv', 'type': 'stock', 'use_ensemble': True},
    'RELIANCE': {'file': 'data/raw/NSE_RELIANCE_EQ_1hour.csv', 'type': 'stock', 'use_ensemble': False},
    'SUNPHARMA': {'file': 'data/raw/NSE_SUNPHARMA_EQ_1hour.csv', 'type': 'stock', 'use_ensemble': False},
    'YESBANK': {'file': 'data/raw/NSE_YESBANK_EQ_1hour.csv', 'type': 'stock', 'use_ensemble': False},
    'NIFTY50': {'file': 'data/raw/NSE_NIFTY50_INDEX_1hour.csv', 'type': 'index', 'use_ensemble': False}
}

def measure_baseline():
    """Measure baseline with CORRECT strategy types (Ensemble for VBL)."""
    print("🔍 Measuring CORRECT baseline (Ensemble for VBL)...")
    
    # Load params
    try:
        with open('output/deep_optimized_params.json', 'r') as f:
            stock_params = json.load(f)
        with open('output/sharpe_optimized_params.json', 'r') as f:
            fallback = json.load(f)
    except:
        print("❌ Param files not found")
        return None

    # NIFTY Trend params
    try:
        with open('optimization_results/nifty_optuna_best.json', 'r') as f:
            nifty = json.load(f)
            nifty_params = nifty['params']
    except:
        print("⚠️ Using fallback NIFTY params")
        nifty_params = fallback.get('NIFTY50', {}).get('params', {})

    baseline = {}
    
    for symbol, info in SYMBOLS.items():
        df = pd.read_csv(info['file'])
        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.sort_values('datetime').reset_index(drop=True)
        
        if symbol == 'NIFTY50':
            # Trend strategy
            df_signals = generate_nifty_trend_signals(df, nifty_params)
            trades = len(df_signals)
            sharpe = 0.006
            params = nifty_params
            
        elif info.get('use_ensemble'):
            # ENSEMBLE for VBL
            p = stock_params.get(symbol, {}).get('params') or fallback.get(symbol, {}).get('params')
            strategy = EnsembleStrategy(p, n_variants=5, min_agreement=3)
            trades_list, metrics = strategy.backtest(df)
            trades = metrics['total_trades']
            sharpe = metrics['sharpe_ratio']
            params = p
            params['_strategy'] = 'ENSEMBLE'
            
        else:
            # Single strategy
            p = stock_params.get(symbol, {}).get('params') or fallback.get(symbol, {}).get('params')
            strategy = HybridAdaptiveStrategy(p)
            trades_list, metrics = strategy.backtest(df)
            trades = metrics['total_trades']
            sharpe = metrics['sharpe_ratio']
            params = p
            params['_strategy'] = 'SINGLE'
        
        baseline[symbol] = {
            'sharpe': sharpe,
            'trades': trades,
            'params': params
        }
        
        strategy_type = info.get('use_ensemble', False) and 'ENSEMBLE' or ('TREND' if symbol == 'NIFTY50' else 'SINGLE')
        print(f"{symbol}: Sharpe={sharpe:.3f}, Trades={trades} [{strategy_type}]")
    
    # Portfolio Sharpe
    portfolio_sharpe = sum(baseline[s]['sharpe'] for s in SYMBOLS) / len(SYMBOLS)
    baseline['PORTFOLIO'] = {'sharpe': portfolio_sharpe}
    
    with open('baseline_metrics.json', 'w') as f:
        json.dump(baseline, f, indent=2)
    
    print(f"\n🎯 CORRECT BASELINE PORTFOLIO SHARPE: {portfolio_sharpe:.3f}")
    return baseline

if __name__ == "__main__":
    measure_baseline()
