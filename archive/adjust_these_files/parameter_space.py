"""
PARAMETER SPACE DEFINITION FOR OPTUNA OPTIMIZATION

This file defines the search space for each strategy type.
Optuna will intelligently explore these ranges using Bayesian optimization.

Copilot Instructions:
- Each parameter has min/max bounds and distribution type
- Categorical parameters (like allowed_hours) use suggest_categorical
- Continuous parameters use suggest_float or suggest_int
"""

import optuna
from typing import Dict

class ParameterSpace:
    """
    Defines parameter search spaces for different strategy types.
    Symbol-specific configurations for optimal performance.
    """
    
    @staticmethod
    def get_mean_reversion_space(trial: optuna.Trial, symbol: str) -> Dict:
        """
        Parameter space for mean reversion strategies.
        Used for: SUNPHARMA, VBL (base params)
        
        Args:
            trial: Optuna trial object
            symbol: Symbol name for symbol-specific tuning
        
        Returns:
            Dictionary of parameters to test
        """
        # RSI thresholds (most critical parameters)
        rsi_entry = trial.suggest_int('rsi_entry', 15, 45, step=1)
        rsi_exit = trial.suggest_int('rsi_exit', 50, 95, step=1)
        
        # Ensure exit > entry (logical constraint)
        if rsi_exit <= rsi_entry + 10:
            rsi_exit = rsi_entry + 10
        
        # Volatility filter (symbol-specific ranges)
        if symbol == 'VBL':
            # VBL is high-volatility stock
            vol_min = trial.suggest_float('vol_min', 0.005, 0.015, log=True)
        elif symbol == 'SUNPHARMA':
            # SUNPHARMA is lower-volatility pharma stock
            vol_min = trial.suggest_float('vol_min', 0.002, 0.008, log=True)
        else:
            # Default range
            vol_min = trial.suggest_float('vol_min', 0.003, 0.012, log=True)
        
        # Time-of-day filter (categorical - can select multiple hours)
        # Optuna will try different combinations
        hour_combination = trial.suggest_categorical('hour_combo', [
            'morning_only',      # [9, 10]
            'morning_extended',  # [9, 10, 11]
            'full_day',          # [9, 10, 11, 12, 13]
            'skip_noon',         # [9, 10, 13]
            'skip_opening'       # [10, 11, 12]
        ])
        
        # Map to actual hours
        hour_mapping = {
            'morning_only': [9, 10],
            'morning_extended': [9, 10, 11],
            'full_day': [9, 10, 11, 12, 13],
            'skip_noon': [9, 10, 13],
            'skip_opening': [10, 11, 12]
        }
        allowed_hours = hour_mapping[hour_combination]
        
        # Hold period
        max_hold = trial.suggest_int('max_hold', 3, 15, step=1)
        
        # Risk management (Sharpe-focused)
        profit_target = trial.suggest_float('profit_target', 0.5, 2.5, step=0.1)
        stop_loss = trial.suggest_float('stop_loss', 0.3, 1.5, step=0.1)
        
        # Minimum reward:risk ratio
        min_rr = trial.suggest_float('min_rr', 1.0, 2.5, step=0.1)
        
        return {
            'rsi_entry': rsi_entry,
            'rsi_exit': rsi_exit,
            'vol_min': vol_min,
            'allowed_hours': allowed_hours,
            'max_hold': max_hold,
            'profit_target': profit_target,
            'stop_loss': stop_loss,
            'min_rr': min_rr
        }
    
    @staticmethod
    def get_trend_following_space(trial: optuna.Trial, symbol: str) -> Dict:
        """
        Parameter space for trend-following strategies.
        Used for: NIFTY50 (indices)
        
        Args:
            trial: Optuna trial object
            symbol: Symbol name
        
        Returns:
            Dictionary of parameters to test
        """
        # EMA periods (for trend detection)
        ema_fast = trial.suggest_int('ema_fast', 5, 12, step=1)
        ema_slow = trial.suggest_int('ema_slow', 15, 30, step=1)
        ema_trend = trial.suggest_int('ema_trend', 40, 60, step=1)
        
        # Ensure proper ordering: fast < slow < trend
        if ema_slow <= ema_fast:
            ema_slow = ema_fast + 5
        if ema_trend <= ema_slow:
            ema_trend = ema_slow + 10
        
        # Momentum thresholds
        momentum_threshold = trial.suggest_float('momentum_threshold', 0.2, 1.0, step=0.05)
        
        # Trend strength filter
        min_trend_strength = trial.suggest_float('min_trend_strength', 0.2, 0.7, step=0.05)
        
        # Time-of-day filter
        hour_combo = trial.suggest_categorical('hour_combo', [
            'morning_only',
            'morning_extended',
            'avoid_opening',
            'full_day'
        ])
        
        hour_mapping = {
            'morning_only': [9, 10],
            'morning_extended': [9, 10, 11],
            'avoid_opening': [10, 11, 12, 13],
            'full_day': [9, 10, 11, 12, 13]
        }
        allowed_hours = hour_mapping[hour_combo]
        
        # Hold period (indices need longer holds for trends to play out)
        max_hold = trial.suggest_int('max_hold', 5, 15, step=1)
        
        # Risk management (tighter for indices)
        profit_target = trial.suggest_float('profit_target', 0.8, 2.0, step=0.1)
        stop_loss = trial.suggest_float('stop_loss', 0.5, 1.2, step=0.1)
        
        return {
            'ema_fast': ema_fast,
            'ema_slow': ema_slow,
            'ema_trend': ema_trend,
            'momentum_threshold': momentum_threshold,
            'min_trend_strength': min_trend_strength,
            'allowed_hours': allowed_hours,
            'max_hold': max_hold,
            'profit_target': profit_target,
            'stop_loss': stop_loss
        }
    
    @staticmethod
    def get_hybrid_space(trial: optuna.Trial, symbol: str) -> Dict:
        """
        Parameter space for hybrid (regime-switching) strategies.
        Used for: RELIANCE, YESBANK
        
        Combines mean reversion + trend following parameters.
        """
        # Get base mean reversion params
        params = ParameterSpace.get_mean_reversion_space(trial, symbol)
        
        # Add regime detection parameters
        params['ker_period'] = trial.suggest_int('ker_period', 20, 40, step=5)
        params['ker_threshold_meanrev'] = trial.suggest_float('ker_threshold_meanrev', 0.15, 0.40, step=0.05)
        params['ker_threshold_trend'] = trial.suggest_float('ker_threshold_trend', 0.40, 0.70, step=0.05)
        
        # Ensure thresholds don't overlap
        if params['ker_threshold_trend'] <= params['ker_threshold_meanrev'] + 0.1:
            params['ker_threshold_trend'] = params['ker_threshold_meanrev'] + 0.1
        
        # Momentum parameters (for trending regime)
        params['momentum_threshold'] = trial.suggest_float('momentum_threshold', 0.3, 0.8, step=0.05)
        
        return params
    
    @staticmethod
    def get_ensemble_space(trial: optuna.Trial, symbol: str) -> Dict:
        """
        Parameter space for ensemble strategies.
        Used for: VBL (variance reduction)
        
        Returns:
            Base parameters + ensemble configuration
        """
        # Get base mean reversion params
        params = ParameterSpace.get_mean_reversion_space(trial, symbol)
        
        # Ensemble-specific parameters
        params['n_variants'] = trial.suggest_int('n_variants', 3, 7, step=1)
        params['min_agreement'] = trial.suggest_int('min_agreement', 2, 5, step=1)
        
        # Ensure min_agreement <= n_variants
        if params['min_agreement'] > params['n_variants']:
            params['min_agreement'] = params['n_variants'] - 1
        
        params['confidence_threshold'] = trial.suggest_float('confidence_threshold', 0.3, 0.7, step=0.05)
        
        # Diversity parameters (how different should variants be)
        params['diversity_rsi'] = trial.suggest_int('diversity_rsi', 3, 8, step=1)
        params['diversity_vol'] = trial.suggest_float('diversity_vol', 0.001, 0.004, step=0.0005)
        
        return params


