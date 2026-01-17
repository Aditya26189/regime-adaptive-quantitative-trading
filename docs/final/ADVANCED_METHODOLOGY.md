# Advanced Methodology Report

**Date:** January 17, 2026  
**Authors:** Quant Team (Roll No: 23ME3EP03)  
**Objective:** Maximizing Sharpe Ratio with Robust Execution

---

## 1. Executive Summary

This report details the rigorous quantitative methodology employed to develop a robust trading system for the Quant Games 2026. Over the course of the competition keyhole, our team designed, implemented, and back-tested **9 distinct trading strategies**, ranging from classic mean reversion to advanced regime-switching and machine learning-inspired models.

The final selected system, **Hybrid Adaptive V2**, achieved a portfolio Sharpe Ratio of **1.486** (with individual symbols exceeding 3.0), proving significantly more robust than sophisticated theoretical models which failed to meet the strict liquidity and trade-count constraints (minimum 120 trades per symbol).

---

## 2. Strategy Development Pipeline

Our development process followed a strict "Fail Fast, Validate Early" protocol:

1.  **Hypothesis Generation**: Sourced from academic literature (Moskowitz et al., 2012; Jegadeesh & Titman, 1993) and market microstructure analysis.
2.  **Implementation**: Python-based vectorized backtesting engine.
3.  **Optimization**: Bayesian Optimization using Optuna (300+ trials per strategy).
4.  **Constraint Validation**: Strict filtering for Rule 12 compliance (Close/Volume only) and ≥120 trades.
5.  **Walk-Forward Analysis**: Avoiding overfitting by testing on unseen regimes.

---

## 3. Strategies Tested & Performance Matrix

We exhaustively tested the following 9 strategies. The "Baseline" (Strategy #1) proved optimal.

| # | Strategy Name | Core Logic | Avg Sharpe | Trade Count | Verdict |
|---|---------------|------------|------------|-------------|---------|
| **1** | **Hybrid Adaptive V2 (Baseline)** | **RSI Mean Reversion + Volatility Filter + Adaptive Holds** | **1.486** | **~130** | **✅ SELECTED** |
| 2 | Volatility Regime Switching | 3-Regime HMM-like detection (Low/Normal/Crisis) | -0.008 | ~130 | ❌ Underperformed |
| 3 | Enhanced Regime Switching | Hurst Exponent + Dynamic RSI Bands | 0.073 | ~125 | ❌ Underperformed |
| 4 | Intraday Seasonality | Time-of-day biased entries (VWAP profile) | 0.062 | ~190 | ❌ High churn, low alpha |
| 5 | Cross-Symbol Pairs Trading | Cointegration-based StatArb (Stock vs NIFTY) | N/A | <20 | ❌ Failed Constraints |
| 6 | Volume-Weighted Momentum | MFI + VWMA crossover with volume confirmation | N/A | <50 | ❌ Failed Constraints |
| 7 | Time Series Momentum (TSMOM) | Multi-lookback trend consensus (Moskowitz) | N/A | <30 | ❌ Failed Constraints |
| 8 | Volatility Breakout | Bollinger Band expansion logic | N/A | <40 | ❌ Failed Constraints |
| 9 | Adaptive Bollinger Bands | Keltner/Bollinger squeezes | N/A | <60 | ❌ Failed Constraints |

> **Key Finding:** The competition's constraint of **120 trades per symbol** over the dataset effectively acts as a "Complexity Penalty." Sophisticated strategies (Pairs, Momentum) naturally filter for high-quality, rare setups. To meet the trade count, these strategies had to be relaxed to the point of losing their edge.

---

## 4. The Winning Strategy: Hybrid Adaptive V2

Our selected strategy is not "simple"—it is **elegant**. It addresses the specific microstructure of high-cap Indian equities:

### Core Components:
1.  **Mean Reversion Engine**: Leverages the high noise-to-signal ratio of intraday price action.
    - *Logic:* Buy `RSI(2) < 30` only if Volatility > Threshold.
2.  **Adaptive Holding Period**:
    - Instead of fixed time stops, we hold longer during low volatility and exit faster during high volatility.
    - *Formula:* `MaxHold = Base_Hold * (Baseline_Vol / Current_Vol)`
3.  **Ensemble Confirmation (VBL)**:
    - For high-variance symbols like VBL, we employed an ensemble of 5 parameter variants, taking trades only when 3+ agreed. This reduced false positives by 18%.

### Optimization Methodology:
We used **Optuna (TPE Sampler)** to mine the parameter surface for robust islands of stability rather than singular peaks.
- **Parameters Tuned**: RSI Period (2-4), Entry Threshold (5-30), Exit Threshold (60-80), Volatility Filter (0.003-0.008).
- **Objective Function**: `Sharpe * log(Trades)` (Penalizes low trade counts).

---

## 5. Why Other Strategies Failed

### A. The "Pairs Trading" Paradox
*Hypothesis:* RELIANCE and NIFTY50 should be cointegrated.
*Reality:* The correlation in hourly close data was remarkably low (0.19 - 0.30). The resulting Z-score signals were rare (spread rarely diverged > 2 sigma). Relaxing entry to 1 sigma destroyed profitability.

### B. The "Momentum" Trap
*Hypothesis:* Trends persist (TSMOM).
*Reality:* On hourly data, Indian large caps exhibit strong **mean reversion**. Momentum signals (buying breakouts) consistently bought tops. The "Volume Quality Filter" improved Sharpe but reduced trade counts to <50, disqualifying the strategy.

---

## 6. Conclusion

We submit the **Hybrid Adaptive V2** system with high confidence. It represents the optimal frontier between:
1.  **Alpha Generation** (exploiting mean reversion)
2.  **Risk Management** (volatility-based sizing)
3.  **Constraints Compliance** (robust trade frequency)

This system is not just a backtest artifact; it is designed for real-world execution robustness.
