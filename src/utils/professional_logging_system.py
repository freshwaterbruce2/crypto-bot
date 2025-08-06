"""
Professional Logging System for Crypto Trading Bot
==================================================

High-performance logging system with:
- Automatic log rotation (10MB max per file)
- Retention policy (5 files maximum)
- Structured JSON logging for analytics
- Performance monitoring and sampling
- Async logging for high-frequency operations
- Memory-efficient buffered logging
- Real-time log health monitoring

Solves the 1.5GB log file crisis with enterprise-grade log management.
"""

import gzip
import json
import logging
import logging.handlers
import os
import queue
import shutil
import sys
import threading
import time
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class HighFrequencyLogSampler:
    """Prevents log flooding by sampling high-frequency repeated messages"""

    def __init__(self, window_seconds: int = 60, max_messages_per_window: int = 10):
        self.window_seconds = window_seconds
        self.max_messages_per_window = max_messages_per_window
        self.message_windows = defaultdict(deque)
        self.lock = threading.Lock()

    def should_log(self, message_key: str) -> bool:
        """Determine if message should be logged based on frequency"""
        now = time.time()

        with self.lock:
            # Clean old entries
            window = self.message_windows[message_key]
            while window and (now - window[0] > self.window_seconds):
                window.popleft()

            # Check if under limit
            if len(window) < self.max_messages_per_window:
                window.append(now)
                return True

            # Log summary every 100 occurrences
            total_count = getattr(self, f'_total_{hash(message_key)}', 0) + 1
            setattr(self, f'_total_{hash(message_key)}', total_count)

            if total_count % 100 == 0:
                return True  # Allow summary log

            return False


class AsyncLogHandler(logging.Handler):
    """High-performance async log handler that doesn't block trading operations"""

    def __init__(self, target_handler: logging.Handler, queue_size: int = 10000):
        super().__init__()
        self.target_handler = target_handler
        self.log_queue = queue.Queue(maxsize=queue_size)
        self.stop_event = threading.Event()
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()
        self.dropped_logs = 0

    def emit(self, record):
        """Queue log record for async processing"""
        try:
            self.log_queue.put_nowait(record)
        except queue.Full:
            self.dropped_logs += 1
            # Drop oldest and add new
            try:
                self.log_queue.get_nowait()
                self.log_queue.put_nowait(record)
            except queue.Empty:
                pass

    def _worker(self):
        """Background worker that processes log queue"""
        while not self.stop_event.is_set():
            try:
                record = self.log_queue.get(timeout=1.0)
                self.target_handler.emit(record)
                self.log_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                # Fallback logging to prevent complete failure
                print(f"Async log handler error: {e}", file=sys.stderr)

    def close(self):
        """Gracefully shutdown async handler"""
        self.stop_event.set()
        self.worker_thread.join(timeout=5.0)
        self.target_handler.close()
        super().close()


