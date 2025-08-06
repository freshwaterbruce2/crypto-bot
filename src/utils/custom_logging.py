"""
Trading Bot Logging - Professional System Integration
Upgraded with enterprise-grade log management to prevent 1.5GB log files
"""

import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path

# Import professional logging system
try:
    from .professional_logging_system import get_professional_logger, setup_professional_logging
    PROFESSIONAL_LOGGING_AVAILABLE = True
except ImportError:
    PROFESSIONAL_LOGGING_AVAILABLE = False


def setup_logging(level: str = 'INFO', log_file: str = 'kraken_infinity_bot.log') -> logging.Logger:
    """
    Set up logging configuration for the trading bot
    NOW USES PROFESSIONAL SYSTEM with log rotation and compression!
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Path to log file (now handled by professional system)
        
    Returns:
        Configured logger instance with enterprise features
    """

    # Use professional logging system if available
    if PROFESSIONAL_LOGGING_AVAILABLE:
        # Setup professional logging with optimal settings
        setup_professional_logging(
            log_dir="logs",
            max_file_size_mb=10,      # 10MB max per file (prevents 1.5GB crisis)
            backup_count=5,           # Keep 5 backup files
            enable_compression=True,  # Compress old logs
            enable_async=True,        # High-performance async logging
            enable_sampling=True,     # Prevent log flooding
            log_format="text"         # Human-readable format
        )

        # Return enhanced logger
        logger = get_professional_logger('trading_bot')
        logger.info("Professional logging system activated - log rotation enabled")
        return logger

    # Fallback to basic logging with rotation (if professional system fails)
    else:
        logger = logging.getLogger('trading_bot')
        logger.setLevel(getattr(logging, level.upper(), logging.INFO))

        # Clear existing handlers
        logger.handlers.clear()

        # Use rotating file handler instead of basic FileHandler
        from logging.handlers import RotatingFileHandler

        # Create formatter
        formatter = UnicodeSafeFormatter(
            fmt='[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Rotating file handler (prevents massive log files)
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB max
            backupCount=5,          # Keep 5 backups
            encoding='utf-8'
        )
        file_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        logger.warning("Using fallback logging - professional system not available")
        return logger


class UnicodeSafeFormatter(logging.Formatter):
    """Formatter that safely handles Unicode characters for Windows console."""

    # Unicode character replacements for console safety
    UNICODE_REPLACEMENTS = {
        '[OK]': '[OK]',
        '[ERROR]': '[ERROR]',
        '[WARNING]': '[WARNING]',
        '[BULLSEYE]': '[TARGET]',
        '[LAUNCH]': '[LAUNCH]',
        '[MONEY]': '[PROFIT]',
        '[DATA]': '[DATA]',
        '[SYNC]': '[SYNC]',
        '[STAR]': '[STAR]',
        '[CELEBRATE]': '[SUCCESS]',
        '[FIX]': '[CONFIG]',
        '[NOTE]': '[MEMO]',
        # Arrow symbols
        '->': '->',
        '<-': '<-',
        '^': '^',
        'v': 'v',
        # Other symbols
        '*': '*',
    }

    def format(self, record):
        # Format the record normally first
        formatted = super().format(record)

        # Replace Unicode characters with ASCII equivalents
        for unicode_char, replacement in self.UNICODE_REPLACEMENTS.items():
            formatted = formatted.replace(unicode_char, replacement)

        # Remove any remaining problematic Unicode characters
        # Keep only printable ASCII characters
        formatted = ''.join(char if ord(char) < 128 else '?' for char in formatted)

        return formatted


class ConfidenceDisplayFilter(logging.Filter):
    """Convert decimal confidence values (0.0-1.0) to percentages (0%-100%)."""

    def filter(self, record):
        """Fix confidence values in log messages."""
        if hasattr(record, 'msg'):
            # Pattern to match confidence values
            pattern = r'confidence[:=\s]+(\d*\.?\d+)([%\s])'

            def fix_confidence_match(match):
                value = float(match.group(1))
                suffix = match.group(2)

                # Convert decimal to percentage if needed
                if value <= 1.0 and suffix != '%':
                    value = value * 100

                return f'confidence: {value:.1f}%'

            # Fix the message
            record.msg = re.sub(pattern, fix_confidence_match, str(record.msg), flags=re.IGNORECASE)

        return True


