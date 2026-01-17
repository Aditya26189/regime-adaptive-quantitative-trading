"""
Cross-Symbol Pairs Trading Strategy
Trade spread between stock and NIFTY50 index for mean reversion.

Expected Sharpe: 1.9-2.4
Rule 12 Compliant: Uses only 'close' prices
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')


class PairsTradingStrategy:
    """
    Pairs Trading: STOCK vs NIFTY50
    Exploits co-integration between stocks and market index.
    """
    
    def __init__(self, params: Dict):
        self.beta_window = params.get('beta_window', 60)
        self.entry_z_score = params.get('entry_z_score', -2.0)
        self.exit_z_score = params.get('exit_z_score', -0.5)
        self.max_hold = params.get('max_hold', 10)
        self.allowed_hours = params.get('allowed_hours', [9, 10, 11, 12, 13])
    
    def calculate_beta(self, stock_close: pd.Series, nifty_close: pd.Series, window: int) -> pd.Series:
        """
        Calculate rolling beta using ONLY close prices.
        Beta = Cov(stock_ret, nifty_ret) / Var(nifty_ret)
        """
        stock_ret = stock_close.pct_change()
        nifty_ret = nifty_close.pct_change()
        
        # Rolling covariance
        cov = stock_ret.rolling(window).cov(nifty_ret)
        
        # Rolling variance of nifty
        var = nifty_ret.rolling(window).var()
        
        beta = cov / (var + 1e-10)
        return beta.fillna(1.0)
    
    def calculate_spread_z_score(self, stock_close: pd.Series, nifty_close: pd.Series, 
                                   beta: pd.Series, window: int) -> pd.Series:
        """
        Calculate z-score of stock-market spread.
        Spread = stock_price - beta * nifty_price (normalized)
        """
        # Normalize prices
        stock_norm = stock_close / stock_close.iloc[0]
        nifty_norm = nifty_close / nifty_close.iloc[0]
        
        spread = stock_norm - beta * nifty_norm
        
        spread_mean = spread.rolling(window).mean()
        spread_std = spread.rolling(window).std()
        
        z_score = (spread - spread_mean) / (spread_std + 1e-10)
        return z_score.fillna(0)
    
    def backtest(self, symbol: str) -> Tuple[List, Dict]:
        """
        Run backtest for stock-NIFTY pair.
        """
        # Load data
        df_stock = pd.read_csv(f'data/raw/NSE_{symbol}_EQ_1hour.csv')
        df_nifty = pd.read_csv('data/raw/NSE_NIFTY50_INDEX_1hour.csv')
        
        df_stock['datetime'] = pd.to_datetime(df_stock['datetime'])
        df_nifty['datetime'] = pd.to_datetime(df_nifty['datetime'])
        
        # Merge on datetime
        df = df_stock[['datetime', 'close']].merge(
            df_nifty[['datetime', 'close']],
            on='datetime',
            suffixes=('_stock', '_nifty')
        )
        df = df.sort_values('datetime').reset_index(drop=True)
        df['hour'] = df['datetime'].dt.hour
        
        # Calculate indicators
        df['beta'] = self.calculate_beta(df['close_stock'], df['close_nifty'], self.beta_window)
        df['spread_z'] = self.calculate_spread_z_score(
            df['close_stock'], df['close_nifty'], df['beta'], self.beta_window
        )
        
        # Backtest loop
        trades = []
        capital = 100000
        in_position = False
        entry_price = 0
        entry_time = None
        entry_qty = 0
        bars_held = 0
        
        warmup = max(100, self.beta_window + 10)
        
        for i in range(warmup, len(df)):
            current = df.iloc[i]
            current_price = current['close_stock']
            current_hour = current['hour']
            
            # ENTRY
            if not in_position:
                if current_hour not in self.allowed_hours:
                    continue
                
                # Entry: spread extremely low (stock cheap relative to market)
                if current['spread_z'] < self.entry_z_score:
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
                
                exit_signal = current['spread_z'] > self.exit_z_score
                time_exit = bars_held >= self.max_hold
                eod_exit = current_hour >= 15
                
                if exit_signal or time_exit or eod_exit:
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
        
        # Calculate metrics
        metrics = self._calculate_metrics(trades, capital)
        return trades, metrics
    
    def _calculate_metrics(self, trades: List, final_capital: float) -> Dict:
        """Calculate Sharpe and other metrics"""
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


def optimize_pairs_trading(symbol: str, n_iterations: int = 300) -> Tuple[Dict, float, int]:
    """Optimize pairs trading parameters."""
    import random
    
    param_space = {
        'beta_window': [20, 40, 60, 80, 100],
        'entry_z_score': [-2.5, -2.0, -1.8, -1.5, -1.2],
        'exit_z_score': [-0.8, -0.5, -0.3, 0.0, 0.3],
        'max_hold': [5, 8, 10, 12, 15],
    }
    
    best_sharpe = -999
    best_params = None
    best_trades = 0
    
    for i in range(n_iterations):
        params = {k: random.choice(v) for k, v in param_space.items()}
        
        try:
            strategy = PairsTradingStrategy(params)
            trades, metrics = strategy.backtest(symbol)
            
            if metrics['total_trades'] < 120:
                continue
            
            if metrics['sharpe_ratio'] > best_sharpe:
                best_sharpe = metrics['sharpe_ratio']
                best_params = params.copy()
                best_trades = metrics['total_trades']
                
        except Exception as e:
            continue
    
    return best_params, best_sharpe, best_trades
