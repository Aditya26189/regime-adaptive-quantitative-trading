"""
PARALLEL MULTI-SYMBOL OPTIMIZER

Runs Optuna optimization for all 5 symbols simultaneously using multiprocessing.
Utilizes all CPU cores for maximum speed.

Expected Runtime:
- Single symbol: 45-60 minutes (200 trials)
- All 5 symbols parallel: 60-90 minutes (using 4-8 cores)

Copilot Instructions:
- Uses joblib for parallel processing
- Each symbol gets its own Optuna study
- Results saved to SQLite database automatically
- Progress tracking and visualization
"""

import optuna
import pandas as pd
import numpy as np
from pathlib import Path
import json
from datetime import datetime
from typing import Dict, List, Tuple
import joblib
from joblib import Parallel, delayed
import warnings
warnings.filterwarnings('ignore')

# Suppress Optuna logging spam
optuna.logging.set_verbosity(optuna.logging.WARNING)


class ParallelSymbolOptimizer:
    """
    Optimizes all 5 symbols in parallel using Optuna + Bayesian optimization.
    
    This is the main class you'll interact with.
    Simply call .optimize_all() and wait for results.
    """
    
    # Symbol configuration
    SYMBOLS = {
        'NSE:NIFTY50-INDEX': {
            'data_file': 'data/NSE_NIFTY50_INDEX_1hour.csv',
            'strategy_type': 'trend',
            'display_name': 'NIFTY50'
        },
        'NSE:VBL-EQ': {
            'data_file': 'data/NSE_VBL_EQ_1hour.csv',
            'strategy_type': 'ensemble',
            'display_name': 'VBL'
        },
        'NSE:SUNPHARMA-EQ': {
            'data_file': 'data/NSE_SUNPHARMA_EQ_1hour.csv',
            'strategy_type': 'mean_reversion',
            'display_name': 'SUNPHARMA'
        },
        'NSE:RELIANCE-EQ': {
            'data_file': 'data/NSE_RELIANCE_EQ_1hour.csv',
            'strategy_type': 'hybrid',
            'display_name': 'RELIANCE'
        },
        'NSE:YESBANK-EQ': {
            'data_file': 'data/NSE_YESBANK_EQ_1hour.csv',
            'strategy_type': 'hybrid',
            'display_name': 'YESBANK'
        }
    }
    
    def __init__(self, 
                 n_trials: int = 200,
                 n_jobs: int = -1,  # -1 = use all cores
                 timeout: int = None,  # seconds (None = no limit)
                 output_dir: str = 'optimization_results/'):
        """
        Initialize parallel optimizer.
        
        Args:
            n_trials: Number of Optuna trials per symbol
            n_jobs: Number of parallel jobs (-1 = all cores)
            timeout: Maximum time per symbol in seconds (None = unlimited)
            output_dir: Where to save results
        """
        self.n_trials = n_trials
        self.n_jobs = n_jobs
        self.timeout = timeout
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
        
        # Database for storing Optuna studies
        self.db_path = self.output_dir / 'optuna_studies.db'
        self.storage = f'sqlite:///{self.db_path}'
        
        self.results = {}
    
    def optimize_single_symbol(self, 
                               symbol: str, 
                               config: Dict) -> Tuple[str, Dict]:
        """
        Optimize parameters for single symbol using Optuna.
        
        This function runs in parallel for each symbol.
        
        Args:
            symbol: Trading symbol
            config: Symbol configuration dict
        
        Returns:
            (symbol, results_dict)
        """
        print(f"\n{'='*60}")
        print(f"Starting optimization: {config['display_name']}")
        print(f"Strategy: {config['strategy_type']}")
        print(f"Trials: {self.n_trials}")
        print(f"{'='*60}")
        
        # Load data
        try:
            data = pd.read_csv(config['data_file'])
        except FileNotFoundError:
            print(f"ERROR: Data file not found: {config['data_file']}")
            return symbol, {'error': 'Data file not found'}
        
        # Create objective function
        from src.optimization.objective_functions import create_objective_function
        objective = create_objective_function(
            symbol, 
            data, 
            config['strategy_type']
        )
        
        # Create Optuna study
        study_name = f"{config['display_name']}_optuna"
        
        try:
            study = optuna.create_study(
                study_name=study_name,
                storage=self.storage,
                direction='maximize',  # Maximize competition score
                load_if_exists=True,   # Resume if interrupted
                sampler=optuna.samplers.TPESampler(  # Bayesian optimization
                    n_startup_trials=20,  # Random for first 20, then Bayesian
                    multivariate=True,    # Consider parameter interactions
                    seed=42               # Reproducible results
                )
            )
        except Exception as e:
            print(f"ERROR creating study: {e}")
            return symbol, {'error': str(e)}
        
        # Run optimization
        start_time = datetime.now()
        
        try:
            study.optimize(
                objective,
                n_trials=self.n_trials,
                timeout=self.timeout,
                show_progress_bar=True,
                n_jobs=1  # Each symbol runs single-threaded (parallelism is across symbols)
            )
        except Exception as e:
            print(f"ERROR during optimization: {e}")
            return symbol, {'error': str(e)}
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds() / 60
        
        # Extract results
        best_params = study.best_params
        best_score = study.best_value
        best_trial = study.best_trial
        
        # Get stored metrics from best trial
        metrics = {
            'sharpe': best_trial.user_attrs.get('sharpe', 0),
            'return': best_trial.user_attrs.get('return', 0),
            'win_rate': best_trial.user_attrs.get('win_rate', 0),
            'drawdown': best_trial.user_attrs.get('drawdown', 0),
            'trades': best_trial.user_attrs.get('trades', 0)
        }
        
        # Compile results
        results = {
            'symbol': symbol,
            'display_name': config['display_name'],
            'strategy_type': config['strategy_type'],
            'best_params': best_params,
            'best_score': best_score,
            'metrics': metrics,
            'n_trials': len(study.trials),
            'optimization_time_minutes': duration,
            'completed_at': datetime.now().isoformat()
        }
        
        print(f"\n{'─'*60}")
        print(f"COMPLETED: {config['display_name']}")
        print(f"{'─'*60}")
        print(f"Best Score: {best_score:.3f}")
        print(f"Sharpe: {metrics['sharpe']:.3f}")
        print(f"Return: {metrics['return']:+.2f}%")
        print(f"Win Rate: {metrics['win_rate']:.1%}")
        print(f"Trades: {metrics['trades']}")
        print(f"Time: {duration:.1f} minutes")
        print(f"{'─'*60}\n")
        
        return symbol, results
    
    def optimize_all(self) -> Dict:
        """
        Optimize all 5 symbols in parallel.
        
        This is the main method you call.
        
        Returns:
            Dictionary of results keyed by symbol
        """
        print("\n" + "="*60)
        print("STARTING PARALLEL OPTIMIZATION")
        print("="*60)
        print(f"Symbols: {len(self.SYMBOLS)}")
        print(f"Trials per symbol: {self.n_trials}")
        print(f"Parallel jobs: {self.n_jobs if self.n_jobs > 0 else 'ALL CORES'}")
        print(f"Output directory: {self.output_dir}")
        print("="*60 + "\n")
        
        start_time = datetime.now()
        
        # Run optimizations in parallel
        results_list = Parallel(n_jobs=self.n_jobs, verbose=10)(
            delayed(self.optimize_single_symbol)(symbol, config)
            for symbol, config in self.SYMBOLS.items()
        )
        
        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds() / 60
        
        # Convert to dictionary
        self.results = {symbol: result for symbol, result in results_list}
        
        # Save results
        self._save_results()
        
        # Print summary
        self._print_summary(total_duration)
        
        return self.results
    
    def _save_results(self):
        """Save optimization results to JSON file."""
        # Save complete results
        results_file = self.output_dir / 'optimization_results.json'
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        # Save best parameters only (for easy loading)
        best_params = {
            symbol: result['best_params']
            for symbol, result in self.results.items()
            if 'best_params' in result
        }
        
        params_file = self.output_dir / 'best_params_per_symbol.json'
        with open(params_file, 'w') as f:
            json.dump(best_params, f, indent=2)
        
        print(f"\n✓ Results saved:")
        print(f"  - {results_file}")
        print(f"  - {params_file}")
    
    def _print_summary(self, total_duration: float):
        """Print optimization summary."""
        print("\n" + "="*60)
        print("OPTIMIZATION COMPLETE")
        print("="*60)
        print(f"Total Time: {total_duration:.1f} minutes")
        print(f"\nPer-Symbol Results:")
        print("-" * 60)
        
        # Calculate portfolio metrics
        portfolio_sharpe = []
        portfolio_return = []
        
        for symbol, result in self.results.items():
            if 'error' in result:
                print(f"{result['display_name']:12s}: ERROR - {result['error']}")
                continue
            
            metrics = result['metrics']
            portfolio_sharpe.append(metrics['sharpe'])
            portfolio_return.append(metrics['return'])
            
            print(f"{result['display_name']:12s}: "
                  f"Sharpe={metrics['sharpe']:5.2f} | "
                  f"Return={metrics['return']:+6.2f}% | "
                  f"WinRate={metrics['win_rate']:5.1%} | "
                  f"Trades={metrics['trades']:3d}")
        
        # Portfolio summary
        if portfolio_sharpe:
            avg_sharpe = np.mean(portfolio_sharpe)
            avg_return = np.mean(portfolio_return)
            
            print("-" * 60)
            print(f"{'PORTFOLIO':12s}: "
                  f"Sharpe={avg_sharpe:5.2f} | "
                  f"Return={avg_return:+6.2f}%")
            print("="*60)
            
            # Estimate rank
            if avg_sharpe >= 1.35:
                rank_estimate = "TOP 1-3 🏆🏆🏆"
            elif avg_sharpe >= 1.25:
                rank_estimate = "TOP 3-5 🏆🏆"
            elif avg_sharpe >= 1.15:
                rank_estimate = "TOP 5-10 🏆"
            elif avg_sharpe >= 1.00:
                rank_estimate = "TOP 10-15"
            else:
                rank_estimate = "TOP 15-25"
            
            print(f"\nEstimated Rank: {rank_estimate}")
            print("="*60 + "\n")
    
    def generate_visualization(self):
        """
        Generate optimization visualization plots.
        Requires optuna-dashboard or plotly.
        """
        try:
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots
        except ImportError:
            print("Plotly not installed. Skipping visualization.")
            return
        
        print("\nGenerating visualization plots...")
        
        # Create plots directory
        plots_dir = self.output_dir / 'plots'
        plots_dir.mkdir(exist_ok=True)
        
        for symbol, result in self.results.items():
            if 'error' in result:
                continue
            
            study_name = f"{result['display_name']}_optuna"
            
            try:
                study = optuna.load_study(
                    study_name=study_name,
                    storage=self.storage
                )
                
                # Optimization history plot
                fig = optuna.visualization.plot_optimization_history(study)
                fig.write_html(plots_dir / f"{result['display_name']}_history.html")
                
                # Parameter importance plot
                fig = optuna.visualization.plot_param_importances(study)
                fig.write_html(plots_dir / f"{result['display_name']}_importance.html")
                
                print(f"  ✓ {result['display_name']}: Plots saved")
                
            except Exception as e:
                print(f"  ✗ {result['display_name']}: Visualization failed - {e}")
        
        print(f"\n✓ Plots saved to: {plots_dir}/")


# Quick start example for Copilot:
"""
from src.optimization.parallel_optimizer import ParallelSymbolOptimizer

# Create optimizer
optimizer = ParallelSymbolOptimizer(
    n_trials=200,      # 200 trials per symbol (Bayesian is smart)
    n_jobs=-1,         # Use all CPU cores
    timeout=3600       # 1 hour max per symbol
)

# Run optimization (this will take 60-90 minutes)
results = optimizer.optimize_all()

# Generate visualization
optimizer.generate_visualization()

# Access results
for symbol, result in results.items():
    print(f"{symbol}: Sharpe={result['metrics']['sharpe']:.2f}")
"""
