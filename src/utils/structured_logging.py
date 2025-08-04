"""
Structured Logging System for Trading Bot
=========================================

High-performance structured logging with JSON formatting, performance metrics,
and trading-specific log enrichment for better monitoring and debugging.
"""

import json
import logging
import time
import threading
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from functools import wraps
from collections import defaultdict, deque
import sys
import traceback

# Performance tracking
_log_metrics = defaultdict(int)
_log_timings = deque(maxlen=1000)
_metric_lock = threading.Lock()


class TradingLogFormatter(logging.Formatter):
    """Custom JSON formatter for trading logs"""
    
    def __init__(self, include_extra: bool = True):
        super().__init__()
        self.include_extra = include_extra
        self.hostname = self._get_hostname()
        
    def _get_hostname(self) -> str:
        """Get hostname for log enrichment"""
        try:
            import socket
            return socket.gethostname()
        except:
            return "unknown"
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON"""
        
        # Base log structure
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "thread": record.thread,
            "process": record.process,
            "hostname": self.hostname
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info)
            }
        
        # Add extra fields
        if self.include_extra:
            for key, value in record.__dict__.items():
                if key not in log_entry and not key.startswith('_'):
                    # Skip standard logging attributes
                    if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                                 'filename', 'module', 'lineno', 'funcName', 'created',
                                 'msecs', 'relativeCreated', 'thread', 'threadName',
                                 'processName', 'process', 'getMessage', 'exc_info', 'exc_text',
                                 'stack_info', 'taskName']:
                        try:
                            # Serialize complex objects as strings
                            if isinstance(value, (dict, list, tuple)):
                                log_entry[key] = json.dumps(value) if len(str(value)) < 1000 else str(value)[:1000]
                            else:
                                log_entry[key] = value
                        except (TypeError, ValueError):
                            log_entry[key] = str(value)
        
        return json.dumps(log_entry, default=str, separators=(',', ':'))


class TradingLogger:
    """Enhanced logger for trading operations with performance tracking"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.name = name
        
        # Performance tracking
        self.operation_counts = defaultdict(int)
        self.operation_timings = defaultdict(list)
        
    def _log_with_context(self, level: int, msg: str, **kwargs):
        """Log with trading context"""
        with _metric_lock:
            _log_metrics[level] += 1
            _log_timings.append(time.time())
        
        # Enrich with trading context
        extra = {
            'log_id': f"{int(time.time()*1000)}_{threading.get_ident()}",
            'bot_version': kwargs.pop('bot_version', '2025.1'),
            'exchange': kwargs.pop('exchange', 'kraken'),
            **kwargs
        }
        
        self.logger.log(level, msg, extra=extra)
    
    def info(self, msg: str, **kwargs):
        """Log info message with context"""
        self._log_with_context(logging.INFO, msg, **kwargs)
    
    def warning(self, msg: str, **kwargs):
        """Log warning message with context"""
        self._log_with_context(logging.WARNING, msg, **kwargs)
    
    def error(self, msg: str, **kwargs):
        """Log error message with context"""
        self._log_with_context(logging.ERROR, msg, **kwargs)
    
    def debug(self, msg: str, **kwargs):
        """Log debug message with context"""
        self._log_with_context(logging.DEBUG, msg, **kwargs)
    
    def critical(self, msg: str, **kwargs):
        """Log critical message with context"""
        self._log_with_context(logging.CRITICAL, msg, **kwargs)
    
    def trade(self, symbol: str, side: str, amount: float, price: float, **kwargs):
        """Log trade execution with structured data"""
        self._log_with_context(
            logging.INFO,
            f"Trade executed: {side} {amount} {symbol} @ {price}",
            event_type="trade_execution",
            symbol=symbol,
            side=side,
            amount=amount,
            price=price,
            trade_value=amount * price,
            **kwargs
        )
    
    def balance_update(self, asset: str, old_balance: float, new_balance: float, **kwargs):
        """Log balance update with structured data"""
        change = new_balance - old_balance
        self._log_with_context(
            logging.INFO,
            f"Balance updated: {asset} {old_balance} -> {new_balance} ({change:+.8f})",
            event_type="balance_update",
            asset=asset,
            old_balance=old_balance,
            new_balance=new_balance,
            balance_change=change,
            **kwargs
        )
    
    def signal_generated(self, symbol: str, signal_type: str, confidence: float, **kwargs):
        """Log trading signal with structured data"""
        self._log_with_context(
            logging.INFO,
            f"Signal: {signal_type} {symbol} (confidence: {confidence:.2%})",
            event_type="trading_signal",
            symbol=symbol,
            signal_type=signal_type,
            confidence=confidence,
            **kwargs
        )
    
    def performance_metric(self, metric_name: str, value: float, unit: str = "", **kwargs):
        """Log performance metric"""
        self._log_with_context(
            logging.INFO,
            f"Performance: {metric_name} = {value} {unit}",
            event_type="performance_metric",
            metric_name=metric_name,
            metric_value=value,
            metric_unit=unit,
            **kwargs
        )
    
    def api_call(self, endpoint: str, method: str, duration: float, status_code: int = None, **kwargs):
        """Log API call with performance data"""
        self._log_with_context(
            logging.INFO,
            f"API call: {method} {endpoint} ({duration:.3f}s)",
            event_type="api_call",
            endpoint=endpoint,
            method=method,
            duration=duration,
            status_code=status_code,
            **kwargs
        )
    
    def websocket_event(self, event_type: str, channel: str, data_size: int = 0, **kwargs):
        """Log WebSocket event with structured data"""
        self._log_with_context(
            logging.DEBUG,
            f"WebSocket: {event_type} on {channel} ({data_size} bytes)",
            event_type="websocket_event",
            ws_event_type=event_type,
            channel=channel,
            data_size=data_size,
            **kwargs
        )


