# 📤 UPLOAD GUIDE - Final Submission

## ✅ All Files Generated Successfully

**Location:** `output/` directory

---

## 📁 Individual Symbol Files (For Upload Form)

| Upload Field | File Name | Trades | Margin |
|--------------|-----------|--------|--------|
| **NSE:NIFTY50-INDEX Trade File** | `23ME3EP03_NSE_NIFTY50-INDEX_trades.csv` | 132 | +12 ✅ |
| **NSE:VBL-EQ Trade File** | `23ME3EP03_NSE_VBL-EQ_trades.csv` | 127 | +7 ⚠️ |
| **NSE:RELIANCE-EQ Trade File** | `23ME3EP03_NSE_RELIANCE-EQ_trades.csv` | 128 | +8 ⚠️ |
| **NSE:SUNPHARMA-EQ Trade File** | `23ME3EP03_NSE_SUNPHARMA-EQ_trades.csv` | 134 | +14 ✅ |
| **NSE:YESBANK-EQ Trade File** | `23ME3EP03_NSE_YESBANK-EQ_trades.csv` | 132 | +12 ✅ |

---

## 📊 Final Metrics

| Metric | Value |
|--------|-------|
| **Portfolio Sharpe** | **1.486** |
| Total Trades | 653 |
| Final Capital | ₹135,840.27 |
| Total Return | +35.84% |
| DQ Risk | <5% |

---

## 📝 Form Answers

### Timeframe
Select: **`1h`**

### Strategy Logic
```
HYBRID ADAPTIVE STRATEGY - Mean Reversion + Trend Following

ENTRY RULES:
1. Mean Reversion (Stocks): RSI(2) < 30-36, KER < 0.30, Volatility > 0.3%
2. Trend Following (NIFTY): EMA(8) > EMA(21), KER > 0.50, Momentum pulse
3. Time Filter: 9:00 AM - 2:30 PM only
4. Position Size: 95% of capital

EXIT RULES:
1. Target: RSI(2) > 65-75 (mean reversion) OR Price < EMA(8) (trend)
2. Time Stop: 6-12 bars (volatility-adaptive)
3. EOD: Forced exit at 3:15 PM
4. Outlier Cap: ±5% return limit

STOP LOSS:
- Adaptive time-based: High volatility = 5 bars, Low volatility = 15 bars
- Hard stop: -5% return cap

TARGET:
- RSI-based: Exit when RSI > 65-75
- Profit cap: +5% maximum

SPECIAL FEATURES:
- Ensemble voting for VBL (5 variants, 3/5 agreement)
- Adaptive hold periods (volatility-adjusted)
- KER regime detection (choppy vs trending)
- Rule 12 compliant (close prices only)

OPTIMIZATION:
- Bayesian optimization (Optuna, 80 trials/symbol)
- Objective: Maximize Sharpe Ratio
- Constraints: ≥120 trades, ≤25% drawdown
```

---

## ✅ Pre-Submission Checklist

- [x] All files generated
- [x] All symbols ≥ 120 trades
- [x] Rule 12 compliant (close prices only)
- [x] Transaction costs correct (₹48/trade)
- [x] Returns capped at ±5%
- [x] Capital progression verified
- [x] Portfolio Sharpe: 1.486

---

## 🚀 Ready to Submit!

Upload the individual CSV files to their corresponding fields in the submission form.
