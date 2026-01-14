"""Core module containing backtester, risk manager, and metrics."""

from .backtester import Backtester, Trade
from .risk_manager import RiskManager
from .metrics import MetricsCalculator

__all__ = ['Backtester', 'Trade', 'RiskManager', 'MetricsCalculator']
