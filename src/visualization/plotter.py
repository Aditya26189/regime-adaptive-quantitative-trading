"""
Visualization module for trading performance.

This module provides functions to generate professional charts
for analyzing trading strategy performance.
"""

from typing import Dict, Optional, Any, List
import numpy as np

# Import matplotlib with Agg backend for non-interactive use
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


def plot_equity_curve(
    results: Dict[str, Any],
    save_path: Optional[str] = None,
    figsize: tuple = (12, 6),
    dpi: int = 150
) -> None:
    """
    Plot the equity curve over time.
    
    Args:
        results: Dictionary with 'equity_curve' and optionally 'timestamps'
        save_path: Optional path to save the figure
        figsize: Figure size (width, height)
        dpi: Resolution for saved figure
    """
    fig, ax = plt.subplots(figsize=figsize)
    
    equity = results.get('equity_curve', [])
    timestamps = results.get('timestamps', range(len(equity)))
    
    # Plot equity
    ax.plot(timestamps, equity, 'b-', linewidth=1.5, label='Equity')
    
    # Add initial equity line
    if len(equity) > 0:
        initial_equity = equity[0]
        ax.axhline(y=initial_equity, color='gray', linestyle='--', 
                   alpha=0.5, label=f'Initial: ${initial_equity:,.0f}')
    
    # Formatting
    ax.set_title('Portfolio Equity Curve', fontsize=14, fontweight='bold')
    ax.set_xlabel('Time', fontsize=12)
    ax.set_ylabel('Equity ($)', fontsize=12)
    ax.legend(loc='upper left')
    ax.grid(True, alpha=0.3)
    
    # Format y-axis with commas
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=dpi, bbox_inches='tight')
        print(f"  ✓ Saved equity curve to {save_path}")
    
    plt.close(fig)


def plot_drawdown(
    results: Dict[str, Any],
    save_path: Optional[str] = None,
    figsize: tuple = (12, 6),
    dpi: int = 150
) -> None:
    """
    Plot the drawdown chart.
    
    Args:
        results: Dictionary with 'equity_curve'
        save_path: Optional path to save the figure
        figsize: Figure size (width, height)
        dpi: Resolution for saved figure
    """
    fig, ax = plt.subplots(figsize=figsize)
    
    equity = np.array(results.get('equity_curve', []))
    timestamps = results.get('timestamps', range(len(equity)))
    
    if len(equity) < 2:
        plt.close(fig)
        return
    
    # Calculate drawdown
    peak = np.maximum.accumulate(equity)
    drawdown = (equity - peak) / peak * 100  # As percentage
    
    # Plot drawdown as filled area
    ax.fill_between(timestamps, drawdown, 0, 
                    color='red', alpha=0.3, label='Drawdown')
    ax.plot(timestamps, drawdown, 'r-', linewidth=1)
    
    # Mark maximum drawdown
    max_dd_idx = np.argmin(drawdown)
    max_dd = drawdown[max_dd_idx]
    ax.scatter([timestamps[max_dd_idx]], [max_dd], 
               color='darkred', s=100, zorder=5,
               label=f'Max DD: {max_dd:.2f}%')
    
    # Formatting
    ax.set_title('Portfolio Drawdown', fontsize=14, fontweight='bold')
    ax.set_xlabel('Time', fontsize=12)
    ax.set_ylabel('Drawdown (%)', fontsize=12)
    ax.legend(loc='lower left')
    ax.grid(True, alpha=0.3)
    
    # Set y-axis limits
    ax.set_ylim(min(drawdown) * 1.1, 5)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=dpi, bbox_inches='tight')
        print(f"  ✓ Saved drawdown chart to {save_path}")
    
    plt.close(fig)


