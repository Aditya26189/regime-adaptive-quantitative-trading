# Quant Games 2026 - System Architecture & Implementation

## 1. System Design Philosophy
The system implements a **multi-strategy, regime-adaptive architecture** designed to maximize Sharpe Ratio while strictly adhering to competition constraints (Rule 12, trade limits, transaction costs).

### Key Architectural Decisions
1.  **Switchblade Strategy Combiner**: Instead of a "one-size-fits-all" model, we effectively use different strategies for different asset classes:
    *   **Indices (NIFTY50):** Trend Following (EMA + Momentum). Indices trend; mean reversion fails.
    *   **Stocks (VBL, SUNPHARMA):** Mean Reversion (RSI + Volatility). Stocks exhibit oscillation logic.
    *   **High Variance (VBL):** Ensemble Voting (5-variant consensus). Filters out noise.

2.  **Optuna Bayesian Optimization**:
    *   Replaces random search with TPE (Tree-structured Parzen Estimator).
    *   Multi-objective scoring: Optimize `0.7*Sharpe + 0.1*Return + 0.1*Drawdown`.
    *   Parallel execution across all CPU cores.

3.  **Strict Compliance Layer**:
    *   **Close-Only (Rule 12):** All indicators use `close` price. No intra-candle peeking.
    *   **Outlier Capping:** Hard cap of 5% return per trade to prevent lucky outliers from skewing metrics.
    *   **Trade Count Enforcement:** Strategies optimized with `min_trades=120` constraint.

---

## 2. Directory Structure & Code Flow

```
fyers/
├── config/
│   └── settings.py              # Central env config
│
├── data/
│   └── raw/                     # 1-hour historical data
│
├── src/
│   ├── strategies/              # Strategy Logic
│   │   ├── nifty_trend_strategy.py  # Trend Following (NIFTY)
│   │   ├── hybrid_adaptive.py       # Mean Rev / Adaptive (Stocks)
│   │   └── ensemble_wrapper.py      # Meta-strategy (VBL)
│   │
│   ├── optimization/            # Optimization Engine (Optuna)
│   │   ├── parameter_space.py       # Search ranges
│   │   ├── objective_functions.py   # Scoring logic (Weighted)
│   │   └── parallel_optimizer.py    # Multi-core runner
│   │
│   ├── submission/              # Final Artifact Gen
│   │   └── winning_submission_generator.py # Generator
│   │
│   └── utils/                   # Shared Libs
│       ├── indicators.py            # RSI, EMA, Volatility
│       └── regime_detection.py      # Broker logic
│
└── scripts/
    ├── run_full_optimization.py     # Entry point: Optimizer
    ├── validate_results.py          # Entry point: Validator
    └── generate_final_submission.py # Entry point: Submission
```

---

## 3. Strategy Logic Details

### A. NIFTY50 Trend Following
*   **Logic:** Captures sustained moves in the index.
*   **Entry:** Fast EMA > Slow EMA AND Momentum > Threshold AND High Volatility.
*   **Exit:** Trend reversal OR Momentum loss OR Max hold time.
*   **Why:** NIFTY50 had -1.14 Sharpe with mean reversion. Trend strategy flipped it to Positive.

### B. VBL Ensemble
*   **Logic:** Voting mechanism to reduce false positives in high-volatility stock.
*   **Implementation:** Runs 5 variations of RSI strategy (Different lookbacks/thresholds).
*   **Signal:** Enters only if ≥3 variants agree.
*   **Result:** Highest Sharpe in portfolio (1.57).

### C. Hybrid Adaptive (SUNPHARMA, RELIANCE, YESBANK)
*   **Logic:** Baseline Mean Reversion with Regime Filter.
*   **Regime Filter:** Uses Kaufman Efficiency Ratio (KER).
    *   KER > 0.5 (Trend) → Skip Mean Rev signals.
    *   KER < 0.5 (Range) → Take Mean Rev signals.

---

## 4. Optimization Pipeline

1.  **Search Space Definition (`parameter_space.py`)**: Defines min/max for EMAs, RSI, Thresholds.
2.  **Simulation (`parallel_optimizer.py`)**:
    *   Loads data.
    *   Spawns process per symbol.
    *   Runs Optuna Trial -> Backtest -> Calculate Metrics.
3.  **Scoring (`objective_functions.py`)**:
    *   Returns `-inf` if trades < 120.
    *   Calculates `Score = 0.7*Sharpe + ...`
4.  **Selection**: Best parameter set saved to JSON.

---

## 5. Compliance Verification
*   **Rule 12:** Verified via code review of `indicators.py` (uses `close` only).
*   **Transaction Costs:** Fixed ₹48/trade deducted in `backtester`.
*   **Min Trades:** `validate_results.py` asserts `count >= 120`.
