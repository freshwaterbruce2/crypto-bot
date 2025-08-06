#!/usr/bin/env python3
"""
Unicode-Safe Logging System - Permanent Solution for Windows Console Issues
===========================================================================

This module provides a comprehensive logging solution that prevents UnicodeEncodeError
exceptions on Windows systems while maintaining full logging functionality.

Key Features:
- Automatic Unicode character sanitization
- Windows console compatibility
- UTF-8 file logging support
- Emoji-safe formatters
- Graceful fallback for problematic characters

Usage:
    from src.utils.unicode_safe_logging import setup_unicode_safe_logging
    logger = setup_unicode_safe_logging(__name__)
    logger.info("This will never cause Unicode errors! [OK][LAUNCH]")
"""

import logging
import os
import re
import sys
from logging.handlers import RotatingFileHandler
from typing import Any, Dict, Optional


class UnicodeSafeFormatter(logging.Formatter):
    """
    Custom formatter that sanitizes Unicode characters to prevent encoding errors.
    
    This formatter automatically replaces problematic Unicode characters with
    safe ASCII alternatives while preserving log functionality.
    """

    # Unicode replacement mapping for common emoji and symbols
    UNICODE_REPLACEMENTS = {
        '[OK]': '[SUCCESS]',
        '[FAIL]': '[ERROR]',
        '[WARN]': '[WARNING]',
        '[LAUNCH]': '[LAUNCH]',
        '[STATS]': '[DATA]',
        '[PROFIT]': '[PROFIT]',
        '[REFRESH]': '[REFRESH]',
        '[TARGET]': '[TARGET]',
        '[AI]': '[AI]',
        '[TIME]': '[TIME]',
        '[CONFIG]': '[CONFIG]',
        '[UP]': '[TREND_UP]',
        '[DOWN]': '[TREND_DOWN]',
        '[LINK]': '[LINK]',
        '[IDEA]': '[IDEA]',
        '[GUARD]': '[SECURITY]',
        '[FAST]': '[FAST]',
        '[SUCCESS]': '[CELEBRATION]',
        '[SCAN]': '[SEARCH]',
        '[SAVE]': '[SAVE]',
        '[NET]': '[NETWORK]',
        '[LIST]': '[LIST]',
        '[EVENT]': '[EVENT]',
        '[ERROR]': '[RED]',
        '[GREEN]': '[GREEN]',
        '[YELLOW]': '[YELLOW]',
        '[BLUE]': '[BLUE]',
        '[STAR]': '[STAR]',
        '[SPARK]': '[SPARKLE]',
        '[MEDAL]': '[MEDAL]',
        '[TROPHY]': '[TROPHY]',
        '[RANDOM]': '[RANDOM]',
        '[MOBILE]': '[MOBILE]',
        '[SIGNAL]': '[SATELLITE]',
        '[ALERT]': '[BELL]',
        '[STATS]': '[BAR_CHART]',
        '[UP]': '[CHART_UP]',
        '[DOWN]': '[CHART_DOWN]',
        '[NOTE]': '[MEMO]',
        # Arrow symbols
        '->': '->',
        '<-': '<-',
        '^': '^',
        'v': 'v',
        '<->': '<->',
        '↕': '^v',
        '=>': '=>',
        '<=': '<=',
        '⇑': '^^',
        '⇓': 'vv',
        '⇔': '<=>',
        '⇕': '^^vv',
        # Mathematical symbols
        '≈': '~=',
        '≠': '!=',
        '≤': '<=',
        '≥': '>=',
        '±': '+/-',
        '∞': 'inf',
        '∑': 'sum',
        '∏': 'prod',
        '∫': 'integral',
        '∂': 'd/dx',
        '∆': 'delta',
        '∇': 'grad',
        '∝': 'prop',
        '∈': 'in',
        '∉': 'not_in',
        '∪': 'union',
        '∩': 'intersect',
        '⊂': 'subset',
        '⊃': 'superset',
        '⊆': 'subset_eq',
        '⊇': 'superset_eq',
        # Currency symbols
        '€': 'EUR',
        '£': 'GBP',
        '¥': 'JPY',
        '₿': 'BTC',
        # Quote marks and dashes
        '"': '"',
        '"': '"',
        ''': "'",
        ''': "'",
        '–': '-',
        '—': '--',
        '…': '...',
        # Degree and other symbols
        '°': 'deg',
        '™': '(TM)',
        '®': '(R)',
        '©': '(C)',
        '§': 'section',
        '¶': 'para',
        '†': 'dagger',
        '‡': 'double_dagger',
        '*': '*',
        '‰': 'permille',
        '‱': 'permyriad',
    }

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the Unicode-safe formatter."""
        super().__init__(*args, **kwargs)
        # Compile regex pattern for efficient Unicode detection
        self.unicode_pattern = re.compile(r'[^\x00-\x7F]+')

    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record with Unicode safety.
        
        Args:
            record: The log record to format
            
        Returns:
            str: Safely formatted log message
        """
        try:
            # Get the original formatted message
            formatted_message = super().format(record)

            # Apply Unicode replacements
            safe_message = self._sanitize_unicode(formatted_message)

            return safe_message

        except Exception:
            # Fallback formatting if something goes wrong
            return f"[LOGGING_ERROR] {record.levelname}: {self._sanitize_unicode(str(record.getMessage()))}"

    def _sanitize_unicode(self, text: str) -> str:
        """
        Sanitize Unicode characters in text.
        
        Args:
            text: Input text that may contain Unicode characters
            
        Returns:
            str: Text with Unicode characters safely replaced
        """
        if not isinstance(text, str):
            text = str(text)

        # Apply known replacements first
        for unicode_char, replacement in self.UNICODE_REPLACEMENTS.items():
            text = text.replace(unicode_char, replacement)

        # Handle any remaining non-ASCII characters
        def replace_unknown_unicode(match):
            """Replace unknown Unicode characters with safe alternatives."""
            char = match.group(0)
            # Try to get a meaningful replacement
            try:
                import unicodedata
                name = unicodedata.name(char, '').replace(' ', '_').lower()
                if name:
                    return f'[{name}]'
            except:
                pass

            # Fallback to hex representation
            return f'[U+{ord(char):04X}]'

        # Replace any remaining Unicode characters
        safe_text = self.unicode_pattern.sub(replace_unknown_unicode, text)

        return safe_text