def plot_returns_distribution(
    results: Dict[str, Any],
    save_path: Optional[str] = None,
    figsize: tuple = (12, 6),
    dpi: int = 150,
    bins: int = 50
) -> None:
    """
    Plot histogram of returns distribution.
    
    Args:
        results: Dictionary with 'returns'
        save_path: Optional path to save the figure
        figsize: Figure size (width, height)
        dpi: Resolution for saved figure
        bins: Number of histogram bins
    """
    fig, ax = plt.subplots(figsize=figsize)
    
    returns = np.array(results.get('returns', []))
    returns = returns[np.isfinite(returns)]
    
    if len(returns) < 2:
        plt.close(fig)
        return
    
    # Convert to percentage
    returns_pct = returns * 100
    
    # Plot histogram
    n, bins_edges, patches = ax.hist(
        returns_pct, bins=bins, 
        color='steelblue', alpha=0.7, edgecolor='white'
    )
    
    # Color positive and negative returns differently
    for patch, left, right in zip(patches, bins_edges[:-1], bins_edges[1:]):
        if right < 0:
            patch.set_facecolor('red')
        elif left > 0:
            patch.set_facecolor('green')
    
    # Add mean and median lines
    mean_ret = np.mean(returns_pct)
    median_ret = np.median(returns_pct)
    ax.axvline(mean_ret, color='blue', linestyle='--', 
               linewidth=2, label=f'Mean: {mean_ret:.4f}%')
    ax.axvline(median_ret, color='orange', linestyle='--', 
               linewidth=2, label=f'Median: {median_ret:.4f}%')
    ax.axvline(0, color='black', linestyle='-', linewidth=1, alpha=0.5)
    
    # Add statistics text
    std_ret = np.std(returns_pct)
    skew = float(np.mean(((returns_pct - mean_ret) / std_ret) ** 3)) if std_ret > 0 else 0
    
    stats_text = f'Std: {std_ret:.4f}%\nSkew: {skew:.2f}'
    ax.text(0.95, 0.95, stats_text, transform=ax.transAxes,
            verticalalignment='top', horizontalalignment='right',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    # Formatting
    ax.set_title('Returns Distribution', fontsize=14, fontweight='bold')
    ax.set_xlabel('Return (%)', fontsize=12)
    ax.set_ylabel('Frequency', fontsize=12)
    ax.legend(loc='upper left')
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=dpi, bbox_inches='tight')
        print(f"  ✓ Saved returns distribution to {save_path}")
    
    plt.close(fig)


def plot_position_history(
    results: Dict[str, Any],
    save_path: Optional[str] = None,
    figsize: tuple = (12, 4),
    dpi: int = 150
) -> None:
    """
    Plot position history over time.
    
    Args:
        results: Dictionary with 'position_curve'
        save_path: Optional path to save the figure
        figsize: Figure size (width, height)
        dpi: Resolution for saved figure
    """
    fig, ax = plt.subplots(figsize=figsize)
    
    positions = results.get('position_curve', [])
    timestamps = results.get('timestamps', range(len(positions)))
    
    if len(positions) == 0:
        plt.close(fig)
        return
    
    # Plot positions as step chart
    ax.step(timestamps, positions, where='post', 
            color='purple', linewidth=1.5, label='Position')
    ax.fill_between(timestamps, positions, 0, 
                    step='post', alpha=0.3, color='purple')
    ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    
    # Formatting
    ax.set_title('Position History', fontsize=14, fontweight='bold')
    ax.set_xlabel('Time', fontsize=12)
    ax.set_ylabel('Position (units)', fontsize=12)
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=dpi, bbox_inches='tight')
        print(f"  ✓ Saved position history to {save_path}")
    
    plt.close(fig)


