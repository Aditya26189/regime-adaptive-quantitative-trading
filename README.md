# 📈 Algorithmic Trading Strategy Framework

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

> **A sophisticated algorithmic trading framework implementing adaptive mean-reversion strategies for Indian equity markets**

Built for competitive quantitative trading with emphasis on robustness, reproducibility, and production-grade code quality.

---

## 🎯 Project Overview

This repository contains a comprehensive algorithmic trading system developed for the **IIT Kharagpur Quant Games 2026**. The framework implements multiple trading strategies with a focus on short-term mean reversion in large-cap Indian equities.

### Key Highlights

- **Portfolio Sharpe Ratio:** 1.486
- **Best Strategy Performance:** 3.132 (SUNPHARMA)
- **Total Strategies Implemented:** 17+
- **Production-Ready Codebase:** ~3,500+ lines
- **Comprehensive Testing:** Multiple validation frameworks

---

## 🚀 Key Features

### Advanced Trading Strategies

- **Hybrid Adaptive V2:** Volatility-adaptive mean reversion with dynamic holding periods
- **Enhanced Regime Switching:** Market regime detection with Hurst exponent analysis
- **Adaptive Bollinger Bands:** Dynamic band calculation based on market volatility
- **Statistical Arbitrage:** Pairs trading and cointegration-based strategies
- **Ensemble Methods:** Multi-strategy combination with intelligent weighting

### Technical Capabilities

- ✅ **Rule-Compliant:** Strict adherence to Close/Volume only constraints
- ⚡ **High Performance:** Optimized backtesting engine with parallel processing
- 📊 **Advanced Analytics:** Comprehensive performance metrics and visualizations
- 🔄 **Reproducible:** Deterministic parameter optimization with seed control
- 🎯 **Production-Grade:** Modular architecture with comprehensive error handling

---

## 📁 Repository Structure

```
LSTM/
├── 📂 src/                      # Core source code
│   ├── strategies/              # Trading strategy implementations
│   ├── optimization/            # Parameter optimization modules
│   ├── utils/                   # Utility functions and helpers
│   ├── validation/              # Validation and compliance checks
│   └── submission/              # Submission file generators
├── 📂 config/                   # Configuration files
│   ├── settings.py              # Project settings
│   └── sharpe_config.py         # Sharpe calculation configuration
├── 📂 data/                     # Data directory
│   └── raw/                     # Raw market data files
├── 📂 docs/                     # Comprehensive documentation
│   ├── ADVANCED_METHODOLOGY.md  # Strategy methodology
│   ├── STRATEGY_ANALYTICS.md    # Performance analysis
│   ├── STRATEGY_DEFENSE.md      # Strategy rationale
│   └── USER_GUIDE.md            # User guide and tutorials
├── 📂 scripts/                  # Utility scripts
├── 📂 experiments/              # Research and experimentation
├── 📂 optimization_results/     # Optimization outputs
├── 📂 output/                   # Generated outputs
└── 📂 reports/                  # Analysis reports and visualizations
```

---

## 🛠️ Installation

### Prerequisites

- Python 3.10 or higher
- pip package manager
- Virtual environment (recommended)

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone https://github.com/Aditya26189/LSTM.git
   cd LSTM
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure settings**
   ```bash
   # Edit config/settings.py with your configuration
   # Set up data paths and parameters
   ```

---

## 📊 Quick Start

### Running a Basic Backtest

```python
from src.strategies.hybrid_adaptive_v2 import HybridAdaptiveV2
from src.utils.data_loader import load_market_data

# Load data
data = load_market_data('SUNPHARMA')

# Initialize strategy
strategy = HybridAdaptiveV2(params={
    'rsi_period': 2,
    'rsi_entry': 30,
    'rsi_exit': 70,
    'max_hold': 10,
    'adaptive_enabled': True
})

# Run backtest
trades, metrics = strategy.backtest(data)
print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.3f}")
```

### Generating Submission Files

```bash
python generate_final_submission_files.py
```

Output files will be generated in `output/` directory.

---

## 💡 Core Innovation: Volatility-Adaptive Holding

The breakthrough feature of our system is the **dynamic time-warping mechanism**:

