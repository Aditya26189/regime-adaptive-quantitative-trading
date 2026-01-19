# STRATEGY 3 SUBMISSION PACKAGE
## IIT Kharagpur Quant Games 2026

**Student:** Aditya Singh  
**Roll Number:** 23ME3EP03  
**Submission Date:** January 17, 2026

---

## SUBMISSION CHECKLIST

### ✅ Timeframe
**Answer:** **1h** (1 Hour / 60-minute candles)

### ✅ Strategy Logic
**Answer:** See `STRATEGY_3_LOGIC.md` (comprehensive document uploaded)

**Quick Summary:**
- **NIFTY50:** Trend-following with profit ladders (RSI 60/70/80)
- **RELIANCE:** Hybrid adaptive V2 (Multi-timeframe + KER regime)
- **VBL:** Regime switching (Dynamic RSI 25-35 based on volatility)
- **YESBANK:** Boosted hybrid (RSI 27, +4 confirmation)
- **SUNPHARMA:** V2 Boosted + Ladders (RSI 41, +3 confirmation)

---

## TRADE FILES FOR UPLOAD

### File 1: NSE:NIFTY50-INDEX Trade File
**Filename:** `23ME3EP03_NSE_NIFTY50-INDEX_trades.csv`  
**Location:** `output/23ME3EP03_NSE_NIFTY50-INDEX_trades.csv`  
**Trades:** 126  
**Strategy:** Trend-following with profit ladders  
**File Size:** 18.4 KB

### File 2: NSE:RELIANCE-EQ Trade File
**Filename:** `23ME3EP03_NSE_RELIANCE-EQ_trades.csv`  
**Location:** `output/23ME3EP03_NSE_RELIANCE-EQ_trades.csv`  
**Trades:** 128  
**Strategy:** Hybrid Adaptive V2 (Multi-timeframe)  
**File Size:** 15.8 KB

### File 3: NSE:VBL-EQ Trade File
**Filename:** `23ME3EP03_NSE_VBL-EQ_trades.csv`  
**Location:** `output/23ME3EP03_NSE_VBL-EQ_trades.csv`  
**Trades:** 237  
**Strategy:** Regime Switching (Adaptive RSI)  
**File Size:** 35.4 KB

### File 4: NSE:YESBANK-EQ Trade File
**Filename:** `23ME3EP03_NSE_YESBANK-EQ_trades.csv`  
**Location:** `output/23ME3EP03_NSE_YESBANK-EQ_trades.csv`  
**Trades:** 132  
**Strategy:** Boosted Hybrid (+4 RSI confirmation)  
**File Size:** 16.3 KB

### File 5: NSE:SUNPHARMA-EQ Trade File
**Filename:** `23ME3EP03_NSE_SUNPHARMA-EQ_trades.csv`  
**Location:** `output/23ME3EP03_NSE_SUNPHARMA-EQ_trades.csv`  
**Trades:** 134  
**Strategy:** V2 Boosted + Profit Ladders  
**File Size:** 16.7 KB

---

## PERFORMANCE SUMMARY

| Symbol | Trades | Sharpe (Full) | Sharpe (OOS) | Status |
|--------|--------|---------------|--------------|--------|
| NIFTY50 | 126 | 1.667 | 3.286 | ✅ |
| RELIANCE | 128 | 2.985 | 1.439 | ✅ |
| VBL | 237 | 2.092 | 3.854 | ✅ |
| YESBANK | 132 | 1.759 | -1.805 | ⚠️ |
| SUNPHARMA | 134 | 4.292 | 2.753 | ✅ |
| **Portfolio** | **757** | **2.559** | **1.905** | ✅ |

**Conservative Sharpe Estimate:** 1.905 (out-of-sample tested)  
**Optimistic Sharpe Estimate:** 2.559 (full data)

---

## UPLOAD INSTRUCTIONS

1. **Timeframe:** Select **"1h"** from dropdown

2. **Strategy Logic:** Upload **`STRATEGY_3_LOGIC.md`**
   - Contains detailed entry/exit rules for all 5 symbols
   - Includes risk management and validation

3. **Trade Files:** Upload the following 5 CSVs from `output/` folder:
   - `23ME3EP03_NSE_NIFTY50-INDEX_trades.csv`
   - `23ME3EP03_NSE_RELIANCE-EQ_trades.csv`
   - `23ME3EP03_NSE_VBL-EQ_trades.csv`
   - `23ME3EP03_NSE_YESBANK-EQ_trades.csv`
   - `23ME3EP03_NSE_SUNPHARMA-EQ_trades.csv`

---

## VALIDATION PROOF

### Out-of-Sample Test (70/30 Split)
- **Train Period:** Jan-Sep 2025 (70%)
- **Test Period:** Oct-Dec 2025 (30%)
- **Result:** 1.905 Sharpe on unseen data ✅

**Report:** `output/OVERFITTING_CHECK.json`

### Constraint Compliance
✅ All symbols ≥ 120 trades  
✅ Transaction costs (₹48/trade) included  
✅ Rule 12 compliant (only close prices)  
✅ No look-ahead bias  
✅ Outlier capping (5% max return)

---

## COMPETITION RANKING ESTIMATE

**Conservative (OOS):** 1.905 Sharpe → **Top 3-8**  
**Optimistic (Full):** 2.559 Sharpe → **Top 1-3**

**Realistic Expectation:** **Top 5 / 100 teams** 🏆

---

## SUPPORTING DOCUMENTATION

Additional files available for judges' review:

1. **`docs/final/EXECUTIVE_SUMMARY.md`** - High-level overview
2. **`docs/final/PHASE_1_DOCUMENTATION.md`** - Foundation strategies
3. **`docs/final/PHASE_2_DOCUMENTATION.md`** - Advanced optimization
4. **`docs/final/PHASE_3_DOCUMENTATION.md`** - Final breakthrough
5. **`output/final_validation_report.json`** - Full validation metrics
6. **`output/OVERFITTING_CHECK.json`** - Train/test split results

---

## CONTACT INFORMATION

**Aditya Singh**  
Roll Number: 23ME3EP03  
Department: Mechanical Engineering (3rd Year)  
Institution: IIT Kharagpur  
Email: [Your IIT KGP Email]

---

**READY TO SUBMIT** ✅

All files validated and ready for competition upload.
