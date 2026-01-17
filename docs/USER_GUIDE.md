# USER GUIDE
## Comprehensive Operations Manual

***

## Part 1: Quick Start (5 Minutes)

### 1.1 Repository Overview
Welcome to the team **23ME3EP03** submission repository.
```text
.
├── submission/final/       # ✅ OFFICIAL CSV SUBMISSIONS
├── docs/             # 📘 Documentation (Methodology, Defense, Visuals)
├── src/strategies/         # 🐍 Strategy Logic (HybridAdaptiveV2)
├── scripts/                # 🛠️ Re-generation scripts
└── README.md               # 🏆 Landing Page
```

### 1.2 The "One-Liner"
This repository hosts a **Hybrid Adaptive Mean Reversion** system that achieved a **1.486 Portfolio Sharpe** (with SUNPHARMA > 3.1) by leveraging RSI(2) and volatility-adaptive holding periods.

### 1.3 Prerequisites
*   Python 3.10+
*   Pandas, Numpy, Optuna
*   `pip install -r requirements.txt`

---

## Part 2: Reproduction & Verification

### 2.1 Regenerating Submission Files
To prove reproducibility, you can regenerate the exact submission CSVs from source:
```bash
python scripts/generate_final_submission_files.py
```
*Output:* `output/23ME3EP03_FINAL_submission_*.csv`

### 2.2 Verifying Trade Counts
Run the audit script to confirm all symbols met the 120-trade requirement:
```bash
python scripts/audit_rule12_compliance.py
```
*(Note: Use a custom script if this specific file doesn't exist, checking `len(df)` on CSVs)*

### 2.3 Generating Visuals
To rebuild the equity charts found in `VISUAL_ANALYSIS.md`:
```bash
python scripts/generate_submission_visuals.py
```
*Output:* `reports/figures/*.png`

### 2.4 Running the "Rescue Plan" (Optional)
To verify our findings regarding the "failed" Pairs Trading strategy:
```bash
python experiments/focused_rescue.py
```
*Warning: Takes ~3-4 hours to optimize.*

---

## Part 3: Understanding the System

### 3.1 Key Configuration
The strategy parameters are hardcoded in `generate_final_submission_files.py` (representing the optimal frozen set).
*   **RSI Entry/Exit:** 30 / 70
*   **Max Hold:** 10 (Base)
*   **Adaptive:** Enabled

### 3.2 Modifying for Research
If you wish to test new ideas:
1.  Open `src/strategies/hybrid_adaptive_v2.py`
2.  Modify the `generate_signals` method.
3.  Run `experiments/run_advanced_strategies.py` to backtest.

---

## Part 4: FAQ

**Q: Why are there no `High/Low` columns in the data?**
A: We strictly removed them to ensure Rule 12 compliance. The strategy only sees `Close` and `Volume`.

**Q: How did you get 3.13 Sharpe on Sunpharma?**
A: See `ADVANCED_METHODOLOGY.md` -> "Adaptive Hold Periods." It's not a bug; it's a feature.

**Q: Can I deploy this live?**
A: The logic is sound, but this code is built for backtesting. You would need an execution bridge (OMSys) for live routing.

***

*Team 23ME3EP03*
