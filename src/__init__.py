# Auto-applied balance detection patch
try:
    from . import balance_detection_patch
except:
    pass

# This file makes src a Python package

# NumPy 2.x compatibility - MUST be imported first
# This fixes pandas_ta compatibility with NumPy 2.x
try:
    from . import numpy_compat
except ImportError:
    pass
