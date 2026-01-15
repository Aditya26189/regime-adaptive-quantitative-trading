# Convolve 4.0 - Quantitative Trading Infrastructure

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A production-quality quantitative trading infrastructure built for the **Convolve 4.0** competition, sponsored by Quadeye (high-frequency trading firm).

## 🚀 Features

- **Event-driven backtester** - Tick-by-tick processing with no lookahead bias
- **Sophisticated risk management** - Position limits, drawdown circuit breakers, volatility filters
- **Comprehensive signal library** - Z-score, momentum, OBI, microprice deviation
- **Train/test split evaluation** - Detect overfitting before submission
- **Parameter grid search** - Automated parameter optimization
- **Professional visualization** - Equity curves, drawdown charts, returns distribution
- **Pre-submission validation** - Automated checklist for competition readiness

---

## 📁 Project Structure

```
conclave/
├── config.py                      # System-wide configuration
├── requirements.txt               # Python dependencies
├── QUICKSTART.md                  # Competition day workflow
│
├── src/
│   ├── core/                      # Core backtesting engine
│   │   ├── backtester.py         # Event-driven tick processor
│   │   ├── risk_manager.py       # Risk gates (position/drawdown/vol)
│   │   └── metrics.py            # Performance metrics (Sharpe, Sortino, etc.)
│   │
│   ├── data/                      # Data handling
│   │   ├── loader.py             # CSV loading + validation
│   │   ├── features.py           # Feature engineering
│   │   └── noise_filters.py      # Data cleaning (outliers, bounces, spikes)
│   │
│   ├── signals/                   # Signal generators
│   │   ├── price_based.py        # Z-score, momentum, mean reversion
│   │   ├── flow_based.py         # OBI, microprice deviation
│   │   └── regime_based.py       # Volatility/trend/spread filters
│   │
│   ├── execution/                 # Strategy execution
│   │   ├── strategy.py           # Signal + risk combiner
│   │   └── ensemble.py           # Multi-signal ensemble voting
│   │
│   ├── evaluation/                # Performance analysis
│   │   └── signal_analysis.py    # Information Coefficient (IC) analysis
│   │
│   └── visualization/             # Plotting
│       └── plotter.py            # Charts and dashboards
│
├── scripts/
│   ├── run_pipeline.py           # Main execution script
│   ├── grid_search.py            # Parameter optimization
│   ├── walk_forward.py           # Overfitting detection
│   └── validate_submission.py    # Pre-submission checks
│
└── tests/
    └── test_integration.py       # Integration tests
```

---

## 🚀 New Advanced Components

### Noise Filtering
Clean dirty market data before analysis:
```bash
python -c "from src.data.noise_filters import NoiseFilter; ..."
```
- Removes price outliers (5σ)
- Smooths bid-ask bounces
- Flags volume spikes
- Validates timestamps

### Walk-Forward Optimization
Detect overfitting with rolling windows:
```bash
python scripts/walk_forward.py --data data.csv --strategy z_score
```
- Tests parameters across multiple time periods
- Reports degradation % (ideal: <20%)
- Warns when overfitting is high

### Signal IC Analysis
Measure predictive power of signals:
```bash
python -m src.evaluation.signal_analysis --data data.csv
```
- Computes Spearman correlation with forward returns
- Shows regime-specific IC (CALM/NORMAL/VOLATILE)
- Recommends which signals to use

### Ensemble Strategy
Combine multiple signals for robustness:
```python
from src.execution.ensemble import EnsembleStrategy
ensemble = EnsembleStrategy([(obi_signal, {}), (z_score_signal, {})])
```
- Weighted voting across signals
- IC-weighted ensembles
- Minimum agreement threshold



## 🛠️ Installation

### Prerequisites
- Python 3.12+
- Virtual environment (recommended)

### Setup

```bash
# Clone the repository
cd conclave

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate    # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

**Dependencies:**
- `numpy` - Numerical computations
- `pandas` - Data handling
- `matplotlib` - Visualization

---

## 📊 Usage

### Basic Backtest

```bash
python scripts/run_pipeline.py \
    --data data/raw/market_data.csv \
    --strategy z_score \
    --plot
```

### Available Strategies

| Strategy | Type | Best For |
|----------|------|----------|
| `z_score` | Mean Reversion | Range-bound markets |
| `momentum` | Trend Following | Trending markets |
| `mean_reversion` | Simple MR | Quick reversions |
| `obi` | Order Flow | Order book data |
| `microprice` | Flow-based | Volume-weighted signals |

### Train/Test Split Evaluation

Detect overfitting by evaluating on separate train/test sets:

```bash
python scripts/run_pipeline.py \
    --data data/raw/market_data.csv \
    --strategy z_score \
    --eval-mode split \
    --train-ratio 0.7
```

**Output:**
```
IN-SAMPLE (Training) METRICS
Sharpe              :     0.85
Max DD              :   -12.3%

OUT-OF-SAMPLE (Test) METRICS
Sharpe              :     0.62  [Warning: 27% degradation]
Max DD              :   -18.5%
```

### Parameter Optimization

Find optimal parameters using grid search:

```bash
python scripts/grid_search.py \
    --data data/raw/market_data.csv \
    --strategy z_score \
    --top-n 5
```

**Output:**
```
TOP 5 PARAMETER COMBINATIONS
#1
   Parameters: {'window': 20, 'entry_z': 2.5, 'exit_z': 0.5}
   Sharpe:     0.8234
   Max DD:     -8.12%
   ...
```

### Regime Filter Comparison

Compare performance with/without volatility filtering:

```bash
python scripts/run_pipeline.py \
    --data data/raw/market_data.csv \
    --strategy z_score \
    --compare-regime-filter