class CompressedRotatingFileHandler(logging.handlers.RotatingFileHandler):
    """Enhanced rotating file handler with compression and smart rotation"""

    def __init__(self, filename, mode='a', maxBytes=0, backupCount=0,
                 encoding=None, delay=False, compress_old_logs=True):
        super().__init__(filename, mode, maxBytes, backupCount, encoding, delay)
        self.compress_old_logs = compress_old_logs

    def doRollover(self):
        """Enhanced rollover with compression and cleanup"""
        if self.stream:
            self.stream.close()
            self.stream = None

        # Standard rotation
        if self.backupCount > 0:
            for i in range(self.backupCount - 1, 0, -1):
                sfn = self.rotation_filename(f"{self.baseFilename}.{i}")
                dfn = self.rotation_filename(f"{self.baseFilename}.{i + 1}")
                if os.path.exists(sfn):
                    if os.path.exists(dfn):
                        os.remove(dfn)
                    os.rename(sfn, dfn)

            # Move current log to .1
            dfn = self.rotation_filename(f"{self.baseFilename}.1")
            if os.path.exists(dfn):
                os.remove(dfn)
            os.rename(self.baseFilename, dfn)

            # Compress rotated log
            if self.compress_old_logs and os.path.exists(dfn):
                self._compress_log_file(dfn)

        # Open new log file
        if not self.delay:
            self.stream = self._open()

    def _compress_log_file(self, filepath: str):
        """Compress a rotated log file"""
        try:
            compressed_path = f"{filepath}.gz"
            with open(filepath, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            os.remove(filepath)
        except Exception as e:
            print(f"Failed to compress log {filepath}: {e}", file=sys.stderr)


class TradingLogFormatter(logging.Formatter):
    """Professional formatter with structured JSON and performance data"""

    def __init__(self, format_type: str = "json", include_performance: bool = True):
        super().__init__()
        self.format_type = format_type
        self.include_performance = include_performance
        self.hostname = self._get_hostname()
        self.start_time = time.time()

    def _get_hostname(self) -> str:
        """Get hostname for log identification"""
        try:
            import socket
            return socket.gethostname()
        except:
            return "trading-bot"

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON or text"""

        if self.format_type == "json":
            return self._format_json(record)
        else:
            return self._format_text(record)

    def _format_json(self, record: logging.LogRecord) -> str:
        """Format as structured JSON"""

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

        # Add performance data
        if self.include_performance:
            log_entry["uptime_seconds"] = time.time() - self.start_time
            log_entry["memory_mb"] = self._get_memory_usage()

        # Add exception info
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info)
            }

        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in log_entry and not key.startswith('_'):
                # Skip standard logging attributes
                if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                             'filename', 'module', 'lineno', 'funcName', 'created',
                             'msecs', 'relativeCreated', 'thread', 'threadName',
                             'processName', 'process', 'getMessage', 'exc_info', 'exc_text',
                             'stack_info', 'taskName']:
                    try:
                        if isinstance(value, (dict, list, tuple)):
                            log_entry[key] = json.dumps(value) if len(str(value)) < 500 else str(value)[:500]
                        else:
                            log_entry[key] = value
                    except (TypeError, ValueError):
                        log_entry[key] = str(value)

        return json.dumps(log_entry, default=str, separators=(',', ':'))

    def _format_text(self, record: logging.LogRecord) -> str:
        """Format as readable text"""
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        return f"[{timestamp}] [{record.levelname:8}] [{record.name}] - {record.getMessage()}"

    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except:
            return 0.0


class LogHealthMonitor:
    """Monitors log system health and performance"""

    def __init__(self):
        self.log_counts = defaultdict(int)
        self.error_counts = defaultdict(int)
        self.start_time = time.time()
        self.last_health_check = time.time()
        self.health_issues = []
        self.lock = threading.Lock()

    def record_log(self, level: str, module: str):
        """Record a log event for monitoring"""
        with self.lock:
            self.log_counts[level] += 1
            if level in ['ERROR', 'CRITICAL']:
                self.error_counts[module] += 1

    def get_health_report(self) -> Dict[str, Any]:
        """Generate health report"""
        with self.lock:
            uptime_hours = (time.time() - self.start_time) / 3600
            total_logs = sum(self.log_counts.values())

            return {
                "uptime_hours": uptime_hours,
                "total_logs": total_logs,
                "logs_per_hour": total_logs / max(uptime_hours, 0.01),
                "log_levels": dict(self.log_counts),
                "error_modules": dict(self.error_counts),
                "health_issues": self.health_issues.copy(),
                "last_check": datetime.fromtimestamp(self.last_health_check).isoformat()
            }

    def check_health(self) -> List[str]:
        """Check log system health and return issues"""
        issues = []

        with self.lock:
            # Check log volume
            uptime_hours = (time.time() - self.start_time) / 3600
            total_logs = sum(self.log_counts.values())
            logs_per_hour = total_logs / max(uptime_hours, 0.01)

            if logs_per_hour > 10000:
                issues.append(f"High log volume: {logs_per_hour:.0f} logs/hour")

            # Check error rates
            error_count = self.log_counts.get('ERROR', 0) + self.log_counts.get('CRITICAL', 0)
            error_rate = error_count / max(total_logs, 1) * 100

            if error_rate > 10:
                issues.append(f"High error rate: {error_rate:.1f}%")

            # Check for error patterns
            for module, count in self.error_counts.items():
                if count > 100:
                    issues.append(f"Module {module} has {count} errors")

            self.health_issues = issues
            self.last_health_check = time.time()

        return issues


class ProfessionalLoggingSystem:
    """Complete professional logging system for crypto trading bot"""

    def __init__(self,
                 log_dir: str = "logs",
                 max_file_size_mb: int = 10,
                 backup_count: int = 5,
                 enable_compression: bool = True,
                 enable_async: bool = True,
                 enable_sampling: bool = True,
                 log_format: str = "json"):

        self.log_dir = Path(log_dir)
        self.max_file_size_mb = max_file_size_mb
        self.backup_count = backup_count
        self.enable_compression = enable_compression
        self.enable_async = enable_async
        self.enable_sampling = enable_sampling
        self.log_format = log_format

        # Create log directory
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Initialize components
        self.sampler = HighFrequencyLogSampler() if enable_sampling else None
        self.health_monitor = LogHealthMonitor()

        # Configure logging
        self._setup_logging()

        # Start health monitoring
        self._start_health_monitoring()

    def _setup_logging(self):
        """Setup complete logging configuration"""

        # Clear existing handlers
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        root_logger.setLevel(logging.DEBUG)

        # Create formatters
        json_formatter = TradingLogFormatter("json", include_performance=True)
        text_formatter = TradingLogFormatter("text", include_performance=False)

        # Main rotating file handler
        main_file = self.log_dir / "kraken_trading_bot.log"
        main_handler = CompressedRotatingFileHandler(
            str(main_file),
            maxBytes=self.max_file_size_mb * 1024 * 1024,
            backupCount=self.backup_count,
            encoding='utf-8',
            compress_old_logs=self.enable_compression
        )
        main_handler.setLevel(logging.INFO)
        main_handler.setFormatter(json_formatter if self.log_format == "json" else text_formatter)

        # Error-only file handler
        error_file = self.log_dir / "errors.log"
        error_handler = CompressedRotatingFileHandler(
            str(error_file),
            maxBytes=5 * 1024 * 1024,  # 5MB for errors
            backupCount=3,
            encoding='utf-8',
            compress_old_logs=self.enable_compression
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(json_formatter)

        # Console handler (critical only to reduce noise)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.WARNING)
        console_handler.setFormatter(text_formatter)

        # Trading activity handler (trades, signals, opportunities)
        trading_file = self.log_dir / "trading_activity.log"
        trading_handler = CompressedRotatingFileHandler(
            str(trading_file),
            maxBytes=20 * 1024 * 1024,  # 20MB for trading activity
            backupCount=10,
            encoding='utf-8',
            compress_old_logs=self.enable_compression
        )
        trading_handler.setLevel(logging.INFO)
        trading_handler.setFormatter(json_formatter)
        trading_handler.addFilter(self._trading_filter)

        # Performance metrics handler
        perf_file = self.log_dir / "performance.log"
        perf_handler = CompressedRotatingFileHandler(
            str(perf_file),
            maxBytes=10 * 1024 * 1024,  # 10MB for performance
            backupCount=5,
            encoding='utf-8',
            compress_old_logs=self.enable_compression
        )
        perf_handler.setLevel(logging.INFO)
        perf_handler.setFormatter(json_formatter)
        perf_handler.addFilter(self._performance_filter)

        # Wrap handlers with async if enabled
        handlers = [main_handler, error_handler, console_handler, trading_handler, perf_handler]

        if self.enable_async:
            async_handlers = []
            for handler in handlers:
                if not isinstance(handler, logging.StreamHandler):  # Keep console synchronous
                    async_handler = AsyncLogHandler(handler, queue_size=5000)
                    async_handler.setLevel(handler.level)
                    async_handlers.append(async_handler)
                else:
                    async_handlers.append(handler)
            handlers = async_handlers

        # Add handlers to root logger
        for handler in handlers:
            root_logger.addHandler(handler)

        # Configure specific loggers to reduce noise
        self._configure_external_loggers()

        # Log system initialization
        logging.info("Professional logging system initialized")
        logging.info(f"Log directory: {self.log_dir}")
        logging.info(f"Max file size: {self.max_file_size_mb}MB")
        logging.info(f"Backup count: {self.backup_count}")
        logging.info(f"Compression: {self.enable_compression}")
        logging.info(f"Async logging: {self.enable_async}")
        logging.info(f"Sampling: {self.enable_sampling}")
        logging.info(f"Format: {self.log_format}")

    def _trading_filter(self, record: logging.LogRecord) -> bool:
        """Filter for trading-related logs"""
        trading_keywords = ['trade', 'signal', 'buy', 'sell', 'order', 'position', 'profit', 'opportunity', 'balance']
        message = record.getMessage().lower()
        return any(keyword in message for keyword in trading_keywords)

    def _performance_filter(self, record: logging.LogRecord) -> bool:
        """Filter for performance-related logs"""
        perf_keywords = ['performance', 'latency', 'duration', 'memory', 'cpu', 'rate_limit', 'connection']
        message = record.getMessage().lower()
        return any(keyword in message for keyword in perf_keywords)

    def _configure_external_loggers(self):
        """Configure external library loggers to reduce noise"""
        noisy_loggers = [
            ('ccxt.base.exchange', logging.WARNING),
            ('urllib3.connectionpool', logging.WARNING),
            ('websockets.protocol', logging.ERROR),
            ('asyncio', logging.WARNING),
            ('kraken.ws', logging.INFO),
            ('requests.packages.urllib3', logging.WARNING),
        ]

        for logger_name, level in noisy_loggers:
            logger = logging.getLogger(logger_name)
            logger.setLevel(level)

    def _start_health_monitoring(self):
        """Start background health monitoring"""
        def health_check_worker():
            while True:
                try:
                    time.sleep(300)  # Check every 5 minutes
                    issues = self.health_monitor.check_health()
                    if issues:
                        logging.warning(f"Log system health issues: {', '.join(issues)}")
                except Exception as e:
                    logging.error(f"Health monitoring error: {e}")

        health_thread = threading.Thread(target=health_check_worker, daemon=True)
        health_thread.start()

    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger with enhanced functionality"""
        logger = logging.getLogger(name)

        # Add custom methods for trading operations
        def log_trade(symbol, side, amount, price, **kwargs):
            logger.info(f"TRADE: {side.upper()} {amount} {symbol} @ {price}",
                       extra={'event_type': 'trade', 'symbol': symbol, 'side': side,
                             'amount': amount, 'price': price, **kwargs})

        def log_signal(symbol, signal_type, confidence, **kwargs):
            logger.info(f"SIGNAL: {signal_type} {symbol} (confidence: {confidence:.1%})",
                       extra={'event_type': 'signal', 'symbol': symbol, 'signal_type': signal_type,
                             'confidence': confidence, **kwargs})

        def log_performance(metric_name, value, unit="", **kwargs):
            logger.info(f"PERF: {metric_name} = {value} {unit}",
                       extra={'event_type': 'performance', 'metric_name': metric_name,
                             'metric_value': value, 'metric_unit': unit, **kwargs})

        # Attach custom methods
        logger.log_trade = log_trade
        logger.log_signal = log_signal
        logger.log_performance = log_performance

        # Override default methods to include health monitoring
        original_log = logger._log
        def monitored_log(level, msg, args, **kwargs):
            self.health_monitor.record_log(logging.getLevelName(level), name)
            return original_log(level, msg, args, **kwargs)
        logger._log = monitored_log

        return logger

    def get_health_report(self) -> Dict[str, Any]:
        """Get comprehensive health report"""
        return self.health_monitor.get_health_report()

    def emergency_cleanup(self):
        """Emergency cleanup of log files"""
        try:
            # Archive current logs
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_dir = self.log_dir / "emergency_archive" / timestamp
            archive_dir.mkdir(parents=True, exist_ok=True)

            # Move all .log files to archive
            for log_file in self.log_dir.glob("*.log"):
                if log_file.is_file():
                    shutil.move(str(log_file), str(archive_dir / log_file.name))

            logging.warning(f"Emergency cleanup completed. Files archived to: {archive_dir}")
            return str(archive_dir)

        except Exception as e:
            logging.error(f"Emergency cleanup failed: {e}")
            return None

    def rotate_logs_now(self):
        """Force immediate log rotation"""
        for handler in logging.getLogger().handlers:
            if hasattr(handler, 'doRollover'):
                handler.doRollover()
        logging.info("Manual log rotation completed")

    def shutdown(self):
        """Gracefully shutdown logging system"""
        logging.info("Shutting down professional logging system")

        # Close all handlers
        for handler in logging.getLogger().handlers:
            if hasattr(handler, 'close'):
                handler.close()

        logging.shutdown()


# Global instance
_logging_system = None


def setup_professional_logging(**kwargs) -> ProfessionalLoggingSystem:
    """Setup professional logging system (singleton pattern)"""
    global _logging_system

    if _logging_system is None:
        _logging_system = ProfessionalLoggingSystem(**kwargs)

    return _logging_system


def get_professional_logger(name: str) -> logging.Logger:
    """Get a professional logger instance"""
    if _logging_system is None:
        setup_professional_logging()

    return _logging_system.get_logger(name)


def get_logging_health_report() -> Dict[str, Any]:
    """Get logging system health report"""
    if _logging_system is None:
        return {"error": "Logging system not initialized"}

    return _logging_system.get_health_report()


def emergency_log_cleanup() -> Optional[str]:
    """Emergency log cleanup"""
    if _logging_system is None:
        return None

    return _logging_system.emergency_cleanup()


# Export main components
__all__ = [
    'ProfessionalLoggingSystem',
    'setup_professional_logging',
    'get_professional_logger',
    'get_logging_health_report',
    'emergency_log_cleanup'
]
