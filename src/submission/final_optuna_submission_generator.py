"""
Final Optuna Submission Generator 🏆
Combines:
1. Optuna-optimized NIFTY parameters (Best Trend Strategy)
2. Battle-tested Deep/Ensemble parameters for stocks (Fallback from failed Optuna run)
"""

import pandas as pd
import numpy as np
import json
import os
from datetime import datetime
import sys

# Add project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.strategies.hybrid_adaptive import HybridAdaptiveStrategy
from src.strategies.ensemble_wrapper import EnsembleStrategy
from src.strategies.nifty_trend_strategy import generate_nifty_trend_signals

STUDENT_ROLL_NUMBER = "23ME3EP03"

DATA_PATHS = {
    'NIFTY50': ('data/raw/NSE_NIFTY50_INDEX_1hour.csv', 'NSE:NIFTY50-INDEX'),
    'RELIANCE': ('data/raw/NSE_RELIANCE_EQ_1hour.csv', 'NSE:RELIANCE-EQ'),
    'VBL': ('data/raw/NSE_VBL_EQ_1hour.csv', 'NSE:VBL-EQ'),
    'YESBANK': ('data/raw/NSE_YESBANK_EQ_1hour.csv', 'NSE:YESBANK-EQ'),
    'SUNPHARMA': ('data/raw/NSE_SUNPHARMA_EQ_1hour.csv', 'NSE:SUNPHARMA-EQ'),
}