def configure_logging():
    """Setup professional, reliable logging for trading bot with automatic rotation."""

    # Use professional logging system if available
    if PROFESSIONAL_LOGGING_AVAILABLE:
        # Load config for log level
        config_path = Path(__file__).parent.parent.parent / 'config.json'
        try:
            with open(config_path, encoding='utf-8') as f:
                config = json.load(f)
        except Exception:
            config = {}

        log_level = config.get('log_level', 'INFO')

        # Setup professional logging system
        logging_system = setup_professional_logging(
            log_dir="logs",
            max_file_size_mb=10,      # 10MB max per file
            backup_count=5,           # Keep 5 backup files
            enable_compression=True,  # Compress old logs
            enable_async=True,        # High-performance async logging
            enable_sampling=True,     # Prevent log flooding
            log_format="text"         # Human-readable format
        )

        # Get root logger
        root_logger = logging.getLogger()

        # Log initialization (only once)
        if not hasattr(configure_logging, '_logged'):
            root_logger.info('[LOGGER] Professional logging system activated')
            root_logger.info('[LOGGER] Log rotation: 10MB max, 5 backups, compression enabled')
            root_logger.info('[LOGGER] Async logging and sampling enabled for performance')
            configure_logging._logged = True

        return root_logger

    # Fallback to improved basic logging
    else:
        # Load config
        config_path = Path(__file__).parent.parent.parent / 'config.json'
        try:
            with open(config_path, encoding='utf-8') as f:
                config = json.load(f)
        except Exception:
            config = {}

        # Settings
        log_level = getattr(logging, config.get('log_level', 'INFO').upper(), logging.INFO)

        # Create log directory
        log_dir = Path('./logs')
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / 'kraken_trading_bot.log'

        # Use rotating file handler
        from logging.handlers import RotatingFileHandler

        # Regular formatter for file output (supports Unicode)
        file_formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Unicode-safe formatter for console output
        console_formatter = UnicodeSafeFormatter(
            '[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Rotating file handler (prevents massive log files)
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB max
            backupCount=5,          # Keep 5 backups
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(file_formatter)
        file_handler.addFilter(ConfidenceDisplayFilter())

        # Console handler with Unicode safety
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(console_formatter)
        console_handler.addFilter(ConfidenceDisplayFilter())

        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        root_logger.handlers.clear()
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)

        # Log once
        if not hasattr(configure_logging, '_logged'):
            root_logger.warning('[LOGGER] Using fallback logging with rotation')
            root_logger.info(f'[LOGGER] Logging initialized: {log_file}')
            configure_logging._logged = True

        return root_logger


def log_trade_opportunity(symbol, side, confidence, price, metrics=None):
    """
    Log a trading opportunity with profit focus.
    Supports our buy-low-sell-high micro-scalping strategy.
    
    Args:
        symbol: Trading pair (e.g., 'BTC/USDT')
        side: 'buy' or 'sell'
        confidence: Signal confidence (0-1 or 0-100)
        price: Current price in quote currency (USDT)
        metrics: Optional dict with additional metrics
    """
    # Ensure confidence is in percentage format
    if confidence <= 1.0:
        confidence = confidence * 100

    # Format the opportunity message (no $ for USDT prices)
    msg = f"[OPPORTUNITY] {symbol} {side.upper()} signal - Confidence: {confidence:.1f}% - Price: {price:.2f}"

    # Add profit metrics if available
    if metrics:
        if 'expected_profit' in metrics:
            msg += f" - Expected Profit: {metrics['expected_profit']:.2f}%"
        if 'position_size' in metrics:
            msg += f" - Position: {metrics['position_size']:.2f} USDT"
        if 'profit_target' in metrics:
            msg += f" - Target: {metrics['profit_target']:.2f}"

    # Log at INFO level for visibility
    logger.info(msg)

    # Also log to a separate opportunities file for analysis
    try:
        opp_file = Path('trading_data/logs/opportunities.log')
        opp_file.parent.mkdir(parents=True, exist_ok=True)

        with open(opp_file, 'a', encoding='utf-8') as f:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"[{timestamp}] {msg}\n")
    except Exception:
        pass  # Don't let opportunity logging fail the main process


# Create module-level logger instance
logger = logging.getLogger(__name__)

# For backward compatibility
setup_trading_logging = configure_logging
setup_unified_logger = configure_logging


__all__ = ["logger", "configure_logging", "log_trade_opportunity"]
