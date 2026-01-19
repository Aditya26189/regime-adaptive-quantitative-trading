# Future Improvements - Roadmap for Enhancement

**Author:** Aditya Singh (Roll: 23ME3EP03)  
**Current Portfolio Sharpe:** 2.276

---

## Introduction

While our submission achieved top-tier results (2.276 Sharpe, Top 3-5 ranking), there are several promising avenues for future improvement. This document outlines potential enhancements that could push performance toward 2.5-3.0 Sharpe.

---

## Short-Term Improvements (0-2 months)

### 1. Enhanced VBL Strategy

**Current Issue:** VBL has lowest Sharpe (0.657)

**Proposed Solution:** Machine Learning Regime Detection

```python
from sklearn.ensemble import RandomForestClassifier

def ml_regime_detection(data):
    """Use ML to classify market regimes more accurately"""
    features = [
        'volatility_20d',
        'volatility_5d',
        'volume_ratio',
        'price_momentum',
        'rsi_divergence'
    ]
    
    # Train classifier on historical regimes
    clf = RandomForestClassifier(n_estimators=100)
    clf.fit(X_train[features], y_train)
    
    # Predict current regime
    current_regime = clf.predict(X_current[features])
    
    return current_regime
```

**Expected Impact:** VBL Sharpe 0.65 → 0.95 (+46%)  
**Portfolio Impact:** +0.06 Sharpe points

### 2. Time-of-Day Optimization

**Observation:** Win rates vary significantly by time of day

**Proposed Solution:** Trade only during optimal hours (10:30-13:30)

```python
def is_optimal_trading_time(timestamp):
    """Check if current time is in optimal window"""
    time = timestamp.time()
    
    optimal_start = pd.Timestamp('10:30:00').time()
    optimal_end = pd.Timestamp('13:30:00').time()
    
    return optimal_start <= time <= optimal_end

# In strategy:
if signal == 'BUY' and is_optimal_trading_time(current_time):
    enter_trade()
```

**Expected Impact:** Win rate +3-5%, Sharpe +0.15  
**Trade Count:** May drop below minimum for some symbols (need testing)

### 3. Dynamic RSI Boost

**Current:** Fixed RSI boost (+3 or +4)

**Proposed:** Adaptive boost based on market conditions

```python
def calculate_dynamic_rsi_boost(volatility, trend_strength):
    """Adjust RSI boost based on market regime"""
    if volatility < 0.15:  # Low vol
        boost = 5  # More aggressive
    elif volatility < 0.30:  # Medium vol
        boost = 3  # Standard
    else:  # High vol
        boost = 1  # Conservative
    
    # Adjust for trend strength
    if trend_strength > 0.7:  # Strong trend
        boost -= 1  # Less mean reversion
    
    return max(0, boost)
```

**Expected Impact:** +0.1-0.2 Sharpe across RELIANCE/SUNPHARMA

---

## Medium-Term Improvements (2-6 months)

### 4. Multi-Strategy Ensemble per Symbol

**Current:** Single strategy per symbol

**Proposed:** Combine multiple strategies with dynamic weighting

```python
class EnsembleStrategy:
    def __init__(self):
        self.strategies = [
            HybridAdaptiveV2(rsi_boost=3),
            HybridAdaptiveV2(rsi_boost=5),
            TrendFollowing(),
            MeanReversion()
        ]
        self.weights = [0.4, 0.3, 0.2, 0.1]  # Optimize these
    
    def generate_signals(self, data):
        """Weighted vote across strategies"""
        signals = [s.generate_signals(data) for s in self.strategies]
        
        # Weighted majority vote
        buy_score = sum(w for s, w in zip(signals, self.weights) if s == 'BUY')
        sell_score = sum(w for s, w in zip(signals, self.weights) if s == 'SELL')
        
        if buy_score > 0.5:
            return 'BUY'
        elif sell_score > 0.5:
            return 'SELL'
        else:
            return 'HOLD'
```

**Expected Impact:** +0.2-0.3 Sharpe (reduces single-strategy risk)

### 5. Order Book-Based Entry Timing

**Current:** Enter at next bar open (may miss optimal price)

**Proposed:** Use order book data for smarter execution

```python
def optimal_entry_price(current_price, order_book):
    """Find optimal entry between bid-ask"""
    bid = order_book['bid_price']
    ask = order_book['ask_price']
    mid = (bid + ask) / 2
    
    # Place limit order at mid-price
    # If not filled in 30 seconds, use market order
    
    return mid  # Better than always paying ask
```

**Expected Impact:** -0.03% slippage per trade → +0.15 Sharpe

### 6. Correlation-Based Portfolio Allocation

**Current:** Equal (or near-equal) allocation across symbols

**Proposed:** Optimize allocations based on correlation matrix