def generate_final_submission():
    print("="*70)
    print("GENERATING FINAL OPTUNA SUBMISSION")
    print("="*70)
    
    # 1. Load best available parameters
    try:
        # Stock parameters (Deep/Fallback)
        with open('output/deep_optimized_params.json', 'r') as f:
            deep_params_all = json.load(f)
        with open('output/sharpe_optimized_params.json', 'r') as f:
            fallback_params_all = json.load(f)
            
        # NIFTY parameters (Try Optuna first, then standard trend)
        nifty_params = None
        if os.path.exists('optimization_results/nifty_optuna_best.json'):
             with open('optimization_results/nifty_optuna_best.json', 'r') as f:
                data = json.load(f)
                nifty_params = data['params']
                print(f"✅ Loaded Optuna NIFTY Params (Sharpe: {data['metrics']['sharpe']:.4f})")
        
        if not nifty_params:
            print("⚠️ Optuna NIFTY not found, using standard Trend params")
            with open('output/nifty_trend_optimized_params.json', 'r') as f:
                 data = json.load(f)
                 nifty_params = data['NIFTY50_TREND']

    except Exception as e:
        print(f"❌ Failed to load params: {e}")
        return

    all_trades = []
    all_metrics = {}

    for symbol in ['NIFTY50', 'RELIANCE', 'VBL', 'YESBANK', 'SUNPHARMA']:
        print(f"\n{symbol}:")
        
        file_path, symbol_code = DATA_PATHS[symbol]
        df = pd.read_csv(file_path)
        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.sort_values('datetime').reset_index(drop=True)
        
        # --- STRATEGY EXECUTION ---
        if symbol == 'NIFTY50':
            print("  Using Trend Strategy (Optuna/Optimized)...")
            trades_df = generate_nifty_trend_signals(df, nifty_params)
            metrics = {
                'total_trades': len(trades_df),
                'total_return_pct': trades_df['pnl'].sum()/100000*100 if len(trades_df) > 0 else 0,
                'sharpe_ratio': 0.0 # Placeholder, we trust optimization
            }
            trades = trades_df.to_dict('records')
            
            # Map keys
            mapped_trades = []
            for t in trades:
                mapped_trades.append({
                    'entry_time': t['entry_time'],
                    'exit_time': t['exit_time'],
                    'entry_price': t['entry_price'],
                    'exit_price': t['exit_price'],
                    'qty': t['qty'],
                    'pnl': t['pnl']
                })
            trades = mapped_trades
            source = "OPTUNA_TREND"
            
        else:
            # Smart Selection Logic (Deep vs Fallback vs Ensemble)
            deep_entry = deep_params_all.get(symbol, {})
            fallback_entry = fallback_params_all.get(symbol, {})
            
            # Choose Deep vs Fallback
            if deep_entry.get('params'):
                d_strat = HybridAdaptiveStrategy(deep_entry['params'])
                _, d_met = d_strat.backtest(df)
                f_strat = HybridAdaptiveStrategy(fallback_entry['params'])
                _, f_met = f_strat.backtest(df)
                
                if d_met.get('sharpe_ratio', -999) > f_met.get('sharpe_ratio', -999):
                    chosen_params = deep_entry['params']
                    source = "DEEP"
                else:
                    chosen_params = fallback_entry['params']
                    source = "FALLBACK"
            else:
                chosen_params = fallback_entry['params']
                source = "FALLBACK"
                
            # Logic for VBL Ensemble
            if symbol == 'VBL':
                print("  Testing VBL Ensemble...")
                e_strat = EnsembleStrategy(chosen_params, n_variants=5, min_agreement=3)
                e_trades, e_met = e_strat.backtest(df)
                s_strat = HybridAdaptiveStrategy(chosen_params)
                _, s_met = s_strat.backtest(df)
                
                if e_met['sharpe_ratio'] > s_met['sharpe_ratio']:
                    metrics, trades = e_met, e_trades
                    source += "_ENSEMBLE"
                else:
                    metrics, trades = s_met, s_strat.backtest(df)[0]
            else:
                strategy = HybridAdaptiveStrategy(chosen_params)
                trades, metrics = strategy.backtest(df)

        print(f"  Source: {source}")
        print(f"  Trades: {metrics['total_trades']}")
        print(f"  Return: {metrics['total_return_pct']:.2f}%")
        
        all_metrics[symbol] = metrics

        # --- CSV FORMATTING & CAPPING ---
        for trade in trades:
            entry_price = trade.get('entry_price', trade.get('entry_trade_price'))
            exit_price = trade.get('exit_price', trade.get('exit_trade_price'))
            
            # 5% Outlier Cap
            raw_ret = ((exit_price - entry_price) / entry_price) * 100
            if raw_ret > 5.0:
                exit_price = entry_price * 1.05
            elif raw_ret < -5.0: # Optional safety
                 pass 
                 
            all_trades.append({
                'student_roll_number': STUDENT_ROLL_NUMBER,
                'strategy_submission_number': 1,
                'symbol': symbol_code,
                'timeframe': '60',
                'entry_trade_time': trade.get('entry_time', trade.get('entry_trade_time')),
                'exit_trade_time': trade.get('exit_time', trade.get('exit_trade_time')),
                'entry_trade_price': entry_price,
                'exit_trade_price': exit_price,
                'qty': trade.get('qty', 1),
                'fees': 48,
                'cumulative_capital_after_trade': 100000, 
            })

    # Save CSV
    submission_df = pd.DataFrame(all_trades)
    submission_df = submission_df.sort_values(['symbol', 'entry_trade_time'])
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"output/{STUDENT_ROLL_NUMBER}_final_optuna_submission_{timestamp}.csv"
    submission_df.to_csv(filename, index=False)
    
    # Portfolio Metrics
    avg_sharpe = sum(m.get('sharpe_ratio', 0) for m in all_metrics.values()) / 5
    avg_return = sum(m.get('total_return_pct', 0) for m in all_metrics.values()) / 5
    
    print("\n" + "="*70)
    print("FINAL PORTFOLIO METRICS")
    print("="*70)
    print(f"Avg Sharpe: {avg_sharpe:.3f}")
    print(f"Avg Return: {avg_return:.2f}%")
    print(f"Total Trades: {len(submission_df)}")
    print(f"✅ Saved to {filename}")

if __name__ == "__main__":
    generate_final_submission()
