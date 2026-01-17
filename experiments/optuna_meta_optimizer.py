"""
Comprehensive Optuna Meta-Optimizer
Implements Bayesian optimization for:
1. Fixed Pairs Trading (Stock vs NIFTY) - Relaxed constraints
2. Fixed Volume Momentum - Relaxed constraints
3. SUNPHARMA Micro-Optimization (using HybridAdaptiveStrategyV2)
4. VBL+RELIANCE Ensemble (using EnsembleStrategy)

Target: Portfolio Sharpe > 2.0
"""

import optuna
import pandas as pd
import numpy as np
import json
from datetime import datetime
from typing import Dict, List, Tuple
import warnings
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.strategies.hybrid_adaptive_v2 import HybridAdaptiveStrategyV2
from src.strategies.ensemble_wrapper import EnsembleStrategy

warnings.filterwarnings('ignore')
optuna.logging.set_verbosity(optuna.logging.WARNING)

# 1. FIXED PAIRS TRADING STRATEGY (Relaxed)
class OptimizedPairsTradingStrategy:
    def __init__(self, params: Dict):
        self.params = params
        
    def calculate_beta(self, stock_close: pd.Series, nifty_close: pd.Series, window: int) -> pd.Series:
        stock_ret = stock_close.pct_change()
        nifty_ret = nifty_close.pct_change()
        cov = stock_ret.rolling(window).cov(nifty_ret)
        var = nifty_ret.rolling(window).var()
        return (cov / (var + 1e-10)).fillna(1.0)
    
    def calculate_zscore(self, series: pd.Series, window: int) -> pd.Series:
        return ((series - series.rolling(window).mean()) / (series.rolling(window).std() + 1e-10)).fillna(0)
    
    def backtest(self, symbol: str) -> float:
        try:
            # Load Data
            df_stock = pd.read_csv(f'data/raw/NSE_{symbol}_EQ_1hour.csv')
            df_nifty = pd.read_csv('data/raw/NSE_NIFTY50_INDEX_1hour.csv')
            
            # Merge
            df_stock['datetime'] = pd.to_datetime(df_stock['datetime'])
            df_nifty['datetime'] = pd.to_datetime(df_nifty['datetime'])
            df = pd.merge(df_stock[['datetime', 'close']], df_nifty[['datetime', 'close']], 
                         on='datetime', suffixes=('_stock', '_nifty'))
            
            # Indicators
            beta = self.calculate_beta(df['close_stock'], df['close_nifty'], self.params['beta_window'])
            # Normalized spread
            spread = (df['close_stock']/df['close_stock'].iloc[0]) - beta * (df['close_nifty']/df['close_nifty'].iloc[0])
            zscore = self.calculate_zscore(spread, self.params['beta_window'])
            
            # Strategy Logic
            entry_long = zscore < self.params['entry_z']
            exit_long = zscore > self.params['exit_z']
            
            # Trades
            trades = []
            capital = 100000
            position = 0
            entry_price = 0
            
            for i in range(len(df)):
                if entry_long.iloc[i] and position == 0:
                    price = df['close_stock'].iloc[i]
                    qty = int((capital - 24) * 0.95 / price)
                    if qty > 0:
                        position = qty
                        entry_price = price
                        capital -= 24
                elif exit_long.iloc[i] and position > 0:
                    price = df['close_stock'].iloc[i]
                    pnl = position * (price - entry_price) - 48
                    capital += pnl
                    trades.append(pnl)
                    position = 0
            
            # Relaxed constraint: 100 trades
            if len(trades) < 100: 
                return -999
                
            returns = pd.Series(trades) / 100000
            if returns.std() == 0: return 0
            return (returns.mean() / returns.std())
            
        except Exception:
            return -999

    @staticmethod
    def optimize(symbol: str, n_trials: int = 50):
        def objective(trial):
            params = {
                'beta_window': trial.suggest_int('beta_window', 20, 100),
                'entry_z': trial.suggest_float('entry_z', -2.5, -1.0), # Relaxed entry
                'exit_z': trial.suggest_float('exit_z', -0.5, 1.0),
            }
            return OptimizedPairsTradingStrategy(params).backtest(symbol)
        
        study = optuna.create_study(direction='maximize')
        study.optimize(objective, n_trials=n_trials)
        return study.best_params, study.best_value

