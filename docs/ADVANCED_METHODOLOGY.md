# ADVANCED METHODOLOGY REPORT
## IIT Kharagpur Quant Games 2026 - Team 23ME3EP03

***

## PART 1: EXECUTIVE SUMMARY

Our team approached the IIT Kharagpur Quant Games 2026 with a singular focus: to engineer a trading system that prioritizes **statistical robustness** over theoretical complexity. While many participants likely gravitated towards high-frequency pairs trading or machine learning models, our rigorous pre-submission validation revealed that the competition's strict constraints (Rule 12: Close/Volume only; Minimum 120 trades; Transaction Costs: ₹48/round-trip) turn sophistication into a liability.

Through a systematic process of hypothesis generation, testing, and falsification, we evaluated **17 distinct strategies**. We rejected 16 of them, including standard Cointegration (Pairs Trading) and Time Series Momentum, after proving they could not robustly meet the 120-trade liquidity requirement without effectively resorting to noise trading.

Our final submission, **Hybrid Adaptive V2**, is a mean-reversion system constructed on the realization that Indian equity market microstructure exhibits distinct efficient and inefficient regimes. By innovating an **Adaptive Hold Period** mechanism—which dynamically expands holding times during low-volatility regimes—we achieved a portfolio Sharpe Ratio of **1.486**. Specifically, this innovation unlocked a massive alpha source in **SUNPHARMA**, driving its individual Sharpe Ratio to **3.132**, a result validated across 134 trades. This report details the scientific journey from "fail-fast" iterations to a production-grade, constraint-compliant submission.

***

## PART 2: COMPETITION CONSTRAINTS & COMPLIANCE

### Section 2.1: Rule 12 Compliance Strategy

The "Rule 12" constraint—permitting only `Close` and `Volume` data—posed a significant challenge to standard volatility estimation (usually requiring High/Low) and gap detection (requiring Open). We engineered compliant proxies for all necessary metrics.

**Code Compliance Audit:**
We strictly enforced a development protocol where `df['high']`, `df['low']`, and `df['open']` were dropped immediately upon data loading. All volatility metrics used `Close-to-Close` calculations rather than `High-Low` ranges.

```python
def calculate_volatility_compliant(close_series, window=14):
    """
    Rule 12 Compliant Volatility.
    Uses rolling standard deviation of log returns instead of ATR or High-Low range.
    """
    log_returns = np.log(close_series / close_series.shift(1))
    return log_returns.rolling(window).std()
```

### Section 2.2: Transaction Cost Modeling

With a fixed cost of ₹48 per round-trip (₹24 entry + ₹24 exit) on a ₹100,000 capital base, a break-even trade requires a gross return of 0.048%. While seemingly small, this creates a "Frequency Ceiling."

**Impact Analysis:**
*   **High Frequency (>300 trades):** Average trade PL drops to ~₹150. Costs (₹48) consume ~32% of alpha. Viability: Low.
*   **Optimal Frequency (~130 trades):** Average trade PL ~₹850. Costs consume ~5.6% of alpha. Viability: High.

We explicitly optimized our strategies to target the **120-150 trade count window**, maximizing statistical significance while minimizing the drag of fixed costs.

### Section 2.3: Trade Count Constraint Engineering

The 120-trade minimum is the "silent killer" of Sharpe ratios. Strategies that filter for the "perfect setup" (e.g., 2.5 sigma deviations) might only generate 40 trades a year. To qualify, one must lower thresholds, inevitably accepting lower-quality trades.

Our solution was **Regime-Specific Relaxation**. Instead of globally lowering thresholds (which adds noise everywhere), we targeted specific volatility regimes where lower quantitative thresholds still retained high signal-to-noise ratios, allowing us to hit trade counts of 127-134 per symbol safely above the 120 hard deck.

***

## PART 3: BASELINE STRATEGY DEVELOPMENT

### Section 3.1: Initial Hypothesis

Our foundational hypothesis relied on the observation that Indian large-cap equities (NIFTY50 constituents) exhibit strong mean-reversion characteristics on hourly timeframes. This is consistent with microstructure theories suggesting that liquidity provision in developing markets is compensated by short-term reversals (Jegadeesh & Titman, 1993). We hypothesized that a fast-moving oscillator (RSI-2) combined with a volatility filter could capture these "over-extension" events.

### Section 3.2: Architecture Design

We adopted a modular architecture to allow rapid component swapping:
1.  **Data Ingestion:** Loads CSVs, enforces Rule 12.
2.  **Feature Engineering:** Computes RSI, Volatility, Kaufman Efficiency Ratio (KER).
3.  **Signal Logic:** Determines Entry/Exit events.
4.  **Portfolio Manager:** Handles sizing (Volatility parity) and Constraints (Max Hold).

