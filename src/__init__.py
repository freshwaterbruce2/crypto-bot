# This file makes src a Python package

# NumPy 2.x compatibility - MUST be imported first
# This fixes pandas_ta compatibility with NumPy 2.x
try:
    from .utils import numpy_compat
except ImportError:
    # Fallback to absolute import if relative import fails
    try:
        from src.utils import numpy_compat
    except ImportError:
        # If numpy_compat still can't be imported, just pass
        pass

# Balance detection patch - commented out as module doesn't exist
# If you need this functionality, create the module first
# try:
#     from . import balance_detection_patch
# except ImportError:
#     pass
