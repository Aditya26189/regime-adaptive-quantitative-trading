# Quant Games 2026 - Trading Strategy System

## 🏆 Final Results
- **Portfolio Sharpe Ratio:** 1.263
- **Portfolio Return:** +7.15%
- **Estimated Rank:** Top 1-5

## Project Structure

```
fyers/
├── config/                     # Configuration files
│   ├── settings.py            # Environment settings
│   └── sharpe_config.py       # Parameter search spaces
├── data/
│   └── raw/                   # Historical price data (1-hour)
├── src/
│   ├── strategies/            # Trading strategies
│   │   ├── hybrid_adaptive.py # Main adaptive strategy
│   │   ├── ensemble_wrapper.py# Multi-variant ensemble
│   │   └── nifty_trend_strategy.py # NIFTY-specific trend
│   ├── optimizers/            # Parameter optimization
│   │   ├── sharpe_optimizer.py
│   │   ├── deep_optimizer.py
│   │   └── ultra_fine_tune.py
│   ├── submission/            # Submission generators
│   │   └── winning_submission_generator.py
│   ├── utils/                 # Utilities
│   │   ├── indicators.py
│   │   └── regime_detection.py
│   └── validation/            # Compliance checks
├── output/                    # Generated submissions
├── docs/                      # Documentation
└── README.md
```

## Quick Start

- Save submission CSV to `output/` folder

## Key Features
- **Per-Symbol Optimization:** Tailored parameters for NIFTY50, RELIANCE, VBL, YESBANK, SUNPHARMA.
- **Rule 12 Compliance:** Strictly uses close prices only.
- **Transaction Costs:** Accounts for ₹48/roundtrip fees.
- **Constraint validation:** Ensures ≥120 trades per symbol.

## Results
- **Average Return:** +3.85% (Top 20-30 Est.)
- **Best Symbol:** VBL (+14.88%)
- **Worst Symbol:** NIFTY50 (-4.32%)

## Documentation
- [Implementation Guide](docs/OPTIMIZATION_IMPLEMENTATION.md)
- [Results Analysis](docs/OPTIMIZATION_RESULTS_ANALYSIS.md)
