"""
NumPy Compatibility Module

This module provides compatibility handling for numpy operations,
ensuring the trading bot can function with or without numpy installed.
"""

import logging
from typing import List, Union, Optional, Tuple
import statistics

logger = logging.getLogger(__name__)

# Try to import numpy, but provide fallbacks if not available
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    logger.warning("NumPy not installed. Using pure Python fallbacks for numerical operations.")
    HAS_NUMPY = False
    np = None


class NumpyCompat:
    """Provides numpy-compatible operations with pure Python fallbacks"""
    
    @staticmethod
    def array(data: List[Union[int, float]]) -> Union['np.ndarray', List[float]]:
        """Create array from data"""
        if HAS_NUMPY:
            return np.array(data)
        return [float(x) for x in data]
    
    @staticmethod
    def mean(data: Union[List[float], 'np.ndarray']) -> float:
        """Calculate mean of data"""
        if HAS_NUMPY and hasattr(data, '__array__'):
            return float(np.mean(data))
        return statistics.mean(data) if data else 0.0
    
    @staticmethod
    def std(data: Union[List[float], 'np.ndarray'], ddof: int = 0) -> float:
        """Calculate standard deviation"""
        if HAS_NUMPY and hasattr(data, '__array__'):
            return float(np.std(data, ddof=ddof))
        if len(data) < 2:
            return 0.0
        # Use statistics module with appropriate degrees of freedom
        if ddof == 0:
            return statistics.pstdev(data)  # Population std dev
        else:
            return statistics.stdev(data)   # Sample std dev
    
    @staticmethod
    def max(data: Union[List[float], 'np.ndarray']) -> float:
        """Find maximum value"""
        if HAS_NUMPY and hasattr(data, '__array__'):
            return float(np.max(data))
        return max(data) if data else 0.0
    
    @staticmethod
    def min(data: Union[List[float], 'np.ndarray']) -> float:
        """Find minimum value"""
        if HAS_NUMPY and hasattr(data, '__array__'):
            return float(np.min(data))
        return min(data) if data else 0.0
    
    @staticmethod
    def diff(data: Union[List[float], 'np.ndarray']) -> List[float]:
        """Calculate differences between consecutive elements"""
        if HAS_NUMPY and hasattr(data, '__array__'):
            return np.diff(data).tolist()
        if len(data) < 2:
            return []
        return [data[i+1] - data[i] for i in range(len(data)-1)]
    
    @staticmethod
    def abs(data: Union[float, List[float], 'np.ndarray']) -> Union[float, List[float]]:
        """Calculate absolute values"""
        if isinstance(data, (int, float)):
            return abs(data)
        if HAS_NUMPY and hasattr(data, '__array__'):
            return np.abs(data)
        return [abs(x) for x in data]
    
    @staticmethod
    def zeros(shape: Union[int, Tuple[int, ...]]) -> Union['np.ndarray', List]:
        """Create array of zeros"""
        if HAS_NUMPY:
            return np.zeros(shape)
        if isinstance(shape, int):
            return [0.0] * shape
        # For multi-dimensional, return nested lists
        size = shape[0] if shape else 0
        return [0.0] * size
    
    @staticmethod
    def linspace(start: float, stop: float, num: int) -> List[float]:
        """Create evenly spaced values"""
        if HAS_NUMPY:
            return np.linspace(start, stop, num).tolist()
        if num <= 1:
            return [start]
        step = (stop - start) / (num - 1)
        return [start + i * step for i in range(num)]


# Create a global instance for easy access
numpy_compat = NumpyCompat()


# Export commonly used functions at module level
def safe_mean(data: List[float]) -> float:
    """Calculate mean with error handling"""
    try:
        return numpy_compat.mean(data)
    except Exception as e:
        logger.error(f"Error calculating mean: {e}")
        return 0.0


def safe_std(data: List[float], ddof: int = 0) -> float:
    """Calculate standard deviation with error handling"""
    try:
        return numpy_compat.std(data, ddof=ddof)
    except Exception as e:
        logger.error(f"Error calculating std: {e}")
        return 0.0


def safe_array(data: List[Union[int, float]]) -> Union['np.ndarray', List[float]]:
    """Create array with error handling"""
    try:
        return numpy_compat.array(data)
    except Exception as e:
        logger.error(f"Error creating array: {e}")
        return []


# Status function for checking numpy availability
def has_numpy() -> bool:
    """Check if numpy is available"""
    return HAS_NUMPY


# Log numpy status on module import
if HAS_NUMPY:
    logger.info("NumPy compatibility: Using NumPy for numerical operations")
else:
    logger.info("NumPy compatibility: Using pure Python fallbacks")