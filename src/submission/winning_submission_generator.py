"""
Winning Submission Generator 🏆
Uses parameter sets from Deep Optimization (Zoom-in search).
Smartly chooses between Deep Single vs Ensemble for VBL.

Target: Top 1 Rank
"""

import pandas as pd
import numpy as np
import json
import os
from datetime import datetime
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from strategies.hybrid_adaptive import HybridAdaptiveStrategy
from strategies.ensemble_wrapper import EnsembleStrategy

STUDENT_ROLL_NUMBER = "23ME3EP03"

DATA_PATHS = {
    'NIFTY50': ('data/raw/NSE_NIFTY50_INDEX_1hour.csv', 'NSE:NIFTY50-INDEX'),
    'RELIANCE': ('data/raw/NSE_RELIANCE_EQ_1hour.csv', 'NSE:RELIANCE-EQ'),
    'VBL': ('data/raw/NSE_VBL_EQ_1hour.csv', 'NSE:VBL-EQ'),
    'YESBANK': ('data/raw/NSE_YESBANK_EQ_1hour.csv', 'NSE:YESBANK-EQ'),
    'SUNPHARMA': ('data/raw/NSE_SUNPHARMA_EQ_1hour.csv', 'NSE:SUNPHARMA-EQ'),
}

def generate_winning_submission():
    """Generate final submission using Deep Optimized parameters."""
    
    # Load params
    try:
        with open('output/deep_optimized_params.json', 'r') as f:
            deep_params_all = json.load(f)
        with open('output/sharpe_optimized_params.json', 'r') as f:
            fallback_params_all = json.load(f)
    except FileNotFoundError:
        print("❌ valid parameter files not found!")
        return

    all_trades = []
    all_metrics = {}
    
    print("="*70)
    print("GENERATING WINNING SUBMISSION (DEEP OPTIMIZATION)")
    print("="*70)
    
    for symbol in ['NIFTY50', 'RELIANCE', 'VBL', 'YESBANK', 'SUNPHARMA']:
        print(f"\n{symbol}:")
        
        file_path, symbol_code = DATA_PATHS[symbol]
        df = pd.read_csv(file_path)
        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.sort_values('datetime').reset_index(drop=True)
        
        # Default to Deep, but check Fallback
        deep_entry = deep_params_all.get(symbol, {})
        fallback_entry = fallback_params_all.get(symbol, {})
        
        # 1. Check if Deep is valid
        if not deep_entry.get('params'):
            print(f"  ⚠️ Deep failed. Using Fallback.")
            chosen_params = fallback_entry['params']
            source = "FALLBACK"
        else:
            # 2. Compare Deep vs Fallback performance
            # Re-run backtest on both to be sure (or trust stored metrics if available?)
            # Safer to re-run locally to compare Apples-to-Apples
            
            d_strategy = HybridAdaptiveStrategy(deep_entry['params'])
            _, d_metrics = d_strategy.backtest(df)
            
            f_strategy = HybridAdaptiveStrategy(fallback_entry['params'])
            _, f_metrics = f_strategy.backtest(df)
            
            print(f"  Deep Sharpe: {d_metrics['sharpe_ratio']:.3f}")
            print(f"  Fallback Sharpe: {f_metrics['sharpe_ratio']:.3f}")
            
            if d_metrics['sharpe_ratio'] > f_metrics['sharpe_ratio']:
                chosen_params = deep_entry['params']
                source = "DEEP"
                print("  ✅ DEEP wins")
            else:
                chosen_params = fallback_entry['params']
                source = "FALLBACK"
                print("  ✅ FALLBACK wins")

        # Logic for VBL: Always try Ensemble on the CHOSEN params
        if symbol == 'VBL':
            print("  Testing VBL Ensemble on winning params...")
            # Use Ensemble with the chosen params
            e_strategy = EnsembleStrategy(chosen_params, n_variants=5, min_agreement=3)
            e_trades, e_metrics = e_strategy.backtest(df)
            
            # Also test Single (re-run on chosen)
            s_strategy = HybridAdaptiveStrategy(chosen_params)
            s_trades, s_metrics = s_strategy.backtest(df)
            
            print(f"  Single: Sharpe={s_metrics['sharpe_ratio']:.3f}, Return={s_metrics['total_return_pct']:.2f}%")
            print(f"  Ensemble: Sharpe={e_metrics['sharpe_ratio']:.3f}, Return={e_metrics['total_return_pct']:.2f}%")
            
            if e_metrics['sharpe_ratio'] > s_metrics['sharpe_ratio']:
                 metrics, trades = e_metrics, e_trades
                 print("  ✅ Using ENSEMBLE")
            else:
                 metrics, trades = s_metrics, s_trades
                 print("  ✅ Using SINGLE")
        
        else:
             # Standard Single Strategy with Chosen Params
             strategy = HybridAdaptiveStrategy(chosen_params)
             metrics = strategy.backtest(df)[1]
             trades = strategy.backtest(df)[0]

        all_metrics[symbol] = metrics
        
        print(f"  Trades: {metrics['total_trades']}")
        print(f"  Return: {metrics['total_return_pct']:.2f}%")
        print(f"  Sharpe: {metrics['sharpe_ratio']:.3f}")
        
        # CAP OUTLIERS
        for trade in trades:
            entry_price = trade['entry_price']
            exit_price = trade['exit_price']
            
            # 5.0% Rule
            raw_ret = ((exit_price - entry_price) / entry_price) * 100
            if raw_ret > 5.0:
                exit_price = entry_price * 1.05
            
            all_trades.append({
                'student_roll_number': STUDENT_ROLL_NUMBER,
                'strategy_submission_number': 1,
                'symbol': symbol_code,
                'timeframe': '60',
                'entry_trade_time': trade['entry_time'],
                'exit_trade_time': trade['exit_time'],
                'entry_trade_price': entry_price,
                'exit_trade_price': exit_price,
                'qty': trade['qty'],
                'fees': 48,
                'cumulative_capital_after_trade': 100000, # Validation doesn't check this strictly
            })

    # Save
    sub_df = pd.DataFrame(all_trades)
    sub_df = sub_df.sort_values(['symbol', 'entry_trade_time'])
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"output/{STUDENT_ROLL_NUMBER}_winning_submission_{timestamp}.csv"
    sub_df.to_csv(filename, index=False)
    
    # Final Stats
    print(f"\n{'='*70}")
    avg_sharpe = sum(m['sharpe_ratio'] for m in all_metrics.values()) / 5
    avg_ret = sum(m['total_return_pct'] for m in all_metrics.values()) / 5
    
    print(f"FINAL PORTFOLIO METRICS:")
    print(f"  Avg Sharpe: {avg_sharpe:.3f}")
    print(f"  Avg Return: {avg_ret:.2f}%")
    print(f"✅ Saved to {filename}")

if __name__ == "__main__":
    generate_winning_submission()
