"""
Trading Bot Logging - Simplified and Reliable
Supports profit-focused micro-scalping strategy
"""

import logging
import sys
import re
import json
from pathlib import Path
from datetime import datetime


def setup_logging(level: str = 'INFO', log_file: str = 'kraken_infinity_bot.log') -> logging.Logger:
    """
    Set up logging configuration for the trading bot
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Path to log file
        
    Returns:
        Configured logger instance
    """
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create logger
    logger = logging.getLogger('trading_bot')
    logger.setLevel(numeric_level)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Create formatter
    formatter = UnicodeSafeFormatter(
        fmt='[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
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
    """Setup simple, reliable logging for trading bot."""
    # Load config
    config_path = Path(__file__).parent.parent.parent / 'config.json'
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception:
        config = {}
    
    # Settings
    log_level = getattr(logging, config.get('log_level', 'INFO').upper(), logging.INFO)
    log_dir = Path(config.get('log_dir', 'trading_data/logs'))
    
    # Create log directory and use main log file
    try:
        # Primary: Write to project root for main monitoring
        project_root = Path(__file__).parent.parent.parent
        main_log_file = project_root / 'kraken_infinity_bot.log'
        
        # Secondary: Write to trading data for historical analysis
        log_dir.mkdir(parents=True, exist_ok=True)
        secondary_log_file = log_dir / 'trading_bot.log'
        
        log_file = main_log_file
    except Exception:
        # Fallback to local directory
        log_dir = Path('./logs')
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / 'trading_bot.log'
    
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
    
    # File handler (can handle Unicode with UTF-8 encoding)
    file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
    file_handler.setFormatter(file_formatter)
    file_handler.addFilter(ConfidenceDisplayFilter())
    
    # Console handler with Unicode safety
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)  # Use Unicode-safe formatter
    console_handler.addFilter(ConfidenceDisplayFilter())
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Log once
    if not hasattr(configure_logging, '_logged'):
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