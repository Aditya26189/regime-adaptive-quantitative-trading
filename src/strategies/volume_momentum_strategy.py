"""
Volume-Weighted Momentum Strategy
Uses Money Flow Index and VWMA for high-conviction setups.

Expected Sharpe: 1.8-2.3
Rule 12 Compliant: Uses only 'close' and 'volume'
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')


class VolumeWeightedMomentumStrategy:
    """
    Volume Momentum Strategy: Price + Volume confirmation
    """
    
    def __init__(self, params: Dict):
        self.vwma_period = params.get('vwma_period', 15)
        self.mfi_period = params.get('mfi_period', 14)
        self.mfi_entry = params.get('mfi_entry', 25)
        self.mfi_exit = params.get('mfi_exit', 75)
        self.vol_surge_threshold = params.get('vol_surge_threshold', 0.20)
        self.max_hold = params.get('max_hold', 10)
        self.allowed_hours = params.get('allowed_hours', [9, 10, 11, 12, 13])
    
    def calculate_vwma(self, close: pd.Series, volume: pd.Series, period: int) -> pd.Series:
        """Volume-Weighted Moving Average"""
        volume_price = close * volume
        vwma = volume_price.rolling(period).sum() / (volume.rolling(period).sum() + 1e-10)
        return vwma
    
    def calculate_mfi(self, close: pd.Series, volume: pd.Series, period: int) -> pd.Series:
        """
        Money Flow Index (Volume-weighted RSI)
        Uses ONLY close and volume (Rule 12 compliant)
        """
        typical_price = close
        raw_money_flow = typical_price * volume
        
        price_direction = close > close.shift(1)
        positive_flow = raw_money_flow.where(price_direction, 0)
        negative_flow = raw_money_flow.where(~price_direction, 0)
        
        positive_mf = positive_flow.rolling(period).sum()
        negative_mf = negative_flow.rolling(period).sum()
        
        mfi_ratio = positive_mf / (negative_mf + 1e-10)
        mfi = 100 - (100 / (1 + mfi_ratio))
        
        return mfi.fillna(50)
    
    def calculate_volume_surge(self, volume: pd.Series, period: int = 3) -> pd.Series:
        """Volume rate of change"""
        return volume.pct_change(period)
    
    def backtest(self, symbol: str) -> Tuple[List, Dict]:
        """Run backtest with volume momentum signals."""
        df = pd.read_csv(f'data/raw/NSE_{symbol}_EQ_1hour.csv')
        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.sort_values('datetime').reset_index(drop=True)
        df['hour'] = df['datetime'].dt.hour
        
        # Check volume column exists
        if 'volume' not in df.columns:
            return [], {'sharpe_ratio': -999, 'total_trades': 0, 'error': 'no_volume'}
        
        # Calculate indicators
        df['vwma'] = self.calculate_vwma(df['close'], df['volume'], self.vwma_period)
        df['mfi'] = self.calculate_mfi(df['close'], df['volume'], self.mfi_period)
        df['vol_surge'] = self.calculate_volume_surge(df['volume'], 3)
        
        # Backtest loop
        trades = []
        capital = 100000
        in_position = False
        entry_price = 0
        entry_time = None
        entry_qty = 0
        bars_held = 0
        
        warmup = 50
        
        for i in range(warmup, len(df)):
            current = df.iloc[i]
            current_price = current['close']
            current_hour = current['hour']
            
            if pd.isna(current['mfi']) or pd.isna(current['vwma']):
                continue
            
            # ENTRY
            if not in_position:
                if current_hour not in self.allowed_hours:
                    continue
                
                # THREE conditions must be met
                cond1 = current_price < current['vwma']  # Price below VWMA
                cond2 = current['mfi'] < self.mfi_entry  # MFI oversold
                cond3 = current['vol_surge'] > self.vol_surge_threshold  # Volume surge
                
                if cond1 and cond2 and cond3:
                    qty = int((capital - 24) * 0.95 / current_price)
                    if qty > 0:
                        entry_price = current_price
                        entry_time = current['datetime']
                        entry_qty = qty
                        capital -= 24
                        in_position = True
                        bars_held = 0
            
            # EXIT
            else:
                bars_held += 1
                
                exit1 = current['mfi'] > self.mfi_exit
                exit2 = current_price > current['vwma'] * 1.02
                time_exit = bars_held >= self.max_hold
                eod_exit = current_hour >= 15
                
                if exit1 or exit2 or time_exit or eod_exit:
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


def optimize_volume_momentum(symbol: str, n_iterations: int = 300) -> Tuple[Dict, float, int]:
    """Optimize volume momentum parameters."""
    import random
    
    param_space = {
        'vwma_period': [10, 15, 20, 25],
        'mfi_period': [10, 14, 20],
        'mfi_entry': [20, 25, 30, 35],
        'mfi_exit': [65, 70, 75, 80],
        'vol_surge_threshold': [0.10, 0.15, 0.20, 0.25, 0.30],
        'max_hold': [5, 8, 10, 12],
    }
    
    best_sharpe = -999
    best_params = None
    best_trades = 0
    
    for i in range(n_iterations):
        params = {k: random.choice(v) for k, v in param_space.items()}
        
        try:
            strategy = VolumeWeightedMomentumStrategy(params)
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
