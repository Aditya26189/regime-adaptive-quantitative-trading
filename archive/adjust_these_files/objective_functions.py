"""
MULTI-OBJECTIVE OPTIMIZATION FUNCTIONS

Defines how to score each parameter combination.
Uses weighted combination of multiple metrics to avoid overfitting to single objective.

Copilot Instructions:
- objective_function() is what Optuna calls for each trial
- Returns single score (weighted combination of metrics)
- Includes penalties for constraint violations
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple
import warnings
warnings.filterwarnings('ignore')

class CompetitionObjective:
    """
    Multi-objective scoring function aligned with competition ranking criteria.
    
    Competition ranks by:
    1. Average Sharpe Ratio (PRIMARY)
    2. Equity Curve Consistency (secondary)
    3. Max Drawdown Control (secondary)
    4. Logic Clarity (manual judging)
    
    We optimize weighted combination of these.
    """
    
    # Weights for multi-objective optimization
    WEIGHTS = {
        'sharpe': 0.70,           # Primary objective (70%)
        'return': 0.10,           # Secondary - total return (10%)
        'drawdown': 0.10,         # Secondary - drawdown control (10%)
        'consistency': 0.10       # Secondary - win rate stability (10%)
    }
    
    # Hard constraints (violations return -999)
    CONSTRAINTS = {
        'min_trades': 120,        # Competition requirement
        'max_single_trade': 5.0,  # Outlier detection (% return)
        'min_win_rate': 0.35,     # Too low = pure luck
        'max_drawdown': 15.0      # Too high = excessive risk
    }
    
    @staticmethod
    def calculate_sharpe_with_penalties(trades_df: pd.DataFrame, 
                                         capital: float = 100000) -> Tuple[float, Dict]:
        """
        Calculate competition-adjusted Sharpe ratio.
        
        Includes penalties for:
        - High variance (reduces Sharpe)
        - Large drawdowns (judges care about this)
        - Outlier dependency (strategy relies on one lucky trade)
        
        Args:
            trades_df: DataFrame with columns [pnl, entry_price, exit_price, qty]
            capital: Initial capital
        
        Returns:
            (competition_sharpe, metrics_dict)
        """
        if len(trades_df) == 0:
            return -999, {}
        
        # Calculate per-trade returns
        trades_df['return_pct'] = trades_df['pnl'] / capital * 100
        
        # Base metrics
        mean_return = trades_df['return_pct'].mean()
        std_return = trades_df['return_pct'].std()
        
        if std_return == 0 or pd.isna(std_return):
            return -999, {}
        
        base_sharpe = mean_return / std_return
        
        # Calculate additional metrics
        win_rate = (trades_df['pnl'] > 0).sum() / len(trades_df)
        total_return = trades_df['pnl'].sum() / capital * 100
        
        # Drawdown calculation
        cumulative_pnl = trades_df['pnl'].cumsum()
        running_max = cumulative_pnl.expanding().max()
        drawdown = (cumulative_pnl - running_max) / capital * 100
        max_drawdown = abs(drawdown.min())
        
        # Penalty 1: Variance penalty (competition wants consistency)
        variance_penalty = std_return / 5.0  # Normalize to 0-1 range
        
        # Penalty 2: Drawdown penalty (exponential - large drawdowns heavily penalized)
        if max_drawdown > 8:
            drawdown_penalty = (max_drawdown - 8) / 2.0
        else:
            drawdown_penalty = 0
        
        # Penalty 3: Outlier dependency
        # Remove top/bottom 5% and recalculate Sharpe
        trimmed_returns = trades_df['return_pct'].clip(
            lower=trades_df['return_pct'].quantile(0.05),
            upper=trades_df['return_pct'].quantile(0.95)
        )
        trimmed_sharpe = (trimmed_returns.mean() / trimmed_returns.std() 
                          if trimmed_returns.std() > 0 else -999)
        outlier_dependency = max(0, base_sharpe - trimmed_sharpe)
        outlier_penalty = outlier_dependency * 1.5
        
        # Penalty 4: Low win rate (< 40% looks like gambling)
        if win_rate < 0.40:
            win_rate_penalty = (0.40 - win_rate) * 2.0
        else:
            win_rate_penalty = 0
        
        # Bonus: Consistent wins (win rate 55-65% is ideal sweet spot)
        if 0.50 <= win_rate <= 0.65:
            consistency_bonus = 0.2
        else:
            consistency_bonus = 0
        
        # Competition Sharpe = Base Sharpe - Penalties + Bonuses
        competition_sharpe = (
            base_sharpe 
            - variance_penalty 
            - drawdown_penalty 
            - outlier_penalty 
            - win_rate_penalty
            + consistency_bonus
        )
        
        metrics = {
            'base_sharpe': base_sharpe,
            'competition_sharpe': competition_sharpe,
            'mean_return': mean_return,
            'std_return': std_return,
            'total_return': total_return,
            'win_rate': win_rate,
            'max_drawdown': max_drawdown,
            'trade_count': len(trades_df),
            'penalties': {
                'variance': variance_penalty,
                'drawdown': drawdown_penalty,
                'outlier': outlier_penalty,
                'win_rate': win_rate_penalty
            },
            'bonuses': {
                'consistency': consistency_bonus
            }
        }
        
        return competition_sharpe, metrics
    
    @staticmethod
    def check_constraints(trades_df: pd.DataFrame, metrics: Dict) -> Tuple[bool, str]:
        """
        Check if strategy violates hard constraints.
        
        Returns:
            (is_valid, violation_reason)
        """
        # Constraint 1: Minimum trade count
        if metrics['trade_count'] < CompetitionObjective.CONSTRAINTS['min_trades']:
            return False, f"Insufficient trades: {metrics['trade_count']} < 120"
        
        # Constraint 2: No extreme outliers
        if len(trades_df) > 0:
            max_trade_return = trades_df['return_pct'].abs().max()
            if max_trade_return > CompetitionObjective.CONSTRAINTS['max_single_trade']:
                return False, f"Outlier trade: {max_trade_return:.2f}% > 5%"
        
        # Constraint 3: Minimum win rate (avoid pure luck strategies)
        if metrics['win_rate'] < CompetitionObjective.CONSTRAINTS['min_win_rate']:
            return False, f"Win rate too low: {metrics['win_rate']:.1%} < 35%"
        
        # Constraint 4: Maximum drawdown
        if metrics['max_drawdown'] > CompetitionObjective.CONSTRAINTS['max_drawdown']:
            return False, f"Drawdown too large: {metrics['max_drawdown']:.2f}% > 15%"
        
        return True, "All constraints satisfied"
    
    @staticmethod
    def calculate_final_score(metrics: Dict) -> float:
        """
        Calculate weighted final score for Optuna to maximize.
        
        Score = Weighted sum of:
        - Competition Sharpe (70%)
        - Total Return normalized (10%)
        - Drawdown control (10%)
        - Win Rate consistency (10%)
        
        Returns:
            Final score (higher is better)
        """
        # Component 1: Competition Sharpe (primary)
        sharpe_score = metrics['competition_sharpe']
        
        # Component 2: Return (normalized to 0-1 scale, assuming 0-20% range)
        return_score = min(metrics['total_return'] / 20.0, 1.0)
        
        # Component 3: Drawdown control (inverse - lower is better)
        # Convert to 0-1 scale where 1 = 0% drawdown, 0 = 15% drawdown
        drawdown_score = max(0, 1 - metrics['max_drawdown'] / 15.0)
        
        # Component 4: Win rate consistency
        # Peak at 55-60%, falls off on both sides
        ideal_win_rate = 0.575
        win_rate_distance = abs(metrics['win_rate'] - ideal_win_rate)
        consistency_score = max(0, 1 - win_rate_distance * 2.0)
        
        # Weighted combination
        final_score = (
            CompetitionObjective.WEIGHTS['sharpe'] * sharpe_score +
            CompetitionObjective.WEIGHTS['return'] * return_score +
            CompetitionObjective.WEIGHTS['drawdown'] * drawdown_score +
            CompetitionObjective.WEIGHTS['consistency'] * consistency_score
        )
        
        return final_score


def create_objective_function(symbol: str, data: pd.DataFrame, strategy_type: str):
    """
    Factory function to create Optuna objective function for specific symbol.
    
    This is what you pass to study.optimize().
    
    Args:
        symbol: Trading symbol (e.g., 'NSE:NIFTY50-INDEX')
        data: Historical OHLC data
        strategy_type: 'trend', 'mean_reversion', 'hybrid', or 'ensemble'
    
    Returns:
        Objective function that Optuna will call
    
    Example:
        objective = create_objective_function('NSE:NIFTY50-INDEX', data, 'trend')
        study.optimize(objective, n_trials=200)
    """
    def objective(trial):
        """
        Optuna objective function.
        Called once per trial with suggested parameters.
        
        Returns:
            Score to maximize (competition-adjusted score)
        """
        # Import here to avoid circular dependency
        from src.optimization.parameter_space import SymbolParameterMapper
        from src.strategies.nifty_trend_strategy import generate_nifty_trend_signals
        from src.strategies.hybrid_adaptive import generate_hybrid_signals
        from src.strategies.ensemble_wrapper import ensemble_backtest
        
        # Get parameters for this trial
        params = SymbolParameterMapper.get_parameter_space(trial, symbol)
        
        # Backtest with these parameters
        try:
            if strategy_type == 'trend':
                trades_df = generate_nifty_trend_signals(data, params)
            elif strategy_type == 'ensemble':
                _, trades_df = ensemble_backtest(data, params)
            elif strategy_type == 'hybrid':
                trades_df = generate_hybrid_signals(data, params)
            else:  # mean_reversion
                from src.strategies.hybrid_adaptive import generate_hybrid_signals
                trades_df = generate_hybrid_signals(data, params)
            
        except Exception as e:
            # Strategy failed (e.g., no trades generated)
            print(f"Trial {trial.number} failed: {e}")
            return -999
        
        # Calculate metrics
        competition_sharpe, metrics = CompetitionObjective.calculate_sharpe_with_penalties(
            trades_df, capital=100000
        )
        
        # Check constraints
        is_valid, violation_reason = CompetitionObjective.check_constraints(trades_df, metrics)
        
        if not is_valid:
            # Constraint violation - return very low score
            print(f"Trial {trial.number} violated constraint: {violation_reason}")
            return -999
        
        # Calculate final weighted score
        final_score = CompetitionObjective.calculate_final_score(metrics)
        
        # Store metrics in trial for later analysis
        trial.set_user_attr('sharpe', metrics['competition_sharpe'])
        trial.set_user_attr('return', metrics['total_return'])
        trial.set_user_attr('win_rate', metrics['win_rate'])
        trial.set_user_attr('drawdown', metrics['max_drawdown'])
        trial.set_user_attr('trades', metrics['trade_count'])
        
        return final_score
    
    return objective


# Example usage for Copilot:
"""
import optuna
from objective_functions import create_objective_function

# Load data
data = pd.read_csv('data/NSE_NIFTY50_INDEX_1hour.csv')

# Create objective function
objective = create_objective_function('NSE:NIFTY50-INDEX', data, 'trend')

# Create and run study
study = optuna.create_study(
    direction='maximize',
    study_name='nifty50_optimization',
    storage='sqlite:///optimization_results/optuna_study.db',
    load_if_exists=True
)

study.optimize(objective, n_trials=200, show_progress_bar=True)

# Get best parameters
best_params = study.best_params
best_score = study.best_value
print(f"Best score: {best_score:.3f}")
print(f"Best params: {best_params}")
"""
