"""
PARAMETER SPACE DEFINITION FOR OPTUNA OPTIMIZATION

This file defines the search space for each strategy type.
Optuna will intelligently explore these ranges using Bayesian optimization.
"""

from typing import Dict, Any
import optuna


def get_nifty_params(trial: optuna.Trial) -> Dict[str, Any]:
    """
    NIFTY50 Trend Following Parameters
    Explores EMA combinations, momentum thresholds, and volatility filters.
    """
    return {
        # Trend detection logic
        'ema_fast': trial.suggest_int('ema_fast', 3, 20),
        'ema_slow': trial.suggest_int('ema_slow', 20, 100),
        
        # Momentum confirmation
        'momentum_period': trial.suggest_int('momentum_period', 5, 20),
        'momentum_threshold': trial.suggest_float('momentum_threshold', 0.05, 0.5),
        
        # Trend strength filter
        'ema_diff_threshold': trial.suggest_float('ema_diff_threshold', 0.01, 0.3),
        
        # Regime filter
        'vol_min': trial.suggest_float('vol_min', 0.0, 0.2),
        'vol_period': 14,
        
        # Risk management
        'max_hold': trial.suggest_int('max_hold', 3, 20),
        'allowed_hours': [9, 10, 11, 12, 13, 14],
    }


def get_vbl_params(trial: optuna.Trial) -> Dict[str, Any]:
    """
    VBL Mean Reversion / Ensemble Parameters
    Explores RSI settings and Ensemble configuration.
    """
    return {
        # RSI Core
        'rsi_period': trial.suggest_int('rsi_period', 2, 14),
        'rsi_oversold': trial.suggest_int('rsi_oversold', 10, 40),
        'rsi_overbought': trial.suggest_int('rsi_overbought', 60, 90),
        
        # Regime Detection (KER)
        'ker_period': trial.suggest_int('ker_period', 10, 30),
        'ker_threshold': trial.suggest_float('ker_threshold', 0.3, 0.8),
        
        # Volatility Filters
        'vol_min': trial.suggest_float('vol_min', 0.001, 0.02),
        'vol_max': trial.suggest_float('vol_max', 0.02, 0.10),
        
        # Exit rules
        'max_hold': trial.suggest_int('max_hold', 5, 20),
        
        # Ensemble Logic
        'use_ensemble': trial.suggest_categorical('use_ensemble', [True, False]),
        'n_variants': 5,
        'min_agreement': 3,
    }


def get_sunpharma_params(trial: optuna.Trial) -> Dict[str, Any]:
    """SUNPHARMA Mean Reversion Parameters"""
    return {
        'rsi_period': trial.suggest_int('rsi_period', 2, 7),
        'rsi_oversold': trial.suggest_int('rsi_oversold', 15, 35),
        'rsi_overbought': trial.suggest_int('rsi_overbought', 65, 85),
        'ker_period': trial.suggest_int('ker_period', 10, 20),
        'ker_threshold': trial.suggest_float('ker_threshold', 0.3, 0.7),
        'vol_min': trial.suggest_float('vol_min', 0.002, 0.015),
        'vol_max': trial.suggest_float('vol_max', 0.015, 0.05),
        'max_hold': trial.suggest_int('max_hold', 4, 15),
    }


def get_reliance_params(trial: optuna.Trial) -> Dict[str, Any]:
    """RELIANCE Hybrid Adaptive Parameters"""
    return {
        'rsi_period': trial.suggest_int('rsi_period', 2, 10),
        'rsi_oversold': trial.suggest_int('rsi_oversold', 15, 35),
        'rsi_overbought': trial.suggest_int('rsi_overbought', 65, 90),
        'ker_period': trial.suggest_int('ker_period', 8, 25),
        'ker_threshold': trial.suggest_float('ker_threshold', 0.2, 0.8),
        'vol_min': trial.suggest_float('vol_min', 0.002, 0.02),
        'vol_max': trial.suggest_float('vol_max', 0.015, 0.06),
        'max_hold': trial.suggest_int('max_hold', 5, 20),
    }


def get_yesbank_params(trial: optuna.Trial) -> Dict[str, Any]:
    """YESBANK Hybrid Parameters"""
    return {
        'rsi_period': trial.suggest_int('rsi_period', 2, 12),
        'rsi_oversold': trial.suggest_int('rsi_oversold', 10, 40),
        'rsi_overbought': trial.suggest_int('rsi_overbought', 60, 95),
        'ker_period': trial.suggest_int('ker_period', 8, 20),
        'ker_threshold': trial.suggest_float('ker_threshold', 0.2, 0.8),
        'vol_min': trial.suggest_float('vol_min', 0.001, 0.015),
        'vol_max': trial.suggest_float('vol_max', 0.015, 0.08),
        'max_hold': trial.suggest_int('max_hold', 3, 20),
    }


SYMBOL_PARAM_FUNCTIONS = {
    'NIFTY50': get_nifty_params,
    'VBL': get_vbl_params,
    'SUNPHARMA': get_sunpharma_params,
    'RELIANCE': get_reliance_params,
    'YESBANK': get_yesbank_params,
}
