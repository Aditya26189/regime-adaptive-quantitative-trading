"""
Hybrid Adaptive Strategy - Switches between Mean Reversion and Trend Following
Based on Kaufman Efficiency Ratio (KER) regime detection
Optimized for Sharpe Ratio with outlier capping

Rule 12 Compliant: Uses ONLY close prices
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import sys
import os

# Add paths for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.regime_detection import RegimeDetector
from utils.indicators import calculate_rsi, calculate_volatility

class HybridAdaptiveStrategy:
    """
    Adaptive strategy that switches between:
    - Mean Reversion (low KER - choppy markets)
    - Trend Following (high KER - efficient trends)
    
    With outlier capping for competition compliance.
    """
    
    def __init__(self, params: Dict):
        self.params = params
        self.regime_detector = RegimeDetector()
        self.max_return_cap = params.get('max_return_cap', 5.0)  # Cap at 5%
    
    def _calculate_ema(self, close: pd.Series, span: int) -> pd.Series:
        """Exponential Moving Average"""
        return close.ewm(span=span, adjust=False).mean()
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate signals with regime-based switching"""
        df = df.copy()
        
        # Calculate KER for regime detection
        ker_period = self.params.get('ker_period', 10)
        df['KER'] = self.regime_detector.calculate_ker(df['close'], ker_period)
        
        # Regime thresholds
        ker_threshold_meanrev = self.params.get('ker_threshold_meanrev', 0.30)
        ker_threshold_trend = self.params.get('ker_threshold_trend', 0.50)
        
        # Classify regime
        df['regime'] = 'MIXED'
        df.loc[df['KER'] < ker_threshold_meanrev, 'regime'] = 'MEAN_REV'
        df.loc[df['KER'] > ker_threshold_trend, 'regime'] = 'TREND'
        
        # === MEAN REVERSION INDICATORS ===
        rsi_period = self.params.get('rsi_period', 2)
        df['RSI'] = calculate_rsi(df['close'], rsi_period)
        
        rsi_entry = self.params.get('rsi_entry', 30)
        rsi_exit = self.params.get('rsi_exit', 70)
        
        # Volatility filter
        vol_lookback = self.params.get('vol_lookback', 14)
        df['volatility'] = calculate_volatility(df['close'], vol_lookback)
        vol_min = self.params.get('vol_min_pct', 0.005)
        vol_filter = df['volatility'] > vol_min
        
        # Mean reversion signal
        meanrev_long = (df['RSI'].shift(1) < rsi_entry) & vol_filter
        
        # === TREND FOLLOWING INDICATORS ===
        ema_fast = self.params.get('ema_fast', 8)
        ema_slow = self.params.get('ema_slow', 21)
        df['ema_fast'] = self._calculate_ema(df['close'], ema_fast)
        df['ema_slow'] = self._calculate_ema(df['close'], ema_slow)
        df['trend_up'] = df['ema_fast'] > df['ema_slow']
        
        # Momentum pulse
        price_change = df['close'].diff()
        pulse_mult = self.params.get('trend_pulse_mult', 0.4)
        vol_std = df['close'].rolling(14).std()
        df['pulse_up'] = price_change > (pulse_mult * vol_std)
        
        trend_long = df['trend_up'] & df['pulse_up']
        
        # === REGIME-SPECIFIC SIGNALS ===
        df['signal_long_meanrev'] = meanrev_long & (df['regime'] == 'MEAN_REV')
        df['signal_long_trend'] = trend_long & (df['regime'] == 'TREND')
        
        # Combined signal
        df['signal_long'] = df['signal_long_meanrev'] | df['signal_long_trend']
        
        # Track signal source
        df['signal_source'] = 'NONE'
        df.loc[df['signal_long_meanrev'], 'signal_source'] = 'MEANREV'
        df.loc[df['signal_long_trend'], 'signal_source'] = 'TREND'
        
        return df
    
    def backtest(self, df: pd.DataFrame, initial_capital: float = 100000) -> Tuple[List[Dict], Dict]:
        """Backtest with regime-aware exits and outlier capping"""
        df = self.generate_signals(df)
        
        # Ensure datetime column
        if 'datetime' not in df.columns and df.index.name == 'datetime':
            df = df.reset_index()
        
        trades = []
        capital = initial_capital
        
        in_position = False
        entry_strategy = None
        entry_price = 0
        entry_time = None
        entry_capital = 0
        entry_qty = 0
        bars_held = 0
        
        fee_per_order = 24
        max_hold = self.params.get('max_hold_bars', 10)
        allowed_hours = self.params.get('allowed_hours', [9, 10, 11, 12, 13])
        rsi_exit = self.params.get('rsi_exit', 70)
        
        for i in range(50, len(df)):
            current_time = df['datetime'].iloc[i]
            current_hour = current_time.hour
            current_minute = current_time.minute
            current_close = df['close'].iloc[i]
            
            # === ENTRY ===
            if not in_position:
                if current_hour not in allowed_hours:
                    continue
                if current_hour >= 14 and current_minute >= 30:
                    continue
                
                if df['signal_long'].iloc[i]:
                    qty = int((capital - fee_per_order) * 0.95 / current_close)
                    
                    if qty > 0:
                        entry_price = current_close
                        entry_time = current_time
                        entry_capital = capital
                        entry_qty = qty
                        capital -= fee_per_order
                        in_position = True
                        entry_strategy = df['signal_source'].iloc[i]
                        bars_held = 0
            
            # === EXIT ===
            else:
                bars_held += 1
                
                # Calculate current return
                current_return_pct = ((current_close - entry_price) / entry_price) * 100
                
                # Outlier cap exit - exit if return exceeds cap
                outlier_exit = current_return_pct >= self.max_return_cap
                
                # Regime-specific exit
                if entry_strategy == 'MEANREV':
                    target_exit = df['RSI'].iloc[i] > rsi_exit
                elif entry_strategy == 'TREND':
                    # Exit when price crosses below fast EMA
                    target_exit = current_close < df['ema_fast'].iloc[i]
                else:
                    target_exit = False
                
                time_exit = bars_held >= max_hold
                eod_exit = (current_hour >= 15 and current_minute >= 15)
                
                if target_exit or outlier_exit or time_exit or eod_exit:
                    exit_price = current_close
                    exit_time = current_time
                    
                    gross_pnl = entry_qty * (exit_price - entry_price)
                    net_pnl = gross_pnl - (2 * fee_per_order)
                    capital = entry_capital + gross_pnl - (2 * fee_per_order)
                    
                    trades.append({
                        'entry_time': entry_time,
                        'exit_time': exit_time,
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'qty': entry_qty,
                        'strategy': entry_strategy,
                        'pnl': net_pnl,
                        'capital': capital,
                        'bars_held': bars_held,
                        'return_pct': ((exit_price - entry_price) / entry_price) * 100,
                        'outlier_capped': outlier_exit,
                    })
                    
                    in_position = False
        
        metrics = self._calculate_metrics(trades, initial_capital, capital)
        return trades, metrics
    
    def _calculate_metrics(self, trades: List[Dict], initial_capital: float, final_capital: float) -> Dict:
        """Calculate comprehensive metrics including Sharpe ratio"""
        if len(trades) == 0:
            return {
                'total_trades': 0,
                'total_return_pct': 0,
                'sharpe_ratio': 0,
                'max_drawdown_pct': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'final_capital': final_capital,
            }
        
        trades_df = pd.DataFrame(trades)
        
        total_trades = len(trades_df)
        total_return_pct = (final_capital - initial_capital) / initial_capital * 100
        winning_trades = (trades_df['pnl'] > 0).sum()
        win_rate = (winning_trades / total_trades) * 100
        
        total_wins = trades_df[trades_df['pnl'] > 0]['pnl'].sum()
        total_losses = abs(trades_df[trades_df['pnl'] < 0]['pnl'].sum())
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        # Sharpe ratio
        returns = (trades_df['pnl'] / initial_capital) * 100
        
        if returns.std() > 0 and len(returns) > 1:
            # Annualize: assume ~6 trading hours/day, ~250 days/year
            trades_per_year = 1500 / (len(trades_df) / 250) if len(trades_df) > 0 else 1
            sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(min(trades_per_year, 252))
        else:
            sharpe_ratio = 0
        
        # Maximum drawdown
        capital_curve = trades_df['capital'].values
        running_max = np.maximum.accumulate(capital_curve)
        drawdown = (capital_curve - running_max) / running_max * 100
        max_drawdown_pct = drawdown.min()
        
        # Strategy breakdown
        meanrev_trades = (trades_df['strategy'] == 'MEANREV').sum()
        trend_trades = (trades_df['strategy'] == 'TREND').sum()
        capped_trades = trades_df['outlier_capped'].sum() if 'outlier_capped' in trades_df else 0
        
        return {
            'total_trades': total_trades,
            'meanrev_trades': meanrev_trades,
            'trend_trades': trend_trades,
            'capped_trades': capped_trades,
            'total_return_pct': total_return_pct,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown_pct': max_drawdown_pct,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'final_capital': final_capital,
            'avg_trade_pnl': trades_df['pnl'].mean(),
            'max_return': trades_df['return_pct'].max(),
            'min_return': trades_df['return_pct'].min(),
        }


