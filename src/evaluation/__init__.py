"""Evaluation module for signal analysis and performance metrics."""

from .signal_analysis import (
    compute_signal_ic,
    compute_ic_by_regime,
    analyze_all_signals,
    print_signal_report
)

__all__ = [
    'compute_signal_ic',
    'compute_ic_by_regime',
    'analyze_all_signals',
    'print_signal_report'
]
