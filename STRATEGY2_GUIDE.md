# STRATEGY #2 SUBMISSION GUIDE (1.573 Sharpe)

## ⚠️ WARNING: High Risk Submission
This submission has **SUNPHARMA at exactly 120 trades** = 50% DQ probability

---

## Form Answers

### Strategy No.
**Select:** `2`

### Timeframe
**Select:** `1h`

### Strategy Logic
```
ADVANCED HYBRID STRATEGY - Ensemble + Adaptive Techniques

ENTRY RULES:
1. VBL: Ensemble voting (5 variants, 3/5 agreement required)
2. Stocks: RSI(2) < 30, KER < 0.30, Volatility > 0.5%
3. NIFTY: EMA(8) > EMA(21), Momentum pulse, KER > 0.50
4. Time: 9:00 AM - 2:30 PM only
5. Position: 95% capital

EXIT RULES:
1. Mean Reversion: RSI(2) > 70
2. Trend: Price < EMA(8)
3. Adaptive Hold: 6-12 bars (volatility-based)
4. EOD: 3:15 PM forced exit
5. Cap: ±5% return limit

STOP LOSS:
- Adaptive time-based (volatility-adjusted)
- High volatility: 5 bars exit
- Low volatility: 15 bars hold
- Hard stop: -5% cap

TARGET:
- RSI > 70 for mean reversion
- Profit cap: +5%
- Adaptive hold optimization

SPECIAL FEATURES:
- Ensemble voting (VBL only)
- Adaptive hold periods (SUNPHARMA, RELIANCE)
- KER regime detection
- Bayesian optimization (Optuna)
- Rule 12 compliant

RISK: SUNPHARMA has exactly 120 trades
```

---

## Upload Files

| Field | File | Trades |
|-------|------|--------|
| **NSE:NIFTY50-INDEX** | `STRATEGY2_NSE_NIFTY50-INDEX_trades.csv` | 132 |
| **NSE:VBL-EQ** | `STRATEGY2_NSE_VBL-EQ_trades.csv` | 127 |
| **NSE:RELIANCE-EQ** | `STRATEGY2_NSE_RELIANCE-EQ_trades.csv` | 128 |
| **NSE:SUNPHARMA-EQ** | `STRATEGY2_NSE_SUNPHARMA-EQ_trades.csv` | 120 ⚠️ |
| **NSE:YESBANK-EQ** | `STRATEGY2_NSE_YESBANK-EQ_trades.csv` | 122 |

---

## Metrics

**Portfolio Sharpe:** 1.573
**Total Trades:** 629
**DQ Risk:** ~50% (SUNPHARMA exactly 120)

---

## ⚠️ RECOMMENDATION

Consider submitting **Strategy #1** (1.486 Sharpe) instead:
- Lower Sharpe but <5% DQ risk
- All symbols have safety margins
- Files: `23ME3EP03_NSE_*_trades.csv`
