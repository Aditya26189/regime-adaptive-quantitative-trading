# IIT Kharagpur Quant Games 2026 - Algo Strategy

## Project Overview
This repository contains the algorithmic trading strategy and optimization tools for the Quant Games 2026 competition. The project implements a per-symbol parameter optimization approach to maximize returns while adhering to strict competition constraints (Rule 12, trade limits, transaction costs).

## Directory Structure

```
fyers/
├── config/                 # Configuration and settings
│   └── settings.py         # Central config loader
├── data/
│   └── raw/                # Historical CSV data
├── docs/                   # Documentation and reports
│   ├── OPTIMIZATION_IMPLEMENTATION_DOCUMENTATION.md
│   └── OPTIMIZATION_RESULTS_ANALYSIS.md
├── output/                 # Generated files (submissions, logs, params)
│   ├── optimal_params_per_symbol.json
│   └── *_submission_*.csv
├── src/
│   ├── core/               # Core logic (legacy/utility)
│   ├── optimizers/         # Optimization scripts
│   │   └── fast_optimizer.py
│   ├── strategies/         # Strategy implementations (legacy)
│   ├── submission/         # Submission generation
│   │   └── submission_generator.py
│   ├── utils/              # Helper functions
│   │   └── indicators.py
│   └── legacy/             # Archived original scripts
└── .env                    # Environment variables (roll number)
```

## Quick Start

### 1. Setup Environment
Ensure you have Python installed and required packages:
```bash
pip install pandas numpy python-dotenv
```
Create a `.env` file in the root directory (already created):
```
STUDENT_ROLL_NUMBER=23ME3EP03
```

### 2. Run Optimization
To find the best parameters for each symbol:
```bash
python src/optimizers/fast_optimizer.py
```
This will:
- Run random search optimization (500 iterations/symbol)
- Save results to `output/optimal_params_per_symbol.json`

### 3. Generate Submission
To create the final CSV for the competition:
```bash
python src/submission/submission_generator.py
```
This will:
- Load optimized parameters
- Generate trades
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
