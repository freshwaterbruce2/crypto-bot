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

from .portfolio_manager import PortfolioManager, PortfolioConfig
from .position_tracker import PositionTracker, Position, PositionStatus
from .risk_manager import RiskManager, RiskLimits, RiskMetrics
from .rebalancer import Rebalancer, RebalanceStrategy, RebalanceResult
from .analytics import PortfolioAnalytics, PerformanceMetrics, AnalyticsConfig

__all__ = [
    'PortfolioManager',
    'PortfolioConfig',
    'PositionTracker',
    'Position',
    'PositionStatus',
    'RiskManager',
    'RiskLimits',
    'RiskMetrics',
    'Rebalancer',
    'RebalanceStrategy',
    'RebalanceResult',
    'PortfolioAnalytics',
    'PerformanceMetrics',
    'AnalyticsConfig'
]

__version__ = "1.0.0"