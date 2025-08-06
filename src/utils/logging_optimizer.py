"""
Logging Optimization Configuration
Prevents log bloat by implementing smart log rotation and filtering
"""

import logging
import logging.handlers
import os
from datetime import datetime


class RepeatFilter(logging.Filter):
    """Filter to prevent repeated log messages from flooding the log file"""

    def __init__(self, max_repeats=5):
        super().__init__()
        self.max_repeats = max_repeats
        self.message_counts = {}
        self.last_reset = datetime.now()

    def filter(self, record):
        # Reset counts every hour
        now = datetime.now()
        if (now - self.last_reset).seconds > 3600:
            self.message_counts = {}
            self.last_reset = now

        # Create a key from the message
        key = f"{record.levelname}:{record.msg}"

        # Track message count
        if key not in self.message_counts:
            self.message_counts[key] = 0

        self.message_counts[key] += 1

        # Allow first N occurrences
        if self.message_counts[key] <= self.max_repeats:
            return True

        # Log summary every 100 occurrences
        if self.message_counts[key] % 100 == 0:
            record.msg = f"{record.msg} [Repeated {self.message_counts[key]} times]"
            return True

        return False


def configure_optimized_logging(log_dir="logs", max_file_size_mb=50, backup_count=10):
    """
    Configure optimized logging with rotation and filtering

    Args:
        log_dir: Directory for log files
        max_file_size_mb: Maximum size per log file in MB
        backup_count: Number of backup files to keep
    """

    # Create log directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )

    # File handler with rotation (detailed logs)
    file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'kraken_bot.log'),
        maxBytes=max_file_size_mb * 1024 * 1024,  # Convert to bytes
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    file_handler.addFilter(RepeatFilter(max_repeats=5))

    # Console handler (important messages only)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    console_handler.addFilter(RepeatFilter(max_repeats=3))

    # Error file handler (errors only)
    error_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'kraken_bot_errors.log'),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)

    # Add handlers to root logger
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(error_handler)

    # Configure specific loggers to reduce noise
    noisy_loggers = [
        'ccxt.base.exchange',
        'urllib3.connectionpool',
        'websockets.protocol',
        'asyncio'
    ]

    for logger_name in noisy_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.WARNING)

    # Special handling for balance manager logs
    balance_logger = logging.getLogger('src.balance.balance_manager')
    balance_logger.setLevel(logging.INFO)  # Reduce DEBUG spam

    # Log rotation on startup if file is too large
    if os.path.exists(file_handler.baseFilename):
        file_size_mb = os.path.getsize(file_handler.baseFilename) / (1024 * 1024)
        if file_size_mb > max_file_size_mb:
            file_handler.doRollover()
            root_logger.info(f"Rotated log file (was {file_size_mb:.1f}MB)")

    root_logger.info("=" * 60)
    root_logger.info("OPTIMIZED LOGGING INITIALIZED")
    root_logger.info(f"Max file size: {max_file_size_mb}MB")
    root_logger.info(f"Backup count: {backup_count}")
    root_logger.info(f"Repeat filter: Max {RepeatFilter().max_repeats} repeats")
    root_logger.info("=" * 60)

    return root_logger


# Example usage in your bot.py:
if __name__ == "__main__":
    # Initialize optimized logging
    logger = configure_optimized_logging(
        log_dir="logs",
        max_file_size_mb=50,  # 50MB max per file
        backup_count=10       # Keep 10 backup files
    )

    # Test the repeat filter
    for _i in range(20):
        logger.error("Balance refresh failed")  # Will only log first 5 + summaries

    logger.info("Logging optimization complete!")