> **"Don't fight the volatility. Use it."**

### How It Works

- **Low Volatility Regime:** Extended holding periods (up to 18 hours) allow mean reversion to fully materialize
- **High Volatility Regime:** Shortened holding periods (5-8 hours) capture quick snap-backs while minimizing tail risk

This innovation alone improved SUNPHARMA Sharpe from **2.12 → 3.132**

### Technical Implementation

```python
def calculate_adaptive_hold_period(volatility, base_hold=10):
    """
    Dynamically adjust holding period based on market volatility
    
    Args:
        volatility: Current market volatility measure
        base_hold: Base holding period (default: 10)
    
    Returns:
        Adjusted holding period
    """
    vol_percentile = get_volatility_percentile(volatility)
    
    if vol_percentile < 25:  # Low volatility
        return base_hold * 1.8
    elif vol_percentile > 75:  # High volatility
        return base_hold * 0.5
    else:  # Normal regime
        return base_hold
```

---

## 📈 Performance Metrics

### Strategy Performance Summary

| Symbol | Strategy | Sharpe Ratio | Total Trades | Win Rate |
|--------|----------|--------------|--------------|----------|
| SUNPHARMA | Hybrid Adaptive V2 | **3.132** | 145 | 62.8% |
| RELIANCE | Hybrid Adaptive V2 | 1.824 | 132 | 58.3% |
| VBL | Enhanced Regime | 1.456 | 128 | 55.1% |
| YESBANK | Volume Momentum | 1.123 | 134 | 51.2% |
| NIFTY50 | Trend Following | 0.987 | 115 | 49.6% |

### Portfolio Statistics

- **Combined Sharpe Ratio:** 1.486
- **Total Trades:** 654
- **Average Win Rate:** 55.4%
- **Maximum Drawdown:** -12.3%
- **Profit Factor:** 1.67

---

## 🔬 Strategy Implementations

### 1. Hybrid Adaptive V2 (Primary Strategy)

**File:** `src/strategies/hybrid_adaptive_v2.py`

**Description:** Mean reversion strategy with volatility-adaptive holding periods and dynamic RSI thresholds.

**Key Features:**
- RSI(2) based entry/exit signals
- Volatility regime detection
- Adaptive position sizing
- Risk-adjusted profit targets

### 2. Enhanced Regime Switching

**File:** `src/strategies/enhanced_regime_strategy.py`

**Description:** Market regime detection using Hurst exponent and adaptive parameter adjustment.

**Key Features:**
- Hurst exponent calculation for trend/mean-reversion detection
- Dynamic RSI bands
- Regime-specific position management

### 3. Adaptive Bollinger Bands

**File:** `src/strategies/adaptive_bb_strategy.py`

**Description:** Volatility bands with adaptive width calculation.

**Key Features:**
- Dynamic band width adjustment
- Volume confirmation
- Multi-timeframe analysis

### 4. Statistical Arbitrage

**File:** `src/strategies/stat_arb_strategy.py`

**Description:** Pairs trading with cointegration testing.

**Key Features:**
- Augmented Dickey-Fuller testing
- Z-score based entry/exit
- Hedged position management

---

## 🎯 Optimization Framework

### Parallel Optimization

The framework includes a sophisticated parallel optimization system using Optuna:

```bash
python src/optimization/parallel_optimizer.py --symbol SUNPHARMA --trials 500
```

**Features:**
- Multi-objective optimization (Sharpe, trade count, drawdown)
- Bayesian parameter search
- Parallel trial execution
- Cross-validation to prevent overfitting

### Parameter Spaces

All strategy parameters are defined in `src/optimization/parameter_space.py`:

```python
PARAMETER_SPACES = {
    'hybrid_adaptive_v2': {
        'rsi_period': [2, 3, 5],
        'rsi_entry': [25, 30, 35],
        'rsi_exit': [65, 70, 75],
        'max_hold': [8, 10, 12, 15],
        'vol_window': [10, 15, 20],
        'adaptive_enabled': [True, False]
    }
}
```

---

## 📚 Documentation

### Available Documents

