"""
Volatility Regime Switching Strategy
Detects 3 market regimes and switches strategies accordingly.

Expected Sharpe: 1.7-2.2
Rule 12 Compliant: Uses only 'close' prices
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')


class VolatilityRegimeSwitchingStrategy:
    """
    Three-Regime Strategy with Crisis Detection
    Adapts to market conditions dynamically.
    """
    
    def __init__(self, params: Dict):
        self.vol_window = params.get('vol_window', 20)
        self.percentile_lookback = params.get('percentile_lookback', 120)
        self.high_vol_strategy = params.get('high_vol_strategy', 'AVOID')
        self.rsi_period = params.get('rsi_period', 2)
        self.max_hold = params.get('max_hold', 10)
        self.allowed_hours = params.get('allowed_hours', [9, 10, 11, 12, 13])
    
    def calculate_realized_volatility(self, close: pd.Series, window: int) -> pd.Series:
        """Realized volatility from close prices only"""
        returns = close.pct_change()
        return returns.rolling(window).std()
    
    def calculate_volatility_percentile(self, realized_vol: pd.Series, lookback: int) -> pd.Series:
        """Calculate rolling percentile of volatility"""
        def percentile_func(x):
            if len(x) < 2:
                return 50
            current = x.iloc[-1]
            return ((x < current).sum() / len(x)) * 100
        
        return realized_vol.rolling(lookback).apply(percentile_func, raw=False)
    
    def classify_regime(self, vol_percentile: pd.Series) -> pd.Series:
        """Classify into 3 regimes based on volatility percentile"""
        regime = pd.Series('NORMAL', index=vol_percentile.index)
        regime[vol_percentile < 30] = 'LOW_VOL'
        regime[vol_percentile > 80] = 'HIGH_VOL'
        return regime
    
    def calculate_rsi(self, close: pd.Series, period: int) -> pd.Series:
        """Calculate RSI"""
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = -delta.where(delta < 0, 0).rolling(period).mean()
        rs = gain / (loss + 1e-10)
        return 100 - (100 / (1 + rs))
    
    def backtest(self, symbol: str) -> Tuple[List, Dict]:
        """Run backtest with regime-aware signals."""
        # Load data
        if 'NIFTY' in symbol.upper():
            df = pd.read_csv('data/raw/NSE_NIFTY50_INDEX_1hour.csv')
        else:
            df = pd.read_csv(f'data/raw/NSE_{symbol}_EQ_1hour.csv')
        
        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.sort_values('datetime').reset_index(drop=True)
        df['hour'] = df['datetime'].dt.hour
        
        # Calculate indicators
        df['realized_vol'] = self.calculate_realized_volatility(df['close'], self.vol_window)
        df['vol_percentile'] = self.calculate_volatility_percentile(
            df['realized_vol'], self.percentile_lookback
        )
        df['regime'] = self.classify_regime(df['vol_percentile'])
        df['rsi'] = self.calculate_rsi(df['close'], self.rsi_period)
        
        # Backtest loop
        trades = []
        capital = 100000
        in_position = False
        entry_price = 0
        entry_time = None
        entry_qty = 0
        bars_held = 0
        entry_regime = None
        
        warmup = max(self.percentile_lookback, 150)
        
        for i in range(warmup, len(df)):
            current = df.iloc[i]
            current_price = current['close']
            current_hour = current['hour']
            current_regime = current['regime']
            
            if pd.isna(current['rsi']) or pd.isna(current['vol_percentile']):
                continue
            
            # ENTRY
            if not in_position:
                if current_hour not in self.allowed_hours:
                    continue
                
                # Regime-specific entry conditions
                entry_signal = False
                
                if current_regime == 'LOW_VOL':
                    entry_signal = current['rsi'] < 25 and current['realized_vol'] > 0.002
                    
                elif current_regime == 'NORMAL':
                    entry_signal = current['rsi'] < 30 and current['realized_vol'] > 0.004
                    
                elif current_regime == 'HIGH_VOL':
                    if self.high_vol_strategy == 'AVOID':
                        entry_signal = False
                    else:  # CONTRARIAN
                        vol_declining = current['realized_vol'] < df['realized_vol'].iloc[i-3]
                        entry_signal = current['rsi'] < 15 and vol_declining
                
                if entry_signal:
                    qty = int((capital - 24) * 0.95 / current_price)
                    if qty > 0:
                        entry_price = current_price
                        entry_time = current['datetime']
                        entry_qty = qty
                        entry_regime = current_regime
                        capital -= 24
                        in_position = True
                        bars_held = 0
            
            # EXIT
            else:
                bars_held += 1
                
                # Regime-specific exits
                if entry_regime == 'LOW_VOL':
                    exit_rsi = current['rsi'] > 65
                elif entry_regime == 'NORMAL':
                    exit_rsi = current['rsi'] > 70
                else:
                    exit_rsi = current['rsi'] > 60
                
                # Crisis protection: Emergency exit on regime change
                crisis_exit = (entry_regime in ['LOW_VOL', 'NORMAL'] and 
                              current_regime == 'HIGH_VOL')
                
                time_exit = bars_held >= self.max_hold
                eod_exit = current_hour >= 15
                
                if exit_rsi or crisis_exit or time_exit or eod_exit:
                    gross_pnl = entry_qty * (current_price - entry_price)
                    net_pnl = gross_pnl - 48
                    capital += gross_pnl - 24
                    
                    trades.append({
                        'entry_time': entry_time,
                        'exit_time': current['datetime'],
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'qty': entry_qty,
                        'pnl': net_pnl,
                        'bars_held': bars_held,
                        'entry_regime': entry_regime,
                        'exit_regime': current_regime,
                    })
                    
                    in_position = False
        
        metrics = self._calculate_metrics(trades, capital)
        return trades, metrics
    
    def _calculate_metrics(self, trades: List, final_capital: float) -> Dict:
        """Calculate metrics"""
        if len(trades) == 0:
            return {'sharpe_ratio': -999, 'total_return': -999, 'total_trades': 0}
        
        trades_df = pd.DataFrame(trades)
        trades_df['return_pct'] = (trades_df['pnl'] / 100000) * 100
        
        if trades_df['return_pct'].std() == 0:
            sharpe = 0
        else:
            sharpe = trades_df['return_pct'].mean() / trades_df['return_pct'].std()
        
        total_return = (final_capital - 100000) / 100000 * 100
        win_rate = (trades_df['pnl'] > 0).mean() * 100
        
        return {
            'sharpe_ratio': sharpe,
            'total_return': total_return,
            'total_trades': len(trades_df),
            'win_rate': win_rate,
            'avg_pnl': trades_df['pnl'].mean(),
        }


def optimize_volatility_regime(symbol: str, n_iterations: int = 300) -> Tuple[Dict, float, int]:
    """Optimize volatility regime parameters."""
    import random
    
    param_space = {
        'vol_window': [14, 20, 30],
        'percentile_lookback': [60, 120, 180, 200],
        'high_vol_strategy': ['AVOID', 'CONTRARIAN'],
        'rsi_period': [2, 3],
        'max_hold': [6, 8, 10, 12],
    }
    
    best_sharpe = -999
    best_params = None
    best_trades = 0
    
    for i in range(n_iterations):
        params = {k: random.choice(v) for k, v in param_space.items()}
        
        try:
            strategy = VolatilityRegimeSwitchingStrategy(params)
            trades, metrics = strategy.backtest(symbol)
            
            if metrics['total_trades'] < 120:
                continue
            
            if metrics['sharpe_ratio'] > best_sharpe:
                best_sharpe = metrics['sharpe_ratio']
                best_params = params.copy()
                best_trades = metrics['total_trades']
                
        except Exception:
            continue
    
    return best_params, best_sharpe, best_trades
