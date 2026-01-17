# Master User Guide

**Project:** Quant Games 2026 Submission  
**Team Roll:** 23ME3EP03

---

## 📚 Table of Contents

1.  [Quick Start](#quick-start)
2.  [Repository Structure](#repository-structure)
3.  [Documentation Index](#documentation-index)
4.  [Reproduction Steps](#reproduction-steps)

---

## 🚀 Quick Start

**Final Submission Files** are located in:
> `submission/final/`

The main combined CSV is:
> `submission/final/FINAL_SUBMISSION.csv`

---

## 📂 Repository Structure

```text
.
├── submission/
│   ├── final/          # ✅ FINAL CSV FILES FOR UPLOAD
│   └── archive/        # Old versions
├── docs/
│   ├── final/          # ✅ OFFICIAL DOCUMENTATION (Read these)
│   └── archive/        # Deprecated logs
├── reports/
│   └── figures/        # Generated charts
├── src/                # Source code for strategies
├── experiments/        # Optimization scripts (Optuna)
└── scripts/            # Utility scripts
```

---

## 📖 Documentation Index

For a complete understanding of our work, read in this order:

1.  **[Advanced Methodology Report](final/ADVANCED_METHODOLOGY.md)**
    *   *Read this for:* Deep dive into how we built and tested 9 strategies.
2.  **[Strategy Defense](final/STRATEGY_DEFENSE.md)**
    *   *Read this for:* Academic justification and market theory.
3.  **[Visual Analysis](final/VISUAL_ANALYSIS.md)**
    *   *Read this for:* Charts, equity curves, and drawdown graphs.

---

## 🛠 Reproduction Steps

To reproduce our results from source:

1.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Run Final Generator:**
    ```bash
    python generate_final_submission_files.py
    ```
    *This will regenerate the CSVs in `output/` using the hardcoded optimal parameters.*

3.  **Generate Visuals:**
    ```bash
    python scripts/generate_submission_visuals.py
    ```
    *This will update charts in `reports/figures/`.*

---

## ⚠️ Compliance Note

All strategies adhere strictly to:
- **Rule 12:** Only Close and Volume data used.
- **Trade Counts:** Minimum 120 trades per symbol verified.
- **Formatting:** Columns match competition spec exactly.