def plot_all(
    results: Dict[str, Any],
    save_path: str,
    figsize: tuple = (14, 12),
    dpi: int = 150
) -> None:
    """
    Generate full performance dashboard (3 subplots).
    
    Includes:
    - Equity curve
    - Drawdown
    - Returns distribution
    
    Args:
        results: Results dictionary from backtester
        save_path: Path to save the combined figure
        figsize: Figure size (width, height)
        dpi: Resolution for saved figure
    """
    fig, axes = plt.subplots(3, 1, figsize=figsize)
    
    equity = np.array(results.get('equity_curve', []))
    timestamps = results.get('timestamps', range(len(equity)))
    returns = np.array(results.get('returns', []))
    
    if len(equity) < 2:
        print("  ⚠ Not enough data to generate plots")
        plt.close(fig)
        return
    
    # ===== Subplot 1: Equity Curve =====
    ax1 = axes[0]
    ax1.plot(timestamps, equity, 'b-', linewidth=1.5, label='Equity')
    if len(equity) > 0:
        initial_equity = equity[0]
        ax1.axhline(y=initial_equity, color='gray', linestyle='--', 
                    alpha=0.5, label=f'Initial: ${initial_equity:,.0f}')
    ax1.set_title('Portfolio Equity Curve', fontsize=14, fontweight='bold')
    ax1.set_ylabel('Equity ($)', fontsize=11)
    ax1.legend(loc='upper left', fontsize=9)
    ax1.grid(True, alpha=0.3)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
    
    # ===== Subplot 2: Drawdown =====
    ax2 = axes[1]
    peak = np.maximum.accumulate(equity)
    drawdown = (equity - peak) / peak * 100
    ax2.fill_between(timestamps, drawdown, 0, color='red', alpha=0.3)
    ax2.plot(timestamps, drawdown, 'r-', linewidth=1)
    max_dd_idx = np.argmin(drawdown)
    max_dd = drawdown[max_dd_idx]
    ax2.scatter([timestamps[max_dd_idx]], [max_dd], 
                color='darkred', s=80, zorder=5,
                label=f'Max DD: {max_dd:.2f}%')
    ax2.set_title('Portfolio Drawdown', fontsize=14, fontweight='bold')
    ax2.set_ylabel('Drawdown (%)', fontsize=11)
    ax2.legend(loc='lower left', fontsize=9)
    ax2.grid(True, alpha=0.3)
    ax2.set_ylim(min(drawdown) * 1.1, 5)
    
    # ===== Subplot 3: Returns Distribution =====
    ax3 = axes[2]
    returns_clean = returns[np.isfinite(returns)]
    if len(returns_clean) > 1:
        returns_pct = returns_clean * 100
        n, bins_edges, patches = ax3.hist(
            returns_pct, bins=50,
            color='steelblue', alpha=0.7, edgecolor='white'
        )
        for patch, left, right in zip(patches, bins_edges[:-1], bins_edges[1:]):
            if right < 0:
                patch.set_facecolor('red')
            elif left > 0:
                patch.set_facecolor('green')
        mean_ret = np.mean(returns_pct)
        ax3.axvline(mean_ret, color='blue', linestyle='--', 
                    linewidth=2, label=f'Mean: {mean_ret:.4f}%')
        ax3.axvline(0, color='black', linestyle='-', linewidth=1, alpha=0.5)
    
    ax3.set_title('Returns Distribution', fontsize=14, fontweight='bold')
    ax3.set_xlabel('Return (%)', fontsize=11)
    ax3.set_ylabel('Frequency', fontsize=11)
    ax3.legend(loc='upper left', fontsize=9)
    ax3.grid(True, alpha=0.3)
    
    # Adjust layout
    plt.tight_layout()
    
    # Save
    plt.savefig(save_path, dpi=dpi, bbox_inches='tight')
    print(f"  ✓ Saved dashboard to {save_path}")
    
    plt.close(fig)


def print_metrics_table(metrics: Dict[str, float]) -> None:
    """
    Print a formatted table of metrics.
    
    Args:
        metrics: Dictionary of metric names to values
    """
    print("\n" + "=" * 50)
    print("PERFORMANCE METRICS")
    print("=" * 50)
    
    for key, value in metrics.items():
        if isinstance(value, float):
            if abs(value) < 1:
                print(f"{key:<20}: {value:>12.4f}")
            else:
                print(f"{key:<20}: {value:>12.2f}")
        else:
            print(f"{key:<20}: {value:>12}")
    
    print("=" * 50)
