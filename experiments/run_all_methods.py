"""
Comprehensive Optimization Suite - All 8 Methods Combined
Optimizes portfolio Sharpe from 1.486 to 1.70+ target
"""

import pandas as pd
import numpy as np
import json
import random
import optuna
from datetime import datetime
from pathlib import Path
import sys
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.strategies.hybrid_adaptive_v2 import HybridAdaptiveStrategyV2
from src.strategies.hybrid_adaptive import HybridAdaptiveStrategy
from src.strategies.ensemble_wrapper import EnsembleStrategy

# ============================================================================
# CONFIGURATION
# ============================================================================

SYMBOLS = {
    'VBL': 'data/raw/NSE_VBL_EQ_1hour.csv',
    'RELIANCE': 'data/raw/NSE_RELIANCE_EQ_1hour.csv',
    'SUNPHARMA': 'data/raw/NSE_SUNPHARMA_EQ_1hour.csv',
    'YESBANK': 'data/raw/NSE_YESBANK_EQ_1hour.csv',
}

# ============================================================================
# DATA LOADING
# ============================================================================

def load_data():
    """Load all symbol data"""
    data_cache = {}
    for symbol, filepath in SYMBOLS.items():
        df = pd.read_csv(filepath)
        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.sort_values('datetime').reset_index(drop=True)
        data_cache[symbol] = df
    return data_cache

def load_baseline_params():
    """Load current baseline parameters"""
    baseline = json.load(open('baseline_metrics.json', 'r'))
    advanced = json.load(open('advanced_optimization_results.json', 'r'))
    return baseline, advanced

# ============================================================================
# METHOD 1: SGD OPTIMIZER
# ============================================================================

class SGDOptimizer:
    """Gradient-based parameter optimization"""
    
    def __init__(self, symbol, df, initial_params):
        self.symbol = symbol
        self.df = df
        self.params = initial_params.copy()
        self.learning_rate = 0.1
        
    def evaluate_sharpe(self, params):
        """Evaluate strategy with given params"""
        try:
            strategy = HybridAdaptiveStrategyV2(params)
            trades, metrics = strategy.backtest(self.df)
            
            if metrics['total_trades'] < 120:
                return -1000.0, metrics['total_trades']
            
            return metrics['sharpe_ratio'], metrics['total_trades']
        except:
            return -999.0, 0
    
    def compute_gradient(self, params, epsilon=0.5):
        """Numerical gradient computation"""
        gradients = {}
        base_sharpe, _ = self.evaluate_sharpe(params)
        
        param_names = ['rsi_entry', 'rsi_exit', 'max_hold_bars']
        
        for param_name in param_names:
            if param_name not in params:
                continue
            
            params_plus = params.copy()
            params_plus[param_name] = params[param_name] + epsilon
            sharpe_plus, _ = self.evaluate_sharpe(params_plus)
            
            gradient = (sharpe_plus - base_sharpe) / epsilon
            gradients[param_name] = gradient
        
        return gradients, base_sharpe
    
    def optimize(self, n_iterations=20):
        """Run SGD optimization"""
        print(f"\n[SGD] Optimizing {self.symbol}...")
        
        best_sharpe = -999
        best_params = self.params.copy()
        best_trades = 0
        
        for iteration in range(n_iterations):
            gradients, current_sharpe = self.compute_gradient(self.params)
            
            for param_name, gradient in gradients.items():
                self.params[param_name] += self.learning_rate * gradient
                
                if param_name == 'rsi_entry':
                    self.params[param_name] = int(np.clip(self.params[param_name], 20, 45))
                elif param_name == 'rsi_exit':
                    self.params[param_name] = int(np.clip(self.params[param_name], 60, 85))
                elif param_name == 'max_hold_bars':
                    self.params[param_name] = int(np.clip(self.params[param_name], 5, 18))
            
            sharpe, trades = self.evaluate_sharpe(self.params)
            
            if sharpe > best_sharpe:
                best_sharpe = sharpe
                best_params = self.params.copy()
                best_trades = trades
        
        print(f"  Best: Sharpe={best_sharpe:.3f}, Trades={best_trades}")
        
        return {
            'method': 'SGD',
            'symbol': self.symbol,
            'best_sharpe': best_sharpe,
            'best_trades': best_trades,
            'best_params': best_params
        }