class UnicodeSafeStreamHandler(logging.StreamHandler):
    """
    Stream handler that safely handles Unicode characters on Windows console.
    """

    def emit(self, record: logging.LogRecord):
        """
        Emit a log record with Unicode safety.
        
        Args:
            record: The log record to emit
        """
        try:
            # Get the formatted message
            msg = self.format(record)

            # Handle encoding for different stream types
            if hasattr(self.stream, 'encoding') and self.stream.encoding:
                # Use stream's encoding if available
                try:
                    encoded_msg = msg.encode(self.stream.encoding, errors='replace').decode(self.stream.encoding)
                    self.stream.write(encoded_msg + self.terminator)
                except (UnicodeEncodeError, UnicodeDecodeError):
                    # Fallback to ASCII-safe version
                    ascii_msg = msg.encode('ascii', errors='replace').decode('ascii')
                    self.stream.write(ascii_msg + self.terminator)
            else:
                # Default safe output
                ascii_msg = msg.encode('ascii', errors='replace').decode('ascii')
                self.stream.write(ascii_msg + self.terminator)

            self.flush()

        except Exception:
            # Ultimate fallback - just try to output something useful
            try:
                fallback_msg = f"[LOG_ERROR] {record.levelname}: {record.getMessage()}"
                ascii_fallback = fallback_msg.encode('ascii', errors='replace').decode('ascii')
                self.stream.write(ascii_fallback + self.terminator)
                self.flush()
            except:
                # If even this fails, we give up gracefully
                pass


