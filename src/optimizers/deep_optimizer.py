"""
Deep Zoom-in Optimizer for Hackathon Victory 🏆
Implements a multi-stage optimization process:
1. Broad Exploration (Random Search)
2. Local Zoom-in (Perturbation around best candidates)
3. Final Selection based on Sharpe

Target: Portfolio Sharpe > 1.25 (Top 1)
"""

import pandas as pd
import numpy as np
import json
import random
import sys
import os
from typing import Dict, List, Any
import copy

# Add paths
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from strategies.hybrid_adaptive import HybridAdaptiveStrategy
from config.sharpe_config import SharpeConfig

class DeepOptimizer:
    def __init__(self):
        self.config = SharpeConfig()
        
    def _generate_random_params(self, param_space: Dict) -> Dict:
        """Generate a single random parameter set from search space"""
        params = {}
        for key, space in param_space.items():
            if key == 'strategy_type':
                params[key] = space
                continue
                
            if isinstance(space, list):
                # Categorical or Discrete choice
                params[key] = random.choice(space)
            elif isinstance(space, tuple) and len(space) == 2:
                # Range (min, max)
                if isinstance(space[0], int):
                    params[key] = random.randint(space[0], space[1])
                else:
                    params[key] = random.uniform(space[0], space[1])
        
        return params

    def _perturb_params(self, params: Dict, param_space: Dict, intensity: float = 0.2) -> Dict:
        """Perturb parameters around a center point for zoom-in"""
        new_params = params.copy()
        
        for key, value in params.items():
            if key not in param_space or key == 'strategy_type':
                continue
                
            space = param_space[key]
            
            if isinstance(space, list):
                # For lists, 20% chance to pick a neighbor if ordered, or random
                if random.random() < intensity:
                    new_params[key] = random.choice(space)
            
            elif isinstance(space, tuple) and len(space) == 2:
                # For ranges, perturb by +/- intensity * range_width
                min_val, max_val = space
                if isinstance(min_val, int):
                    span = max_val - min_val
                    change = int(span * intensity * random.uniform(-1, 1))
                    val = max(min_val, min(max_val, value + change))
                    new_params[key] = int(val)
                else:
                    span = max_val - min_val
                    change = span * intensity * random.uniform(-1, 1)
                    val = max(min_val, min(max_val, value + change))
                    new_params[key] = float(val)
                    
        return new_params

    def optimize_symbol(self, symbol: str, data: pd.DataFrame, 
                       n_coarse: int = 500, n_fine: int = 100) -> Dict:
        """
        Run Deep Optimization for a single symbol
        Phase 1: Coarse Random Search (n_coarse iterations)
        Phase 2: Zoom-in on Top 5 candidates (n_fine iterations total)
        """
        print(f"\n🚀 STARTING DEEP OPTIMIZATION FOR {symbol}")
        param_space = self.config.get_symbol_config(symbol)
        
        # === PHASE 1: COARSE SEARCH ===
        print(f"  Phase 1: Coarse Search ({n_coarse} iter)...")
        results = []
        
        for i in range(n_coarse):
            params = self._generate_random_params(param_space)
            strategy = HybridAdaptiveStrategy(params)
            _, metrics = strategy.backtest(data)
            
            if metrics['total_trades'] >= 120:
                results.append({
                    'params': params,
                    'metrics': metrics,
                    'score': metrics['sharpe_ratio'] # Primary wrapper objective
                })
        
        if not results:
            print("  ❌ No valid parameters found in Phase 1!")
            return {}

        # Sort by Sharpe
        results.sort(key=lambda x: x['score'], reverse=True)
        top_candidates = results[:5]
        
        print(f"  Top Coarse Result: Sharpe={top_candidates[0]['score']:.3f}, Return={top_candidates[0]['metrics']['total_return_pct']:.2f}%")
        
        # === PHASE 2: ZOOM-IN REFINEMENT ===
        print(f"  Phase 2: Fine-Tuning ({n_fine} iter)...")
        refined_results = []
        
        # Distribute fine iterations among top candidates
        iters_per_candidate = n_fine // len(top_candidates)
        
        for candidate in top_candidates:
            # Add the candidate itself
            refined_results.append(candidate)
            
            base_params = candidate['params']
            
            for _ in range(iters_per_candidate):
                # Perturb parameters (intensity 0.15 = 15% variation)
                new_params = self._perturb_params(base_params, param_space, intensity=0.15)
                strategy = HybridAdaptiveStrategy(new_params)
                _, metrics = strategy.backtest(data)
                
                if metrics['total_trades'] >= 120:
                    refined_results.append({
                        'params': new_params,
                        'metrics': metrics,
                        'score': metrics['sharpe_ratio']
                    })
        
        # Final Sort
        refined_results.sort(key=lambda x: x['score'], reverse=True)
        best = refined_results[0]
        
        print(f"  🏆 FINAL BEST: Sharpe={best['score']:.3f}, Return={best['metrics']['total_return_pct']:.2f}%")
        
        # Check improvement
        improvement = best['score'] - results[0]['score']
        print(f"  📈 Phase 2 Improvement: {improvement:+.3f} Sharpe")
        
        return best

    def run_full_optimization(self):
        """Run optimization for all symbols"""
        all_best_params = {}
        
        # Only re-run specific symbols to save time
        symbols = ['NIFTY50', 'RELIANCE'] 
        
        class NpEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, np.integer):
                    return int(obj)
                if isinstance(obj, np.floating):
                    return float(obj)
                if isinstance(obj, np.ndarray):
                    return obj.tolist()
                return super(NpEncoder, self).default(obj)

        for symbol in symbols:
            file_path, _ = self.config.get_data_path(symbol)
            df = pd.read_csv(file_path)
            df['datetime'] = pd.to_datetime(df['datetime'])
            df = df.sort_values('datetime').reset_index(drop=True)
            
            # Intense search
            n_coarse, n_fine = 600, 200 # Slightly reduced
                
            result = self.optimize_symbol(symbol, df, n_coarse, n_fine)
            
            if result:
                all_best_params[symbol] = result
            else:
                print(f"⚠️ Failed to optimize {symbol}, using default/empty")
                all_best_params[symbol] = {'params': {}, 'metrics': {}}

        # Save results
        with open('output/deep_optimized_params.json', 'w') as f:
            json.dump(all_best_params, f, indent=2, cls=NpEncoder)
            
        print("\n✅ Deep Optimization Complete! Saved to output/deep_optimized_params.json")

if __name__ == "__main__":
    optimizer = DeepOptimizer()
    optimizer.run_full_optimization()