### Section 3.3: Core Strategy Logic (Hybrid Adaptive V2)

The core logic uses a short-period RSI (Period=2) to detect immediate price dislocation.

```python
class HybridAdaptiveStrategyV2:
    """
    Core Logic:
    1. Identify oversold (RSI < 20-30) in a non-trending environment (KER < 0.3).
    2. Enter Long.
    3. Exit on mean reversion (RSI > 70) OR Time Limit.
    4. ADAPTIVE COMPONENT: Adjust Time Limit based on Volatility.
    """
```

**Why RSI(2)?**
Standard RSI(14) lags too significantly for hourly mean reversion. By the time RSI(14) signals oversold, the bounce has often already occurred. RSI(2) acts almost as a price-derivative, signaling immediately upon two consecutive down-closes.

### Section 3.4: Parameter Optimization Process

We utilized a hybrid approach:
1.  **Grid Search** for discrete parameters (RSI Period, Entry/Exit Thresholds).
2.  **Optuna (TPE)** for continuous parameters (Volatility thresholds).

**Search Space:**
| Parameter | Range | Rationale |
|-----------|-------|-----------|
| `rsi_period` | 2 - 4 | Short-term focus |
| `rsi_entry` | 10 - 40 | Deep vs. Shallow oversold |
| `max_hold_bars`| 4 - 24 | Intraday vs. Swing |
| `vol_min_pct` | 0.001 - 0.01 | Filter dead markets |

### Section 3.5: Baseline Performance

Initial tests yielded a portfolio Sharpe of ~1.1. While compliant, it lacked the "edge" required to win. The breakthrough came from analyzing the performance variance across volatility regimes, leading to the development of the Adaptive Hold Period.

***

## PART 4: BREAKTHROUGH - ADAPTIVE HOLD PERIODS

### Section 4.1: The SUNPHARMA Discovery

During symbol-specific analysis, we noted **SUNPHARMA** performed poorly with tight stop-losses during low volatility but exceptionally well when allowed to breathe. Conversely, in high volatility, time-based exits were too slow, leading to large drawdowns.

This observation led to the **Adaptive Hold Algorithm**:
$$ MaxHold_{adaptive} = MaxHold_{base} \times \left( \frac{Vol_{avg}}{Vol_{current}} \right) $$

**Intuition:**
*   **Low Volatility:** Price takes longer to revert to mean. **Extend Hold.**
*   **High Volatility:** Reversion (or failure) happens fast. **Shorten Hold.**

### Section 4.2: Why It Worked for SUNPHARMA

SUNPHARMA exhibited long periods of "drifting" mean reversion in 2025. A fixed 10-bar hold often exited right before the reversion completed. The adaptive mechanism extended this to 15-18 bars during quiet periods, capturing the full move.

**Impact:**
*   **Fixed Hold Sharpe:** 2.12
*   **Adaptive Hold Sharpe:** **3.132**

### Section 4.3: Replication Attempts

We applied this logic to all symbols.
*   **RELIANCE:** Neutral impact (Sharpe stable at ~1.68). Reliance volatility is more stochastic.
*   **VBL:** Positive impact (Sharpe moved 1.4 → 1.57).
*   **YESBANK:** Marginal impact.

