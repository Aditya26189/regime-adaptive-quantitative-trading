"""
Volume Quality Filter - Filter low-quality setups using volume

Rule 12 Compliant: Volume itself isn't forbidden, just high/low/open
Using volume as a QUALITY filter to take only high-conviction trades.

Expected: +0.1-0.2 Sharpe per symbol by filtering noise
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')


def add_volume_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add volume-based quality metrics.
    Only take trades when volume is elevated = higher conviction moves.
    """
    df = df.copy()
    
    # Check if volume column exists
    if 'volume' not in df.columns:
        df['volume_percentile'] = 0.5  # Default to neutral
        df['volume_surge'] = False
        return df
    
    # Volume percentile (rolling)
    df['volume_percentile'] = df['volume'].rolling(100).apply(
        lambda x: (x.iloc[-1] > x).sum() / len(x) if len(x) > 0 else 0.5,
        raw=False
    )
    
    # Volume surge detection (20% above average)
    vol_avg = df['volume'].rolling(20).mean()
    df['volume_surge'] = df['volume'] > (vol_avg * 1.2)
    
    # Volume trend (is volume increasing?)
    df['volume_trend'] = df['volume'].rolling(5).mean() > df['volume'].rolling(20).mean()
    
    return df


def apply_volume_filter(df: pd.DataFrame, signals: pd.Series, 
                        min_percentile: float = 0.60) -> pd.Series:
    """
    Filter signals to only include high-volume periods.
    
    Args:
        df: DataFrame with volume metrics
        signals: Original entry signals
        min_percentile: Minimum volume percentile to take trade (0.6 = top 40% volume)
    
    Returns:
        Filtered signals
    """
    df = add_volume_metrics(df)
    
    # Only take signals when volume is elevated
    filtered_signals = signals & (df['volume_percentile'] > min_percentile)
    
    return filtered_signals


class VolumeFilteredStrategy:
    """
    Wrapper that adds volume quality filtering to any base strategy.
    """
    
    def __init__(self, base_params: Dict, volume_params: Dict = None):
        self.base_params = base_params
        self.volume_params = volume_params or {
            'min_percentile': 0.60,
            'require_surge': False,
            'require_trend': False,
        }
    
    def generate_base_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate RSI-based mean reversion signals"""
        df = df.copy()
        
        # RSI calculation
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(self.base_params.get('rsi_period', 2)).mean()
        loss = -delta.where(delta < 0, 0).rolling(self.base_params.get('rsi_period', 2)).mean()
        rs = gain / (loss + 1e-10)
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # Entry signal: RSI oversold
        df['entry_signal'] = df['RSI'] < self.base_params.get('rsi_entry', 30)
        
        # Exit signal: RSI overbought
        df['exit_signal'] = df['RSI'] > self.base_params.get('rsi_exit', 70)
        
        return df
    
    def apply_volume_filter(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply volume quality filter"""
        df = add_volume_metrics(df)
        
        # Filter entry signals by volume
        volume_condition = df['volume_percentile'] > self.volume_params['min_percentile']
        
        if self.volume_params.get('require_surge', False):
            volume_condition = volume_condition & df['volume_surge']
        
        if self.volume_params.get('require_trend', False):
            volume_condition = volume_condition & df['volume_trend']
        
        df['filtered_entry'] = df['entry_signal'] & volume_condition
        
        return df
    
    def backtest(self, symbol: str) -> Tuple[List, Dict]:
        """Run backtest with volume filtering"""
        df = pd.read_csv(f'data/raw/NSE_{symbol}_EQ_1hour.csv')
        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.sort_values('datetime').reset_index(drop=True)
        df['hour'] = df['datetime'].dt.hour
        
        # Generate and filter signals
        df = self.generate_base_signals(df)
        df = self.apply_volume_filter(df)
        
        # Backtest
        trades = []
        capital = 100000
        in_position = False
        entry_price = 0
        entry_time = None
        entry_qty = 0
        bars_held = 0
        
        max_hold = self.base_params.get('max_hold', 10)
        allowed_hours = self.base_params.get('allowed_hours', [9, 10, 11, 12, 13])
        
        for i in range(120, len(df)):
            current = df.iloc[i]
            
            if pd.isna(current['RSI']):
                continue
            
            # ENTRY (using filtered signals)
            if not in_position:
                if current['hour'] not in allowed_hours:
                    continue
                
                if current['filtered_entry']:
                    qty = int((capital - 24) * 0.95 / current['close'])
                    if qty > 0:
                        entry_price = current['close']
                        entry_time = current['datetime']
                        entry_qty = qty
                        capital -= 24
                        in_position = True
                        bars_held = 0
            
            # EXIT
            else:
                bars_held += 1
                
                exit_signal = current['exit_signal']
                time_exit = bars_held >= max_hold
                eod_exit = current['hour'] >= 15
                
                if exit_signal or time_exit or eod_exit:
                    gross_pnl = entry_qty * (current['close'] - entry_price)
                    net_pnl = gross_pnl - 48
                    capital += gross_pnl - 24
                    
                    trades.append({
                        'entry_time': entry_time,
                        'exit_time': current['datetime'],
                        'entry_price': entry_price,
                        'exit_price': current['close'],
                        'qty': entry_qty,
                        'pnl': net_pnl,
                        'bars_held': bars_held,
                    })
                    
                    in_position = False
        
        # Metrics
        if len(trades) == 0:
            return [], {'total_trades': 0, 'sharpe_ratio': -999}
        
        trades_df = pd.DataFrame(trades)
        trades_df['return_pct'] = (trades_df['pnl'] / 100000) * 100
        
        sharpe = trades_df['return_pct'].mean() / (trades_df['return_pct'].std() + 1e-10)
        
        return trades, {
            'total_trades': len(trades),
            'sharpe_ratio': sharpe,
            'total_return': (capital - 100000) / 100000 * 100,
            'win_rate': (trades_df['pnl'] > 0).mean() * 100,
        }


def test_volume_filter():
    """Test volume filtering on all symbols"""
    print("="*60)
    print("VOLUME QUALITY FILTER TEST")
    print("="*60)
    
    symbols = ['VBL', 'RELIANCE', 'SUNPHARMA', 'YESBANK']
    
    base_params = {
        'rsi_period': 2,
        'rsi_entry': 30,
        'rsi_exit': 70,
        'max_hold': 10,
    }
    
    for min_pct in [0.5, 0.6, 0.7]:
        print(f"\n--- Volume Percentile Threshold: {min_pct} ---")
        
        for symbol in symbols:
            volume_params = {'min_percentile': min_pct}
            
            strategy = VolumeFilteredStrategy(base_params, volume_params)
            trades, metrics = strategy.backtest(symbol)
            
            status = "✅" if metrics['total_trades'] >= 120 else "❌"
            print(f"  {symbol:12} Sharpe={metrics['sharpe_ratio']:.3f}, Trades={metrics['total_trades']} {status}")


if __name__ == '__main__':
    test_volume_filter()