```

**Output:**
```
REGIME FILTER COMPARISON
Metric          No Filter    With Filter    Change
Sharpe             0.45         0.62        +38%
Max DD           -18.2%       -12.1%        +33%
...
Recommendation: USE REGIME FILTER ✅
```

### Pre-Submission Validation

Run automated checks before submitting:

```bash
python scripts/validate_submission.py
```

**Checks:**
- ✅ All required files present
- ✅ Code imports without errors
- ✅ Test pipeline completes
- ✅ Metrics within reasonable bounds
- ✅ No NaN/Inf values

---

## ⚙️ Configuration

Edit `config.py` to customize parameters:

```python
class Config:
    # Backtesting
    INITIAL_CASH = 100000
    MAKER_FEE = 0.0002  # 2 bps
    TAKER_FEE = 0.0002
    
    # Risk Management
    MAX_POSITION = 100
    MAX_DRAWDOWN = 0.15  # 15% circuit breaker
    VOL_THRESHOLD = 0.01
    
    # Signals
    LOOKBACK_WINDOW = 20
    ENTRY_Z_THRESHOLD = 2.0
    EXIT_Z_THRESHOLD = 0.5
```

---

## 📈 CLI Reference

### `run_pipeline.py` Options

```bash
--data PATH              Path to CSV file (required)
--strategy NAME          Strategy to use (default: z_score)
--eval-mode MODE         'full' or 'split' (default: full)
--train-ratio FLOAT      Train/test split ratio (default: 0.7)
--max-position INT       Max position size (default: 100)
--max-drawdown FLOAT     Max DD before halt (default: 0.15)
--trade-qty INT          Quantity per trade (default: 1)
--use-regime-filter      Enable volatility filter
--compare-regime-filter  Compare with/without filter
--plot                   Generate charts
--debug                  Enable debug output
```

### `grid_search.py` Options

```bash
--data PATH              Path to CSV file (required)
--strategy NAME          Strategy to optimize (default: z_score)
--max-position INT       Max position size (default: 100)
--top-n INT              Number of top results (default: 5)
--output-dir PATH        Output directory (default: results/)
```

---

## 🏗️ Architecture Details

### Event-Driven Backtester

Processes data **tick-by-tick** to avoid lookahead bias:

```python
for tick in market_data:
    signal = strategy.get_signal(tick, history)
    if risk_manager.can_trade(signal, position, equity):
        execute_trade(tick, signal)
    update_equity(tick)
```

### Risk Management

All trades pass through risk gates:

1. **Drawdown check** - Halt if equity falls > 15% from peak
2. **Position limits** - Enforce max long/short positions
3. **Volatility filter** - Reduce trading in high-volatility periods

### Signal Generation

Modular signal functions return `'BUY'`, `'SELL'`, `'CLOSE'`, or `None`:

```python
def z_score_signal(data, window=20, entry_z=2.0, exit_z=0.5):
    z = (price - rolling_mean) / rolling_std
    if z < -entry_z: return 'BUY'
    if z > entry_z: return 'SELL'
    if abs(z) < exit_z: return 'CLOSE'
    return None
```

---

## 🧪 Testing

Run the full integration test suite:

```bash
python tests/test_integration.py
```

**Tests:**
- DataLoader (CSV loading, validation, schema detection)
- FeatureEngine (returns, volatility, OBI, microprice)
- Signals (z_score, momentum, OBI, regimes)
- RiskManager (position limits, drawdown, volatility)
- Backtester (tick processing, trades, equity)
- MetricsCalculator (Sharpe, Sortino, max DD)
- End-to-end integration

---

## 📝 Performance Metrics

| Metric | Formula | Interpretation |
|--------|---------|----------------|
| **Sharpe Ratio** | `mean(returns) / std(returns) * √periods` | Risk-adjusted return (>1 is good) |
| **Sortino Ratio** | `mean(returns) / std(downside) * √periods` | Downside risk-adjusted return |
| **Max Drawdown** | `min((equity - peak) / peak)` | Worst peak-to-trough decline |
| **Calmar Ratio** | `annual_return / |max_drawdown|` | Return per unit of drawdown risk |
| **Win Rate** | `winning_trades / total_trades` | Percentage of profitable trades |
| **Profit Factor** | `sum(gains) / sum(losses)` | Gross profit / gross loss (>1 is profitable) |

---

## 🎯 Competition Workflow

See **[QUICKSTART.md](QUICKSTART.md)** for detailed competition day workflow.

**Quick version:**
1. Load competition data
2. Run grid search for best parameters
3. Evaluate with train/test split
4. Run validation checks
5. Submit!

---

## 📚 Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - Competition day guide
- **[config.py](config.py)** - All configurable parameters
- **[walkthrough.md](.gemini/antigravity/brain/.../walkthrough.md)** - Technical walkthrough

---

## 🤝 Contributing

This is a competition project. After the competition, contributions are welcome!

---

## 📄 License

MIT License - See LICENSE file for details

---

## 🏆 Built For

**Convolve 4.0 - Quantitative Finance Track**  
Sponsored by **Quadeye** (High-Frequency Trading Firm)

---

## 💡 Key Design Principles

1. **Correctness over cleverness** - Simple, working code beats clever, broken code
2. **No lookahead bias** - Event-driven processing ensures realistic simulation
3. **Risk-first** - All trades gated through risk management
4. **Modular** - Easy to add new strategies, signals, or features
5. **Explainable** - Clear logic, extensive docstrings, no black boxes
6. **Production-quality** - Type hints, error handling, comprehensive testing

---

**Built with ❤️ for algorithmic trading**