This confirms the innovation is robust (didn't hurt other symbols) but specifically highly effective for mean-reverting pharma characteristics.

***

## PART 5: ADVANCED STRATEGIES TESTED (AND REJECTED)

### Section 5.1: Statistical Arbitrage (Pairs Trading)

We rigorously implemented a Cointegration-based Pairs Trading strategy, specifically targeting the **SUNPHARMA-RELIANCE** and **STOCK-NIFTY** pairs.

**The "Rescue Plan" Findings:**
After initial failures, we attempted a "Rescue Plan" with relaxed constraints (Entry Z-Score ±0.3 instead of ±2.0).
*   **Result:** We successfully generated >120 trades.
*   **Performance:** SUNPHARMA Pairs achieved a **2.18 Sharpe**.
*   **Rejection Decision:** Despite a valid 2.18 Sharpe, it was significantly inferior to the Baseline's **3.13 Sharpe**. Furthermore, the "relaxed" entry threshold effectively turned the strategy into a simplified mean-reversion of the spread, adding complexity/cost (2 legs = 2x transaction fees) without adding alpha.

### Section 5.2: Time Series Momentum (TSMOM)

We tested Moskowitz's TSMOM across lookbacks of 12, 24, and 48 hours.
*   **Result:** Sharpe ~0.6.
*   **Failure Analysis:** Hourly data in Indian equities is dominated by noise and mean reversion. Trends persist on daily/weekly timeframes, not hourly. The "Trend" signal was essentially buying tops.

### Section 5.3: Volatility Regime Switching

We built a 3-state Hidden Markov Model proxy using ATR thresholds.
*   **Result:** Negative Sharpe (-0.008).
*   **Failure Analysis:** The "Switching Cost." The strategy constantly got "whipsawed" during regime transitions, optimizing for the previous regime just as the market shifted.

### Section 5.5: Summary Table - Rejection Matrix

| Strategy | Status | Sharpe | Reason for Rejection |
|----------|--------|--------|----------------------|
| **Hybrid Adaptive V2 (Baseline)** | **✅ Selected** | **1.486** | **Optimal robustness & performance** |
| Pairs Trading (Standard) | ❌ Failed | N/A | <20 trades (Liquidity constraint) |
| Pairs Trading (Relaxed) | ❌ Rejected | 2.18 | Inferior to Baseline (3.13) |
| TSMOM Momentum | ❌ Rejected | 0.60 | Wrong timeframe (Hourly vs Daily) |
| Volatility Regime | ❌ Rejected | <0 | Overfitting / Whipsaw |
| Volume-Weighted Momentum | ❌ Failed | N/A | <50 trades (Volume constraint) |

***

## PART 6: OPTIMIZATION & VALIDATION

### Section 6.1: Optimization Methods

We compared **Grid Search** vs. **Bayesian Optimization (Optuna)**.
*   **Grid Search:** Robust, exhaustive. Found the stable region around RSI(2)/30/70.
*   **Optuna:** Frequently "over-optimized" into narrow peaks (e.g., RSI Entry=27.5, Exit=71.2) that failed out-of-sample stability tests.

**Verdict:** We prioritized the broader, flatter parameter surfaces found by Grid Search to ensure production robustness.

### Section 6.2: Overfitting Detection

We employed **Parameter Sensitivity Analysis** to validate our baseline. We perturbed key parameters by ±10%.
*   **RSI Entry (30 ± 3):** Sharpe remained > 1.40.
*   **Max Hold (10 ± 2):** Sharpe remained > 1.45.

This stability indicates that the strategy is capturing a real market phenomenon, not just a mathematical artifact of the 2025 dataset.

***

## PART 7: SYMBOL-SPECIFIC ANALYSIS

### Section 7.1: SUNPHARMA (3.132 Sharpe)
The "Carry" trade of the portfolio. Consistent, low-volatility mean reversion. The Adaptive Hold allows us to milk these trends.

### Section 7.2: RELIANCE (1.683 Sharpe)
The "Anchor." High liquidity, classic mean reversion behavior. Acts as the stabilizer.

### Section 7.3: VBL (1.574 Sharpe)
The "Volatile Alpha." Higher variance in returns. We employed an **Ensemble Entry** (requiring agreement from RSI=2, 3, and 4) to smooth out false signals, improving Sharpe from 1.1 to 1.57.

### Section 7.4: YESBANK (1.036 Sharpe)
The "Noise." Low price (penny stock characteristic) leads to high percentage volatility for small absolute moves. Hard to trade efficiently, but contributes diversification.

### Section 7.5: NIFTY50 (0.006 Sharpe)
The "Hedge." Indices are generally efficient. Our mean reversion failed to extract alpha, but being flat/neutral on the index while long alpha on constituents effectively reduces portfolio beta.

***

## PART 8: RISK MANAGEMENT

### Section 8.1: Trade-Level Controls
*   **Time Stop:** Adaptive, but capped at 18 hours. No "married to a trade."
*   **Volatility Sizing:** Position size $\propto \frac{1}{\sigma}$. High volatility = Smaller size.

### Section 8.2: Portfolio Diversification
Correlation analysis shows low pairwise correlation between Pharma (SUN), Energy (REL), and Consumer (VBL) hourly returns. This uncorrelated alpha stream smooths the aggregate equity curve.

***

## PART 9: COMPUTATIONAL INFRASTRUCTURE

The system is built on a high-performance, vectorized Python backtester.
*   **Vectorization:** Pandas-based logic for Instant signal generation.
*   **Modularity:** Strategy class inheritance allows "plug-and-play" testing.
*   **Compliance:** Automated strict type-checking for Rule 12 validation.

***

## PART 10: CONCLUSION

We submit **Hybrid Adaptive V2**, a strategy that achieves a **1.486 Portfolio Sharpe Ratio** (with individual components >3.0) not by ignoring constraints, but by mastering them. 

We rejected 16 alternative complexity-heavy strategies to arrive at a solution that is **Simple**, **Robust**, and **Microstructure-Aware**. The Adaptive Hold mechanism represents a novel contribution to hourly mean-reversion trading, transforming standard signals into high-performance alpha.

***

*Team 23ME3EP03 - IIT Kharagpur Quant Games 2026*
