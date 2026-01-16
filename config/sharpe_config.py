"""
Sharpe Optimization Configuration
Defines parameter search spaces for multi-objective optimization
"""

from typing import Dict, List, Tuple

class SharpeConfig:
    """
    Central configuration for Sharpe ratio optimization.
    All indicators are Close-only compliant (Rule 12).
    """
    
    # ===== GLOBAL SETTINGS =====
    STUDENT_ROLL_NUMBER = "23ME3EP03"
    STRATEGY_NUMBER = 1
    INITIAL_CAPITAL = 100000
    FEE_PER_ORDER = 24
    POSITION_SIZE_PCT = 0.95
    
    MIN_TRADES_REQUIRED = 120
    TARGET_AVG_SHARPE = 1.25
    MAX_OUTLIER_RETURN = 5.0  # Cap per-trade return at 5%
    
    # ===== DATA PATHS =====
    DATA_PATHS = {
        'NIFTY50': ('data/raw/NSE_NIFTY50_INDEX_1hour.csv', 'NSE:NIFTY50-INDEX'),
        'RELIANCE': ('data/raw/NSE_RELIANCE_EQ_1hour.csv', 'NSE:RELIANCE-EQ'),
        'VBL': ('data/raw/NSE_VBL_EQ_1hour.csv', 'NSE:VBL-EQ'),
        'YESBANK': ('data/raw/NSE_YESBANK_EQ_1hour.csv', 'NSE:YESBANK-EQ'),
        'SUNPHARMA': ('data/raw/NSE_SUNPHARMA_EQ_1hour.csv', 'NSE:SUNPHARMA-EQ'),
    }
    
    # ===== SYMBOL-SPECIFIC SEARCH SPACES =====
    
    # VBL: Star performer - maintain high return but cap outliers
    VBL_PARAMS = {
        'strategy_type': 'DYNAMIC_MEANREV',
        'rsi_period': [2, 3, 4],
        'rsi_entry_range': (35, 45),
        'rsi_exit_range': (90, 98),
        'vol_min_pct': [0.008, 0.010, 0.012, 0.014],
        'allowed_hours': [[9, 10], [9, 10, 11]],
        'max_hold_bars': [8, 10, 12],
        'use_dynamic_thresholds': [True, False],
        'dynamic_std_mult': [1.8, 2.0, 2.2],
    }
    
    # SUNPHARMA: Strong performer - fine-tune for consistency
    SUNPHARMA_PARAMS = {
        'strategy_type': 'DYNAMIC_MEANREV',
        'rsi_period': [2, 3],
        'rsi_entry_range': (38, 48),
        'rsi_exit_range': (55, 70),
        'vol_min_pct': [0.003, 0.004, 0.005],
        'allowed_hours': [[10, 11], [9, 10, 11]],
        'max_hold_bars': [6, 8, 10],
        'use_dynamic_thresholds': [True],
        'dynamic_std_mult': [1.8, 2.0],
    }
    
    # RELIANCE: Weak - needs hybrid approach
    RELIANCE_PARAMS = {
        'strategy_type': 'HYBRID',
        'ker_period': [8, 10, 12],
        'ker_threshold_meanrev': [0.25, 0.28, 0.30],
        'ker_threshold_trend': [0.45, 0.50],
        'rsi_period': [2, 3],
        'rsi_entry_range': (25, 35),
        'rsi_exit_range': (80, 92),
        'vol_min_pct': [0.004, 0.005, 0.006],
        'ema_fast': [5, 8],
        'ema_slow': [15, 21],
        'allowed_hours': [[9, 10], [9, 10, 11, 12]],
        'max_hold_bars': [4, 6, 8],
    }
    
    # YESBANK: Very weak - strict regime filtering + outlier capping
    YESBANK_PARAMS = {
        'strategy_type': 'HYBRID',
        'ker_period': [8, 10],
        'ker_threshold_meanrev': [0.20, 0.22, 0.25],
        'ker_threshold_trend': [0.50, 0.55],
        'rsi_period': [2, 3],
        'rsi_entry_range': (18, 28),
        'rsi_exit_range': (75, 88),
        'vol_min_pct': [0.004, 0.005, 0.006],
        'ema_fast': [5, 8],
        'ema_slow': [15, 21],
        'allowed_hours': [[9, 10, 11, 13]],
        'max_hold_bars': [1, 2, 3],
    }
    
    # NIFTY50: Negative Sharpe - MUST use trend-following
    NIFTY50_PARAMS = {
        'strategy_type': 'HYBRID',
        'ker_period': [10, 12, 15],
        'ker_threshold_meanrev': [0.18, 0.20, 0.22],  # Strict - rarely mean revert
        'ker_threshold_trend': [0.30, 0.35, 0.40],  # Lower - favor trends
        'rsi_period': [2, 3],
        'rsi_entry_range': (28, 35),
        'rsi_exit_range': (60, 72),
        'vol_min_pct': [0.006, 0.008, 0.010],
        'ema_fast': [5, 8, 10],
        'ema_slow': [18, 21, 26],
        'trend_pulse_mult': [0.3, 0.4, 0.5],
        'allowed_hours': [[9, 10, 11, 12, 13]],
        'max_hold_bars': [3, 5, 8],
    }
    
    # ===== OPTIMIZATION SETTINGS =====
    N_RANDOM_ITERATIONS = 300  # Balanced speed vs coverage
    
    # Multi-objective weights
    METRIC_WEIGHTS = {
        'sharpe_ratio': 0.50,
        'total_return': 0.20,
        'max_drawdown': 0.15,
        'win_rate': 0.10,
        'trade_count_penalty': 0.05,
    }
    
    @classmethod
    def get_symbol_config(cls, symbol: str) -> Dict:
        """Get parameter search space for a specific symbol"""
        symbol_map = {
            'VBL': cls.VBL_PARAMS,
            'SUNPHARMA': cls.SUNPHARMA_PARAMS,
            'RELIANCE': cls.RELIANCE_PARAMS,
            'YESBANK': cls.YESBANK_PARAMS,
            'NIFTY50': cls.NIFTY50_PARAMS,
        }
        return symbol_map.get(symbol, {})
    
    @classmethod
    def get_data_path(cls, symbol: str) -> Tuple[str, str]:
        """Get data file path and symbol code"""
        return cls.DATA_PATHS.get(symbol, ('', ''))

config = SharpeConfig()
