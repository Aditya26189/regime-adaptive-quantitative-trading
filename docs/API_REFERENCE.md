# API Reference

## Overview

This document provides detailed API reference for the core modules and classes in the Algorithmic Trading Strategy Framework.

---

## Table of Contents

- [Strategies](#strategies)
- [Optimization](#optimization)
- [Utils](#utils)
- [Validation](#validation)
- [Configuration](#configuration)

---

## Strategies

### BaseStrategy

Abstract base class for all trading strategies.

```python
from src.strategies.base_strategy import BaseStrategy
```

#### Methods

##### `__init__(params: Dict)`

Initialize strategy with parameters.

**Parameters:**
- `params` (Dict): Strategy parameters

**Example:**
```python
strategy = MyStrategy(params={'rsi_period': 14})
```

##### `generate_signals(df: pd.DataFrame) -> pd.DataFrame`

Generate trading signals from market data.

**Parameters:**
- `df` (pd.DataFrame): Market data with columns ['date', 'close', 'volume']

**Returns:**
- pd.DataFrame: Data with additional 'signal' column (-1, 0, 1)

**Example:**
```python
signals = strategy.generate_signals(market_data)
```

##### `backtest(df: pd.DataFrame) -> Tuple[List[Dict], Dict[str, float]]`

Run backtest on historical data.

**Parameters:**
- `df` (pd.DataFrame): Historical market data

**Returns:**
- Tuple containing:
  - List[Dict]: List of trades
  - Dict[str, float]: Performance metrics

**Example:**
```python
trades, metrics = strategy.backtest(data)
print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
```

---

### HybridAdaptiveV2

Volatility-adaptive mean reversion strategy.

```python
from src.strategies.hybrid_adaptive_v2 import HybridAdaptiveV2
```

#### Parameters

```python
params = {
    'rsi_period': 2,          # RSI calculation period
    'rsi_entry': 30,          # RSI entry threshold
    'rsi_exit': 70,           # RSI exit threshold
    'max_hold': 10,           # Maximum holding period (hours)
    'vol_window': 20,         # Volatility calculation window
    'adaptive_enabled': True   # Enable adaptive holding
}
```

#### Example Usage

```python
# Initialize strategy
strategy = HybridAdaptiveV2(params={
    'rsi_period': 2,
    'rsi_entry': 30,
    'rsi_exit': 70,
    'max_hold': 10,
    'adaptive_enabled': True
})

# Load data
data = pd.read_csv('data/raw/SUNPHARMA.csv')

# Run backtest
trades, metrics = strategy.backtest(data)

# Print results
print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.3f}")
print(f"Total Trades: {metrics['total_trades']}")
print(f"Win Rate: {metrics['win_rate']:.2%}")
```

---

### EnhancedRegimeSwitching

Market regime detection with adaptive parameters.

```python
from src.strategies.enhanced_regime_strategy import EnhancedRegimeSwitchingStrategy
```

#### Parameters

```python
params = {
    'hurst_window': 100,      # Hurst exponent window
    'rsi_period': 2,          # RSI period
    'regime_threshold': 0.5,  # Regime detection threshold
    'max_hold': 12            # Maximum holding period
}
```

#### Methods

##### `calculate_hurst_exponent(series: pd.Series, window: int) -> pd.Series`

Calculate Hurst exponent for trend detection.

**Parameters:**
- `series` (pd.Series): Price series
- `window` (int): Rolling window size

**Returns:**
- pd.Series: Hurst exponent values (0-1)

**Interpretation:**
- H < 0.5: Mean-reverting regime
- H ≈ 0.5: Random walk
- H > 0.5: Trending regime

---

### AdaptiveBollingerStrategy

Dynamic Bollinger Bands with adaptive width.

```python
from src.strategies.adaptive_bb_strategy import AdaptiveBollingerStrategy
```

#### Parameters

```python
params = {
    'bb_period': 20,          # Bollinger Band period
    'bb_std': 2.0,            # Standard deviations
    'adaptive_factor': 1.5,   # Adaptation multiplier
    'vol_threshold': 0.02     # Volatility threshold
}
```

---

## Optimization

### optimize_strategy

Optimize strategy parameters using Bayesian optimization.

```python
from src.optimization.parallel_optimizer import optimize_strategy
```

#### Function Signature

```python
def optimize_strategy(
    strategy_name: str,
    symbol: str,
    n_trials: int = 300,
    n_jobs: int = -1,
    timeout: Optional[int] = None
) -> Dict
```

#### Parameters

- `strategy_name` (str): Name of strategy to optimize
- `symbol` (str): Symbol to optimize for
- `n_trials` (int): Number of optimization trials (default: 300)
- `n_jobs` (int): Number of parallel jobs (default: -1, use all cores)
- `timeout` (Optional[int]): Timeout in seconds

#### Returns

Dict containing:
- `best_params` (Dict): Optimal parameters
- `best_value` (float): Best objective value (Sharpe ratio)
- `n_trials` (int): Number of trials completed
- `study` (optuna.Study): Complete study object

#### Example

```python
results = optimize_strategy(
    strategy_name='hybrid_adaptive_v2',
    symbol='SUNPHARMA',
    n_trials=500,
    n_jobs=4
)

print(f"Best Sharpe: {results['best_value']:.3f}")
print(f"Best Parameters: {results['best_params']}")
```

---

### ParameterSpace

Define parameter search spaces for optimization.

```python
from src.optimization.parameter_space import PARAMETER_SPACES
```

#### Structure

```python
PARAMETER_SPACES = {
    'hybrid_adaptive_v2': {
        'rsi_period': [2, 3, 5],
        'rsi_entry': [25, 30, 35],
        'rsi_exit': [65, 70, 75],
        'max_hold': [8, 10, 12, 15],
        'vol_window': [10, 15, 20],
        'adaptive_enabled': [True, False]
    }
}
```

---

## Utils

### calculate_sharpe_ratio

Calculate Sharpe ratio from returns.

```python
from src.utils.metrics import calculate_sharpe_ratio
```

#### Function Signature

```python
def calculate_sharpe_ratio(
    returns: pd.Series,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252
) -> float
```

#### Parameters

- `returns` (pd.Series): Series of returns
- `risk_free_rate` (float): Annual risk-free rate (default: 0.0)
- `periods_per_year` (int): Trading periods per year (default: 252)

#### Returns

- float: Annualized Sharpe ratio

#### Example

```python
returns = pd.Series([0.01, 0.02, -0.01, 0.03, -0.005])
sharpe = calculate_sharpe_ratio(returns)
print(f"Sharpe Ratio: {sharpe:.2f}")
```

---

### calculate_max_drawdown

Calculate maximum drawdown.

```python
from src.utils.metrics import calculate_max_drawdown
```

#### Function Signature

```python
def calculate_max_drawdown(equity_curve: pd.Series) -> float
```

#### Parameters

- `equity_curve` (pd.Series): Cumulative equity curve

#### Returns

- float: Maximum drawdown (as decimal)

#### Example

```python
equity = pd.Series([100, 105, 103, 108, 95, 110])
max_dd = calculate_max_drawdown(equity)
print(f"Max Drawdown: {max_dd:.2%}")
```

---

### load_market_data

Load and preprocess market data.

```python
from src.utils.data_loader import load_market_data
```

#### Function Signature

```python
def load_market_data(
    symbol: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    cache: bool = True
) -> pd.DataFrame
```

#### Parameters

- `symbol` (str): Symbol name
- `start_date` (Optional[str]): Start date (YYYY-MM-DD)
- `end_date` (Optional[str]): End date (YYYY-MM-DD)
- `cache` (bool): Use cached data if available

#### Returns

- pd.DataFrame: Market data with columns ['date', 'close', 'volume']

#### Example

```python
data = load_market_data('SUNPHARMA', start_date='2020-01-01')
print(f"Loaded {len(data)} bars")
```

---

## Validation

### Rule12Validator

Validate Rule 12 compliance (Close/Volume only).

```python
from src.validation.rule12_validator import Rule12Validator
```

#### Methods

##### `validate(df: pd.DataFrame) -> Dict`

Check if data uses only Close and Volume.

**Parameters:**
- `df` (pd.DataFrame): Market data

**Returns:**
- Dict with keys:
  - `passed` (bool): Validation result
  - `violations` (List[str]): List of violations

**Example:**
```python
validator = Rule12Validator()
result = validator.validate(market_data)

if result['passed']:
    print("Rule 12 compliant!")
else:
    print("Violations:", result['violations'])
```

---

### TradeCountValidator

Validate minimum trade count requirement.

```python
from src.validation.trade_count_validator import TradeCountValidator
```

#### Methods

##### `validate(trades: List[Dict], minimum: int = 120) -> Dict`

Check if trade count meets requirements.

**Parameters:**
- `trades` (List[Dict]): List of trades
- `minimum` (int): Minimum required trades (default: 120)

**Returns:**
- Dict with validation results

---

## Configuration

### Settings

Global configuration settings.

```python
from config.settings import (
    SYMBOLS_CONFIG,
    BACKTEST_CONFIG,
    OPTIMIZATION_CONFIG
)
```

#### SYMBOLS_CONFIG

```python
SYMBOLS_CONFIG = {
    'SUNPHARMA': {
        'symbol': 'NSE:SUNPHARMA-EQ',
        'file': 'data/raw/NSE_SUNPHARMA_EQ_1hour.csv',
        'timeframe': '60',
        'type': 'mean_reverting'
    }
}
```

#### BACKTEST_CONFIG

```python
BACKTEST_CONFIG = {
    'initial_capital': 100000,
    'transaction_cost': 0.001,
    'slippage': 0.0005,
    'position_size': 1.0
}
```

#### OPTIMIZATION_CONFIG

```python
OPTIMIZATION_CONFIG = {
    'n_trials': 300,
    'n_jobs': -1,
    'timeout': 7200,
    'cv_folds': 3
}
```

---

## Error Handling

### Custom Exceptions

```python
from src.utils.exceptions import (
    TradingException,
    DataValidationError,
    StrategyExecutionError,
    OptimizationError
)
```

#### TradingException

Base exception for all trading-related errors.

```python
try:
    result = strategy.backtest(data)
except TradingException as e:
    logger.error(f"Trading error: {e}")
```

#### DataValidationError

Raised when data validation fails.

```python
try:
    validator.validate(data)
except DataValidationError as e:
    print(f"Data validation failed: {e}")
```

---

## Type Hints

Common type definitions used throughout the codebase.

```python
from typing import Dict, List, Tuple, Optional, Union
import pandas as pd
import numpy as np

# Type aliases
Params = Dict[str, Union[int, float, str, bool]]
Trade = Dict[str, Union[str, float, int]]
Metrics = Dict[str, float]
Signal = int  # -1, 0, or 1

# Function signature example
def backtest(
    data: pd.DataFrame,
    params: Params
) -> Tuple[List[Trade], Metrics]:
    pass
```

---

## Constants

Common constants used across the framework.

```python
from src.utils.constants import (
    TRADING_DAYS_PER_YEAR,
    HOURS_PER_DAY,
    MIN_TRADES_REQUIRED,
    TRANSACTION_COST,
    SLIPPAGE
)
```

### Available Constants

```python
TRADING_DAYS_PER_YEAR = 252
HOURS_PER_DAY = 24
MIN_TRADES_REQUIRED = 120
TRANSACTION_COST = 0.001  # 0.1%
SLIPPAGE = 0.0005  # 0.05%
```

---

## Examples

### Complete Backtesting Workflow

```python
from src.strategies.hybrid_adaptive_v2 import HybridAdaptiveV2
from src.utils.data_loader import load_market_data
from src.utils.metrics import calculate_sharpe_ratio, calculate_max_drawdown
from src.validation.validators import validate_all

# 1. Load data
data = load_market_data('SUNPHARMA')

# 2. Initialize strategy
strategy = HybridAdaptiveV2(params={
    'rsi_period': 2,
    'rsi_entry': 30,
    'rsi_exit': 70,
    'max_hold': 10
})

# 3. Run backtest
trades, metrics = strategy.backtest(data)

# 4. Validate results
validation = validate_all(trades, data)

# 5. Print results
print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.3f}")
print(f"Max Drawdown: {metrics['max_drawdown']:.2%}")
print(f"Total Trades: {len(trades)}")
print(f"Validation: {'PASSED' if validation['passed'] else 'FAILED'}")
```

---

## Version History

- **v1.0.0** (2026-01-19): Initial API documentation

---

*For more examples and tutorials, see the [User Guide](USER_GUIDE.md)*
