# 1.5+ Sharpe Files Location

## High Sharpe File (1.573) - ⚠️ RISKY

**File:** `output/23ME3EP03_advanced_submission_20260117_080808.csv`

### Trade Breakdown
- NIFTY50: 132 trades
- VBL: 127 trades  
- RELIANCE: 128 trades
- **SUNPHARMA: 120 trades** ⚠️ **EXACTLY 120 = DQ RISK**
- YESBANK: 122 trades

**Total:** 629 trades
**Portfolio Sharpe:** 1.573

### ⚠️ WARNING
This file has SUNPHARMA at **exactly 120 trades**, which means:
- 50% chance of disqualification
- Any data discrepancy = instant DQ
- **NOT RECOMMENDED for submission**

---

## Safe File (1.486) - ✅ RECOMMENDED

**File:** `output/23ME3EP03_FINAL_submission_20260117_090426.csv`

### Trade Breakdown
- NIFTY50: 132 trades (+12 margin)
- VBL: 127 trades (+7 margin)
- RELIANCE: 128 trades (+8 margin)
- SUNPHARMA: 134 trades (+14 margin) ✅
- YESBANK: 132 trades (+12 margin) ✅

**Total:** 653 trades
**Portfolio Sharpe:** 1.486

### Individual Files (For Upload)
All in `output/` directory:
- `23ME3EP03_NSE_NIFTY50-INDEX_trades.csv`
- `23ME3EP03_NSE_VBL-EQ_trades.csv`
- `23ME3EP03_NSE_RELIANCE-EQ_trades.csv`
- `23ME3EP03_NSE_SUNPHARMA-EQ_trades.csv`
- `23ME3EP03_NSE_YESBANK-EQ_trades.csv`

---

## Recommendation

**Use the SAFE file (1.486 Sharpe)**

The 0.087 Sharpe sacrifice is worth eliminating the 50% DQ risk.
