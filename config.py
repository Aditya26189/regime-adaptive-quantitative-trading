"""
Configuration module for the quantitative trading infrastructure.

This module contains all configurable parameters for backtesting,
risk management, signal generation, and file paths.
"""


class Config:
    """
    Single source of truth for all trading system parameters.
    
    All parameters are class attributes for easy access without instantiation.
    Modify these values to tune the trading system's behavior.
    """
    
    # ==================== BACKTESTING PARAMETERS ====================
    
    # Initial cash for the portfolio (USD)
    INITIAL_CASH: float = 100000.0
    
    # Transaction fees (as decimal, e.g., 0.0002 = 2 basis points)
    MAKER_FEE: float = 0.0002  # Fee for limit orders (providing liquidity)
    TAKER_FEE: float = 0.0002  # Fee for market orders (taking liquidity)
    
    # ==================== RISK MANAGEMENT PARAMETERS ====================
    
    # Maximum allowed position (absolute value, in units)
    MAX_POSITION: int = 100
    
    # Maximum drawdown threshold (as decimal, e.g., 0.15 = 15%)
    # Trading halts when drawdown exceeds this threshold
    MAX_DRAWDOWN: float = 0.15
    
    # Volatility threshold for regime filtering
    # Don't trade when rolling volatility exceeds this value
    VOL_THRESHOLD: float = 0.01
    
    # Window size for volatility calculation (number of ticks)
    VOL_WINDOW: int = 100
    
    # ==================== SIGNAL PARAMETERS ====================
    
    # Default lookback window for signal calculations
    LOOKBACK_WINDOW: int = 20
    
    # Z-score thresholds for mean reversion strategy
    ENTRY_Z_THRESHOLD: float = 2.0  # Enter position when |z| > this
    EXIT_Z_THRESHOLD: float = 0.5   # Exit position when |z| < this
    
    # Order book imbalance threshold for flow-based signals
    OBI_THRESHOLD: float = 0.3
    
    # Moving average windows for momentum strategy
    FAST_MA_WINDOW: int = 5
    SLOW_MA_WINDOW: int = 20
    
    # ==================== FILE PATHS ====================
    
    # Directory for raw input data (CSV files)
    RAW_DATA_PATH: str = 'data/raw/'
    
    # Directory for processed/cleaned data
    PROCESSED_DATA_PATH: str = 'data/processed/'
    
    # Directory for results (metrics, plots, logs)
    RESULTS_PATH: str = 'results/'
    
    # ==================== METRICS PARAMETERS ====================
    
    # Periods per year for annualization
    # 252 trading days * 390 minutes per day for minute-level data
    PERIODS_PER_YEAR: int = 252 * 390
    
    # Risk-free rate for Sharpe calculation (annualized)
    RISK_FREE_RATE: float = 0.0
    
    # ==================== VISUALIZATION PARAMETERS ====================
    
    # Default DPI for saved plots
    PLOT_DPI: int = 150
    
    # Figure size (width, height) in inches
    FIGURE_SIZE: tuple = (12, 8)