def test_hybrid_strategy():
    """Test the hybrid strategy on a single symbol"""
    import pandas as pd
    
    # Test on NIFTY50 (the problem child)
    df = pd.read_csv('data/raw/NSE_NIFTY50_INDEX_1hour.csv')
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.sort_values('datetime').reset_index(drop=True)
    
    # Test params focused on trend-following for NIFTY50
    params = {
        'ker_period': 12,
        'ker_threshold_meanrev': 0.20,  # Strict - rarely mean revert
        'ker_threshold_trend': 0.35,    # Lower - favor trends
        'rsi_period': 2,
        'rsi_entry': 32,
        'rsi_exit': 65,
        'vol_min_pct': 0.008,
        'ema_fast': 8,
        'ema_slow': 21,
        'trend_pulse_mult': 0.4,
        'allowed_hours': [9, 10, 11, 12, 13],
        'max_hold_bars': 5,
        'max_return_cap': 5.0,
    }
    
    strategy = HybridAdaptiveStrategy(params)
    trades, metrics = strategy.backtest(df)
    
    print("="*70)
    print("HYBRID STRATEGY TEST - NIFTY50")
    print("="*70)
    print(f"Total Trades: {metrics['total_trades']}")
    print(f"  - Mean Reversion: {metrics['meanrev_trades']}")
    print(f"  - Trend Following: {metrics['trend_trades']}")
    print(f"  - Outlier Capped: {metrics['capped_trades']}")
    print(f"Return: {metrics['total_return_pct']:.2f}%")
    print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.3f}")
    print(f"Max Drawdown: {metrics['max_drawdown_pct']:.2f}%")
    print(f"Win Rate: {metrics['win_rate']:.1f}%")
    print(f"Max Trade Return: {metrics['max_return']:.2f}%")
    print(f"Min Trade Return: {metrics['min_return']:.2f}%")
    
    if metrics['total_trades'] >= 120:
        print(f"✅ Trade count: {metrics['total_trades']} (>= 120)")
    else:
        print(f"❌ Trade count: {metrics['total_trades']} (< 120)")
    
    return trades, metrics


if __name__ == "__main__":
    test_hybrid_strategy()