# 2. FIXED VOLUME MOMENTUM STRATEGY (Relaxed)
class OptimizedVolumeMomentumStrategy:
    def __init__(self, params: Dict):
        self.params = params
        
    def calculate_vwma(self, close, volume, window):
        return (close * volume).rolling(window).sum() / (volume.rolling(window).sum() + 1e-10)
        
    def calculate_mfi(self, close, volume, window):
        delta = close.diff()
        pos = delta.where(delta > 0, 0) * volume
        neg = -delta.where(delta < 0, 0) * volume
        ratio = pos.rolling(window).sum() / (neg.rolling(window).sum() + 1e-10)
        return 100 - (100 / (1 + ratio))

    def backtest(self, symbol: str) -> float:
        try:
            df = pd.read_csv(f'data/raw/NSE_{symbol}_EQ_1hour.csv')
            df['datetime'] = pd.to_datetime(df['datetime'])
            
            vwma = self.calculate_vwma(df['close'], df['volume'], self.params['vwma_period'])
            mfi = self.calculate_mfi(df['close'], df['volume'], self.params['mfi_period'])
            
            # ENTRY: Close < VWMA (Value) AND MFI < Entry (Oversold)
            entry = (df['close'] < vwma) & (mfi < self.params['mfi_entry'])
            
            # EXIT: MFI > Exit OR Price > VWMA (Mean reversion)
            exit = (mfi > self.params['mfi_exit']) | (df['close'] > vwma * 1.01)
            
            trades = []
            capital = 100000
            position = 0
            entry_price = 0
            
            for i in range(50, len(df)):
                if entry.iloc[i] and position == 0:
                     price = df['close'].iloc[i]
                     qty = int((capital - 24) * 0.95 / price)
                     if qty > 0:
                         position = qty
                         entry_price = price
                         capital -= 24
                elif exit.iloc[i] and position > 0:
                    price = df['close'].iloc[i]
                    pnl = position * (price - entry_price) - 48
                    capital += pnl
                    trades.append(pnl)
                    position = 0
            
            if len(trades) < 100: return -999
            
            returns = pd.Series(trades) / 100000
            if returns.std() == 0: return 0
            return (returns.mean() / returns.std())
            
        except Exception:
            return -999

    @staticmethod
    def optimize(symbol: str, n_trials: int = 50):
        def objective(trial):
            params = {
                'vwma_period': trial.suggest_int('vwma_period', 10, 50),
                'mfi_period': trial.suggest_int('mfi_period', 5, 20), # Shorter MFI
                'mfi_entry': trial.suggest_int('mfi_entry', 20, 50), # Higher entry threshold
                'mfi_exit': trial.suggest_int('mfi_exit', 50, 80),
            }
            return OptimizedVolumeMomentumStrategy(params).backtest(symbol)
            
        study = optuna.create_study(direction='maximize')
        study.optimize(objective, n_trials=n_trials)
        return study.best_params, study.best_value

# 3. SUNPHARMA BOOSTER (Using HybridAdaptiveStrategyV2)
class SunpharmaBooster:
    @staticmethod
    def backtest(params):
        try:
            df = pd.read_csv('data/raw/NSE_SUNPHARMA_EQ_1hour.csv')
            df['datetime'] = pd.to_datetime(df['datetime'])
            df = df.sort_values('datetime').reset_index(drop=True)
            
            # Instantiate actual strategy
            strategy = HybridAdaptiveStrategyV2(params)
            trades, metrics = strategy.backtest(df)
            
            if metrics['total_trades'] < 120: return -999
            return metrics['sharpe_ratio']
        except Exception as e:
            return -999

    @staticmethod
    def optimize(n_trials=100):
        def objective(trial):
            # Optimize key parameters of HybridAdaptiveStrategyV2
            params = {
                'rsi_period': trial.suggest_int('rsi_period', 2, 4),
                'rsi_entry': trial.suggest_int('rsi_entry', 15, 35),
                'rsi_exit': trial.suggest_int('rsi_exit', 65, 85),
                'vol_min_pct': trial.suggest_float('vol_min_pct', 0.003, 0.008, step=0.001),
                'max_hold_bars': trial.suggest_int('max_hold_bars', 8, 15),
                'ker_period': trial.suggest_int('ker_period', 10, 20),
                'ker_threshold_meanrev': trial.suggest_float('ker_threshold_meanrev', 0.2, 0.4),
                'use_dynamic_rsi': False, # Keep simple for stability
                'use_profit_ladder': True, # Enable advanced feature
            }
            return SunpharmaBooster.backtest(params)
        
        study = optuna.create_study(direction='maximize')
        study.optimize(objective, n_trials=n_trials)
        return study.best_params, study.best_value

