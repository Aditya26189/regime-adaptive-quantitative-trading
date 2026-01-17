# src/utils/profit_ladder.py
"""
Profit Taking Ladders - Scale out in tranches
Expected Impact: +0.08 to +0.12 Sharpe
"""

from typing import List, Dict, Tuple

class PositionManager:
    """Manage partial exits for profit taking."""
    
    def __init__(self, total_qty: int, entry_price: float):
        self.total_qty = total_qty
        self.remaining_qty = total_qty
        self.entry_price = entry_price
        self.partial_exits = []
        
    def scale_out(self, exit_fraction: float, exit_price: float, 
                  exit_time, reason: str, fee: float = 24) -> Tuple[int, float]:
        """
        Exit a fraction of position.
        
        Args:
            exit_fraction: Fraction of REMAINING position to exit (0-1)
            exit_price: Current price
            exit_time: Exit timestamp
            reason: Exit reason string
            fee: Fee per order
        
        Returns:
            (exit_qty, pnl)
        """
        exit_qty = int(self.remaining_qty * exit_fraction)
        if exit_qty <= 0:
            return 0, 0.0
        
        self.remaining_qty -= exit_qty
        pnl = exit_qty * (exit_price - self.entry_price) - fee
        
        self.partial_exits.append({
            'qty': exit_qty,
            'price': exit_price,
            'time': exit_time,
            'reason': reason,
            'pnl': pnl
        })
        
        return exit_qty, pnl
    
    def close_remaining(self, exit_price: float, exit_time, 
                       reason: str, fee: float = 24) -> Tuple[int, float]:
        """Close all remaining position."""
        if self.remaining_qty <= 0:
            return 0, 0.0
        return self.scale_out(1.0, exit_price, exit_time, reason, fee)
    
    def is_fully_closed(self) -> bool:
        return self.remaining_qty <= 0
    
    def get_total_pnl(self) -> float:
        return sum(e['pnl'] for e in self.partial_exits)
    
    def get_avg_exit_price(self) -> float:
        if not self.partial_exits:
            return 0
        total_qty = sum(e['qty'] for e in self.partial_exits)
        if total_qty == 0:
            return 0
        weighted_sum = sum(e['qty'] * e['price'] for e in self.partial_exits)
        return weighted_sum / total_qty


def get_profit_ladder_thresholds(params: dict) -> List[Dict]:
    """
    Get profit taking ladder configuration.
    
    Default: 3 tranches at RSI 60, 75, 85
    """
    return [
        {
            'rsi_threshold': params.get('ladder_rsi_1', 60),
            'exit_fraction': params.get('ladder_frac_1', 0.33),
            'reason': 'quick_profit'
        },
        {
            'rsi_threshold': params.get('ladder_rsi_2', 75),
            'exit_fraction': params.get('ladder_frac_2', 0.50),  # 50% of remaining
            'reason': 'target'
        },
        {
            'rsi_threshold': params.get('ladder_rsi_3', 85),
            'exit_fraction': params.get('ladder_frac_3', 1.0),  # All remaining
            'reason': 'extended'
        }
    ]
