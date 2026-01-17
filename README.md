# Quant Games 2026 - Adaptive Mean Reversion Strategy
### Team 23ME3EP03 | IIT Kharagpur

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-Submission%20Ready-green.svg)](#)

---

## 🏆 Quick Stats

| Metric | Value | Status |
|--------|-------|--------|
| **Portfolio Sharpe** | **1.486** | ✅ Competitive |
| **Best Symbol** | SUNPHARMA (**3.132**) | ⭐⭐⭐ Exceptional |
| **Total Trades** | 654 | ✅ >120 Safe Margin |
| **Strategies Tested** | 17 | 📊 Rigorous Validation |
| **Code Base** | ~3,500 Lines | ⚡ Production Grade |

---

## 📋 Table of Contents

1.  [Executive Summary](#executive-summary)
2.  [Key Innovation](#key-innovation)
3.  [Performance Matrix](#performance-matrix)
4.  [Documentation Suite](#documentation-suite)
5.  [Installation & Usage](#installation--usage)

---

## 🚀 Executive Summary

The **Hybrid Adaptive V2** system is a specialized algorithmic trading strategy designed for the IIT Kharagpur Quant Games 2026. Prioritizing robust execution over theoretical complexity, the system exploits **short-term mean reversion** anomalies in Indian large-cap equities.

By strictly adhering to **Rule 12 (Close/Volume only)** and liquidity constraints, we engineered a solution that achieves a **1.486 Portfolio Sharpe Ratio**, driven by a breakout performance in the Pharma sector (Sharpe > 3.0) via our proprietary **Adaptive Hold** mechanism.

---

## 💡 Key Innovation: Volatility-Adaptive Holding

Most mean reversion strategies fail because they exit too early in trending markets or hold too long in choppy ones.

Our breakthrough came from dynamic time-warping:
> **"Don't fight the volatility. Use it."**

*   **Low Volatility Regime:** We expand our max holding period (up to 18 hours), allowing price drift to revert.
*   **High Volatility Regime:** We contract our holding period (down to 5 hours), capturing snap-backs while minimizing tail risk.

This single innovation boosted our SUNPHARMA Sharpe from **2.12** to **3.132**.

---

## 📊 Performance Matrix

| Symbol | Sharpe Ratio | Total Trades | Win Rate | Role |
|--------|--------------|--------------|----------|------|
| **SUNPHARMA** | **3.132** | 134 | 52% | Alpha Driver |
| **RELIANCE** | 1.683 | 128 | 49% | Stabilizer |
| **VBL** | 1.574 | 127 | 47% | Volatility Harvest |
| **YESBANK** | 1.036 | 132 | 45% | Diversifier |
| **NIFTY50** | 0.006 | 133 | 42% | Hedge / Neutral |
| **PORTFOLIO** | **1.486** | **654** | **48%** | **Aggregate** |

---

## 📂 Documentation Suite

We believe in radical transparency. Our full research methodology is documented below:

*   📘 **[Advanced Methodology Report](docs/ADVANCED_METHODOLOGY.md)**
    *   *The "Scientific Paper" detailing our 17 experiments and rejection of Pairs Trading.*
*   🛡️ **[Strategy Defense](docs/STRATEGY_DEFENSE.md)**
    *   *Theoretical justification and robustness/sensitivity analysis.*
*   📊 **[Visual Analysis](docs/VISUAL_ANALYSIS.md)**
    *   *Equity curves, drawdown charts, and risk metrics.*
*   📖 **[User Guide](docs/USER_GUIDE.md)**
    *   *How to reproduce these results from scratch.*

---

## 🛠 Installation & Usage

### 1. Setup
```bash
git clone https://github.com/yourusername/quant-games-2026.git
pip install -r requirements.txt
```

### 2. Generate Submission
```bash
python scripts/generate_final_submission_files.py
```
*Generates compliant CSVs in `submission/final/`*

### 3. Verification
```bash
python scripts/audit_rule12_compliance.py
```

---

*Copyright © 2026 Team 23ME3EP03. Open sourced for educational purposes.*
