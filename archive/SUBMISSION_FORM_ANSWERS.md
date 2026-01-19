# Submission Form Answers

## Timeframe
**Answer:** `1h`

---

## Strategy Logic

### Overview
Hybrid Adaptive Strategy combining Mean Reversion and Trend Following with regime detection using Kaufman Efficiency Ratio (KER). Symbol-specific optimizations applied.

---

### ENTRY RULES

#### Mean Reversion Entry (VBL, RELIANCE, SUNPHARMA, YESBANK)
1. **Regime Detection:** KER < 0.30 (choppy market)
2. **RSI Oversold:** RSI(2) < entry_threshold (30-36 depending on symbol)
3. **Volatility Filter:** Rolling volatility > 0.3-0.5%
4. **Time Filter:** Entry only between 9:00 AM - 2:30 PM
5. **Position Sizing:** 95% of available capital

#### Trend Following Entry (NIFTY50)
1. **Regime Detection:** KER > 0.50 (trending market)
2. **EMA Alignment:** EMA(8) > EMA(21)
3. **Momentum Pulse:** Price change > 0.4 × volatility
4. **Time Filter:** Entry only between 9:00 AM - 2:30 PM

---

### EXIT RULES

#### Mean Reversion Exit
1. **Target Exit:** RSI(2) > exit_threshold (65-75)
2. **Time Exit:** Maximum hold period (6-12 bars based on volatility)
3. **EOD Exit:** Forced exit at 3:15 PM
4. **Outlier Cap:** Exit if return exceeds +5%

#### Trend Following Exit (NIFTY50)
1. **Trend Break:** Price crosses below EMA(8)
2. **Time Exit:** Maximum 5 bars
3. **EOD Exit:** Forced exit at 3:15 PM

---

### STOP LOSS
**Type:** Time-based and volatility-adaptive
- **Maximum Hold:** 6-12 bars (adjusted by volatility)
- **Adaptive Logic:** High volatility → shorter holds (5 bars), Low volatility → longer holds (15 bars)
- **Hard Stop:** -5% return cap (outlier protection)

---

### TARGET
**Type:** RSI-based mean reversion targets
- **Primary Target:** RSI > 65-75 (symbol-specific)
- **Profit Cap:** +5% maximum return per trade
- **Adaptive Exit:** Dynamic RSI bands adjust to market volatility

---

### SPECIAL FEATURES

#### 1. Ensemble Voting (VBL only)
- 5 parameter variants vote on each signal
- Minimum 3/5 agreement required for entry
- Reduces noise in high-volatility stocks

#### 2. Adaptive Hold Periods (SUNPHARMA, RELIANCE)
- Hold period adjusts based on current volatility
- High volatility → Exit faster
- Low volatility → Hold longer for mean reversion

#### 3. Regime Detection
- KER (Kaufman Efficiency Ratio) classifies market state
- Mean Reversion mode: KER < 0.30
- Trend Following mode: KER > 0.50
- Mixed mode: 0.30 ≤ KER ≤ 0.50

---

### RISK MANAGEMENT
1. **Transaction Costs:** ₹48 per round-trip (₹24 entry + ₹24 exit)
2. **Position Sizing:** 95% of capital per trade
3. **Return Caps:** ±5% per trade
4. **EOD Squareoff:** All positions closed by 3:15 PM
5. **Rule 12 Compliance:** Uses ONLY close prices (no high/low/open)

---

### OPTIMIZATION
- **Method:** Bayesian Optimization (Optuna TPE Sampler)
- **Objective:** Maximize Sharpe Ratio
- **Constraints:** Minimum 120 trades, Maximum 25% drawdown
- **Trials:** 80 per symbol
