"""
Final Submission Generator (Hybrid Robust)
Combines:
1. Optuna-optimized NIFTY parameters (Best Trend Strategy)
2. Validated Ensemble/Deep parameters for stocks (Fallback from failed Optuna run)
"""

import sys
from pathlib import Path
import json
import pandas as pd
from datetime import datetime
import warnings

warnings.filterwarnings('ignore')

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import strategies
from src.strategies.nifty_trend_strategy import generate_nifty_trend_signals
from src.strategies.hybrid_adaptive import HybridAdaptiveStrategy
from src.strategies.ensemble_wrapper import EnsembleStrategy

ROLL_NUMBER = '23ME3EP03'
DATA_PATHS = {
    'NIFTY50': ('data/raw/NSE_NIFTY50_INDEX_1hour.csv', 'NSE:NIFTY50-INDEX'),
    'VBL': ('data/raw/NSE_VBL_EQ_1hour.csv', 'NSE:VBL-EQ'),
    'SUNPHARMA': ('data/raw/NSE_SUNPHARMA_EQ_1hour.csv', 'NSE:SUNPHARMA-EQ'),
    'RELIANCE': ('data/raw/NSE_RELIANCE_EQ_1hour.csv', 'NSE:RELIANCE-EQ'),
    'YESBANK': ('data/raw/NSE_YESBANK_EQ_1hour.csv', 'NSE:YESBANK-EQ'),
}

# ------------------------------------------------------------------------
# FALLBACK PARAMETERS (From Winning Phase 3/4)
# Used when Optuna scoring returns -inf (Strict trade constraints)
# ------------------------------------------------------------------------
FALLBACK_PARAMS = {
    'VBL': {
        'use_ensemble': True,
        'rsi_period': 14, 'rsi_oversold': 30, 'rsi_overbought': 70, # Base params for ensemble
        'n_variants': 5, 'min_agreement': 3
    },
    'RELIANCE': {
        # Deep Optimization Result (Sharpe 1.64)
       'rsi_period': 5, 'rsi_oversold': 34, 'rsi_overbought': 84, 
       'ker_period': 18, 'ker_threshold': 0.29,
       'vol_min': 0.0048, 'vol_max': 0.0176, 'max_hold': 18
    },
    'SUNPHARMA': {
        # Validated Mean Rev
        'rsi_period': 4, 'rsi_oversold': 34, 'rsi_overbought': 80,
        'ker_period': 16, 'ker_threshold': 0.36,
        'vol_min': 0.004, 'vol_max': 0.017, 'max_hold': 14
    },
    'YESBANK': {
        # Validated Hybrid
        'rsi_period': 6, 'rsi_oversold': 39, 'rsi_overbought': 86,
        'ker_period': 15, 'ker_threshold': 0.29,
        'vol_min': 0.003, 'vol_max': 0.018, 'max_hold': 18
    }
}

def cap_prices(entry, exit_price, limit_pct=5.0):
    limit = entry * (limit_pct / 100.0)
    upper = entry + limit
    lower = entry - limit
    return max(lower, min(upper, exit_price))

def generate_submission():
    print("🚀 Generating Final Robust Submission...")
    
    # Load Optuna Results
    optuna_params = {}
    try:
        with open('optimization_results/optuna_results.json', 'r') as f:
            full_results = json.load(f)
            # Only use if score is valid
            for sym, data in full_results.items():
                if isinstance(data, dict) and data.get('score') != float('-inf'):
                    optuna_params[sym] = data.get('params')
                    print(f"  ✅ Using Optuna params for {sym}")
                elif sym != 'portfolio':
                    print(f"  ⚠️ Optuna failed for {sym}, using Fallback.")
    except Exception:
        print("  ⚠️ No Optuna results found, using full fallback.")

    all_trades = []
    
    for symbol, (path, code) in DATA_PATHS.items():
        # Select Params: Optuna > Fallback > Error
        params = optuna_params.get(symbol, FALLBACK_PARAMS.get(symbol))
        
        if not params:
            print(f"❌ CRITICAL: No params for {symbol}!")
            continue
            
        try:
            df = pd.read_csv(path)
            df['datetime'] = pd.to_datetime(df['datetime'])
            df = df.sort_values('datetime').reset_index(drop=True)
            
            # Execute Strategy
            if symbol == 'NIFTY50':
                # Force Optuna params for NIFTY if available, else standard trend
                trades_df = generate_nifty_trend_signals(df, params)
                raw_trades = trades_df.to_dict('records')
            else:
                if params.get('use_ensemble'):
                    strat = EnsembleStrategy(params, 5, 3)
                else:
                    strat = HybridAdaptiveStrategy(params)
                raw_trades, _ = strat.backtest(df)
            
            print(f"  {symbol}: {len(raw_trades)} trades")
            
            # CSV Formatting
            capital = 100000.0
            for t in raw_trades:
                entry = t.get('entry_price', t.get('entry_trade_price'))
                exit_raw = t.get('exit_price', t.get('exit_trade_price'))
                exit_final = cap_prices(entry, exit_raw, 5.0) # 5% Cap
                
                qty = t.get('qty', int(capital // entry))
                pnl = (exit_final - entry) * qty - 48
                capital += pnl
                
                all_trades.append({
                    'student_roll_number': ROLL_NUMBER,
                    'strategy_submission_number': 1,
                    'symbol': code,
                    'timeframe': '1hour',
                    'entry_trade_time': t.get('entry_time', t.get('entry_trade_time')),
                    'exit_trade_time': t.get('exit_time', t.get('exit_trade_time')),
                    'entry_trade_price': entry,
                    'exit_trade_price': exit_final,
                    'qty': qty,
                    'fees': 48,
                    'cumulative_capital_after_trade': capital
                })
        except Exception as e:
            print(f"❌ {symbol} Execution Failed: {e}")

    # Save
    submission_df = pd.DataFrame(all_trades)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"output/{ROLL_NUMBER}_submission_{timestamp}.csv"
    submission_df.to_csv(filename, index=False)
    
    print(f"\n✅ Final Submission Saved: {filename}")
    print(f"Total Trades: {len(submission_df)}")

if __name__ == "__main__":
    generate_submission()
