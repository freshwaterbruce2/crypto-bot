"""
Learning Module
===============
Provides learning and optimization capabilities for the trading bot.
"""

# Legacy components
from .universal_learning_manager import UniversalLearningManager, EventType, universal_learning_manager

# Advanced learning components
try:
    from .unified_learning_system import UnifiedLearningSystem, LearningMetrics, LearningState
    from .neural_pattern_engine import PatternRecognitionEngine, PatternFeatures
    from .advanced_memory_manager import AdvancedMemoryManager, MemoryEntry
    from .learning_integration import LearningSystemIntegrator
    ADVANCED_LEARNING_AVAILABLE = True
except ImportError as e:
    # Advanced learning components are optional
    UnifiedLearningSystem = None
    LearningMetrics = None
    LearningState = None
    PatternRecognitionEngine = None
    PatternFeatures = None
    AdvancedMemoryManager = None
    MemoryEntry = None
    LearningSystemIntegrator = None
    ADVANCED_LEARNING_AVAILABLE = False

# For backward compatibility
try:
    from ..minimum_discovery_learning import MinimumDiscoveryLearning, minimum_discovery_learning
except ImportError:
    MinimumDiscoveryLearning = None
    minimum_discovery_learning = None

__all__ = [
    "EventType",
    "UniversalLearningManager", 
    "universal_learning_manager",
    "MinimumDiscoveryLearning",
    "minimum_discovery_learning",
    # Advanced learning components (if available)
    "UnifiedLearningSystem",
    "LearningMetrics",
    "LearningState", 
    "PatternRecognitionEngine",
    "PatternFeatures",
    "AdvancedMemoryManager",
    "MemoryEntry",
    "LearningSystemIntegrator",
    "ADVANCED_LEARNING_AVAILABLE"
]