1. **[USER_GUIDE.md](docs/USER_GUIDE.md)** - Comprehensive user guide and tutorials
2. **[ADVANCED_METHODOLOGY.md](docs/ADVANCED_METHODOLOGY.md)** - Detailed strategy methodology
3. **[STRATEGY_ANALYTICS.md](docs/STRATEGY_ANALYTICS.md)** - Performance analysis and metrics
4. **[STRATEGY_DEFENSE.md](docs/STRATEGY_DEFENSE.md)** - Strategy rationale and justification
5. **[VISUAL_ANALYSIS.md](docs/VISUAL_ANALYSIS.md)** - Visual analysis and charts

### API Documentation

Detailed API documentation is available in the `docs/api/` directory (auto-generated from docstrings).

---

## 🧪 Testing & Validation

### Running Tests

```bash
# Run all validation tests
python -m pytest tests/

# Run specific strategy validation
python src/validation/validate_strategy.py --strategy hybrid_adaptive_v2

# Check Rule 12 compliance
python src/validation/rule12_validator.py
```

### Compliance Checks

The framework includes comprehensive validation:

- ✅ Trade count verification (minimum 120 trades per symbol)
- ✅ Rule 12 compliance (Close/Volume only)
- ✅ Cost calculation validation
- ✅ Sharpe ratio verification
- ✅ Data integrity checks

---

## 📊 Visualization & Analytics

### Generating Reports

```bash
# Generate equity curves
python scripts/generate_equity_curves.py

# Create performance dashboard
python scripts/generate_dashboard.py

# Export trade analysis
python scripts/export_trade_analysis.py
```

### Sample Visualizations

- Cumulative returns curves
- Drawdown analysis
- Trade distribution heatmaps
- Parameter sensitivity analysis
- Volatility regime transitions

---

## 🔧 Advanced Usage

### Custom Strategy Development

1. Create a new strategy file in `src/strategies/`
2. Inherit from `BaseStrategy` class
3. Implement required methods:
   - `generate_signals()`
   - `backtest()`
   - `calculate_metrics()`

```python
from src.strategies.base_strategy import BaseStrategy

class MyCustomStrategy(BaseStrategy):
    def __init__(self, params):
        super().__init__(params)
    
    def generate_signals(self, df):
        # Implement your signal logic
        pass
    
    def backtest(self, df):
        # Implement backtesting logic
        pass
```

### Parameter Optimization

```python
from src.optimization.optimizer import optimize_strategy

results = optimize_strategy(
    strategy_name='my_custom_strategy',
    symbol='SUNPHARMA',
    n_trials=300,
    objective='sharpe_ratio'
)
```

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Workflow

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Code Standards

- Follow PEP 8 style guidelines
- Add docstrings to all functions and classes
- Include unit tests for new features
- Update documentation as needed

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👥 Team

**Team 23ME3EP03** | IIT Kharagpur

- Quantitative Research & Strategy Development
- Algorithm Implementation & Optimization
- Backtesting & Validation

---

## 📧 Contact

For questions, suggestions, or collaboration opportunities:

- **GitHub:** [Aditya26189](https://github.com/Aditya26189)
- **Repository:** [LSTM](https://github.com/Aditya26189/LSTM)

---

## 🙏 Acknowledgments

- IIT Kharagpur for organizing the Quant Games 2026
- The quantitative finance community for inspiration and knowledge sharing
- Open-source contributors whose libraries made this project possible

---

## 📖 Citation

If you use this code in your research or projects, please cite:

```bibtex
@software{lstm_trading_framework,
  author = {Team 23ME3EP03},
  title = {Algorithmic Trading Strategy Framework},
  year = {2026},
  publisher = {GitHub},
  url = {https://github.com/Aditya26189/LSTM}
}
```

---

## 🔗 Related Projects

- [Quantitative Trading Resources](https://github.com/wilsonfreitas/awesome-quant)
- [Python for Finance](https://github.com/yhilpisch/py4fi2nd)
- [Algorithmic Trading Strategies](https://github.com/topics/algorithmic-trading)

---

<div align="center">

**[Documentation](docs/) • [Issues](https://github.com/Aditya26189/LSTM/issues) • [Discussions](https://github.com/Aditya26189/LSTM/discussions)**

Made with ❤️ by Team 23ME3EP03

</div>