def setup_unicode_safe_logging(
    name: str,
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    log_dir: Optional[str] = None,
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    console_output: bool = True,
    file_output: bool = True
) -> logging.Logger:
    """
    Set up a Unicode-safe logger with comprehensive configuration.
    
    Args:
        name: Logger name (typically __name__)
        level: Logging level (default: INFO)
        log_file: Specific log file name
        log_dir: Directory for log files
        max_file_size: Maximum size for rotating log files
        backup_count: Number of backup files to keep
        console_output: Whether to output to console
        file_output: Whether to output to file
        
    Returns:
        logging.Logger: Configured Unicode-safe logger
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Clear any existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create Unicode-safe formatter
    formatter = UnicodeSafeFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler with Unicode safety
    if console_output:
        console_handler = UnicodeSafeStreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # File handler with UTF-8 encoding
    if file_output:
        if not log_file:
            log_file = f"{name.replace('.', '_')}.log"

        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
            log_path = os.path.join(log_dir, log_file)
        else:
            log_path = log_file

        try:
            file_handler = RotatingFileHandler(
                log_path,
                maxBytes=max_file_size,
                backupCount=backup_count,
                encoding='utf-8'  # Ensure UTF-8 encoding for file output
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            # If file handler fails, continue with console only
            if console_output:
                logger.warning(f"Could not set up file logging: {e}")

    return logger


def configure_global_unicode_safe_logging(
    log_dir: str = "trading_data/logs",
    log_level: int = logging.INFO
) -> Dict[str, Any]:
    """
    Configure global Unicode-safe logging for the entire application.
    
    Args:
        log_dir: Directory for log files
        log_level: Global logging level
        
    Returns:
        Dict[str, Any]: Configuration summary
    """
    # Create log directory
    os.makedirs(log_dir, exist_ok=True)

    # Configure root logger with Unicode safety
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(log_level)

    # Create Unicode-safe formatter
    formatter = UnicodeSafeFormatter(
        '[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler
    console_handler = UnicodeSafeStreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Main application log file
    main_log_path = os.path.join(log_dir, "kraken_bot.log")
    try:
        main_file_handler = RotatingFileHandler(
            main_log_path,
            maxBytes=20 * 1024 * 1024,  # 20MB
            backupCount=10,
            encoding='utf-8'
        )
        main_file_handler.setLevel(log_level)
        main_file_handler.setFormatter(formatter)
        root_logger.addHandler(main_file_handler)
    except Exception as e:
        root_logger.warning(f"Could not set up main log file: {e}")

    # Error log file (ERROR and CRITICAL only)
    error_log_path = os.path.join(log_dir, "kraken_bot_errors.log")
    try:
        error_file_handler = RotatingFileHandler(
            error_log_path,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        error_file_handler.setLevel(logging.ERROR)
        error_file_handler.setFormatter(formatter)
        root_logger.addHandler(error_file_handler)
    except Exception as e:
        root_logger.warning(f"Could not set up error log file: {e}")

    return {
        'status': 'configured',
        'log_dir': log_dir,
        'log_level': logging.getLevelName(log_level),
        'handlers': len(root_logger.handlers),
        'main_log': main_log_path,
        'error_log': error_log_path
    }


def test_unicode_safe_logging():
    """Test the Unicode-safe logging system with various Unicode characters."""
    # Set up test logger
    logger = setup_unicode_safe_logging(
        'unicode_test',
        level=logging.DEBUG,
        log_file='unicode_test.log'
    )

    # Test various Unicode characters and emoji
    test_messages = [
        "Basic ASCII message",
        "Message with emoji: [OK] SUCCESS",
        "Error with emoji: [FAIL] FAILED",
        "Trading symbols: [UP] UP [DOWN] DOWN [PROFIT] PROFIT",
        "Technical symbols: [FAST] FAST [CONFIG] CONFIG [LAUNCH] LAUNCH",
        "Mathematical: π ≈ 3.14159, ∞ infinity, ∑ sum",
        "Currencies: $100 €85 £75 ¥10000 ₿0.001",
        "Special quotes: 'Hello' 'World' -- dash",
        "Non-English: Café naïve résumé piñata jalapeño",
        "Box drawing: [EMOJI] [EMOJI]",
        "More complex: [TARGET][REFRESH][STATS][IDEA][GUARD][STAR][SPARK][SUCCESS]"
    ]

    for i, message in enumerate(test_messages, 1):
        logger.info(f"Test {i}: {message}")

    logger.info("Unicode safety test completed successfully!")
    return logger


if __name__ == "__main__":
    # Run the test
    test_logger = test_unicode_safe_logging()
    print("Unicode-safe logging test completed. Check 'unicode_test.log' for results.")