# 4. ENSEMBLE STRATEGY (VBL+RELIANCE)
class EnsembleOptimizer:
    @staticmethod
    def backtest(params, symbols):
        sharpes = []
        for symbol in symbols:
            try:
                df = pd.read_csv(f'data/raw/NSE_{symbol}_EQ_1hour.csv')
                df['datetime'] = pd.to_datetime(df['datetime'])
                df = df.sort_values('datetime').reset_index(drop=True)
                
                # Use EnsembleStrategy wrapper
                strategy = EnsembleStrategy(
                    base_params=params, 
                    n_variants=params.get('n_variants', 5),
                    min_agreement=params.get('min_agreement', 3)
                )
                trades, metrics = strategy.backtest(df)
                
                if metrics['total_trades'] < 120: 
                    sharpes.append(-999)
                else:
                    sharpes.append(metrics['sharpe_ratio'])
            except:
                sharpes.append(-999)
        
        # We want to maximize the WORST sharpe (safety) or AVERAGE?
        # Let's maximize AVERAGE but punish failures
        avg_sharpe = sum(sharpes) / len(sharpes)
        if any(s == -999 for s in sharpes): return -999
        return avg_sharpe

    @staticmethod
    def optimize(n_trials=50):
        def objective(trial):
            params = {
                'rsi_period': trial.suggest_int('rsi_period', 2, 4),
                'rsi_entry': trial.suggest_int('rsi_entry', 20, 40),
                'rsi_exit': trial.suggest_int('rsi_exit', 60, 80),
                'vol_min_pct': trial.suggest_float('vol_min_pct', 0.003, 0.006, step=0.001),
                'max_hold_bars': trial.suggest_int('max_hold_bars', 5, 12),
                'n_variants': 5,
                'min_agreement': trial.suggest_categorical('min_agreement', [2, 3])
            }
            return EnsembleOptimizer.backtest(params, ['VBL', 'RELIANCE'])
            
        study = optuna.create_study(direction='maximize')
        study.optimize(objective, n_trials=n_trials)
        return study.best_params, study.best_value

def main():
    print("="*60)
    print("OPTUNA META-OPTIMIZER RELOADED")
    print(f"Time: {datetime.now()}")
    print("="*60)
    
    results = {}
    
    # 30 trials for speed in agent mode, user can increase
    N_TRIALS = 30 
    
    # 1. Pairs Trading (Relaxed)
    print(f"\n[Pairs Trading - Relaxed] Optimizing ({N_TRIALS} trials)...")
    for symbol in ['VBL', 'RELIANCE', 'YESBANK', 'SUNPHARMA']:
        params, val = OptimizedPairsTradingStrategy.optimize(symbol, N_TRIALS)
        print(f"  {symbol}: Sharpe={val:.3f}")
        results[f'pairs_{symbol}'] = {'sharpe': val, 'params': params}

    # 2. Volume Momentum (Relaxed)
    print(f"\n[Volume Momentum - Relaxed] Optimizing ({N_TRIALS} trials)...")
    for symbol in ['VBL', 'RELIANCE', 'YESBANK', 'SUNPHARMA']:
        params, val = OptimizedVolumeMomentumStrategy.optimize(symbol, N_TRIALS)
        print(f"  {symbol}: Sharpe={val:.3f}")
        results[f'volume_{symbol}'] = {'sharpe': val, 'params': params}
        
    # 3. SUNPHARMA Booster
    print(f"\n[SUNPHARMA Booster] Optimizing ({N_TRIALS * 2} trials)...")
    params, val = SunpharmaBooster.optimize(N_TRIALS * 2)
    print(f"  SUNPHARMA Best: Sharpe={val:.3f}")
    results['sunpharma_boost'] = {'sharpe': val, 'params': params}
    
    # 4. Ensemble (VBL+RELIANCE)
    print(f"\n[VBL+RELIANCE Ensemble] Optimizing ({N_TRIALS} trials)...")
    params, val = EnsembleOptimizer.optimize(N_TRIALS)
    print(f"  Ensemble Avg Sharpe={val:.3f}")
    results['ensemble'] = {'sharpe': val, 'params': params}
    
    # Save
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    path = f'experiments/results/optuna_meta_optimization_reloaded_{timestamp}.json'
    Path('experiments/results').mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        json.dump(results, f, indent=2)
        
    print(f"\nSaved to {path}")

if __name__ == "__main__":
    main()
