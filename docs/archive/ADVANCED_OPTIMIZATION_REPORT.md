# Advanced Sharpe Optimization: Complete Technical Report

## Executive Summary

This document details the implementation, analytics, and results of an advanced portfolio optimization initiative that improved the **Portfolio Sharpe Ratio from 1.268 to 1.573 (+24%)**.

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Portfolio Sharpe** | 1.268 | **1.573** | +0.305 |
| Best Symbol (SUNPHARMA) | 1.84 | **3.32** | +1.48 |
| Total Trades | 646 | 629 | -17 |
| All Symbols ≥ 120 Trades | ✅ | ✅ | Maintained |

---

## Table of Contents

1. [Problem Statement](#problem-statement)
2. [Baseline Analysis](#baseline-analysis)
3. [Techniques Implemented](#techniques-implemented)
   - [Technique 1: Dynamic Position Sizing](#technique-1-dynamic-position-sizing-kelly-criterion)
   - [Technique 2: Multi-Timeframe Confluence](#technique-2-multi-timeframe-confluence)
   - [Technique 3: Profit Taking Ladders](#technique-3-profit-taking-ladders)
   - [Technique 4: Adaptive Hold Periods](#technique-4-adaptive-hold-periods)
   - [Technique 5: Dynamic RSI Bands](#technique-5-dynamic-rsi-bands)
4. [Implementation Details](#implementation-details)
5. [Optimization Methodology](#optimization-methodology)
6. [Results Analysis](#results-analysis)
7. [Per-Symbol Study](#per-symbol-study)
8. [Lessons Learned](#lessons-learned)
9. [Files Created](#files-created)

---

## Problem Statement

### Initial Challenge
- **Baseline Sharpe:** 1.268 (already optimized through previous phases)
- **Target Sharpe:** 1.40+ (aggressive target: 1.85-2.00)
- **Hard Constraints:**
  - Minimum 120 trades per symbol
  - Only close prices allowed (Rule 12)
  - ₹48 transaction cost per round-trip
  - Maximum 5% return cap per trade

### Key Insight During Diagnosis
During baseline measurement, a critical regression was discovered:

| Symbol | Expected | Actual | Issue |
|--------|----------|--------|-------|
| VBL | 1.574 | 1.161 | ❌ Wrong strategy used |

**Root Cause:** The baseline script was using `HybridAdaptiveStrategy` (single) instead of `EnsembleStrategy` for VBL. This was immediately fixed.

---

## Baseline Analysis

### Correct Baseline (After Fix)

```
🔍 Measuring CORRECT baseline (Ensemble for VBL)...
VBL: Sharpe=1.574, Trades=127 [ENSEMBLE]
RELIANCE: Sharpe=1.644, Trades=121 [SINGLE]
SUNPHARMA: Sharpe=1.840, Trades=144 [SINGLE]
YESBANK: Sharpe=1.278, Trades=122 [SINGLE]
NIFTY50: Sharpe=0.006, Trades=132 [TREND]

🎯 CORRECT BASELINE PORTFOLIO SHARPE: 1.268
```

### Strategy Allocation Pre-Optimization

| Symbol | Strategy Type | Justification |
|--------|---------------|---------------|
| NIFTY50 | Trend Following | Indices trend, don't mean-revert |
| VBL | Ensemble (5-variant) | High volatility needs consensus voting |
| RELIANCE | Hybrid Adaptive | Balance of trend/mean-rev |
| SUNPHARMA | Hybrid Adaptive | Strong mean-reversion characteristics |
| YESBANK | Hybrid Adaptive | Mixed regime behavior |

---

## Techniques Implemented

### Technique 1: Dynamic Position Sizing (Kelly Criterion)

**File:** `src/utils/position_sizing.py`

**Theory:**
The Kelly Criterion determines optimal bet sizing based on edge and odds:

```
f* = (p × b - q) / b

where:
  p = win probability
  b = win/loss ratio  
  q = 1 - p (loss probability)
  f* = fraction of capital to bet
```

**Implementation:**

```python
def calculate_dynamic_position_size(capital, close_price, volatility,
                                   win_rate, avg_win, avg_loss, 
                                   max_risk_pct=2.0, kelly_fraction=0.5):
    # Kelly calculation
    b = abs(avg_win / max(avg_loss, 1))
    q = 1 - win_rate
    kelly_full = (win_rate * b - q) / b
    
    # Use half-Kelly for safety (full Kelly is too aggressive)
    safe_kelly = kelly_full * kelly_fraction
    safe_kelly = max(0.10, min(safe_kelly, 0.50))  # 10-50% bounds
    
    # Volatility adjustment: reduce position in high-vol environments
    normal_vol = 0.01  # 1% baseline
    vol_scalar = min(1.0, normal_vol / max(volatility, 0.001))
    vol_scalar = max(0.3, vol_scalar)  # Never below 30%
    
    # Combined position fraction
    position_fraction = safe_kelly * vol_scalar
    
    return int((capital * position_fraction) / close_price)
```

**Key Features:**
1. **Rolling Performance Tracking:** Uses last 20 trades to calculate win rate
2. **Half-Kelly Safety:** Full Kelly is mathematically optimal but high variance
3. **Volatility Scaling:** Reduces position size when market is chaotic
4. **Risk Limits:** Never risks more than 2% per trade

**Expected Impact:** +0.18 to +0.25 Sharpe
**Actual Impact:** Marginal gains when combined with other techniques

---

### Technique 2: Multi-Timeframe Confluence

**File:** `src/utils/multi_timeframe.py`

**Theory:**
Higher timeframe trends act as a filter for lower timeframe entries. Trading in the direction of the daily trend reduces whipsaws.

**Implementation:**

```python
def calculate_daily_bias(hourly_df, ema_period=50):
    # Resample hourly → daily
    daily = hourly_df.groupby('date').agg({'close': 'last'})
    
    # Calculate daily EMA
    daily['ema'] = daily['close'].ewm(span=ema_period).mean()
    
    # Classify bias
    daily['daily_bias'] = 'NEUTRAL'
    daily.loc[daily['close'] > daily['ema'], 'daily_bias'] = 'BULLISH'
    daily.loc[daily['close'] < daily['ema'], 'daily_bias'] = 'BEARISH'
    
    # Strong bias if price significantly above/below EMA
    pct_diff = (daily['close'] - daily['ema']) / daily['ema'] * 100
    daily.loc[pct_diff > 1.5, 'daily_bias'] = 'STRONG_BULL'
    daily.loc[pct_diff < -1.5, 'daily_bias'] = 'STRONG_BEAR'
    
    return hourly_df.merge(daily[['daily_bias']], on='date')
```

**Signal Filtering Logic:**

```python
# Only take LONG signals when daily is bullish
if require_daily_bias:
    bullish = df['daily_bias'].isin(['BULLISH', 'STRONG_BULL'])
    df['signal_long_meanrev'] = df['signal_long_meanrev'] & bullish
```

**Expected Impact:** +0.12 to +0.18 Sharpe
**Trade-off:** Reduces trade count by 15-20%

---

### Technique 3: Profit Taking Ladders

**File:** `src/utils/profit_ladder.py`

**Theory:**
Instead of all-or-nothing exits, scale out in tranches to:
- Lock in profits early (if trade reverses, you kept 33%)
- Ride winners longer (remaining 67% catches full move)
- Reduce regret ("sold too early" or "held too long")

**Implementation:**

```python
class PositionManager:
    def __init__(self, total_qty, entry_price):
        self.total_qty = total_qty
        self.remaining_qty = total_qty
        self.entry_price = entry_price
        self.partial_exits = []
    
    def scale_out(self, exit_fraction, exit_price, exit_time, reason, fee=24):
        exit_qty = int(self.remaining_qty * exit_fraction)
        if exit_qty <= 0:
            return 0, 0.0
        
        self.remaining_qty -= exit_qty
        pnl = exit_qty * (exit_price - self.entry_price) - fee
        
        self.partial_exits.append({
            'qty': exit_qty,
            'price': exit_price,
            'time': exit_time,
            'reason': reason,
            'pnl': pnl
        })
        
        return exit_qty, pnl
```

**Ladder Configuration:**

| Tranche | RSI Trigger | Exit Fraction | Reason |
|---------|-------------|---------------|--------|
| 1st | RSI > 60 | 33% of position | Quick profit |
| 2nd | RSI > 75 | 50% of remaining | Target reached |
| 3rd | RSI > 85 or time | 100% remaining | Extended/final |

**Expected Impact:** +0.08 to +0.12 Sharpe
**Actual Behavior:** Smoother equity curve, similar total returns

---

### Technique 4: Adaptive Hold Periods

**File:** `src/utils/adaptive_hold.py`

**Theory:**
Fixed hold periods are suboptimal. Market volatility should dictate how long to hold:
- **High volatility:** Markets move fast → Exit quickly (5 bars)
- **Low volatility:** Markets are slow → Be patient (15 bars)

**Implementation:**

```python
def calculate_adaptive_max_hold(volatility, base_hold=10, vol_baseline=0.01,
                               min_hold=3, max_hold=20):
    vol_ratio = volatility / vol_baseline
    
    if vol_ratio > 2.0:       # Very high volatility
        hold = int(base_hold * 0.5)   # 5 bars
    elif vol_ratio > 1.5:     # High volatility
        hold = int(base_hold * 0.7)   # 7 bars
    elif vol_ratio < 0.5:     # Very low volatility
        hold = int(base_hold * 1.5)   # 15 bars
    elif vol_ratio < 0.75:    # Low volatility
        hold = int(base_hold * 1.25)  # 12 bars
    else:
        hold = base_hold              # 10 bars
    
    return max(min_hold, min(hold, max_hold))
```

**Expected Impact:** +0.10 to +0.15 Sharpe
**Actual Impact:** **Major contributor to SUNPHARMA's 3.32 Sharpe gain**

---

### Technique 5: Dynamic RSI Bands

**File:** `src/utils/indicators.py`

**Theory:**
Static RSI thresholds (30/70) don't adapt to changing market conditions:
- **High-volatility periods:** RSI swings wider → Need 20/85 bands
- **Low-volatility periods:** RSI stays tight → Need 35/65 bands

**Implementation:**

```python
def calculate_dynamic_rsi_bands(rsi_series, window=20, num_std=2.0,
                                lower_clip=(15, 45), upper_clip=(60, 95)):
    # Rolling statistics
    rsi_mean = rsi_series.rolling(window=window).mean()
    rsi_std = rsi_series.rolling(window=window).std()
    
    # Calculate bands
    lower_band = rsi_mean - (num_std * rsi_std)
    upper_band = rsi_mean + (num_std * rsi_std)
    
    # Clip to valid RSI range
    lower_band = lower_band.clip(lower=lower_clip[0], upper=lower_clip[1])
    upper_band = upper_band.clip(lower=upper_clip[0], upper=upper_clip[1])
    
    # Fill NaN with defaults during warmup
    lower_band = lower_band.fillna(30)
    upper_band = upper_band.fillna(70)
    
    return lower_band, upper_band
```

**Optuna Parameters:**
- `dynamic_rsi_window`: 15-30 bars
- `dynamic_rsi_std`: 1.5-2.5 standard deviations

---

## Implementation Details

### HybridAdaptiveStrategyV2

**File:** `src/strategies/hybrid_adaptive_v2.py`

This is the core strategy that integrates all 5 techniques:

```python
class HybridAdaptiveStrategyV2:
    def __init__(self, params):
        self.params = params
        # Feature flags
        self.use_dynamic_sizing = params.get('use_dynamic_sizing', False)
        self.use_profit_ladder = params.get('use_profit_ladder', False)
        self.use_adaptive_hold = params.get('use_adaptive_hold', False)
        self.use_multi_timeframe = params.get('use_multi_timeframe', False)
        self.use_dynamic_rsi = params.get('use_dynamic_rsi', False)
    
    def generate_signals(self, df):
        # 1. Apply multi-timeframe filter
        if self.use_multi_timeframe:
            df = calculate_daily_bias(df)
        
        # 2. Calculate RSI with optional dynamic bands
        if self.use_dynamic_rsi:
            df['rsi_lower'], df['rsi_upper'] = calculate_dynamic_rsi_bands(df['RSI'])
        
        # 3. Generate regime-specific signals
        # ... (KER-based regime detection)
        
        # 4. Filter by daily bias if enabled
        if self.use_multi_timeframe and self.params.get('require_daily_bias'):
            df['signal_long'] = df['signal_long'] & (df['daily_bias'] == 'BULLISH')
        
        return df
    
    def backtest(self, df, initial_capital=100000):
        # Entry with dynamic position sizing
        if self.use_dynamic_sizing:
            qty = calculate_dynamic_position_size(...)
        
        # Exit with profit ladder
        if self.use_profit_ladder:
            position_mgr = PositionManager(qty, entry_price)
            # Scale out at RSI thresholds
        
        # Exit with adaptive hold
        if self.use_adaptive_hold:
            adaptive_max = calculate_adaptive_max_hold(current_vol)
            if bars_held >= adaptive_max:
                exit_position()
```

---

## Optimization Methodology

### Optuna Framework

**File:** `optimize_advanced_techniques.py`

**Configuration:**
- **Sampler:** TPE (Tree-structured Parzen Estimator)
- **Trials:** 80 per symbol
- **Objective:** Maximize Sharpe Ratio directly

**Search Space:**

```python
def get_advanced_params(trial, baseline_params):
    params = baseline_params.copy()
    
    # Technique 1: Dynamic Sizing
    params['use_dynamic_sizing'] = trial.suggest_categorical('use_dynamic_sizing', [True, False])
    if params['use_dynamic_sizing']:
        params['kelly_fraction'] = trial.suggest_float('kelly_fraction', 0.3, 0.6)
        params['max_risk_pct'] = trial.suggest_float('max_risk_pct', 1.5, 3.0)
    
    # Technique 2: Multi-Timeframe
    params['use_multi_timeframe'] = trial.suggest_categorical('use_mtf', [True, False])
    
    # Technique 3: Profit Ladder
    params['use_profit_ladder'] = trial.suggest_categorical('use_ladder', [True, False])
    
    # Technique 4: Adaptive Hold
    params['use_adaptive_hold'] = trial.suggest_categorical('use_adaptive_hold', [True, False])
    
    # Technique 5: Dynamic RSI
    params['use_dynamic_rsi'] = trial.suggest_categorical('use_dynamic_rsi', [True, False])
    
    # Base parameters
    params['rsi_period'] = trial.suggest_int('rsi_period', 2, 4)
    params['max_hold_bars'] = trial.suggest_int('max_hold_bars', 6, 14)
    
    return params
```

**Hard Constraints in Objective:**

```python
def objective(trial, symbol, df, baseline_params, baseline_sharpe):
    params = get_advanced_params(trial, baseline_params)
    
    strategy = HybridAdaptiveStrategyV2(params)
    trades, metrics = strategy.backtest(df)
    
    # HARD CONSTRAINTS
    if metrics['total_trades'] < 120:
        return -1000.0  # Reject immediately
    
    if metrics['max_drawdown_pct'] < -25.0:
        return -500.0   # Excessive risk
    
    if metrics['sharpe_ratio'] < baseline_sharpe - 0.2:
        return -100.0   # Big regression
    
    return float(metrics['sharpe_ratio'])
```

---

## Results Analysis

### Per-Symbol Results

| Symbol | Baseline | Optimized | Change | Strategy | Key Features |
|--------|----------|-----------|--------|----------|--------------|
| **SUNPHARMA** | 1.840 | **3.323** | **+1.483** | Advanced V2 | Adaptive Hold |
| RELIANCE | 1.644 | 1.683 | +0.039 | Advanced V2 | Adaptive Hold |
| VBL | 1.574 | 1.574 | 0 | Ensemble | (unchanged) |
| YESBANK | 1.278 | 0.325 | -0.953 | **REJECTED** | Kept Baseline |
| NIFTY50 | 0.006 | 0.006 | 0 | Trend | (unchanged) |

### Portfolio Comparison

```
Before: (1.840 + 1.644 + 1.574 + 1.278 + 0.006) / 5 = 1.268
After:  (3.323 + 1.683 + 1.574 + 1.278 + 0.006) / 5 = 1.573
Change: +0.305 (+24%)
```

### YESBANK Failure Analysis

The optimization for YESBANK produced:
- **Sharpe:** 0.325 (down from 1.278)
- **Trades:** 124 (barely passed constraint)

**Root Cause:** YESBANK's price dynamics don't suit the advanced techniques:
- High noise-to-signal ratio
- Frequent regime changes
- The base Hybrid strategy already exploited its edge

**Decision:** Rejected V2 params, kept original baseline for YESBANK.

---

## Per-Symbol Study

### SUNPHARMA: The Star Performer (+1.48 Sharpe)

**Before:** Sharpe 1.84, 144 trades
**After:** Sharpe 3.32, 120 trades

**What Worked:**
1. **Adaptive Hold** was the key enabler
2. SUNPHARMA has clear volatility regimes
3. During low-vol consolidation → Hold longer for mean reversion
4. During high-vol swings → Exit quickly to lock gains

**Best Parameters Found:**
```json
{
  "use_adaptive_hold": true,
  "use_dynamic_sizing": false,
  "use_multi_timeframe": false,
  "use_profit_ladder": false,
  "use_dynamic_rsi": false,
  "max_hold_bars": 10
}
```

**Insight:** Sometimes the simplest technique is the most effective. SUNPHARMA didn't need complex ladders or multi-timeframe—just smarter hold timing.

---

### VBL: Protected by Ensemble

VBL was explicitly excluded from V2 optimization because:
1. Already at 1.574 Sharpe (excellent performance)
2. Ensemble voting is specifically designed for high-volatility stocks
3. Risk of regression too high

**Strategy:** 5-variant ensemble with 3-vote minimum agreement

---

### NIFTY50: The Challenge Continues

NIFTY50 remains at 0.006 Sharpe. Why?
1. Index behavior is fundamentally different from stocks
2. Mean reversion fails on indices (persistent trends)
3. The Trend Following strategy prevents losses but doesn't generate alpha

**Future Work:** Consider ADX-based trend strength filters

---

## Lessons Learned

### 1. Not All Techniques Work Everywhere
- Adaptive Hold: Excellent for SUNPHARMA, neutral for others
- Profit Ladder: Minimal impact across all symbols
- Multi-Timeframe: Reduced trade counts without proportional gain

### 2. Protect What Works
- VBL Ensemble was preserved (1.574 Sharpe)
- YESBANK baseline was preserved after V2 regression

### 3. Optuna's Value
- 80 trials per symbol found good combinations quickly
- TPE sampler efficiently explored the space
- Hard constraints prevented invalid solutions

### 4. The 120-Trade Constraint is Binding
- Many high-Sharpe configurations fail on trade count
- Had to balance quality vs quantity

---

## Files Created

### Utility Modules
| File | Purpose | Impact |
|------|---------|--------|
| `src/utils/position_sizing.py` | Kelly Criterion + Vol Scaling | Marginal |
| `src/utils/profit_ladder.py` | Scale-out exits | Marginal |
| `src/utils/adaptive_hold.py` | Volatility-based hold | **High** |
| `src/utils/multi_timeframe.py` | Daily bias filter | Low |

### Strategy Files
| File | Purpose |
|------|---------|
| `src/strategies/hybrid_adaptive_v2.py` | All techniques integrated |

### Optimization Scripts
| File | Purpose |
|------|---------|
| `baseline_measurement.py` | Measure correct baseline |
| `optimize_advanced_techniques.py` | Optuna optimizer |
| `generate_advanced_submission.py` | Final CSV generator |

### Output Files
| File | Purpose |
|------|---------|
| `baseline_metrics.json` | Starting point metrics |
| `advanced_optimization_results.json` | Per-symbol results |
| `output/23ME3EP03_advanced_submission_*.csv` | Final submission |

---

## Conclusion

The advanced optimization initiative successfully improved portfolio Sharpe from 1.268 to 1.573 (+24%). The key insight was that **Adaptive Hold Periods** alone drove most of the gains, particularly for SUNPHARMA which jumped from 1.84 to 3.32 Sharpe.

**Key Takeaways:**
1. Simple techniques often outperform complex ones
2. Symbol-specific optimization is essential
3. Protecting existing high performers is as important as improving others
4. The 120-trade constraint forces quality over quantity

**Final Portfolio:** 1.573 Sharpe, 629 trades, all constraints satisfied.
