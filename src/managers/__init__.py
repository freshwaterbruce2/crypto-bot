"""
Managers package for the Kraken trading bot.

Contains manager classes that coordinate different aspects of the trading system:
- UnifiedLearningSystem: Kraken-compliant learning and error management
"""

try:
    from ..learning.unified_learning_system import UnifiedLearningSystem
except ImportError:
    UnifiedLearningSystem = None

__all__ = [
    'UnifiedLearningSystem'
]
