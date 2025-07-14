"""
Alert Manager
Handles system alerts, notifications, and monitoring events for the trading bot
"""

import logging
import time
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class AlertType(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error" 
    CRITICAL = "critical"
    SUCCESS = "success"


class AlertCategory(Enum):
    """Alert categories"""
    TRADING = "trading"
    SYSTEM = "system"
    NETWORK = "network"
    BALANCE = "balance"
    STRATEGY = "strategy"
    RISK = "risk"
    PERFORMANCE = "performance"


@dataclass
class Alert:
    """Alert data structure"""
    type: AlertType
    category: AlertCategory
    message: str
    timestamp: float
    data: Dict[str, Any] = None
    resolved: bool = False
    resolution_time: Optional[float] = None
    
    def __post_init__(self):
        if self.data is None:
            self.data = {}
    
    def resolve(self):
        """Mark alert as resolved"""
        self.resolved = True
        self.resolution_time = time.time()
    
    def age_seconds(self) -> float:
        """Get alert age in seconds"""
        return time.time() - self.timestamp


class AlertManager:
    """Manages alerts and notifications for the trading bot"""
    
    def __init__(self, max_alerts: int = 1000):
        """Initialize alert manager"""
        self.alerts = []
        self.max_alerts = max_alerts
        self.alert_handlers = {}
        self.suppressed_alerts = set()
        self.alert_counters = {}
        
        # Rate limiting for alerts
        self.rate_limits = {
            AlertType.INFO: 10,     # Max 10 info alerts per minute
            AlertType.WARNING: 5,   # Max 5 warnings per minute
            AlertType.ERROR: 3,     # Max 3 errors per minute
            AlertType.CRITICAL: 1   # Max 1 critical per minute
        }
        self.rate_tracking = {}
        
        logger.debug("[ALERT_MGR] Alert manager initialized")
    
    def add_alert(self, alert_type: AlertType, category: AlertCategory, 
                  message: str, data: Dict[str, Any] = None) -> bool:
        """Add new alert to the system"""
        try:
            # Check rate limiting
            if not self._check_rate_limit(alert_type):
                logger.debug(f"[ALERT_MGR] Rate limited {alert_type.value} alert: {message}")
                return False
            
            # Check if alert is suppressed
            alert_key = f"{alert_type.value}:{category.value}:{message}"
            if alert_key in self.suppressed_alerts:
                return False
            
            # Create alert
            alert = Alert(
                type=alert_type,
                category=category,
                message=message,
                timestamp=time.time(),
                data=data or {}
            )
            
            # Add to alerts list
            self.alerts.append(alert)
            self._update_counters(alert_type, category)
            
            # Trigger handlers
            self._trigger_handlers(alert)
            
            # Log the alert
            log_level = self._get_log_level(alert_type)
            logger.log(log_level, f"[ALERT] {category.value.upper()}: {message}")
            
            # Cleanup old alerts
            self._cleanup_alerts()
            
            return True
            
        except Exception as e:
            logger.error(f"[ALERT_MGR] Error adding alert: {e}")
            return False
    
    def add_handler(self, alert_type: AlertType, handler: Callable):
        """Add alert handler for specific alert type"""
        if alert_type not in self.alert_handlers:
            self.alert_handlers[alert_type] = []
        self.alert_handlers[alert_type].append(handler)
        logger.debug(f"[ALERT_MGR] Added handler for {alert_type.value} alerts")
    
    def suppress_alert(self, alert_type: AlertType, category: AlertCategory, 
                      message: str, duration_seconds: int = 300):
        """Suppress specific alert for a duration"""
        alert_key = f"{alert_type.value}:{category.value}:{message}"
        self.suppressed_alerts.add(alert_key)
        
        # Schedule removal of suppression
        def remove_suppression():
            if alert_key in self.suppressed_alerts:
                self.suppressed_alerts.remove(alert_key)
        
        # Note: In a real implementation, you'd use a proper scheduler
        logger.debug(f"[ALERT_MGR] Suppressed alert for {duration_seconds}s: {message}")
    
    def get_alerts(self, alert_type: Optional[AlertType] = None, 
                   category: Optional[AlertCategory] = None,
                   unresolved_only: bool = False,
                   limit: int = 100) -> List[Alert]:
        """Get alerts with optional filtering"""
        filtered_alerts = []
        
        for alert in reversed(self.alerts):  # Most recent first
            # Apply filters
            if alert_type and alert.type != alert_type:
                continue
            if category and alert.category != category:
                continue
            if unresolved_only and alert.resolved:
                continue
            
            filtered_alerts.append(alert)
            
            if len(filtered_alerts) >= limit:
                break
        
        return filtered_alerts
    
    def get_recent_alerts(self, minutes: int = 60) -> List[Alert]:
        """Get alerts from the last N minutes"""
        cutoff_time = time.time() - (minutes * 60)
        return [alert for alert in self.alerts if alert.timestamp >= cutoff_time]
    
    def resolve_alerts(self, alert_type: Optional[AlertType] = None,
                      category: Optional[AlertCategory] = None):
        """Resolve alerts matching criteria"""
        resolved_count = 0
        
        for alert in self.alerts:
            if alert.resolved:
                continue
            
            if alert_type and alert.type != alert_type:
                continue
            if category and alert.category != category:
                continue
            
            alert.resolve()
            resolved_count += 1
        
        if resolved_count > 0:
            logger.info(f"[ALERT_MGR] Resolved {resolved_count} alerts")
        
        return resolved_count
    
    def get_alert_stats(self) -> Dict[str, Any]:
        """Get alert statistics"""
        total_alerts = len(self.alerts)
        unresolved_alerts = sum(1 for alert in self.alerts if not alert.resolved)
        
        # Count by type
        type_counts = {}
        for alert_type in AlertType:
            type_counts[alert_type.value] = sum(1 for alert in self.alerts if alert.type == alert_type)
        
        # Count by category
        category_counts = {}
        for category in AlertCategory:
            category_counts[category.value] = sum(1 for alert in self.alerts if alert.category == category)
        
        # Recent activity (last hour)
        recent_alerts = self.get_recent_alerts(60)
        
        return {
            'total_alerts': total_alerts,
            'unresolved_alerts': unresolved_alerts,
            'recent_alerts_1h': len(recent_alerts),
            'type_counts': type_counts,
            'category_counts': category_counts,
            'suppressed_count': len(self.suppressed_alerts),
            'handler_count': sum(len(handlers) for handlers in self.alert_handlers.values())
        }
    
    def _check_rate_limit(self, alert_type: AlertType) -> bool:
        """Check if alert type is within rate limits"""
        current_time = time.time()
        window_start = current_time - 60  # 1 minute window
        
        if alert_type not in self.rate_tracking:
            self.rate_tracking[alert_type] = []
        
        # Clean old entries
        self.rate_tracking[alert_type] = [
            timestamp for timestamp in self.rate_tracking[alert_type]
            if timestamp > window_start
        ]
        
        # Check limit
        current_count = len(self.rate_tracking[alert_type])
        limit = self.rate_limits.get(alert_type, 5)
        
        if current_count >= limit:
            return False
        
        # Add current timestamp
        self.rate_tracking[alert_type].append(current_time)
        return True
    
    def _update_counters(self, alert_type: AlertType, category: AlertCategory):
        """Update alert counters"""
        counter_key = f"{alert_type.value}:{category.value}"
        self.alert_counters[counter_key] = self.alert_counters.get(counter_key, 0) + 1
    
    def _trigger_handlers(self, alert: Alert):
        """Trigger alert handlers"""
        handlers = self.alert_handlers.get(alert.type, [])
        
        for handler in handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"[ALERT_MGR] Error in alert handler: {e}")
    
    def _get_log_level(self, alert_type: AlertType) -> int:
        """Get logging level for alert type"""
        mapping = {
            AlertType.INFO: logging.INFO,
            AlertType.SUCCESS: logging.INFO,
            AlertType.WARNING: logging.WARNING,
            AlertType.ERROR: logging.ERROR,
            AlertType.CRITICAL: logging.CRITICAL
        }
        return mapping.get(alert_type, logging.INFO)
    
    def _cleanup_alerts(self):
        """Clean up old alerts to maintain memory"""
        if len(self.alerts) > self.max_alerts:
            # Keep the most recent alerts
            self.alerts = self.alerts[-self.max_alerts:]
            logger.debug(f"[ALERT_MGR] Cleaned up old alerts, keeping {self.max_alerts}")
    
    # Convenience methods for common alert types
    def info(self, category: AlertCategory, message: str, data: Dict[str, Any] = None):
        """Add info alert"""
        return self.add_alert(AlertType.INFO, category, message, data)
    
    def warning(self, category: AlertCategory, message: str, data: Dict[str, Any] = None):
        """Add warning alert"""
        return self.add_alert(AlertType.WARNING, category, message, data)
    
    def error(self, category: AlertCategory, message: str, data: Dict[str, Any] = None):
        """Add error alert"""
        return self.add_alert(AlertType.ERROR, category, message, data)
    
    def critical(self, category: AlertCategory, message: str, data: Dict[str, Any] = None):
        """Add critical alert"""
        return self.add_alert(AlertType.CRITICAL, category, message, data)
    
    def success(self, category: AlertCategory, message: str, data: Dict[str, Any] = None):
        """Add success alert"""
        return self.add_alert(AlertType.SUCCESS, category, message, data)


# Global alert manager instance
_global_alert_manager = None


def get_alert_manager() -> AlertManager:
    """Get global alert manager instance"""
    global _global_alert_manager
    if _global_alert_manager is None:
        _global_alert_manager = AlertManager()
    return _global_alert_manager


def alert_info(category: AlertCategory, message: str, data: Dict[str, Any] = None):
    """Global function for info alerts"""
    return get_alert_manager().info(category, message, data)


def alert_warning(category: AlertCategory, message: str, data: Dict[str, Any] = None):
    """Global function for warning alerts"""
    return get_alert_manager().warning(category, message, data)


def alert_error(category: AlertCategory, message: str, data: Dict[str, Any] = None):
    """Global function for error alerts"""
    return get_alert_manager().error(category, message, data)


def alert_critical(category: AlertCategory, message: str, data: Dict[str, Any] = None):
    """Global function for critical alerts"""
    return get_alert_manager().critical(category, message, data)


def alert_success(category: AlertCategory, message: str, data: Dict[str, Any] = None):
    """Global function for success alerts"""
    return get_alert_manager().success(category, message, data)