"""
PARALLEL MULTI-SYMBOL OPTIMIZER

Runs Optuna optimization for all 5 symbols simultaneously using multiprocessing.
Utilizes all CPU cores for maximum speed.
"""

import optuna
from optuna.samplers import TPESampler
import pandas as pd
import json
import sys
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Dict, Any, List
from datetime import datetime
import warnings

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.optimization.objective_functions import objective_function
from src.optimization.parameter_space import SYMBOL_PARAM_FUNCTIONS

warnings.filterwarnings('ignore')

DATA_FILE_MAP = {
    'NIFTY50': 'data/raw/NSE_NIFTY50_INDEX_1hour.csv',
    'VBL': 'data/raw/NSE_VBL_EQ_1hour.csv',
    'SUNPHARMA': 'data/raw/NSE_SUNPHARMA_EQ_1hour.csv',
    'RELIANCE': 'data/raw/NSE_RELIANCE_EQ_1hour.csv',
    'YESBANK': 'data/raw/NSE_YESBANK_EQ_1hour.csv',
}

class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        import numpy as np
        if isinstance(obj, np.integer): return int(obj)
        if isinstance(obj, np.floating): return float(obj)
        if isinstance(obj, np.ndarray): return obj.tolist()
        return super().default(obj)

def optimize_single_symbol(symbol: str, n_trials: int) -> Dict[str, Any]:
    """Worker function to optimize one symbol."""
    print(f"🚀 Starting {symbol} optimization ({n_trials} trials)...")
    
    # Load data locally in process
    data_path = DATA_FILE_MAP.get(symbol)
    if not data_path:
        return {'symbol': symbol, 'error': 'Data file not found'}
        
    df = pd.read_csv(data_path)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.sort_values('datetime').reset_index(drop=True)
    
    # Create Study
    study = optuna.create_study(
        study_name=f"{symbol}_opt",
        direction="maximize",
        sampler=TPESampler(seed=42)
    )
    
    # Optimize
    study.optimize(lambda t: objective_function(t, symbol, df), n_trials=n_trials)
    
    best_params = study.best_params
    best_score = study.best_value
    
    # Add fixed params if needed
    if symbol == 'NIFTY50':
        best_params['vol_period'] = 14
        best_params['allowed_hours'] = [9, 10, 11, 12, 13, 14]
    elif symbol == 'VBL' and best_params.get('use_ensemble'):
        best_params['n_variants'] = 5
        best_params['min_agreement'] = 3

    print(f"✅ {symbol} Done! Score: {best_score:.4f}")
    
    return {
        'symbol': symbol,
        'params': best_params,
        'score': best_score,
        'trials': len(study.trials)
    }

def run_parallel_optimization(symbols: List[str] = None, n_trials: int = 100) -> Dict[str, Any]:
    """Run optimization for multiple symbols in parallel."""
    if not symbols:
        symbols = list(DATA_FILE_MAP.keys())
        
    print(f"\nSTARTING PARALLEL OPTIMIZATION")
    print(f"Symbols: {symbols}")
    print(f"Trials: {n_trials}")
    print(f"Workers: {min(len(symbols), 5)}")
    print("="*60)
    
    results = {}
    start_time = datetime.now()
    
    with ProcessPoolExecutor(max_workers=min(len(symbols), 5)) as executor:
        future_map = {executor.submit(optimize_single_symbol, sym, n_trials): sym for sym in symbols}
        
        for future in as_completed(future_map):
            sym = future_map[future]
            try:
                res = future.result()
                results[sym] = res
            except Exception as e:
                print(f"❌ {sym} Failed: {e}")
                results[sym] = {'error': str(e)}
                
    duration = datetime.now() - start_time
    print(f"\n{'='*60}")
    print(f"OPTIMIZATION COMPLETE (Duration: {duration})")
    print(f"{'='*60}")
    
    # Save results
    Path('optimization_results').mkdir(exist_ok=True)
    with open('optimization_results/optuna_results.json', 'w') as f:
        json.dump(results, f, indent=2, cls=NpEncoder)
        
    return results
