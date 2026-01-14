# Convolve 4.0 - Quick Start Guide

## When Problem Statement Drops (9:00 AM)

### Phase 1: Data Loading (5 minutes)
1. Download data from Unstop
2. Place in `data/raw/market_data.csv`
3. Run baseline:
```bash
.\venv\Scripts\activate
python scripts/run_pipeline.py --data data/raw/market_data.csv --strategy z_score
```
4. Note baseline Sharpe: ____

### Phase 2: Strategy Selection (20 minutes)
Test all strategies:
```bash
python scripts/run_pipeline.py --data data/raw/market_data.csv --strategy z_score --plot
python scripts/run_pipeline.py --data data/raw/market_data.csv --strategy momentum --plot
python scripts/run_pipeline.py --data data/raw/market_data.csv --strategy obi --plot
python scripts/run_pipeline.py --data data/raw/market_data.csv --strategy microprice --plot
```
Compare Sharpe ratios, pick top 2.

### Phase 3: Parameter Tuning (30 minutes)
```bash
python scripts/grid_search.py --data data/raw/market_data.csv --strategy z_score
```
Use best parameters from output.

### Phase 4: Validation (15 minutes)
```bash
python scripts/run_pipeline.py --data data/raw/market_data.csv --strategy z_score --eval-mode split
```
Check train vs test Sharpe - should be within 30%.

### Phase 5: Final Submission (30 minutes)
1. Generate plots with best strategy
2. Export trades: Check `results/` folder
3. Write explanation in notebook
4. Submit files

---

## Available Strategies
| Strategy | Type | Best For |
|----------|------|----------|
| `z_score` | Mean Reversion | Range-bound markets |
| `momentum` | Trend Following | Trending markets |
| `mean_reversion` | Simple MR | Quick mean reversion |
| `obi` | Order Flow | Order book data |
| `microprice` | Flow | Volume-weighted signals |

---

## CLI Quick Reference

### Basic Run
```bash
python scripts/run_pipeline.py --data DATA.csv --strategy STRATEGY --plot
```

### With Risk Parameters
```bash
python scripts/run_pipeline.py --data DATA.csv --strategy z_score \
    --max-position 50 --max-drawdown 0.10 --trade-qty 1
```

### Train/Test Split
```bash
python scripts/run_pipeline.py --data DATA.csv --strategy z_score --eval-mode split
```

### Grid Search
```bash
python scripts/grid_search.py --data DATA.csv --strategy z_score --top-n 10
```

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| Negative prices | Bad data | Check `loader.validate()` output |
| Sharpe = 0 | No variance | Increase trading or check data |
| Circuit breaker | Max DD hit | Increase `--max-drawdown` |
| No trades | Risk too strict | Lower thresholds or increase signals |
| NaN in results | Empty arrays | Check data has enough rows |

---

## File Locations

| File | Purpose |
|------|---------|
| `config.py` | All parameters |
| `results/metrics_*.csv` | Performance metrics |
| `results/trades_*.csv` | Trade log |
| `results/dashboard_*.png` | Equity/drawdown plots |
| `results/grid_search_*.csv` | Optimization results |

---

## Final Checklist
- [ ] Strategy runs without errors
- [ ] Sharpe ratio is reasonable (> 0.3)
- [ ] Max drawdown is acceptable (< 20%)
- [ ] Train/test Sharpe within 30%
- [ ] Plots generated
- [ ] Trades exported
- [ ] Code is commented
