"""
Performance metrics calculator for trading strategies.

This module provides functions to calculate standard quantitative
finance performance metrics including Sharpe ratio, Sortino ratio,
maximum drawdown, Calmar ratio, and profit factor.
"""

from typing import Dict, Union
import numpy as np


class MetricsCalculator:
    """
    Calculator for trading performance metrics.
    
    All methods are static and can be called without instantiation.
    Methods handle edge cases gracefully (empty arrays, zero std dev, etc.).
    
    Example:
        >>> metrics = MetricsCalculator.calculate_all(equity_curve)
        >>> print(f"Sharpe: {metrics['sharpe']:.2f}")
    """
    
    @staticmethod
    def sharpe_ratio(
        returns: np.ndarray,
        periods_per_year: int = 252 * 390,
        risk_free_rate: float = 0.0
    ) -> float:
        """
        Calculate annualized Sharpe ratio.
        
        Sharpe = (mean(returns) - risk_free_rate) / std(returns) * sqrt(periods_per_year)
        
        Args:
            returns: Array of period returns
            periods_per_year: Number of periods in a year (default: minute-level)
            risk_free_rate: Risk-free rate per period
            
        Returns:
            Annualized Sharpe ratio
        """
        returns = np.array(returns)
        
        if len(returns) < 2:
            return 0.0
        
        # Filter out NaN and infinite values
        returns = returns[np.isfinite(returns)]
        
        if len(returns) < 2:
            return 0.0
        
        excess_returns = returns - risk_free_rate
        mean_return = np.mean(excess_returns)
        std_return = np.std(returns, ddof=1)
        
        if std_return == 0 or np.isnan(std_return):
            return 0.0
        
        return float(mean_return / std_return * np.sqrt(periods_per_year))
    
    @staticmethod
    def sortino_ratio(
        returns: np.ndarray,
        periods_per_year: int = 252 * 390,
        risk_free_rate: float = 0.0
    ) -> float:
        """
        Calculate annualized Sortino ratio.
        
        Sortino = (mean(returns) - risk_free_rate) / std(negative_returns) * sqrt(periods_per_year)
        
        Only considers downside volatility (negative returns).
        
        Args:
            returns: Array of period returns
            periods_per_year: Number of periods in a year
            risk_free_rate: Risk-free rate per period
            
        Returns:
            Annualized Sortino ratio
        """
        returns = np.array(returns)
        
        if len(returns) < 2:
            return 0.0
        
        # Filter out NaN and infinite values
        returns = returns[np.isfinite(returns)]
        
        if len(returns) < 2:
            return 0.0
        
        excess_returns = returns - risk_free_rate
        mean_return = np.mean(excess_returns)
        
        # Downside returns (negative only)
        negative_returns = returns[returns < 0]
        
        if len(negative_returns) < 2:
            # No negative returns or not enough for std calculation
            return float(mean_return * np.sqrt(periods_per_year)) if mean_return > 0 else 0.0
        
        downside_std = np.std(negative_returns, ddof=1)
        
        if downside_std == 0 or np.isnan(downside_std):
            return 0.0
        
        return float(mean_return / downside_std * np.sqrt(periods_per_year))
    
    @staticmethod
    def max_drawdown(equity_curve: np.ndarray) -> float:
        """
        Calculate maximum drawdown.
        
        Max DD = min((equity - peak) / peak)
        
        Args:
            equity_curve: Array of equity values over time
            
        Returns:
            Maximum drawdown as a negative decimal (e.g., -0.15 for 15% drawdown)
        """
        equity_curve = np.array(equity_curve)
        
        if len(equity_curve) < 2:
            return 0.0
        
        # Filter out NaN and infinite values
        equity_curve = equity_curve[np.isfinite(equity_curve)]
        
        if len(equity_curve) < 2:
            return 0.0
        
        # Calculate running maximum
        peak = np.maximum.accumulate(equity_curve)
        
        # Avoid division by zero
        peak = np.where(peak == 0, 1, peak)
        
        # Calculate drawdown at each point
        drawdown = (equity_curve - peak) / peak
        
        return float(np.min(drawdown))
    
    @staticmethod
    def calmar_ratio(
        equity_curve: np.ndarray,
        periods_per_year: int = 252 * 390
    ) -> float:
        """
        Calculate Calmar ratio.
        
        Calmar = Annual Return / |Max Drawdown|
        
        Args:
            equity_curve: Array of equity values over time
            periods_per_year: Number of periods in a year
            
        Returns:
            Calmar ratio
        """
        equity_curve = np.array(equity_curve)
        
        if len(equity_curve) < 2:
            return 0.0
        
        # Filter out NaN and infinite values
        equity_curve = equity_curve[np.isfinite(equity_curve)]
        
        if len(equity_curve) < 2:
            return 0.0
        
        # Calculate total return
        total_return = (equity_curve[-1] - equity_curve[0]) / equity_curve[0]
        
        # Annualize the return
        num_periods = len(equity_curve)
        annual_return = total_return * (periods_per_year / num_periods)
        
        # Get max drawdown
        max_dd = MetricsCalculator.max_drawdown(equity_curve)
        
        if max_dd == 0:
            return 0.0
        
        return float(annual_return / abs(max_dd))
    
    @staticmethod
    def win_rate(returns: np.ndarray) -> float:
        """
        Calculate win rate (percentage of positive returns).
        
        Win Rate = count(positive_returns) / count(all_returns)
        
        Args:
            returns: Array of period returns
            
        Returns:
            Win rate as a decimal (0.0 to 1.0)
        """
        returns = np.array(returns)
        
        if len(returns) == 0:
            return 0.0
        
        # Filter out NaN and infinite values
        returns = returns[np.isfinite(returns)]
        
        if len(returns) == 0:
            return 0.0
        
        # Exclude zero returns
        non_zero_returns = returns[returns != 0]
        
        if len(non_zero_returns) == 0:
            return 0.0
        
        return float(np.sum(non_zero_returns > 0) / len(non_zero_returns))
    
    @staticmethod
    def profit_factor(returns: np.ndarray) -> float:
        """
        Calculate profit factor.
        
        Profit Factor = sum(gains) / sum(losses)
        
        A profit factor > 1 indicates a profitable strategy.
        
        Args:
            returns: Array of period returns
            
        Returns:
            Profit factor (ratio of gains to losses)
        """
        returns = np.array(returns)
        
        if len(returns) == 0:
            return 0.0
        
        # Filter out NaN and infinite values
        returns = returns[np.isfinite(returns)]
        
        gains = returns[returns > 0]
        losses = returns[returns < 0]
        
        total_gains = np.sum(gains) if len(gains) > 0 else 0.0
        total_losses = abs(np.sum(losses)) if len(losses) > 0 else 0.0
        
        if total_losses == 0:
            return float('inf') if total_gains > 0 else 0.0
        
        return float(total_gains / total_losses)
    
    @staticmethod
    def total_return(equity_curve: np.ndarray) -> float:
        """
        Calculate total return.
        
        Args:
            equity_curve: Array of equity values over time
            
        Returns:
            Total return as a decimal
        """
        equity_curve = np.array(equity_curve)
        
        if len(equity_curve) < 2:
            return 0.0
        
        return float((equity_curve[-1] - equity_curve[0]) / equity_curve[0])
    
    @staticmethod
    def volatility(
        returns: np.ndarray,
        periods_per_year: int = 252 * 390
    ) -> float:
        """
        Calculate annualized volatility.
        
        Args:
            returns: Array of period returns
            periods_per_year: Number of periods in a year
            
        Returns:
            Annualized volatility
        """
        returns = np.array(returns)
        
        if len(returns) < 2:
            return 0.0
        
        # Filter out NaN and infinite values
        returns = returns[np.isfinite(returns)]
        
        if len(returns) < 2:
            return 0.0
        
        return float(np.std(returns, ddof=1) * np.sqrt(periods_per_year))
    
    @staticmethod
    def calculate_all(
        equity_curve: np.ndarray,
        periods_per_year: int = 252 * 390
    ) -> Dict[str, float]:
        """
        Calculate all metrics.
        
        Args:
            equity_curve: Array of equity values over time
            periods_per_year: Number of periods in a year
            
        Returns:
            Dictionary containing all calculated metrics
        """
        equity_curve = np.array(equity_curve)
        
        if len(equity_curve) < 2:
            return {
                'sharpe': 0.0,
                'sortino': 0.0,
                'max_dd': 0.0,
                'calmar': 0.0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'total_return': 0.0,
                'volatility': 0.0
            }
        
        # Calculate returns from equity curve
        returns = np.diff(equity_curve) / equity_curve[:-1]
        
        return {
            'sharpe': MetricsCalculator.sharpe_ratio(returns, periods_per_year),
            'sortino': MetricsCalculator.sortino_ratio(returns, periods_per_year),
            'max_dd': MetricsCalculator.max_drawdown(equity_curve),
            'calmar': MetricsCalculator.calmar_ratio(equity_curve, periods_per_year),
            'win_rate': MetricsCalculator.win_rate(returns),
            'profit_factor': MetricsCalculator.profit_factor(returns),
            'total_return': MetricsCalculator.total_return(equity_curve),
            'volatility': MetricsCalculator.volatility(returns, periods_per_year)
        }