# ============================================================================
# METHOD 2: GENETIC ALGORITHM
# ============================================================================

class GeneticAlgorithm:
    """Evolutionary optimization"""
    
    def __init__(self, symbol, df, initial_params):
        self.symbol = symbol
        self.df = df
        self.initial_params = initial_params
        self.population_size = 30
        self.mutation_rate = 0.15
        
    def create_individual(self):
        """Generate random parameter set based on baseline"""
        base = self.initial_params.copy()
        return {
            'rsi_period': random.randint(2, 5),
            'rsi_entry': random.randint(25, 40),
            'rsi_exit': random.randint(65, 80),
            'max_hold_bars': random.randint(6, 15),
            'vol_min_pct': round(random.uniform(0.003, 0.012), 4),
            'ker_period': base.get('ker_period', 10),
            'position_size_pct': base.get('position_size_pct', 0.95),
        }
    
    def evaluate_fitness(self, individual):
        """Fitness = Sharpe ratio"""
        try:
            strategy = HybridAdaptiveStrategyV2(individual)
            trades, metrics = strategy.backtest(self.df)
            
            if metrics['total_trades'] < 120:
                return -1000.0, metrics['total_trades']
            
            return metrics['sharpe_ratio'], metrics['total_trades']
        except:
            return -999.0, 0
    
    def crossover(self, parent1, parent2):
        """Breed two parents"""
        child = {}
        for key in parent1:
            child[key] = parent1[key] if random.random() > 0.5 else parent2[key]
        return child
    
    def mutate(self, individual):
        """Random mutation"""
        if random.random() < self.mutation_rate:
            mutation_gene = random.choice(['rsi_entry', 'rsi_exit', 'max_hold_bars', 'vol_min_pct'])
            
            if mutation_gene == 'rsi_entry':
                individual[mutation_gene] = max(20, min(45, individual[mutation_gene] + random.randint(-5, 5)))
            elif mutation_gene == 'rsi_exit':
                individual[mutation_gene] = max(60, min(85, individual[mutation_gene] + random.randint(-5, 5)))
            elif mutation_gene == 'max_hold_bars':
                individual[mutation_gene] = max(5, min(18, individual[mutation_gene] + random.randint(-3, 3)))
            elif mutation_gene == 'vol_min_pct':
                individual[mutation_gene] = max(0.001, min(0.020, individual[mutation_gene] + random.uniform(-0.002, 0.002)))
        
        return individual
    
    def optimize(self, n_generations=20):
        """Run genetic algorithm"""
        print(f"\n[Genetic] Optimizing {self.symbol}...")
        
        population = [self.create_individual() for _ in range(self.population_size)]
        
        best_overall_sharpe = -999
        best_overall_params = None
        best_overall_trades = 0
        
        for generation in range(n_generations):
            # Evaluate all
            fitness_scores = []
            for individual in population:
                fitness, trades = self.evaluate_fitness(individual)
                fitness_scores.append((individual, fitness, trades))
            
            # Sort by fitness
            fitness_scores.sort(key=lambda x: x[1], reverse=True)
            
            # Track best
            if fitness_scores[0][1] > best_overall_sharpe:
                best_overall_sharpe = fitness_scores[0][1]
                best_overall_params = fitness_scores[0][0].copy()
                best_overall_trades = fitness_scores[0][2]
            
            # Selection - keep top half
            survivors = [ind for ind, _, _ in fitness_scores[:len(fitness_scores)//2]]
            
            # Crossover and mutation
            new_population = survivors.copy()
            while len(new_population) < self.population_size:
                parent1, parent2 = random.sample(survivors, 2)
                child = self.crossover(parent1, parent2)
                child = self.mutate(child)
                new_population.append(child)
            
            population = new_population
        
        print(f"  Best: Sharpe={best_overall_sharpe:.3f}, Trades={best_overall_trades}")
        
        return {
            'method': 'Genetic',
            'symbol': self.symbol,
            'best_sharpe': best_overall_sharpe,
            'best_trades': best_overall_trades,
            'best_params': best_overall_params
        }

# ============================================================================
# METHOD 3: HOURLY SEASONALITY
# ============================================================================

class SeasonalityOptimizer:
    """Optimize trading hours per symbol"""
    
    def __init__(self, symbol, df, initial_params):
        self.symbol = symbol
        self.df = df.copy()
        self.initial_params = initial_params
    
    def analyze_hourly_patterns(self):
        """Find optimal trading hours"""
        self.df['hour'] = self.df['datetime'].dt.hour
        
        hourly_performance = {}
        
        for hour in range(9, 16):
            hour_data = self.df[self.df['hour'] == hour]
            
            if len(hour_data) < 30:
                continue
            
            returns = hour_data['close'].pct_change()
            
            hourly_performance[hour] = {
                'avg_return': returns.mean(),
                'volatility': returns.std(),
                'sharpe': returns.mean() / (returns.std() + 1e-10),
                'samples': len(hour_data)
            }
        
        # Rank hours by Sharpe
        ranked_hours = sorted(
            hourly_performance.items(),
            key=lambda x: x[1]['sharpe'],
            reverse=True
        )
        
        return [h for h, _ in ranked_hours[:5]], hourly_performance
    
    def optimize(self):
        """Optimize with best trading hours"""
        print(f"\n[Seasonality] Optimizing {self.symbol}...")
        
        best_hours, _ = self.analyze_hourly_patterns()
        
        # Test different hour combinations
        best_sharpe = -999
        best_params = None
        best_trades = 0
        
        hour_combos = [
            best_hours[:3],
            best_hours[:4],
            best_hours[:5],
            [9, 10, 11, 12, 13, 14],  # all
        ]
        
        for hours in hour_combos:
            params = self.initial_params.copy()
            params['allowed_hours'] = hours
            
            try:
                strategy = HybridAdaptiveStrategyV2(params)
                trades, metrics = strategy.backtest(self.df)
                
                if metrics['total_trades'] >= 120 and metrics['sharpe_ratio'] > best_sharpe:
                    best_sharpe = metrics['sharpe_ratio']
                    best_params = params.copy()
                    best_trades = metrics['total_trades']
            except:
                pass
        
        print(f"  Best: Sharpe={best_sharpe:.3f}, Trades={best_trades}")
        
        return {
            'method': 'Seasonality',
            'symbol': self.symbol,
            'best_sharpe': best_sharpe,
            'best_trades': best_trades,
            'best_params': best_params,
            'optimal_hours': best_params.get('allowed_hours', []) if best_params else []
        }

# ============================================================================
# METHOD 4: DEEP OPTUNA
# ============================================================================

class DeepOptunaOptimizer:
    """Extended Optuna with wider search space"""
    
    def __init__(self, symbol, df, initial_params):
        self.symbol = symbol
        self.df = df
        self.initial_params = initial_params
    
    def objective(self, trial):
        """Expanded parameter space"""
        params = {
            'rsi_period': trial.suggest_int('rsi_period', 2, 5),
            'rsi_entry': trial.suggest_int('rsi_entry', 20, 45),
            'rsi_exit': trial.suggest_int('rsi_exit', 60, 85),
            'max_hold_bars': trial.suggest_int('max_hold', 5, 18),
            'vol_min_pct': trial.suggest_float('vol_min', 0.002, 0.015),
            'ker_period': trial.suggest_int('ker_period', 8, 15),
            'position_size_pct': trial.suggest_float('position_size', 0.85, 0.95),
            'use_adaptive_hold': trial.suggest_categorical('adaptive_hold', [True, False]),
        }
        
        try:
            strategy = HybridAdaptiveStrategyV2(params)
            trades, metrics = strategy.backtest(self.df)
            
            if metrics['total_trades'] < 125:
                return float('-inf')
            
            return metrics['sharpe_ratio']
        except:
            return float('-inf')
    
    def optimize(self, n_trials=100):
        """Run deep Optuna search"""
        print(f"\n[DeepOptuna] Optimizing {self.symbol} ({n_trials} trials)...")
        
        optuna.logging.set_verbosity(optuna.logging.WARNING)
        
        study = optuna.create_study(
            direction='maximize',
            sampler=optuna.samplers.TPESampler(seed=42)
        )
        
        study.optimize(self.objective, n_trials=n_trials, show_progress_bar=False)
        
        best_sharpe = study.best_value
        best_params = {**self.initial_params, **study.best_params}
        
        # Get trade count
        strategy = HybridAdaptiveStrategyV2(best_params)
        trades, metrics = strategy.backtest(self.df)
        
        print(f"  Best: Sharpe={best_sharpe:.3f}, Trades={metrics['total_trades']}")
        
        return {
            'method': 'DeepOptuna',
            'symbol': self.symbol,
            'best_sharpe': best_sharpe,
            'best_trades': metrics['total_trades'],
            'best_params': best_params
        }

# ============================================================================
# METHOD 5: PARAMETER EXPANSION GRID
# ============================================================================

class GridExpansionOptimizer:
    """Exhaustive grid search with expanded ranges"""
    
    def __init__(self, symbol, df, initial_params):
        self.symbol = symbol
        self.df = df
        self.initial_params = initial_params
    
    def optimize(self, max_iterations=150):
        """Run grid search"""
        print(f"\n[GridExpansion] Optimizing {self.symbol}...")
        
        best_sharpe = -999
        best_params = None
        best_trades = 0
        
        iteration = 0
        for rsi_entry in range(22, 40, 3):
            for rsi_exit in range(62, 82, 3):
                for max_hold in range(6, 16, 2):
                    for vol_min in [0.003, 0.005, 0.007, 0.009]:
                        if iteration >= max_iterations:
                            break
                        
                        params = self.initial_params.copy()
                        params['rsi_entry'] = rsi_entry
                        params['rsi_exit'] = rsi_exit
                        params['max_hold_bars'] = max_hold
                        params['vol_min_pct'] = vol_min
                        
                        try:
                            strategy = HybridAdaptiveStrategyV2(params)
                            trades, metrics = strategy.backtest(self.df)
                            
                            if metrics['total_trades'] >= 125 and metrics['sharpe_ratio'] > best_sharpe:
                                best_sharpe = metrics['sharpe_ratio']
                                best_params = params.copy()
                                best_trades = metrics['total_trades']
                        except:
                            pass
                        
                        iteration += 1
        
        print(f"  Best: Sharpe={best_sharpe:.3f}, Trades={best_trades}")
        
        return {
            'method': 'GridExpansion',
            'symbol': self.symbol,
            'best_sharpe': best_sharpe,
            'best_trades': best_trades,
            'best_params': best_params
        }

# ============================================================================
# METHOD 6: ENSEMBLE VOTING
# ============================================================================

class EnsembleOptimizer:
    """Optimize ensemble voting parameters"""
    
    def __init__(self, symbol, df, initial_params):
        self.symbol = symbol
        self.df = df
        self.initial_params = initial_params
    
    def optimize(self):
        """Optimize ensemble"""
        print(f"\n[Ensemble] Optimizing {self.symbol}...")
        
        best_sharpe = -999
        best_params = None
        best_trades = 0
        
        # Test different voting thresholds
        for n_variants in [3, 5, 7]:
            for min_agreement in range(2, n_variants):
                params = {k: v for k, v in self.initial_params.items() if k != '_strategy'}
                
                try:
                    strategy = EnsembleStrategy(params, n_variants=n_variants, min_agreement=min_agreement)
                    trades, metrics = strategy.backtest(self.df)
                    
                    if metrics['total_trades'] >= 120 and metrics['sharpe_ratio'] > best_sharpe:
                        best_sharpe = metrics['sharpe_ratio']
                        best_params = params.copy()
                        best_params['n_variants'] = n_variants
                        best_params['min_agreement'] = min_agreement
                        best_trades = metrics['total_trades']
                except:
                    pass
        
        print(f"  Best: Sharpe={best_sharpe:.3f}, Trades={best_trades}")
        
        return {
            'method': 'Ensemble',
            'symbol': self.symbol,
            'best_sharpe': best_sharpe,
            'best_trades': best_trades,
            'best_params': best_params
        }

# ============================================================================
# METHOD 7: ADAPTIVE HOLD OPTIMIZER
# ============================================================================

class AdaptiveHoldOptimizer:
    """Optimize adaptive hold period parameters"""
    
    def __init__(self, symbol, df, initial_params):
        self.symbol = symbol
        self.df = df
        self.initial_params = initial_params
    
    def optimize(self):
        """Optimize adaptive hold parameters"""
        print(f"\n[AdaptiveHold] Optimizing {self.symbol}...")
        
        best_sharpe = -999
        best_params = None
        best_trades = 0
        
        for min_hold in [4, 5, 6]:
            for max_hold in [10, 12, 14, 16]:
                for vol_multiplier in [0.5, 1.0, 1.5, 2.0]:
                    params = self.initial_params.copy()
                    params['min_hold_bars'] = min_hold
                    params['max_hold_bars'] = max_hold
                    params['vol_hold_multiplier'] = vol_multiplier
                    params['use_adaptive_hold'] = True
                    
                    try:
                        strategy = HybridAdaptiveStrategyV2(params)
                        trades, metrics = strategy.backtest(self.df)
                        
                        if metrics['total_trades'] >= 120 and metrics['sharpe_ratio'] > best_sharpe:
                            best_sharpe = metrics['sharpe_ratio']
                            best_params = params.copy()
                            best_trades = metrics['total_trades']
                    except:
                        pass
        
        print(f"  Best: Sharpe={best_sharpe:.3f}, Trades={best_trades}")
        
        return {
            'method': 'AdaptiveHold',
            'symbol': self.symbol,
            'best_sharpe': best_sharpe,
            'best_trades': best_trades,
            'best_params': best_params
        }

# ============================================================================
# METHOD 8: KER REGIME OPTIMIZER
# ============================================================================

class KERRegimeOptimizer:
    """Optimize KER regime detection parameters"""
    
    def __init__(self, symbol, df, initial_params):
        self.symbol = symbol
        self.df = df
        self.initial_params = initial_params
    
    def optimize(self):
        """Optimize KER parameters"""
        print(f"\n[KERRegime] Optimizing {self.symbol}...")
        
        best_sharpe = -999
        best_params = None
        best_trades = 0
        
        for ker_period in [8, 10, 12, 15]:
            for ker_threshold in [0.20, 0.25, 0.30, 0.35, 0.40]:
                params = self.initial_params.copy()
                params['ker_period'] = ker_period
                params['ker_threshold'] = ker_threshold
                
                try:
                    strategy = HybridAdaptiveStrategyV2(params)
                    trades, metrics = strategy.backtest(self.df)
                    
                    if metrics['total_trades'] >= 120 and metrics['sharpe_ratio'] > best_sharpe:
                        best_sharpe = metrics['sharpe_ratio']
                        best_params = params.copy()
                        best_trades = metrics['total_trades']
                except:
                    pass
        
        print(f"  Best: Sharpe={best_sharpe:.3f}, Trades={best_trades}")
        
        return {
            'method': 'KERRegime',
            'symbol': self.symbol,
            'best_sharpe': best_sharpe,
            'best_trades': best_trades,
            'best_params': best_params
        }

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def run_all_optimizations():
    """Run all 8 methods on all symbols"""
    
    print("="*70)
    print("COMPREHENSIVE OPTIMIZATION SUITE")
    print(f"Start: {datetime.now().strftime('%H:%M:%S')}")
    print("="*70)
    
    # Load data
    data_cache = load_data()
    baseline, advanced = load_baseline_params()
    
    # Get baseline params for each symbol
    baseline_params = {}
    for symbol in SYMBOLS:
        if symbol in baseline:
            baseline_params[symbol] = baseline[symbol]['params']
        elif symbol in advanced.get('results', {}):
            baseline_params[symbol] = advanced['results'][symbol]['params']
        else:
            baseline_params[symbol] = {}
    
    # Store all results
    all_results = []
    
    # Methods to run
    methods = [
        ('SGD', SGDOptimizer, {'n_iterations': 20}),
        ('Genetic', GeneticAlgorithm, {'n_generations': 20}),
        ('Seasonality', SeasonalityOptimizer, {}),
        ('DeepOptuna', DeepOptunaOptimizer, {'n_trials': 80}),
        ('GridExpansion', GridExpansionOptimizer, {'max_iterations': 120}),
        ('Ensemble', EnsembleOptimizer, {}),
        ('AdaptiveHold', AdaptiveHoldOptimizer, {}),
        ('KERRegime', KERRegimeOptimizer, {}),
    ]
    
    # Run each method on each symbol
    for symbol in SYMBOLS:
        print(f"\n{'='*70}")
        print(f"SYMBOL: {symbol}")
        print(f"{'='*70}")
        
        df = data_cache[symbol]
        params = baseline_params[symbol]
        
        for method_name, method_class, config in methods:
            try:
                optimizer = method_class(symbol, df, params)
                
                if method_name == 'Seasonality':
                    result = optimizer.optimize()
                elif method_name == 'Ensemble':
                    result = optimizer.optimize()
                elif method_name == 'AdaptiveHold':
                    result = optimizer.optimize()
                elif method_name == 'KERRegime':
                    result = optimizer.optimize()
                else:
                    result = optimizer.optimize(**config)
                
                all_results.append(result)
                
            except Exception as e:
                print(f"  ERROR in {method_name}: {e}")
                all_results.append({
                    'method': method_name,
                    'symbol': symbol,
                    'best_sharpe': -999,
                    'error': str(e)
                })
    
    return all_results, baseline_params

def analyze_results(all_results, baseline_params):
    """Analyze and summarize results"""
    
    print("\n" + "="*70)
    print("RESULTS ANALYSIS")
    print("="*70)
    
    # Convert to DataFrame
    df = pd.DataFrame(all_results)
    
    # Get baseline sharpes
    baseline_sharpes = {
        'VBL': 1.574,
        'RELIANCE': 1.683,
        'SUNPHARMA': 3.132,
        'YESBANK': 1.036,
    }
    
    # Calculate improvements
    df['baseline_sharpe'] = df['symbol'].map(baseline_sharpes)
    df['improvement'] = df['best_sharpe'] - df['baseline_sharpe']
    
    # 1. Method ranking
    print("\n1. METHOD RANKING (by avg improvement):")
    method_stats = df.groupby('method').agg({
        'improvement': ['mean', 'max'],
        'best_sharpe': 'mean'
    }).round(3)
    print(method_stats.sort_values(('improvement', 'mean'), ascending=False))
    
    # 2. Best per symbol
    print("\n2. BEST METHOD PER SYMBOL:")
    best_per_symbol = {}
    for symbol in df['symbol'].unique():
        symbol_df = df[df['symbol'] == symbol]
        valid = symbol_df[symbol_df['best_sharpe'] > 0]
        if len(valid) > 0:
            best = valid.nlargest(1, 'best_sharpe').iloc[0]
            best_per_symbol[symbol] = best
            print(f"  {symbol:12s} → {best['method']:15s} Sharpe={best['best_sharpe']:.3f} (Δ{best['improvement']:+.3f})")
    
    # 3. Top 3 overall
    print("\n3. TOP 3 STRATEGIES:")
    top3 = df[df['best_sharpe'] > 0].nlargest(3, 'best_sharpe')
    for idx, row in top3.iterrows():
        print(f"  #{idx+1}: {row['method']} on {row['symbol']} = {row['best_sharpe']:.3f}")
    
    # 4. Optimized portfolio
    print("\n4. OPTIMIZED PORTFOLIO:")
    portfolio_sharpe = 0
    for symbol in SYMBOLS:
        if symbol in best_per_symbol:
            sharpe = best_per_symbol[symbol]['best_sharpe']
        else:
            sharpe = baseline_sharpes.get(symbol, 0)
        portfolio_sharpe += sharpe
        print(f"  {symbol:12s}: {sharpe:.3f}")
    
    # Add NIFTY (unchanged at 0.006)
    portfolio_sharpe += 0.006
    portfolio_sharpe /= 5
    
    print(f"\n  NEW PORTFOLIO SHARPE: {portfolio_sharpe:.3f}")
    print(f"  BASELINE:             1.486")
    print(f"  IMPROVEMENT:          {portfolio_sharpe - 1.486:+.3f}")
    
    return best_per_symbol, portfolio_sharpe

def generate_submission(best_per_symbol):
    """Generate optimized submission files"""
    
    print("\n" + "="*70)
    print("GENERATING SUBMISSION FILES")
    print("="*70)
    
    data_cache = load_data()
    
    all_trades = []
    
    for symbol, result in best_per_symbol.items():
        df = data_cache[symbol]
        params = result.get('best_params', {})
        
        if not params:
            continue
        
        try:
            # Check if ensemble
            if result['method'] == 'Ensemble':
                strategy = EnsembleStrategy(
                    params,
                    n_variants=params.get('n_variants', 5),
                    min_agreement=params.get('min_agreement', 3)
                )
            else:
                strategy = HybridAdaptiveStrategyV2(params)
            
            trades, metrics = strategy.backtest(df)
            
            symbol_codes = {
                'VBL': 'NSE:VBL-EQ',
                'RELIANCE': 'NSE:RELIANCE-EQ',
                'SUNPHARMA': 'NSE:SUNPHARMA-EQ',
                'YESBANK': 'NSE:YESBANK-EQ',
            }
            
            for trade in trades:
                all_trades.append({
                    'symbol': symbol_codes[symbol],
                    'entry_time': trade.get('entry_time', trade.get('entry_trade_time')),
                    'exit_time': trade.get('exit_time', trade.get('exit_trade_time')),
                    'entry_price': trade['entry_price'],
                    'exit_price': trade['exit_price'],
                    'qty': trade['qty'],
                })
            
            print(f"  {symbol}: {len(trades)} trades, Sharpe={metrics['sharpe_ratio']:.3f}")
            
        except Exception as e:
            print(f"  ERROR {symbol}: {e}")
    
    # Save best params
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    best_configs = {}
    for symbol, result in best_per_symbol.items():
        best_configs[symbol] = {
            'method': result['method'],
            'sharpe': result['best_sharpe'],
            'trades': result.get('best_trades', 0),
            'params': result.get('best_params', {})
        }
    
    with open(f'experiments/results/best_configs_{timestamp}.json', 'w') as f:
        json.dump(best_configs, f, indent=2, default=str)
    
    print(f"\n✅ Saved to experiments/results/best_configs_{timestamp}.json")
    
    return best_configs


def main():
    """Main execution"""
    
    # Run all optimizations
    all_results, baseline_params = run_all_optimizations()
    
    # Analyze
    best_per_symbol, portfolio_sharpe = analyze_results(all_results, baseline_params)
    
    # Generate submission
    best_configs = generate_submission(best_per_symbol)
    
    print("\n" + "="*70)
    print("OPTIMIZATION COMPLETE")
    print(f"End: {datetime.now().strftime('%H:%M:%S')}")
    print(f"Portfolio Sharpe: {portfolio_sharpe:.3f}")
    print("="*70)
    
    return all_results, best_per_symbol, portfolio_sharpe


if __name__ == '__main__':
    results, best, sharpe = main()
