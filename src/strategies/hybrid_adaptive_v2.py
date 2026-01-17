"""
Hybrid Adaptive Strategy V2 - ALL ADVANCED TECHNIQUES
Integrates:
1. Dynamic Position Sizing (Kelly Criterion)
2. Multi-Timeframe Confluence
3. Profit Taking Ladders
4. Adaptive Hold Periods
5. Dynamic RSI Bands

Target: 1.85-2.00 Sharpe (from 1.268 baseline)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.regime_detection import RegimeDetector
from utils.indicators import calculate_rsi, calculate_volatility, calculate_dynamic_rsi_bands
from utils.position_sizing import calculate_dynamic_position_size, get_rolling_performance
from utils.profit_ladder import PositionManager, get_profit_ladder_thresholds
from utils.adaptive_hold import calculate_adaptive_max_hold
from utils.multi_timeframe import calculate_daily_bias, filter_by_daily_bias


class HybridAdaptiveStrategyV2:
    """
    Enhanced Hybrid Strategy with all 5 advanced techniques.
    """
    
    def __init__(self, params: Dict):
        self.params = params
        self.regime_detector = RegimeDetector()
        self.max_return_cap = params.get('max_return_cap', 5.0)
    
    def _calculate_ema(self, close: pd.Series, span: int) -> pd.Series:
        return close.ewm(span=span, adjust=False).mean()
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate signals with all advanced filters."""
        df = df.copy()
        
        # === MULTI-TIMEFRAME FILTER ===
        use_mtf = self.params.get('use_multi_timeframe', False)
        if use_mtf:
            daily_ema = self.params.get('daily_ema_period', 50)
            df = calculate_daily_bias(df, daily_ema)
        else:
            df['daily_bias'] = 'BULLISH'  # Default: allow all
        
        # === KER REGIME DETECTION ===
        ker_period = self.params.get('ker_period', 10)
        df['KER'] = self.regime_detector.calculate_ker(df['close'], ker_period)
        
        ker_threshold_meanrev = self.params.get('ker_threshold_meanrev', 0.30)
        ker_threshold_trend = self.params.get('ker_threshold_trend', 0.50)
        
        df['regime'] = 'MIXED'
        df.loc[df['KER'] < ker_threshold_meanrev, 'regime'] = 'MEAN_REV'
        df.loc[df['KER'] > ker_threshold_trend, 'regime'] = 'TREND'
        
        # === RSI with Dynamic Bands ===
        rsi_period = self.params.get('rsi_period', 2)
        df['RSI'] = calculate_rsi(df['close'], rsi_period)
        
        use_dynamic_rsi = self.params.get('use_dynamic_rsi', False)
        if use_dynamic_rsi:
            dyn_window = self.params.get('dynamic_rsi_window', 20)
            dyn_std = self.params.get('dynamic_rsi_std', 2.0)
            df['rsi_lower'], df['rsi_upper'] = calculate_dynamic_rsi_bands(
                df['RSI'], window=dyn_window, num_std=dyn_std
            )
        else:
            df['rsi_lower'] = self.params.get('rsi_entry', 30)
            df['rsi_upper'] = self.params.get('rsi_exit', 70)
        
        df['rsi_exit_threshold'] = df['rsi_upper']
        
        # === VOLATILITY ===
        vol_lookback = self.params.get('vol_lookback', 14)
        df['volatility'] = calculate_volatility(df['close'], vol_lookback)
        vol_min = self.params.get('vol_min_pct', 0.005)
        vol_filter = df['volatility'] > vol_min
        
        # === MEAN REVERSION SIGNAL ===
        meanrev_long = (df['RSI'].shift(1) < df['rsi_lower'].shift(1)) & vol_filter
        
        # === TREND FOLLOWING SIGNAL ===
        ema_fast = self.params.get('ema_fast', 8)
        ema_slow = self.params.get('ema_slow', 21)
        df['ema_fast'] = self._calculate_ema(df['close'], ema_fast)
        df['ema_slow'] = self._calculate_ema(df['close'], ema_slow)
        df['trend_up'] = df['ema_fast'] > df['ema_slow']
        
        price_change = df['close'].diff()
        pulse_mult = self.params.get('trend_pulse_mult', 0.4)
        vol_std = df['close'].rolling(14).std()
        df['pulse_up'] = price_change > (pulse_mult * vol_std)
        
        trend_long = df['trend_up'] & df['pulse_up']
        
        # === REGIME-SPECIFIC SIGNALS ===
        df['signal_long_meanrev'] = meanrev_long & (df['regime'] == 'MEAN_REV')
        df['signal_long_trend'] = trend_long & (df['regime'] == 'TREND')
        
        # === MULTI-TIMEFRAME FILTER ===
        require_mtf = self.params.get('require_daily_bias', False)
        if require_mtf and use_mtf:
            bullish = df['daily_bias'].isin(['BULLISH', 'STRONG_BULL'])
            df['signal_long_meanrev'] = df['signal_long_meanrev'] & bullish
            df['signal_long_trend'] = df['signal_long_trend'] & bullish
        
        df['signal_long'] = df['signal_long_meanrev'] | df['signal_long_trend']
        
        df['signal_source'] = 'NONE'
        df.loc[df['signal_long_meanrev'], 'signal_source'] = 'MEANREV'
        df.loc[df['signal_long_trend'], 'signal_source'] = 'TREND'
        
        return df
    
    def backtest(self, df: pd.DataFrame, initial_capital: float = 100000) -> Tuple[List[Dict], Dict]:
        """Backtest with all advanced features."""
        df = self.generate_signals(df)
        
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
        position_mgr = None
        
        fee_per_order = 24
        base_max_hold = self.params.get('max_hold_bars', 10)
        allowed_hours = self.params.get('allowed_hours', [9, 10, 11, 12, 13])
        
        # Feature flags
        use_dynamic_sizing = self.params.get('use_dynamic_sizing', False)
        use_profit_ladder = self.params.get('use_profit_ladder', False)
        use_adaptive_hold = self.params.get('use_adaptive_hold', False)
        
        ladder_thresholds = get_profit_ladder_thresholds(self.params) if use_profit_ladder else []
        ladder_triggered = [False, False, False]
        
        for i in range(50, len(df)):
            current_time = df['datetime'].iloc[i]
            current_hour = current_time.hour
            current_minute = current_time.minute
            current_close = df['close'].iloc[i]
            current_vol = df['volatility'].iloc[i]
            current_rsi = df['RSI'].iloc[i]
            
            # === ENTRY ===
            if not in_position:
                if current_hour not in allowed_hours:
                    continue
                if current_hour >= 14 and current_minute >= 30:
                    continue
                
                if df['signal_long'].iloc[i]:
                    # === DYNAMIC POSITION SIZING ===
                    if use_dynamic_sizing:
                        perf = get_rolling_performance(trades, window=20)
                        qty = calculate_dynamic_position_size(
                            capital=capital,
                            close_price=current_close,
                            volatility=current_vol,
                            win_rate=perf['win_rate'],
                            avg_win=perf['avg_win'],
                            avg_loss=perf['avg_loss'],
                            max_risk_pct=self.params.get('max_risk_pct', 2.0),
                            kelly_fraction=self.params.get('kelly_fraction', 0.5)
                        )
                    else:
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
                        ladder_triggered = [False, False, False]
                        
                        if use_profit_ladder:
                            position_mgr = PositionManager(entry_qty, entry_price)
            
            # === EXIT ===
            else:
                bars_held += 1
                current_return_pct = ((current_close - entry_price) / entry_price) * 100
                
                # === PROFIT LADDER EXITS ===
                partial_pnl = 0
                if use_profit_ladder and position_mgr and not position_mgr.is_fully_closed():
                    for idx, ladder in enumerate(ladder_thresholds):
                        if not ladder_triggered[idx] and current_rsi > ladder['rsi_threshold']:
                            exit_qty, pnl = position_mgr.scale_out(
                                ladder['exit_fraction'], 
                                current_close, 
                                current_time,
                                ladder['reason']
                            )
                            if exit_qty > 0:
                                partial_pnl += pnl
                                ladder_triggered[idx] = True
                
                # === STANDARD EXIT CONDITIONS ===
                outlier_exit = current_return_pct >= self.max_return_cap
                
                if entry_strategy == 'MEANREV':
                    rsi_target = df['rsi_exit_threshold'].iloc[i]
                    target_exit = current_rsi > rsi_target
                elif entry_strategy == 'TREND':
                    target_exit = current_close < df['ema_fast'].iloc[i]
                else:
                    target_exit = False
                
                # === ADAPTIVE HOLD ===
                if use_adaptive_hold:
                    adaptive_max = calculate_adaptive_max_hold(
                        current_vol, base_max_hold, vol_baseline=0.01
                    )
                    time_exit = bars_held >= adaptive_max
                else:
                    time_exit = bars_held >= base_max_hold
                
                eod_exit = (current_hour >= 15 and current_minute >= 15)
                
                # Check if should fully exit
                full_exit = target_exit or outlier_exit or time_exit or eod_exit
                
                if use_profit_ladder and position_mgr:
                    if position_mgr.is_fully_closed():
                        # Already fully closed via ladder
                        full_exit = True
                    elif full_exit:
                        # Close remaining position
                        _, final_pnl = position_mgr.close_remaining(
                            current_close, current_time, 'full_exit'
                        )
                        partial_pnl += final_pnl
                
                if full_exit:
                    exit_price = current_close
                    exit_time = current_time
                    
                    if use_profit_ladder and position_mgr:
                        net_pnl = position_mgr.get_total_pnl()
                        avg_exit = position_mgr.get_avg_exit_price()
                    else:
                        gross_pnl = entry_qty * (exit_price - entry_price)
                        net_pnl = gross_pnl - (2 * fee_per_order)
                    
                    capital = entry_capital + net_pnl
                    
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
                        'ladder_exits': len([t for t in ladder_triggered if t]) if use_profit_ladder else 0
                    })
                    
                    in_position = False
                    position_mgr = None
        
        metrics = self._calculate_metrics(trades, initial_capital, capital)
        return trades, metrics
    
    def _calculate_metrics(self, trades: List[Dict], initial_capital: float, 
                           final_capital: float) -> Dict:
        """Calculate comprehensive metrics."""
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
        
        returns = (trades_df['pnl'] / initial_capital) * 100
        
        if returns.std() > 0 and len(returns) > 1:
            trades_per_year = 1500 / (len(trades_df) / 250) if len(trades_df) > 0 else 1
            sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(min(trades_per_year, 252))
        else:
            sharpe_ratio = 0
        
        capital_curve = trades_df['capital'].values
        running_max = np.maximum.accumulate(capital_curve)
        drawdown = (capital_curve - running_max) / running_max * 100
        max_drawdown_pct = drawdown.min()
        
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
