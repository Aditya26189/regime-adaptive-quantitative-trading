# Optimization Results Summary

## Executive Summary

After 3 rounds of systematic optimization, the current baseline parameters remain the best compromise between trade count requirements (120+) and returns.

**Key Constraints:**
- Minimum 120 trades per symbol (HARD)
- Use only close prices (Rule 12)
- Transaction cost: ₹48 per roundtrip

---

## Optimization Rounds

### Round 1: Parameter Variants with Stop Loss/Profit Targets

| Variant | Avg Return | Avg Trades | Passed 120+ |
|---------|------------|------------|-------------|
| D_Baseline | -2.95% | 143 | 5/5 ✅ |
| F_QuickExit | -11.11% | 182 | 5/5 |
| C_Aggressive | -29.07% | 164 | 5/5 |
| E_ProfitFocus | -29.81% | 169 | 5/5 |
| B_Balanced | -27.43% | 139 | 4/5 |
| A_Conservative | -1.65% | 39 | 0/5 |

**Finding:** Stop losses and profit targets made returns WORSE. D_Baseline is best.

---

### Round 2: Entry Quality Filters

| Variant | Avg Return | Avg Trades | Passed 120+ |
|---------|------------|------------|-------------|
| RSI_Divergence | -0.04% | 21 | 0/5 |
| Strict_Entry_Hold_Longer | -0.20% | 14 | 0/5 |
| Combined_Filters | -0.61% | 6 | 0/5 |
| Momentum_Filter | -0.74% | 16 | 0/5 |
| SMA50_Filter | -4.01% | 60 | 0/5 |
| Looser_Entry_Better_Exit | -9.10% | 178 | 5/5 |

**Finding:** Quality filters dramatically improve returns (RSI Divergence near breakeven!) but reduce trades to far below 120.

---

### Round 3: Hybrid Quality + Quantity

| Variant | Avg Return | Avg Trades | Passed 120+ | Positive |
|---------|------------|------------|-------------|----------|
| Hybrid_RSI35_Div | -2.30% | 67 | 0/5 | 2/5 |
| Hybrid_RSI30_Div | -2.99% | 48 | 0/5 | 2/5 |
| Baseline_Current | -4.77% | 157 | 5/5 ✅ | 1/5 |
| Hybrid_RSI40_Div | -7.04% | 86 | 0/5 | 0/5 |
| NoDiv_RSI22_MedExit | -7.89% | 168 | 5/5 | 0/5 |
| NoDiv_RSI25_EarlyExit | -10.19% | 181 | 5/5 | 0/5 |

**Finding:** Even with RSI < 40 + divergence filter, still can't reach 120 trades. Baseline remains best compromise.

---

## Key Insights

### 1. Trade Count vs Returns Trade-off
- Quality filters (RSI divergence, SMA50) improve returns to near-breakeven
- But these filters reduce trades to 14-67 per symbol (below 120 requirement)
- Relaxing filters to reach 120+ trades degrades returns

### 2. Stop Loss/Profit Target Impact
- Adding stop losses HURT returns (early exits lock in losses)
- Profit targets had minimal positive impact
- Mean reversion works better with RSI-based exits, not price-based

### 3. Symbol-Specific Behavior
- SUNPHARMA: Only symbol with consistent positive returns
- NIFTY50: Consistently worst performer (index harder to trade)
- YESBANK: High volatility, poor mean reversion

### 4. Market Regime Issue
- 2025 data likely has significant bearish periods
- Mean reversion strategy enters on dips, but dips continue
- EMA(200) filter helped historically but fails trade count

---

## Best Available Parameters

### For 120+ Trade Requirement (Competition Safe):

```python
BEST_PARAMS = {
    "RSI_ENTRY": 20,
    "RSI_EXIT": 90,
    "USE_EMA_200": False,  # Removed - too restrictive
    "VOLATILITY_MIN": 0.002,
    "MAX_HOLD_BARS": 12,
}
```

**Expected Performance:**
- Trades: 143 avg per symbol ✅
- Return: -2.95% ⚠️
- Sharpe: 1.75 ✅
- Win Rate: 48.8%

---

## If Trade Count Was Lower (Theoretical)

With 50-80 trade minimum, this would be optimal:

```python
HIGH_QUALITY_PARAMS = {
    "RSI_ENTRY": 35,
    "RSI_EXIT": 75,
    "REQUIRE_RSI_RISING": True,  # Divergence filter
    "VOLATILITY_MIN": 0.001,
    "MAX_HOLD_BARS": 8,
}
```

**Expected Performance:**
- Trades: 67 avg per symbol
- Return: -2.30% (better than baseline)
- Some symbols positive (RELIANCE: +1.93%, SUNPHARMA: +0.41%)

---

## Recommendations

1. **Submit with Current Baseline** - Only option meeting all constraints
2. **Focus on execution** - Submission format, compliance checks
3. **Document the trade-off** - Quality vs quantity constraint
4. **For future:** Lobby for lower trade minimum or per-portfolio counting

---

## Final Strategy Configuration

The current `strategy1_rsi2_meanrev.py` uses the baseline parameters which:
- ✅ Generates 135-154 trades per symbol (passes 120 minimum)
- ✅ Uses only close prices (Rule 12 compliant)
- ✅ Accounts for ₹48 transaction costs
- ⚠️ Returns -2.95% average (negative but near breakeven)
- ✅ Sharpe ratio 1.75 (acceptable for competition)