```python
from scipy.optimize import minimize

def optimize_portfolio_weights(returns_df):
    """Find optimal weights maximizing Sharpe"""
    n_assets = len(returns_df.columns)
    
    def neg_sharpe(weights):
        portfolio_return = (returns_df * weights).sum(axis=1)
        sharpe = portfolio_return.mean() / portfolio_return.std()
        return -sharpe
    
    # Constraints: weights sum to 1, all positive
    constraints = {'type': 'eq', 'fun': lambda w: w.sum() - 1}
    bounds = [(0, 1) for _ in range(n_assets)]
    
    result = minimize(neg_sharpe, x0=[1/n_assets]*n_assets, 
                     constraints=constraints, bounds=bounds)
    
    return result.x
```

**Expected Impact:** +0.1-0.2 Sharpe from better diversification

---

## Long-Term Improvements (6+ months)

### 7. Deep Learning Price Prediction

**Approach:** LSTM networks for pattern recognition

```python
import torch
import torch.nn as nn

class PricePredictor(nn.Module):
    def __init__(self, input_size=10, hidden_size=50, num_layers=2):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, 1)
    
    def forward(self, x):
        out, _ = self.lstm(x)
        prediction = self.fc(out[:, -1, :])
        return prediction

# Train on historical data
# Use predictions to adjust position sizes
```

**Challenges:**
- Requires much more data (5+ years)
- High computational cost
- Risk of over-fitting

**Expected Impact:** +0.3-0.5 Sharpe (if done right)

### 8. Alternative Data Integration

**Current:** Only price/volume data

**Proposed Data Sources:**
- News sentiment (Twitter, news APIs)
- Macroeconomic indicators (GDP, inflation)
- Sectoral rotation signals
- Options flow (implied volatility)

**Example:**

```python
def incorporate_sentiment(price_signal, sentiment_score):
    """Adjust signal based on news sentiment"""
    if price_signal == 'BUY' and sentiment_score > 0.7:
        confidence = 'HIGH'  # Strong buy
    elif price_signal == 'BUY' and sentiment_score < 0.3:
        confidence = 'LOW'  # Weak buy, skip
    
    return confidence
```

**Expected Impact:** +0.2-0.4 Sharpe (better signal quality)

### 9. Reinforcement Learning Agent

**Approach:** Deep Q-Network (DQN) learns optimal trading policy

```python
import gym

class TradingEnv(gym.Env):
    """Custom trading environment for RL"""
    def __init__(self, data):
        self.data = data
        self.action_space = gym.spaces.Discrete(3)  # BUY, SELL, HOLD
        self.observation_space = gym.spaces.Box(low=-np.inf, high=np.inf, shape=(20,))
    
    def step(self, action):
        # Execute trade
        # Calculate reward
        # Return next_state, reward, done, info
        pass

# Train DQN agent
from stable_baselines3 import DQN

agent = DQN('MlpPolicy', env, verbose=1)
agent.learn(total_timesteps=100000)
```

**Expected Impact:** +0.4-0.6 Sharpe (if trained properly)  
**Risk:** Very high chance of over-fitting

---

## Infrastructure Improvements

### 10. Real-Time Backtesting

**Current:** Static historical backtest

**Proposed:** Paper trading system with live data

```python
class PaperTradingEngine:
    """Simulate live trading without risking capital"""
    
    def __init__(self, strategy, broker_api):
        self.strategy = strategy
        self.api = broker_api
        self.capital = 100000
    
    def run(self):
        """Execute strategy in real-time"""
        while market_open():
            data = self.api.get_latest_data()
            signal = self.strategy.generate_signals(data)
            
            if signal == 'BUY':
                self.simulate_buy()
            elif signal == 'SELL':
                self.simulate_sell()
            
            time.sleep(60)  # Check every minute
```

**Benefit:** Catch issues before live deployment

### 11. Automated Parameter Retuning

**Proposed:** Monthly parameter refresh

```python
def scheduled_reoptimization():
    """Re-run Optuna monthly to adapt to market changes"""
    latest_data = load_last_90_days()
    
    study = optuna.create_study(direction='maximize')
    study.optimize(objective, n_trials=200)
    
    new_params = study.best_params
    
    # Compare with current params
    if new_params_sharpe > current_sharpe * 1.1:
        update_production_params(new_params)
        send_alert("Parameters updated")
```

**Benefit:** Strategies adapt to changing markets

### 12. Risk Monitoring Dashboard

**Proposed:** Real-time monitoring of risk metrics

```python
import plotly.dash as dash

app = dash.Dash(__name__)

@app.callback(Output('drawdown-chart', 'figure'))
def update_drawdown():
    """Real-time drawdown monitoring"""
    equity = get_current_equity_curve()
    drawdown = calculate_drawdown(equity)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(y=drawdown, name='Drawdown'))
    fig.add_hline(y=-0.10, line_dash='dash', line_color='red')
    
    return fig
```

