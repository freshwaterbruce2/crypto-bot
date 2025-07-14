"""
Safe Import System
Handles safe module imports with fallbacks and error handling
"""

import logging
import importlib
from typing import Any, Optional, Callable, Dict

logger = logging.getLogger(__name__)


class SafeImporter:
    """Safe module importer with fallback handling"""
    
    def __init__(self):
        """Initialize safe importer"""
        self.fallbacks: Dict[str, Any] = {}
        self.repair_callbacks: Dict[str, Callable] = {}
    
    def register_fallback(self, module_name: str, fallback: Any):
        """Register fallback for module"""
        self.fallbacks[module_name] = fallback
        logger.debug(f"[SAFE_IMPORT] Registered fallback for {module_name}")
    
    def register_repair_callback(self, module_name: str, callback: Callable):
        """Register repair callback for module"""
        self.repair_callbacks[module_name] = callback
        logger.debug(f"[SAFE_IMPORT] Registered repair callback for {module_name}")
    
    def safe_import(self, module_name: str, fallback: Optional[Any] = None) -> Any:
        """Safely import module with fallback"""
        try:
            module = importlib.import_module(module_name)
            logger.debug(f"[SAFE_IMPORT] Successfully imported {module_name}")
            return module
        except ImportError as e:
            logger.warning(f"[SAFE_IMPORT] Failed to import {module_name}: {e}")
            
            # Try repair callback first
            if module_name in self.repair_callbacks:
                try:
                    self.repair_callbacks[module_name]()
                    module = importlib.import_module(module_name)
                    logger.info(f"[SAFE_IMPORT] Repaired and imported {module_name}")
                    return module
                except Exception as repair_error:
                    logger.error(f"[SAFE_IMPORT] Repair failed for {module_name}: {repair_error}")
            
            # Use fallback
            if fallback is not None:
                logger.info(f"[SAFE_IMPORT] Using provided fallback for {module_name}")
                return fallback
            elif module_name in self.fallbacks:
                logger.info(f"[SAFE_IMPORT] Using registered fallback for {module_name}")
                return self.fallbacks[module_name]
            else:
                logger.error(f"[SAFE_IMPORT] No fallback available for {module_name}")
                raise


# Global instance
_safe_importer = SafeImporter()


def safe_import(module_name: str, fallback: Optional[Any] = None) -> Any:
    """Safely import module with fallback"""
    return _safe_importer.safe_import(module_name, fallback)


def register_fallback(module_name: str, fallback: Any):
    """Register fallback for module"""
    _safe_importer.register_fallback(module_name, fallback)


def register_repair_callback(module_name: str, callback: Callable):
    """Register repair callback for module"""
    _safe_importer.register_repair_callback(module_name, callback)


def validate_dependencies(required_modules: list) -> Dict[str, bool]:
    """Validate that required modules are available"""
    results = {}
    for module_name in required_modules:
        try:
            importlib.import_module(module_name)
            results[module_name] = True
        except ImportError:
            results[module_name] = False
    return results


def ensure_module_installed(module_name: str) -> bool:
    """Ensure module is installed and available"""
    try:
        importlib.import_module(module_name)
        return True
    except ImportError:
        logger.warning(f"[SAFE_IMPORT] Module {module_name} not available")
        return False