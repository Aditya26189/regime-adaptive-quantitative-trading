# 🧠 STRATEGY 5 LOGIC DOCUMENTATION
## IIT Kharagpur Quant Games 2026 - Final Submission

**Submission ID:** 5 (Final)
**Date:** January 17, 2026
**Architecture:** Multi-Strategy Portfolio (Hybrid Adaptive + Trend Ladder)

---

## 1. STRATEGY OVERVIEW

Our submission utilizes a **Hybrid Adaptive Architecture** that dynamically selects between Mean Reversion and Trend Following logics based on the **Kaufman Efficiency Ratio (KER)** and **Volatility Regimes**.

Each symbol uses a tuned variation of this core logic to maximize its specific alpha characteristics.

---

## 2. SYMBOL-SPECIFIC LOGIC

### 🔵 RELIANCE (Hybrid Adaptive V2)
**Type:** Multi-Timeframe Mean Reversion (Deep Pullback)
This strategy captures deep dips in a strong blue-chip stock within an uptrend.

*   **ENTRY RULES:**
    1.  **Price < EMA(5)** (Short-term pullback)
    2.  **RSI(2) < 29** (Oversold condition)
    3.  **Volatility > 0.8%** (Ensure sufficient movement)
    4.  **Time:** 09:15 - 12:00 (Morning entry preference)
*   **EXIT RULES:**
    1.  **Target:** **RSI(2) > 90** (Wait for strong mean reversion)
    2.  **Time Limit:** 8 Hours (Intraday/Next-open exit)
    3.  **Stop Loss:** 2.0% Fixed
*   **LOGIC:** RELIANCE is highly efficient. We buy fear (RSI < 29) and sell greed (RSI > 90).

---

### 🟠 SUNPHARMA (V2 Boosted + Profit Ladder)
**Type:** Mean Reversion with Staged Exits
This strategy uses "Profit Ladders" to scale out of positions, capturing both quick pops and extended runs.

*   **ENTRY RULES:**
    1.  **Price < EMA(8)**
    2.  **RSI(4) < 41** (Moderate pullback)
    3.  **Volatility > 0.4%**
    4.  **KER > 0.38** (Efficiency filter)
*   **EXIT RULES (The Ladder):**
    1.  **Tier 1 (35% Qty):** Exit when **RSI > 65** (Secure partial profit)
    2.  **Tier 2 (Remaining):** Exit when **RSI > 52** (Conservative baseline) or Time Limit.
    3.  **Time Limit:** 6 Hours
    4.  **Stop Loss:** 2.0% Fixed
*   **LOGIC:** Pharma stocks can be choppy. The ladder ensures we lock in gains early while keeping exposure for a potential trend resumption.

---

### 🔴 VBL (Hybrid Scalper - Relaxed)
**Type:** High-Frequency Mean Reversion (Scalping)
Designed for high turnover to capture small inefficiencies.

*   **ENTRY RULES:**
    1.  **RSI(14) < 45** (Buying slightly below neutral)
    2.  **No Volatility Filter** (Trade all regimes)
    3.  **Time:** All Day (09:15 - 15:30)
*   **EXIT RULES:**
    1.  **Target:** **RSI(14) > 55** (Quick mean reversion to slightly above neutral)
    2.  **Time Limit:** **3 Hours** (Fast churn)
    3.  **Stop Loss:** 2.0%
*   **LOGIC:** VBL is volatile. By tightening the RSI band (45/55), we trade the "noise" profitably, executing a high number of trades (163) to smooth out the equity curve.

---

### 🟢 YESBANK (Robust Baseline)
**Type:** Deep Value Mean Reversion (Optuna Tuned)
A conservative approach for a high-beta banking stock.

*   **ENTRY RULES:**
    1.  **RSI(4) < 40** (Buying dips)
    2.  **Volatility > 0.1%** (Avoid dead zones)
    3.  **KER Filter:** Active (Avoid buying during crash trends)
    4.  **Time:** All Day
*   **EXIT RULES:**
    1.  **Target:** **RSI(4) > 60** (Moderate rebound)
    2.  **Time Limit:** **4 Hours**
    3.  **Stop Loss:** 2.0%
*   **LOGIC:** YESBANK often traps momentum traders. We fade the drops but exit quickly (RSI 60) before selling pressure returns.

---

### 📈 NIFTY50 (Trend Ladder)
**Type:** Pure Trend Following
Unlike the stocks, the Index is traded with a Momentum strategy.

*   **ENTRY RULES:**
    1.  **EMA Crossover:** EMA(8) > EMA(21) (Uptrend)
    2.  **Momentum:** Price > EMA(8) * 1.0015 (Confirmation)
    3.  **Volatility:** > 0.25% (Avoid flat markets)
*   **EXIT RULES (3-Tier Ladder):**
    1.  **Tier 1 (50%):** **RSI > 60** OR **Gain > 1.0%**
    2.  **Tier 2 (25%):** **RSI > 70** OR **Gain > 1.8%**
    3.  **Tier 3 (25%):** **RSI > 80** OR Trend Broken (Price < EMA 8)
    4.  **Hard Stop:** 2.0%
*   **LOGIC:** Indices trend better than individual stocks. We ride the wave but peel off profits (scale out) as the trend becomes overextended (high RSI).

---

## 3. RISK MANAGEMENT (Global)

1.  **Position Sizing:** Fixed fraction of capital (adjusted for fees).
2.  **Execution:** Next Open execution simulation (conservative).
3.  **Transaction Costs:** ₹48 per trade deducted from PnL.
4.  **Capital Protection:** No strategy holds overnight if the signal reverses; strict Time Limits prevent "zombie positions".

## 4. COMPLIANCE CHECK

-   **Rule 12 (Close Price):** All indicators (RSI, EMA, Volatility) are calculated using **Close** prices only.
-   **No Lookahead:** Signals are calculated on `bar[i]`, Entry is on `bar[i]` (instant) or `bar[i+1]` Open, strictly preserving causality. Overfitting checks (Train/Test) performed.
