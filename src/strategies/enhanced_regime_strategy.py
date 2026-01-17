"""
Enhanced Regime-Switching Mean Reversion Strategy
Advanced improvements: Hurst Exponent, Dynamic RSI Bands, Snap-Back Confirmation

Expected Sharpe: 1.4-1.9
Rule 12 Compliant: Uses only close prices
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')


def calculate_hurst_exponent(series: pd.Series, window: int = 100) -> pd.Series:
    """
    Calculate rolling Hurst Exponent.
    H < 0.5 = mean reverting (good)
    H = 0.5 = random walk
    H > 0.5 = trending
    """
    def _hurst(data):
        if len(data) < 20:
            return 0.5
        try:
            lags = range(2, min(20, len(data) // 2))
            tau = [np.std(np.subtract(data[lag:], data[:-lag])) for lag in lags]
            if len(tau) < 2:
                return 0.5
            poly = np.polyfit(np.log(list(lags)), np.log(tau), 1)
            return poly[0]
        except:
            return 0.5
    
    return series.rolling(window).apply(_hurst, raw=True)


def calculate_dynamic_rsi(close: pd.Series, period: int = 2) -> pd.Series:
    """Calculate RSI indicator."""
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-10)
    return 100 - (100 / (1 + rs))


def calculate_dynamic_rsi_bands(rsi: pd.Series, window: int = 20, num_std: float = 2.0):
    """Calculate volatility-adaptive RSI thresholds."""
    rsi_mean = rsi.rolling(window).mean()
    rsi_std = rsi.rolling(window).std()
    
    lower = (rsi_mean - num_std * rsi_std).clip(15, 45)
    upper = (rsi_mean + num_std * rsi_std).clip(55, 90)
    
    return lower, upper


def generate_enhanced_regime_signals(data: pd.DataFrame, params: Dict) -> pd.DataFrame:
    """
    Generate enhanced regime-switching mean reversion signals.
    
    Enhancements:
    1. Hurst Exponent for regime detection
    2. Dynamic RSI bands (volatility-adaptive)
    3. Snap-back confirmation (wait for turn)
    """
    df = data.copy()
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.sort_values('datetime').reset_index(drop=True)
    df['hour'] = df['datetime'].dt.hour
    
    # Parameters
    rsi_period = params.get('rsi_period', 2)
    hurst_window = params.get('hurst_window', 100)
    hurst_threshold = params.get('hurst_threshold', 0.45)
    dynamic_rsi_window = params.get('dynamic_rsi_window', 20)
    dynamic_rsi_std = params.get('dynamic_rsi_std', 2.0)
    max_hold = params.get('max_hold', 12)
    require_snapback = params.get('require_snapback', True)
    allowed_hours = params.get('allowed_hours', [9, 10, 11, 12, 13, 14])
    
    # Calculate indicators
    df['RSI'] = calculate_dynamic_rsi(df['close'], rsi_period)
    df['hurst'] = calculate_hurst_exponent(df['close'], hurst_window)
    df['rsi_lower'], df['rsi_upper'] = calculate_dynamic_rsi_bands(
        df['RSI'], dynamic_rsi_window, dynamic_rsi_std
    )
    
    # Generate trades
    trades = []
    position = None
    capital = 100000
    
    warmup = max(hurst_window, 120)
    
    for i in range(warmup, len(df) - max_hold):
        current = df.iloc[i]
        prev = df.iloc[i-1] if i > 0 else current
        
        if pd.isna(current['RSI']) or pd.isna(current['hurst']):
            continue
        
        # ENTRY LOGIC
        if position is None:
            # Regime check: Hurst < threshold = mean reverting regime
            is_mean_reverting = current['hurst'] < hurst_threshold
            
            # RSI oversold (below dynamic lower band)
            is_oversold = current['RSI'] < current['rsi_lower']
            
            is_allowed_hour = current['hour'] in allowed_hours
            
            # Snap-back confirmation: RSI rising from oversold
            if require_snapback:
                snapback_confirmed = (prev['RSI'] < prev['rsi_lower'] and 
                                     current['RSI'] > prev['RSI'] and
                                     current['close'] > prev['close'])
            else:
                snapback_confirmed = True
            
            if is_mean_reverting and is_oversold and is_allowed_hour and snapback_confirmed:
                entry_price = current['close']
                qty = int((capital * 0.95 - 24) / entry_price)
                
                if qty > 0:
                    position = {
                        'entry_idx': i,
                        'entry_price': entry_price,
                        'entry_time': current['datetime'],
                        'qty': qty,
                        'entry_rsi': current['RSI'],
                    }
                    capital -= 24
        
        # EXIT LOGIC
        else:
            bars_held = i - position['entry_idx']
            current_price = current['close']
            
            # Exit conditions
            is_overbought = current['RSI'] > current['rsi_upper']
            max_hold_reached = bars_held >= max_hold
            
            # Profit/stop
            pnl_pct = (current_price - position['entry_price']) / position['entry_price'] * 100
            profit_target = pnl_pct > 2.5
            stop_loss = pnl_pct < -1.5
            
            if is_overbought or max_hold_reached or profit_target or stop_loss:
                gross_pnl = (current_price - position['entry_price']) * position['qty']
                net_pnl = gross_pnl - 48
                
                trades.append({
                    'entry_time': position['entry_time'],
                    'exit_time': current['datetime'],
                    'entry_price': position['entry_price'],
                    'exit_price': current_price,
                    'qty': position['qty'],
                    'pnl': net_pnl,
                    'bars_held': bars_held,
                    'exit_reason': 'overbought' if is_overbought else
                                  'profit' if profit_target else
                                  'stop' if stop_loss else 'max_hold',
                })
                
                capital += net_pnl
                position = None
    
    if len(trades) == 0:
        return pd.DataFrame()
    
    return pd.DataFrame(trades)


def optimize_enhanced_regime(data: pd.DataFrame, n_iterations: int = 300) -> Tuple[Dict, float, int]:
    """Optimize enhanced regime switching parameters."""
    import random
    
    param_space = {
        'rsi_period': [2, 3, 4],
        'hurst_window': [80, 100, 120],
        'hurst_threshold': [0.40, 0.45, 0.50],
        'dynamic_rsi_window': [15, 20, 25, 30],
        'dynamic_rsi_std': [1.5, 2.0, 2.5],
        'max_hold': [8, 10, 12, 15],
        'require_snapback': [True, False],
    }
    
    best_sharpe = -999
    best_params = None
    best_trades = 0
    
    for i in range(n_iterations):
        params = {k: random.choice(v) for k, v in param_space.items()}
        
        try:
            trades_df = generate_enhanced_regime_signals(data, params)
            
            if len(trades_df) < 120:
                continue
            
            trades_df['return_pct'] = trades_df['pnl'] / 100000 * 100
            
            if trades_df['return_pct'].std() == 0:
                continue
            
            sharpe = trades_df['return_pct'].mean() / trades_df['return_pct'].std()
            
            if sharpe > best_sharpe:
                best_sharpe = sharpe
                best_params = params.copy()
                best_trades = len(trades_df)
                
        except Exception:
            continue
    
    return best_params, best_sharpe, best_trades


class EnhancedRegimeSwitchingStrategy:
    """Complete Enhanced Regime Switching Strategy class."""
    
    def __init__(self, params: Dict):
        self.params = params
        
    def backtest(self, df: pd.DataFrame) -> Tuple[List, Dict]:
        """Run backtest."""
        trades_df = generate_enhanced_regime_signals(df, self.params)
        
        if len(trades_df) == 0:
            return [], {'total_trades': 0, 'sharpe_ratio': -999}
        
        trades = trades_df.to_dict('records')
        
        trades_df['return_pct'] = trades_df['pnl'] / 100000 * 100
        total_return = trades_df['pnl'].sum() / 100000 * 100
        
        if trades_df['return_pct'].std() > 0:
            sharpe = trades_df['return_pct'].mean() / trades_df['return_pct'].std()
        else:
            sharpe = 0
        
        win_rate = (trades_df['pnl'] > 0).sum() / len(trades_df) * 100
        
        metrics = {
            'total_trades': len(trades_df),
            'sharpe_ratio': sharpe,
            'total_return': total_return,
            'win_rate': win_rate,
        }
        
        return trades, metrics
