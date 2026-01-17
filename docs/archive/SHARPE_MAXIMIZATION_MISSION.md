# Sharpe Maximization Mission

## 🎯 Objective
Improve Portfolio Sharpe Ratio from **1.267** to **1.40+** through systematic, Optuna-driven optimization.

---

## 📊 Baseline Metrics (Pre-Optimization)

| Symbol | Sharpe | Trades | Strategy |
|--------|--------|--------|----------|
| VBL | 1.161 | 127 | Hybrid (Single) |
| RELIANCE | 1.644 | 121 | Deep Optimized |
| SUNPHARMA | 1.840 | 144 | Mean Reversion |
| YESBANK | 1.278 | 122 | Hybrid |
| NIFTY50 | 0.006 | 132 | Trend Following |
| **PORTFOLIO** | **1.186** (Core) / **1.267** (Ensemble) | **646** | Mixed |

---

## 🔧 Optimization Phases

### Phase 1: Dynamic RSI Bands
**Expected Gain:** +0.10 Sharpe

**Technique:**
Replace static RSI thresholds (30/70) with volatility-adaptive bands:
```
RSI_lower = mean(RSI, window) - std_mult × std(RSI, window)
RSI_upper = mean(RSI, window) + std_mult × std(RSI, window)
```

**Parameters Optimized:**
- `dynamic_rsi_window`: 10-40
- `dynamic_rsi_std`: 1.3-2.5
- `rsi_period`: 2-5
- `vol_min_pct`: 0.003-0.012

**Files Modified:**
- `src/utils/indicators.py` - Added `calculate_dynamic_rsi_bands()`
- `src/strategies/hybrid_adaptive.py` - Integrated dynamic bands

---

### Phase 2: Snap-Back Confirmation
**Expected Gain:** +0.05 Sharpe

**Technique:**
Wait for price reversal confirmation before entry (avoid "falling knives"):
1. Setup: RSI was below lower band
2. Momentum: RSI turning up
3. Confirmation: Price closes higher than previous

**Parameters Optimized:**
- `use_snapback`: True/False
- Band width compensation (wider bands to maintain trade count)

---

### Phase 3: Enhanced NIFTY Strategy
**Expected Gain:** +0.10 Sharpe

**Technique:**
Multi-confirmation trend following with ADX (calculated from close prices only):
- Long-term trend: Price > EMA(50)
- Short-term trend: EMA(8) > EMA(21)
- Trend strength: ADX > threshold
- Entry: Pullback to fast EMA or breakout

**Parameters Optimized:**
- `ema_fast`, `ema_mid`, `ema_slow`
- `adx_period`, `adx_threshold`
- `momentum_period`

**Files Created:**
- `src/strategies/nifty_advanced_trend.py`

---

### Phase 4: Ensemble SUNPHARMA
**Expected Gain:** +0.05 Sharpe

**Technique:**
Apply 5-variant voting system to reduce variance:
- Run 5 parameter variants simultaneously
- Enter only when ≥3 agree on signal

**Parameters Optimized:**
- `n_variants`: 5-7
- `min_agreement`: 2-4

---

### Phase 5: Final Validation
- Generate final submission CSV
- Run compliance checks (trade counts, fees, Rule 12)
- Create documentation

---

## 📈 Expected Outcomes

| Phase | Cumulative Sharpe | Change |
|-------|-------------------|--------|
| Baseline | 1.267 | - |
| Phase 1 | 1.35-1.38 | +0.08 to +0.11 |
| Phase 2 | 1.38-1.43 | +0.03 to +0.05 |
| Phase 3 | 1.43-1.50 | +0.05 to +0.10 |
| Phase 4 | 1.45-1.52 | +0.02 to +0.05 |
| **FINAL** | **1.40-1.52** | **+0.13 to +0.25** |

---

## 🔒 Hard Constraints

| Constraint | Requirement | Enforcement |
|------------|-------------|-------------|
| Min Trades | ≥120 per symbol | Return `-1000` in Optuna if violated |
| Max Drawdown | ≤25% | Return `-500` in Optuna if violated |
| Rule 12 | Close prices only | Code review + grep check |
| Fees | ₹48 per round-trip | Applied in backtest |

---

## 🛠️ Key Scripts

| Script | Purpose |
|--------|---------|
| `baseline_measurement.py` | Lock in current performance |
| `optimize_dynamic_rsi.py` | Phase 1 optimization |
| `optimize_snapback.py` | Phase 2 optimization |
| `optimize_nifty_advanced.py` | Phase 3 optimization |
| `optimize_ensemble_sunpharma.py` | Phase 4 optimization |
| `generate_final_submission.py` | Create final CSV |
| `validate_compliance.py` | Check all rules |
| `master_execute.py` | Run all phases automatically |

---

## 📁 Output Files

- `baseline_metrics.json` - Starting point
- `phase1_dynamic_rsi_results.json` - Phase 1 results
- `phase2_snapback_results.json` - Phase 2 results
- `phase3_nifty_results.json` - Phase 3 results
- `phase4_ensemble_results.json` - Phase 4 results
- `output/sharpe_optimized_params_phase[N].json` - Cumulative params
- `output/23ME3EP03_final_submission_*.csv` - Final submission

---

## 🎯 Success Criteria

✅ Portfolio Sharpe ≥ 1.40  
✅ All symbols ≥ 120 trades  
✅ No high/low/open prices used  
✅ Transaction costs applied  
✅ Validated submission CSV generated
