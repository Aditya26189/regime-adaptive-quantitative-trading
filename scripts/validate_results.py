"""
OPTIMIZATION RESULTS VALIDATION SCRIPT

Validates optimization results against competition requirements.
Ensures no rule violations before final submission.
"""

import json
import sys
from pathlib import Path
import pandas as pd
import warnings

warnings.filterwarnings('ignore')

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.strategies.nifty_trend_strategy import generate_nifty_trend_signals
from src.strategies.hybrid_adaptive import HybridAdaptiveStrategy
from src.strategies.ensemble_wrapper import EnsembleStrategy

DATA_FILE_MAP = {
    'NIFTY50': 'data/raw/NSE_NIFTY50_INDEX_1hour.csv',
    'VBL': 'data/raw/NSE_VBL_EQ_1hour.csv',
    'SUNPHARMA': 'data/raw/NSE_SUNPHARMA_EQ_1hour.csv',
    'RELIANCE': 'data/raw/NSE_RELIANCE_EQ_1hour.csv',
    'YESBANK': 'data/raw/NSE_YESBANK_EQ_1hour.csv',
}

def validate_results():
    print("="*60)
    print("VALIDATING OPTUNA RESULTS")
    print("="*60)
    
    results_path = Path('optimization_results/optuna_results.json')
    if not results_path.exists():
        print(f"❌ {results_path} not found!")
        return
    
    try:
        with open(results_path, 'r') as f:
            results = json.load(f)
    except Exception as e:
        print(f"❌ Failed to load JSON: {e}")
        return
        
    all_passed = True
    
    for symbol, data in results.items():
        if symbol == 'portfolio': continue
        
        print(f"\nChecking {symbol}...")
        
        if 'error' in data:
            print(f"❌ Optimization failed: {data['error']}")
            all_passed = False
            continue
            
        params = data.get('params', {})
        if not params:
            print(f"❌ No params found!")
            all_passed = False
            continue
        
        # Load data to re-verify trade count
        try:
            df = pd.read_csv(DATA_FILE_MAP[symbol])
            df['datetime'] = pd.to_datetime(df['datetime'])
            df = df.sort_values('datetime').reset_index(drop=True)
            
            # Generate trades
            if symbol == 'NIFTY50':
                trades = generate_nifty_trend_signals(df, params)
                trade_count = len(trades)
            else:
                if params.get('use_ensemble'):
                    strat = EnsembleStrategy(params, 5, 3)
                else:
                    strat = HybridAdaptiveStrategy(params)
                t, _ = strat.backtest(df)
                trade_count = len(t)
                
            print(f"  Trades: {trade_count}")
            
            if trade_count < 120:
                print(f"❌ FAILED: Trade count {trade_count} < 120")
                all_passed = False
            else:
                print(f"✅ PASSED (Count: {trade_count})")
                
        except Exception as e:
            print(f"❌ RE-VERIFICATION FAILED: {e}")
            all_passed = False
            
    print("\n" + "="*60)
    if all_passed:
        print("✅ ALL CHECKS PASSED - READY FOR SUBMISSION")
    else:
        print("❌ VALIDATION FAILED - DO NOT SUBMIT")
    print("="*60)

if __name__ == "__main__":
    validate_results()