def timed_operation(operation_name: str = None):
    """Decorator to log operation timing"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Log successful operation
                logger = get_logger(func.__module__)
                logger.performance_metric(
                    f"{op_name}_duration",
                    duration,
                    "seconds",
                    operation=op_name,
                    success=True
                )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                # Log failed operation
                logger = get_logger(func.__module__)
                logger.error(
                    f"Operation failed: {op_name} ({duration:.3f}s)",
                    operation=op_name,
                    duration=duration,
                    error_type=type(e).__name__,
                    error_message=str(e),
                    success=False
                )
                raise
                
        return wrapper
    return decorator


def log_exceptions(logger_name: str = None):
    """Decorator to automatically log exceptions"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger = get_logger(logger_name or func.__module__)
                logger.error(
                    f"Exception in {func.__name__}: {str(e)}",
                    function=func.__name__,
                    exception_type=type(e).__name__,
                    exception_message=str(e),
                    traceback=traceback.format_exc()
                )
                raise
        return wrapper
    return decorator


class LoggingContextManager:
    """Context manager for adding context to all logs within a block"""
    
    def __init__(self, logger: TradingLogger, **context):
        self.logger = logger
        self.context = context
        self.original_log_method = None
    
    def __enter__(self):
        # Store original logging method
        self.original_log_method = self.logger._log_with_context
        
        # Create wrapped method with context
        def wrapped_log(level, msg, **kwargs):
            combined_kwargs = {**self.context, **kwargs}
            return self.original_log_method(level, msg, **combined_kwargs)
        
        self.logger._log_with_context = wrapped_log
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore original method
        self.logger._log_with_context = self.original_log_method


def setup_structured_logging(log_level: str = "INFO", 
                            log_file: str = None,
                            enable_console: bool = True) -> None:
    """Setup structured logging for the entire application"""
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Create formatter
    formatter = TradingLogFormatter()
    
    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        except Exception as e:
            print(f"Failed to setup file logging: {e}")
    
    # Set specific logger levels
    logging.getLogger('kraken').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('websockets').setLevel(logging.WARNING)
    
    print(f"Structured logging configured: level={log_level}, file={log_file}")


def get_logger(name: str) -> TradingLogger:
    """Get a trading logger instance"""
    return TradingLogger(name)


def get_logging_stats() -> Dict[str, Any]:
    """Get logging performance statistics"""
    with _metric_lock:
        total_logs = sum(_log_metrics.values())
        recent_logs = len([t for t in _log_timings if time.time() - t < 60])  # Last minute
        
        return {
            "total_logs": total_logs,
            "recent_logs_per_minute": recent_logs,
            "logs_by_level": dict(_log_metrics),
            "avg_logs_per_second": len(_log_timings) / 60 if _log_timings else 0,
            "memory_usage_logs": len(_log_timings)
        }


# Pre-configured loggers for common modules
trade_logger = get_logger("trading")
balance_logger = get_logger("balance")
exchange_logger = get_logger("exchange")
strategy_logger = get_logger("strategy")
performance_logger = get_logger("performance")

# Export main components
__all__ = [
    'TradingLogger',
    'TradingLogFormatter', 
    'setup_structured_logging',
    'get_logger',
    'get_logging_stats',
    'timed_operation',
    'log_exceptions',
    'LoggingContextManager',
    'trade_logger',
    'balance_logger',
    'exchange_logger',
    'strategy_logger',
    'performance_logger'
]