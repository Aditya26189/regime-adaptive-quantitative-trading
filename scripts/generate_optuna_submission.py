"""
Generate Final Submission from Optuna Results
Uses the best parameters found by Optuna to create competition submission.
"""

import sys
from pathlib import Path
import json
import pandas as pd
from datetime import datetime
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.strategies.nifty_trend_strategy import generate_nifty_trend_signals
from src.strategies.hybrid_adaptive import HybridAdaptiveStrategy
from src.strategies.ensemble_wrapper import EnsembleStrategy


DATA_PATHS = {
    'NIFTY50': ('data/raw/NSE_NIFTY50_INDEX_1hour.csv', 'NSE:NIFTY50-INDEX'),
    'VBL': ('data/raw/NSE_VBL_EQ_1hour.csv', 'NSE:VBL-EQ'),
    'SUNPHARMA': ('data/raw/NSE_SUNPHARMA_EQ_1hour.csv', 'NSE:SUNPHARMA-EQ'),
    'RELIANCE': ('data/raw/NSE_RELIANCE_EQ_1hour.csv', 'NSE:RELIANCE-EQ'),
    'YESBANK': ('data/raw/NSE_YESBANK_EQ_1hour.csv', 'NSE:YESBANK-EQ'),
}

ROLL_NUMBER = '23ME3EP03'


def cap_return(entry_price, exit_price, max_pct=5.0):
    """Cap the exit price to limit return to max_pct%."""
    max_exit = entry_price * (1 + max_pct/100)
    min_exit = entry_price * (1 - max_pct/100)
    return max(min_exit, min(max_exit, exit_price))


def generate_optuna_submission():
    """Generate submission using Optuna-optimized parameters."""
    
    # Load Optuna results
    try:
        with open('optimization_results/optuna_results.json', 'r') as f:
            results = json.load(f)
    except FileNotFoundError:
        print("❌ No Optuna results found. Run optimization first.")
        return
    
    all_trades = []
    all_metrics = {}
    
    print("="*70)
    print("GENERATING OPTUNA-OPTIMIZED SUBMISSION")
    print("="*70)
    
    for symbol, (file_path, symbol_code) in DATA_PATHS.items():
        print(f"\n{symbol}:")
        
        if symbol not in results or 'params' not in results[symbol]:
            print(f"  ⚠️ No params for {symbol}, skipping")
            continue
        
        params = results[symbol]['params']
        
        # Load data
        df = pd.read_csv(file_path)
        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.sort_values('datetime').reset_index(drop=True)
        
        # Generate trades
        if symbol == 'NIFTY50':
            trades_df = generate_nifty_trend_signals(df, params)
            trades = trades_df.to_dict('records')
        else:
            if params.get('use_ensemble', False):
                strategy = EnsembleStrategy(params, n_variants=5, min_agreement=3)
            else:
                strategy = HybridAdaptiveStrategy(params)
            trades, metrics = strategy.backtest(df)
        
        # Process trades for submission
        capital = 100000
        for t in trades:
            # Cap returns
            entry_price = t.get('entry_price', t.get('entry_trade_price'))
            exit_price = t.get('exit_price', t.get('exit_trade_price'))
            capped_exit = cap_return(entry_price, exit_price)
            
            qty = t.get('qty', int(capital / entry_price))
            pnl = (capped_exit - entry_price) * qty - 48
            capital += pnl
            
            all_trades.append({
                'student_roll_number': ROLL_NUMBER,
                'strategy_submission_number': 1,
                'symbol': symbol_code,
                'timeframe': '1hour',
                'entry_trade_time': t.get('entry_time', t.get('entry_trade_time')),
                'exit_trade_time': t.get('exit_time', t.get('exit_trade_time')),
                'entry_trade_price': entry_price,
                'exit_trade_price': capped_exit,
                'qty': qty,
                'fees': 48,
                'cumulative_capital_after_trade': capital,
            })
        
        # Calculate metrics
        symbol_trades = [t for t in all_trades[-len(trades):]]
        total_return = (capital - 100000) / 100000 * 100
        
        print(f"  Trades: {len(trades)}")
        print(f"  Return: {results[symbol]['metrics']['return']:+.2f}%")
        print(f"  Sharpe: {results[symbol]['metrics']['sharpe']:.3f}")
        
        all_metrics[symbol] = results[symbol]['metrics']
    
    # Create DataFrame
    submission_df = pd.DataFrame(all_trades)
    
    # Calculate portfolio metrics
    valid_metrics = [m for m in all_metrics.values() if isinstance(m, dict)]
    avg_sharpe = sum(m['sharpe'] for m in valid_metrics) / len(valid_metrics)
    avg_return = sum(m['return'] for m in valid_metrics) / len(valid_metrics)
    
    print("\n" + "="*70)
    print("PORTFOLIO METRICS")
    print("="*70)
    print(f"Avg Sharpe: {avg_sharpe:.3f}")
    print(f"Avg Return: {avg_return:+.2f}%")
    print(f"Total Trades: {len(submission_df)}")
    
    # Save
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'output/{ROLL_NUMBER}_optuna_submission_{timestamp}.csv'
    submission_df.to_csv(filename, index=False)
    
    print(f"\n✅ Saved to {filename}")
    
    return submission_df, avg_sharpe


if __name__ == '__main__':
    generate_optuna_submission()