class SymbolParameterMapper:
    """
    Maps symbols to their appropriate parameter spaces.
    This tells Optuna which search space to use for each symbol.
    """
    
    SYMBOL_STRATEGY_MAP = {
        'NSE:NIFTY50-INDEX': 'trend',       # Index → Trend following
        'NSE:VBL-EQ': 'ensemble',           # High-vol stock → Ensemble
        'NSE:SUNPHARMA-EQ': 'mean_reversion',  # Low-vol stock → Mean reversion
        'NSE:RELIANCE-EQ': 'hybrid',        # Balanced → Hybrid
        'NSE:YESBANK-EQ': 'hybrid'          # Volatile → Hybrid
    }
    
    @staticmethod
    def get_parameter_space(trial: optuna.Trial, symbol: str) -> Dict:
        """
        Get appropriate parameter space for symbol.
        
        Args:
            trial: Optuna trial
            symbol: Trading symbol
        
        Returns:
            Parameter dictionary for this trial
        """
        strategy_type = SymbolParameterMapper.SYMBOL_STRATEGY_MAP.get(symbol, 'mean_reversion')
        
        if strategy_type == 'trend':
            return ParameterSpace.get_trend_following_space(trial, symbol)
        elif strategy_type == 'ensemble':
            return ParameterSpace.get_ensemble_space(trial, symbol)
        elif strategy_type == 'hybrid':
            return ParameterSpace.get_hybrid_space(trial, symbol)
        else:
            return ParameterSpace.get_mean_reversion_space(trial, symbol)


# Example usage for Copilot autocomplete:
"""
import optuna
from parameter_space import SymbolParameterMapper

# Create Optuna study
study = optuna.create_study(direction='maximize')

# Define objective function
def objective(trial):
    symbol = 'NSE:NIFTY50-INDEX'
    params = SymbolParameterMapper.get_parameter_space(trial, symbol)
    
    # ... backtest with params ...
    # return sharpe_ratio
    
study.optimize(objective, n_trials=200)
"""
