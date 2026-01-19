# Quick Reference Guide

> Fast access to common tasks and important information

---

## 🚀 Quick Start (30 seconds)

```bash
git clone https://github.com/Aditya26189/LSTM.git
cd LSTM
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python generate_final_submission_files.py
```

---

## 📁 Important Files

| File | Purpose |
|------|---------|
| [README.md](README.md) | Project overview |
| [docs/USER_GUIDE.md](docs/USER_GUIDE.md) | How to use |
| [docs/API_REFERENCE.md](docs/API_REFERENCE.md) | API docs |
| [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) | Executive summary |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to contribute |

---

## 🎯 Common Tasks

### Run a Backtest

```python
from src.strategies.hybrid_adaptive_v2 import HybridAdaptiveV2
from src.utils.data_loader import load_market_data

data = load_market_data('SUNPHARMA')
strategy = HybridAdaptiveV2(params={'rsi_period': 2})
trades, metrics = strategy.backtest(data)
print(f"Sharpe: {metrics['sharpe_ratio']:.3f}")
```

### Optimize Parameters

```bash
python src/optimization/parallel_optimizer.py --symbol SUNPHARMA --trials 300
```

### Generate Submission

```bash
python generate_final_submission_files.py
```

### Validate Results

```bash
python src/validation/validate_all.py
```

---

## 📊 Key Metrics

| Metric | Value |
|--------|-------|
| Portfolio Sharpe | 1.486 |
| Best Symbol | SUNPHARMA (3.132) |
| Total Trades | 654 |
| Strategies | 17+ |

---

## 🔧 Configuration

### Key Settings

```python
# config/settings.py
SYMBOLS_CONFIG = {
    'SUNPHARMA': {
        'file': 'data/raw/NSE_SUNPHARMA_EQ_1hour.csv',
        'type': 'mean_reverting'
    }
}
```

### Strategy Parameters

```python
params = {
    'rsi_period': 2,
    'rsi_entry': 30,
    'rsi_exit': 70,
    'max_hold': 10,
    'adaptive_enabled': True
}
```

---

## 📚 Documentation Map

```
docs/
├── README.md              # Documentation index
├── INSTALLATION.md        # Setup guide
├── USER_GUIDE.md          # How-to guide
├── API_REFERENCE.md       # API docs
├── ARCHITECTURE.md        # System design
├── ADVANCED_METHODOLOGY.md # Strategy details
├── STRATEGY_ANALYTICS.md   # Performance
├── STRATEGY_DEFENSE.md     # Rationale
└── VISUAL_ANALYSIS.md      # Charts
```

---

## 🐛 Troubleshooting

### Import Error
```bash
export PYTHONPATH="${PYTHONPATH}:/path/to/LSTM"
```

### Module Not Found
```bash
pip install -r requirements.txt
```

### Data Not Found
```bash
# Place CSV files in data/raw/
ls data/raw/
```

---

## 💡 Pro Tips

1. **Use absolute paths** in configuration
2. **Cache data** for faster loading
3. **Parallel optimization** with `n_jobs=-1`
4. **Validate early** to catch issues
5. **Document changes** in CHANGELOG.md

---

## 🔗 Quick Links

- [GitHub Repo](https://github.com/Aditya26189/LSTM)
- [Issues](https://github.com/Aditya26189/LSTM/issues)
- [Documentation](docs/README.md)
- [API Reference](docs/API_REFERENCE.md)

---

## 📞 Getting Help

1. Check [FAQ](docs/USER_GUIDE.md#part-4-faq)
2. Search [Issues](https://github.com/Aditya26189/LSTM/issues)
3. Read [Documentation](docs/README.md)
4. Open new issue

---

## ⚡ Keyboard Shortcuts (in docs)

- `Ctrl+F` - Search in document
- `Ctrl+K` - Create link (GitHub)
- `Ctrl+B` - Bold text
- `Ctrl+I` - Italic text

---

## 📝 Quick Commands

```bash
# Install
pip install -r requirements.txt

# Test
python -m pytest tests/

# Format
black src/

# Lint
flake8 src/

# Run
python generate_final_submission_files.py

# Optimize
python src/optimization/parallel_optimizer.py

# Validate
python src/validation/validate_all.py
```

---

## 🎨 Code Snippets

### Load Data
```python
data = pd.read_csv('data/raw/SUNPHARMA.csv')
```

### Calculate Sharpe
```python
from src.utils.metrics import calculate_sharpe_ratio
sharpe = calculate_sharpe_ratio(returns)
```

### Run Strategy
```python
strategy = HybridAdaptiveV2(params)
trades, metrics = strategy.backtest(data)
```

---

## 📈 Performance Checklist

- [ ] Sharpe > 1.0
- [ ] Trades > 120
- [ ] Win rate > 50%
- [ ] Max drawdown < 20%
- [ ] Rule 12 compliant

---

## 🎯 Interview Talking Points

1. **Innovation:** Volatility-adaptive holding
2. **Performance:** 3.132 Sharpe on SUNPHARMA
3. **Code Quality:** 3,500+ lines, PEP 8
4. **Documentation:** 12+ comprehensive docs
5. **Testing:** Full validation framework

---

## 🏆 Key Features

- ✅ 17+ strategies
- ✅ Bayesian optimization
- ✅ Parallel processing
- ✅ Professional docs
- ✅ Production-ready

---

*For detailed information, see [Full Documentation](docs/README.md)*
