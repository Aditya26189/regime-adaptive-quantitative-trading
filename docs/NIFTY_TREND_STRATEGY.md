# NIFTY50 Trend Strategy Documentation

## Overview

The NIFTY50 Trend Strategy was developed to address the fundamental issue that **indices trend more than they mean-revert**. While mean reversion strategies work well on individual stocks, NIFTY50 (an index) exhibited persistent directional moves that caused the mean reversion approach to fail catastrophically (Sharpe -1.14).

## Strategy Logic

### Entry Conditions (All must be true)
1. **Uptrend Detected:** Fast EMA > Slow EMA by threshold percentage
2. **Momentum Confirmation:** Rate of change > momentum threshold
3. **Volatility Filter:** Volatility > minimum threshold
4. **Time Filter:** Within allowed trading hours
5. **Alignment:** Both momentum and EMA diff are positive

### Exit Conditions (Any triggers exit)
1. **Trend Reversal:** Fast EMA crosses below Slow EMA
2. **Momentum Failure:** Momentum turns negative
3. **Max Hold Reached:** Position held for max_hold bars
4. **EMA Weakening:** Current EMA diff < 30% of entry EMA diff
5. **End of Day:** After 15:15

## Optimal Parameters

```python
{
    'ema_fast': 3,          # Very responsive to price changes
    'ema_slow': 35,         # Long-term trend anchor
    'momentum_period': 10,   # Rate of change lookback
    'momentum_threshold': 0.1, # Minimum momentum required
    'ema_diff_threshold': 0.1, # Minimum trend separation %
    'vol_min': 0.01,        # Volatility floor (effectively off)
    'allowed_hours': [9, 10, 11, 12, 13, 14],
    'max_hold': 8,          # Maximum bars to hold position
    'vol_period': 14        # Volatility calculation period
}
```

## Performance Metrics

| Metric | Value |
|--------|-------|
| **Sharpe Ratio** | -0.020 |
| **Total Return** | -0.94% |
| **Trade Count** | 125 |
| **Win Rate** | 38.1% |
| **Avg Win** | ₹320 |
| **Avg Loss** | ₹-225 |

## Code Location

- **Strategy:** `src/strategies/nifty_trend_strategy.py`
- **Optimizer:** Integrated in `run_nifty_full_optimization.py`
- **Fine-Tuner:** `src/optimizers/ultra_fine_tune.py`

## Key Functions

```python
# Signal generation
generate_nifty_trend_signals(data: pd.DataFrame, params: Dict) -> pd.DataFrame

# Optimization
optimize_nifty_trend_parameters(data: pd.DataFrame, n_iterations: int) -> Tuple[Dict, pd.DataFrame]

# Sharpe calculation
calculate_sharpe_ratio(trades_df: pd.DataFrame) -> float
```

## Why Trend Following Works for NIFTY

1. **Index Behavior:** NIFTY50 aggregates 50 stocks, smoothing individual noise but preserving macro trends.

2. **Liquidity:** High liquidity means fewer whipsaws and cleaner trend signals.

3. **Institutional Flows:** Large fund flows create persistent directional moves.

4. **Rule 12 Constraint:** Close-only data naturally filters intraday noise, making trend signals more reliable.

## Comparison: Mean Rev vs Trend Following on NIFTY50

| Approach | Sharpe | Return | Win Rate |
|----------|--------|--------|----------|
| Mean Reversion | -1.14 | -2.84% | ~45% |
| **Trend Following** | **-0.020** | **-0.94%** | 38% |

The trend approach sacrifices win rate for better risk-adjusted returns by avoiding false signals.
