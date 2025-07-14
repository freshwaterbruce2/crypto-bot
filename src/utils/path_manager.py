"""
Path Manager
Handles file paths and directory management
"""

import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class SecurityError(Exception):
    """SECURITY FIX: Exception for security-related path validation errors"""
    pass


class PathManager:
    """Path manager for handling file paths and directories"""
    
    def __init__(self, base_path: Optional[str] = None):
        """Initialize path manager"""
        self.base_path = Path(base_path) if base_path else Path.cwd()
        self.data_path = self.base_path / "data"
        self.logs_path = self.base_path / "logs"
        self.trading_data_path = Path("D:/trading_bot_data")
    
    def ensure_directories(self):
        """Ensure all required directories exist"""
        directories = [
            self.data_path,
            self.logs_path,
            self.trading_data_path,
            self.trading_data_path / "logs",
            self.trading_data_path / "historical",
            self.trading_data_path / "learning"
        ]
        
        for directory in directories:
            try:
                directory.mkdir(parents=True, exist_ok=True)
                logger.debug(f"[PATH_MANAGER] Ensured directory exists: {directory}")
            except Exception as e:
                logger.error(f"[PATH_MANAGER] Failed to create directory {directory}: {e}")
    
    def get_data_path(self, filename: str = "") -> Path:
        """Get path for data files with security validation"""
        if filename:
            # SECURITY FIX: Prevent path traversal attacks
            filename = os.path.basename(filename)
            if '..' in filename or filename.startswith('/') or filename.startswith('\\'):
                raise SecurityError(f"Invalid filename: {filename}. Path traversal not allowed.")
            # Additional security: check for dangerous characters
            dangerous_chars = ['<', '>', ':', '"', '|', '?', '*']
            if any(char in filename for char in dangerous_chars):
                raise SecurityError(f"Invalid filename: {filename}. Contains dangerous characters.")
        return self.data_path / filename if filename else self.data_path
    
    def get_logs_path(self, filename: str = "") -> Path:
        """Get path for log files with security validation"""
        if filename:
            # SECURITY FIX: Prevent path traversal attacks
            filename = os.path.basename(filename)
            if '..' in filename or filename.startswith('/') or filename.startswith('\\'):
                raise SecurityError(f"Invalid filename: {filename}. Path traversal not allowed.")
        return self.logs_path / filename if filename else self.logs_path
    
    def get_trading_data_path(self, filename: str = "") -> Path:
        """Get path for trading data files with security validation"""
        if filename:
            # SECURITY FIX: Prevent path traversal attacks
            filename = os.path.basename(filename)
            if '..' in filename or filename.startswith('/') or filename.startswith('\\'):
                raise SecurityError(f"Invalid filename: {filename}. Path traversal not allowed.")
        return self.trading_data_path / filename if filename else self.trading_data_path
    
    def get_config_path(self, filename: str = "config.json") -> Path:
        """Get path for config files with security validation"""
        if filename:
            # SECURITY FIX: Prevent path traversal attacks
            filename = os.path.basename(filename)
            if '..' in filename or filename.startswith('/') or filename.startswith('\\'):
                raise SecurityError(f"Invalid filename: {filename}. Path traversal not allowed.")
        return self.base_path / filename
    
    def file_exists(self, path: Path) -> bool:
        """Check if file exists"""
        return path.exists() and path.is_file()
    
    def get_file_size(self, path: Path) -> int:
        """Get file size in bytes"""
        try:
            return path.stat().st_size if self.file_exists(path) else 0
        except Exception:
            return 0