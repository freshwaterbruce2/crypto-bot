"""
Portfolio Management System
==========================

Comprehensive portfolio management system for crypto trading bot with:
- Real-time position tracking and P&L calculation
- Portfolio rebalancing algorithms (DCA, GRID, arbitrage)
- Risk assessment and position limits
- Performance analytics and reporting
- Thread-safe operations for concurrent trading
- Integration with existing balance manager

Components:
- PortfolioManager: Main portfolio management system
- PositionTracker: Position tracking and P&L calculation
- RiskManager: Risk assessment and limits
- Rebalancer: Portfolio rebalancing algorithms
- Analytics: Performance analytics and reporting
"""

from .analytics import AnalyticsConfig, PerformanceMetrics, PortfolioAnalytics
from .portfolio_manager import PortfolioConfig, PortfolioManager
from .position_tracker import Position, PositionStatus, PositionTracker
from .rebalancer import Rebalancer, RebalanceResult, RebalanceStrategy
from .risk_manager import RiskLimits, RiskManager, RiskMetrics

__all__ = [
    "PortfolioManager",
    "PortfolioConfig",
    "PositionTracker",
    "Position",
    "PositionStatus",
    "RiskManager",
    "RiskLimits",
    "RiskMetrics",
    "Rebalancer",
    "RebalanceStrategy",
    "RebalanceResult",
    "PortfolioAnalytics",
    "PerformanceMetrics",
    "AnalyticsConfig",
]

__version__ = "1.0.0"