**Benefit:** Early warning system for strategy degradation

---

## Research Directions

### 13. Multi-Asset Class Extension

**Current:** Indian equities only

**Potential:**
- US equities (SPY, AAPL, TSLA)
- Cryptocurrencies (BTC, ETH)
- Commodities (Gold, Oil)
- Forex (EUR/USD, GBP/USD)

**Challenge:** Each asset class requires different strategies

### 14. Higher Frequency Trading

**Current:** 5-minute bars, intraday holding

**Proposed:** 1-minute bars, seconds-to-minutes holding

**Requirements:**
- Lower latency (co-location)
- Better execution algorithms
- More sophisticated microstructure modeling

**Expected Impact:** +0.5-1.0 Sharpe (if infrastructure supports it)

### 15. Options Strategies

**Idea:** Sell options to collect premium during low-volatility periods

```python
def volatility_selling_strategy(implied_vol, realized_vol):
    """Sell options when IV > RV"""
    if implied_vol > realized_vol * 1.2:
        # IV is expensive, sell straddle
        return 'SELL_STRADDLE'
    else:
        return 'NO_TRADE'
```

**Expected Impact:** +0.3-0.5 Sharpe (uncorrelated with equity strategies)

---

## Priority Matrix

| Improvement | Expected Impact | Implementation Effort | Priority |
|-------------|----------------|----------------------|----------|
| Enhanced VBL Strategy | +0.06 Sharpe | Low | 🔴 HIGH |
| Time-of-Day Filter | +0.15 Sharpe | Low | 🔴 HIGH |
| Dynamic RSI Boost | +0.15 Sharpe | Medium | 🟡 MEDIUM |
| Multi-Strategy Ensemble | +0.25 Sharpe | High | 🟡 MEDIUM |
| Order Book Entry | +0.15 Sharpe | Medium | 🟡 MEDIUM |
| Portfolio Optimization | +0.15 Sharpe | Medium | 🟢 LOW |
| Deep Learning | +0.40 Sharpe | Very High | 🟢 LOW |
| Alternative Data | +0.30 Sharpe | Very High | 🟢 LOW |
| RL Agent | +0.50 Sharpe | Very High | 🟢 LOW |

**Recommended Focus:** Start with high-priority, low-effort items (VBL, Time-of-Day, Dynamic RSI) for quick wins.

---

## Estimated Future Performance

**Current Baseline:** 2.276 Sharpe

**With Short-Term Improvements (2 months):**
- VBL Enhancement: +0.06
- Time-of-Day: +0.15
- Dynamic RSI Boost: +0.15
- **Projected:** 2.60 Sharpe (+14%)

**With Medium-Term Improvements (6 months):**
- Multi-Strategy Ensemble: +0.25
- Order Book Entry: +0.15
- Portfolio Optimization: +0.15
- **Projected:** 3.15 Sharpe (+38%)

**With Long-Term Improvements (12+ months):**
- Deep Learning: +0.40
- Alternative Data: +0.30
- **Projected:** 3.85 Sharpe (+69%)

**Note:** These are optimistic estimates. Real-world results may vary due to implementation challenges and market changes.

---

## Risks & Considerations

### Over-Optimization Risk

**Issue:** More complex strategies may over-fit

**Mitigation:**
- Strict walk-forward validation
- Out-of-sample testing on multiple periods
- Regular parameter refresh

### Market Regime Changes

**Issue:** Strategies optimized on 2024-2025 data may fail in 2026-2027

**Mitigation:**
- Regime-aware strategies
- Automated retuning
- Diversification across uncorrelated approaches

### Infrastructure Costs

**Issue:** Real-time data, computing, co-location are expensive

**Mitigation:**
- Start with paper trading
- Scale only if profitability proven
- Consider cloud solutions (AWS, GCP)

---

## Conclusion

Our current 2.276 Sharpe is excellent, but significant room for improvement exists:

**Quick Wins (2 months):** → 2.60 Sharpe (+14%)  
**Medium-Term (6 months):** → 3.15 Sharpe (+38%)  
**Long-Term (12+ months):** → 3.85 Sharpe (+69%)

**Key Focus Areas:**
1. Fix VBL performance (biggest weak point)
2. Exploit time-of-day patterns
3. Implement ensemble methods for robustness
4. Explore alternative data sources

**Philosophy:** Start with simple, high-ROI improvements before pursuing complex ML/RL approaches.

---

*Document Version: 1.0*  
*Last Updated: January 19, 2026*  
*Author: Aditya Singh (23ME3EP03)*
