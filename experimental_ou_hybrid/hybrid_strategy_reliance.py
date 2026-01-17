"""
HYBRID STRATEGY RELIANCE: Experimental OU-Adaptive Strategy
Switches between Mean Reversion (OU) and Momentum (VWAP/SMA) based on regime.
"""

import pandas as pd
import numpy as np
import os
import sys

# Add project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from experimental_ou_hybrid.regime_filter import MarketRegimeClassifier, RegimeState
from experimental_ou_hybrid.ou_process import OrnsteinUhlenbeck


class HybridOURelianceStrategy:
    def __init__(self, params=None):
        self.params = params or {}
        self.ou_window = self.params.get('ou_window', 200)
        self.s_entry = self.params.get('s_entry', 2.0)
        self.s_exit = self.params.get('s_exit', 0.5)
        self.s_stop = self.params.get('s_stop', 4.0)
        self.sma_period = self.params.get('sma_period', 50)
        self.atr_period = self.params.get('atr_period', 14)
        self.atr_mult = self.params.get('atr_mult', 2.0)
        self.max_hold_bars = self.params.get('max_hold_bars', 15)
        
        self.regime_classifier = MarketRegimeClassifier(window=500)
        
    def calculate_sma(self, series, period):
        return series.rolling(window=period).mean()
        
    def calculate_atr(self, df, period):
        high = df['high'] if 'high' in df.columns else df['close']
        low = df['low'] if 'low' in df.columns else df['close']
        close = df['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=period).mean()
        
    def backtest(self, df, initial_capital=2000000.0):
        df = df.copy()
        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.sort_values('datetime').reset_index(drop=True)
        
        # Indicators
        df['returns'] = df['close'].pct_change()
        df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        df['sma'] = self.calculate_sma(df['close'], self.sma_period)
        df['atr'] = self.calculate_atr(df, self.atr_period)
        
        trades = []
        in_position = False
        entry_price = 0
        entry_time = None
        bars_held = 0
        position_side = None  # 'long' or 'short'
        entry_regime = None
        
        fee_per_order = 48
        capital = initial_capital
        
        for i in range(self.ou_window + 1, len(df)):
            current_close = df['close'].iloc[i]
            current_time = df['datetime'].iloc[i]
            current_return = df['log_returns'].iloc[i]
            
            if np.isnan(current_return):
                continue
                
            # Update regime
            regime = self.regime_classifier.update_and_classify(current_return)
            
            if in_position:
                bars_held += 1
                pct_pnl = (current_close - entry_price) / entry_price
                if position_side == 'short':
                    pct_pnl = -pct_pnl
                    
                should_exit = False
                
                # Exit logic depends on entry regime
                if entry_regime == RegimeState.MEAN_REVERSION:
                    # OU Exit: S-score crosses exit threshold
                    window_prices = df['close'].iloc[i - self.ou_window:i].values
                    ou_params = OrnsteinUhlenbeck.fit(window_prices)
                    
                    if ou_params.valid:
                        s_score = (current_close - ou_params.mu) / ou_params.sigma_eq
                        
                        if position_side == 'long' and s_score > -self.s_exit:
                            should_exit = True
                        elif position_side == 'short' and s_score < self.s_exit:
                            should_exit = True
                        elif abs(s_score) > self.s_stop:
                            should_exit = True  # Stop loss
                    else:
                        should_exit = True  # OU invalid, exit
                        
                elif entry_regime == RegimeState.MOMENTUM:
                    # Momentum Exit: Price crosses SMA or trailing stop
                    sma = df['sma'].iloc[i]
                    atr = df['atr'].iloc[i]
                    
                    if position_side == 'long':
                        trailing_stop = entry_price - self.atr_mult * atr
                        if current_close < sma or current_close < trailing_stop:
                            should_exit = True
                    elif position_side == 'short':
                        trailing_stop = entry_price + self.atr_mult * atr
                        if current_close > sma or current_close > trailing_stop:
                            should_exit = True
                            
                # Time limit
                if bars_held >= self.max_hold_bars:
                    should_exit = True
                    
                # Hard stop (2%)
                if abs(pct_pnl) > 0.02 and pct_pnl < 0:
                    should_exit = True
                    
                if should_exit:
                    exit_price = current_close
                    
                    if position_side == 'long':
                        pnl = (exit_price - entry_price) * qty - fee_per_order
                    else:
                        pnl = (entry_price - exit_price) * qty - fee_per_order
                        
                    capital += pnl
                    
                    trades.append({
                        'symbol': 'RELIANCE',
                        'entry_time': entry_time,
                        'exit_time': current_time,
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'qty': qty,
                        'side': position_side,
                        'regime': entry_regime.name,
                        'pnl': pnl,
                        'return_pct': pct_pnl * 100
                    })
                    
                    in_position = False
                    position_side = None
                    entry_regime = None
                    
            else:
                # Entry logic
                if regime == RegimeState.MEAN_REVERSION:
                    # OU Entry
                    window_prices = df['close'].iloc[i - self.ou_window:i].values
                    ou_params = OrnsteinUhlenbeck.fit(window_prices)
                    
                    if ou_params.valid and ou_params.half_life < 50:  # Reasonable half-life
                        s_score = (current_close - ou_params.mu) / ou_params.sigma_eq
                        
                        qty = int((initial_capital * 0.95 - fee_per_order) / current_close)
                        
                        if s_score < -self.s_entry and qty > 0:
                            # Long entry (price below mean)
                            entry_price = current_close
                            entry_time = current_time
                            bars_held = 0
                            in_position = True
                            position_side = 'long'
                            entry_regime = regime
                            
                        elif s_score > self.s_entry and qty > 0:
                            # Short entry (price above mean) - but we only do long for simplicity
                            pass
                            
                elif regime == RegimeState.MOMENTUM:
                    # Momentum Entry
                    sma = df['sma'].iloc[i]
                    
                    if not np.isnan(sma):
                        qty = int((initial_capital * 0.95 - fee_per_order) / current_close)
                        
                        if current_close > sma and qty > 0:
                            entry_price = current_close
                            entry_time = current_time
                            bars_held = 0
                            in_position = True
                            position_side = 'long'
                            entry_regime = regime
                            
        # Calculate metrics
        metrics = {}
        if trades:
            tdf = pd.DataFrame(trades)
            metrics['total_trades'] = len(tdf)
            metrics['avg_return'] = tdf['return_pct'].mean()
            
            returns = tdf['return_pct'] / 100
            if returns.std() > 0:
                metrics['sharpe_ratio'] = (returns.mean() / returns.std()) * np.sqrt(len(tdf))
            else:
                metrics['sharpe_ratio'] = 0.0
                
            metrics['win_rate'] = len(tdf[tdf['pnl'] > 0]) / len(tdf)
            metrics['regime_breakdown'] = tdf['regime'].value_counts().to_dict()
        else:
            metrics['total_trades'] = 0
            metrics['sharpe_ratio'] = 0.0
            
        return trades, metrics
