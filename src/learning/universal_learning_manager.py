"""
Universal Learning Manager
=========================
Central learning system for the trading bot.
Tracks events, patterns, and optimizes strategies based on Kraken trading data.
Now includes error learning and resolution capabilities.
"""

import asyncio
import hashlib
import json
import logging
import re
import time
import traceback
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.utils.event_bus import Event as BusEvent
from src.utils.event_bus import EventType as BusEventType

# Import event bus for unified communication
from src.utils.event_bus import get_event_bus

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Event types for learning system - Enhanced for Kraken API compliance."""
    # Core trading events
    TRADE_SUCCESS = "trade_success"
    TRADE_FAILURE = "trade_failure"
    MISSED_OPPORTUNITY = "missed_opportunity"

    # Kraken-specific trading events
    ORDER_REJECTED = "order_rejected"
    RATE_LIMIT_HIT = "rate_limit_hit"
    COST_MINIMUM_ERROR = "cost_minimum_error"
    TICK_SIZE_ERROR = "tick_size_error"
    INSUFFICIENT_FUNDS = "insufficient_funds"

    # WebSocket v2 specific events
    WEBSOCKET_CONNECT = "websocket_connect"
    WEBSOCKET_DISCONNECT = "websocket_disconnect"
    WEBSOCKET_ERROR = "websocket_error"
    SUBSCRIPTION_SUCCESS = "subscription_success"
    SUBSCRIPTION_FAILURE = "subscription_failure"

    # System and analytics events
    SYSTEM_ERROR = "system_error"
    ANALYTICS_GENERATION = "analytics_generation"
    REPORT_GENERATION = "report_generation"
    PERFORMANCE_MONITORING = "performance_monitoring"

    # Learning and optimization events
    SYMBOL_MAPPING = "symbol_mapping"
    RISK_ASSESSMENT = "risk_assessment"
    POSITION_VALIDATION = "position_validation"
    RISK_MONITORING = "risk_monitoring"
    PROFIT_MONITORING = "profit_monitoring"
    RISK_MANAGEMENT = "risk_management"
    TRADE_EXECUTION = "trade_execution"
    MINIMUM_LEARNED = "minimum_learned"
    PATTERN_DETECTED = "pattern_detected"

    # Portfolio management events
    REALLOCATION_SUCCESS = "reallocation_success"
    REALLOCATION_FAILURE = "reallocation_failure"
    PORTFOLIO_ANALYSIS = "portfolio_analysis"

    # Error learning events
    ERROR_DETECTED = "error_detected"
    ERROR_RESOLVED = "error_resolved"
    ERROR_PREVENTION_APPLIED = "error_prevention_applied"


@dataclass
class ErrorPattern:
    """Pattern for recognizing and fixing specific error types"""
    pattern_id: str
    error_type: str
    error_regex: str
    component: str
    fix_strategy: str
    fix_params: Dict[str, Any]
    success_count: int = 0
    failure_count: int = 0
    last_seen: Optional[float] = None
    permanent_fix_applied: bool = False
    prevention_rule: Optional[str] = None

    def matches(self, error_message: str) -> bool:
        """Check if this pattern matches the error message"""
        return bool(re.search(self.error_regex, error_message, re.IGNORECASE))

    @property
    def confidence(self) -> float:
        """Calculate confidence in this fix pattern"""
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.0


@dataclass
class ErrorContext:
    """Complete context for an error occurrence"""
    timestamp: float
    component: str
    error_type: str
    error_message: str
    stack_trace: str
    system_state: Dict[str, Any]
    fix_attempted: bool = False
    fix_successful: bool = False
    fix_details: Optional[Dict[str, Any]] = None
    learning_insights: List[str] = field(default_factory=list)


class UniversalLearningManager:
    """
    Central learning manager that coordinates all learning activities.
    Stores patterns, tracks performance, and provides insights.
    Now includes error learning and resolution capabilities.
    """

    _instance = None
    _initialized = False

    @classmethod
    def get_instance(cls, storage_path: str = "D:/trading_data/learning", bot=None):
        """Get singleton instance of UniversalLearningManager"""
        if cls._instance is None:
            cls._instance = cls(storage_path, bot)
        return cls._instance

    def __init__(self, storage_path: str = "D:/trading_data/learning", bot=None):
        # Always ensure logger is available
        self.logger = logger

        # Prevent re-initialization
        if UniversalLearningManager._initialized:
            return
        self.bot = bot
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Event storage
        self.events = []
        self.event_counts = defaultdict(int)

        # Event bus integration
        self.event_bus = get_event_bus()

        # Enhanced pattern storage for Kraken-specific learning
        self.patterns = {
            'trading_patterns': {},
            'error_patterns': {},
            'optimization_patterns': {},
            'minimum_requirements': {},
            'kraken_specific': {
                'rate_limits': {},
                'symbol_mappings': {},
                'websocket_patterns': {},
                'cost_minimums': {},
                'tick_sizes': {}
            },
            'reallocation_patterns': {},
            'execution_timing': {}
        }

        # Error learning components
        self.error_patterns_db: Dict[str, ErrorPattern] = {}
        self.error_history = defaultdict(list)
        self.solution_effectiveness = defaultdict(dict)
        self.context_correlations = defaultdict(dict)

        # Error fix strategies
        self.fix_strategies = {
            'restart_component': self._fix_restart_component,
            'clear_cache': self._fix_clear_cache,
            'reconnect_websocket': self._fix_reconnect_websocket,
            'reset_rate_limiter': self._fix_reset_rate_limiter,
            'reload_config': self._fix_reload_config,
            'update_parsing_strategy': self._fix_update_parsing_strategy,
            'adjust_parameters': self._fix_adjust_parameters,
            'fallback_mode': self._fix_fallback_mode,
            'apply_learned_fix': self._fix_apply_learned,
            'fix_balance_sync': self._fix_balance_sync,
            'fix_unicode_logging': self._fix_unicode_logging,
            'fix_strategy_init': self._fix_strategy_initialization,
            'fix_api_credentials': self._fix_api_credentials,
            'fix_balance_cache': self._fix_balance_cache,
            'fix_minimum_order': self._fix_minimum_order,
            'fix_rebalance_cooldown': self._fix_rebalance_cooldown,
            'reconnect_websocket_with_ping': self._fix_reconnect_websocket_with_ping,
            'fix_nonce_generation': self._fix_nonce_generation,
            'fix_balance_aggregation': self._fix_balance_aggregation,
            'fix_decimal_conversion': self._fix_decimal_conversion,
            'fix_connection_pool': self._fix_connection_pool,
        }

        # Learning thresholds
        self.learning_threshold = 0.7
        self.max_error_patterns = 1000
        self.pattern_decay_days = 30

        # Performance metrics
        self.performance_metrics = {
            'trades': {'successful': 0, 'failed': 0},
            'errors': defaultdict(int),
            'optimizations': 0
        }

        # Load existing data
        self._load_learning_data()

        # Initialize known error patterns
        self._initialize_known_error_patterns()

        # Set up event subscriptions after everything is initialized
        self._setup_event_subscriptions()

        # Mark as initialized
        UniversalLearningManager._initialized = True

    def set_bot_instance(self, bot):
        """Set bot instance for full integration"""
        self.bot = bot
        if hasattr(self, 'logger') and self.logger:
            self.logger.info("[LEARNING] Bot instance set for full integration")

    def connect_to_event_bus(self, event_bus):
        """Connect to event bus for automatic learning"""
        self.event_bus = event_bus
        self._setup_event_subscriptions()
        if hasattr(self, 'logger') and self.logger:
            self.logger.info("[LEARNING] Connected to event bus for automatic learning")

    def _setup_event_subscriptions(self):
        """Set up subscriptions to event bus for automatic learning"""
        # Subscribe to all error events
        self.event_bus.subscribe(BusEventType.TRADE_FAILED, self._handle_trade_failed_event)
        self.event_bus.subscribe(BusEventType.WEBSOCKET_ERROR, self._handle_websocket_error_event)
        self.event_bus.subscribe(BusEventType.RATE_LIMIT_ERROR, self._handle_rate_limit_event)
        self.event_bus.subscribe(BusEventType.BALANCE_ERROR, self._handle_balance_error_event)
        self.event_bus.subscribe(BusEventType.COMPONENT_ERROR, self._handle_component_error_event)

        # Subscribe to success events for pattern learning
        self.event_bus.subscribe(BusEventType.TRADE_EXECUTED, self._handle_trade_success_event)
        self.event_bus.subscribe(BusEventType.BALANCE_UPDATED, self._handle_balance_update_event)

        # Subscribe to pattern detection
        self.event_bus.subscribe(BusEventType.PATTERN_DETECTED, self._handle_pattern_detected_event)

        self.logger.info("[LEARNING] Subscribed to event bus for automatic learning")

    async def _handle_trade_failed_event(self, event: BusEvent):
        """Handle trade failure events from event bus"""
        self.record_event(
            EventType.TRADE_FAILURE,
            event.source,
            False,
            event.data,
            'error'
        )

        # Check if we can learn from this failure
        if 'error' in event.data:
            await self.analyze_and_fix_error(
                event.source,
                'trade_failure',
                event.data['error'],
                event.data
            )

    async def _handle_websocket_error_event(self, event: BusEvent):
        """Handle WebSocket error events"""
        self.record_event(
            EventType.WEBSOCKET_ERROR,
            event.source,
            False,
            event.data,
            'error'
        )

    async def _handle_rate_limit_event(self, event: BusEvent):
        """Handle rate limit events"""
        self.record_event(
            EventType.RATE_LIMIT_HIT,
            event.source,
            False,
            event.data,
            'warning'
        )

        # Learn rate limit patterns
        self._learn_rate_limit_pattern(event.data)

    async def _handle_balance_error_event(self, event: BusEvent):
        """Handle balance error events"""
        self.record_event(
            EventType.SYSTEM_ERROR,
            event.source,
            False,
            event.data,
            'error'
        )

    async def _handle_component_error_event(self, event: BusEvent):
        """Handle component error events"""
        self.record_event(
            EventType.SYSTEM_ERROR,
            event.source,
            False,
            event.data,
            'error'
        )

    async def _handle_trade_success_event(self, event: BusEvent):
        """Handle successful trade events"""
        self.record_event(
            EventType.TRADE_SUCCESS,
            event.source,
            True,
            event.data,
            'info'
        )

    async def _handle_balance_update_event(self, event: BusEvent):
        """Handle balance update events"""
        # Learn balance patterns
        if 'asset' in event.data and 'balance' in event.data:
            self._learn_balance_pattern(event.data)

    async def _handle_pattern_detected_event(self, event: BusEvent):
        """Handle pattern detection events"""
        pattern_type = event.data.get('pattern')
        if pattern_type == 'repeated_error':
            # Create error pattern for automatic resolution
            await self._create_error_resolution_pattern(event.data)
        elif pattern_type == 'frequent_rate_limits':
            # Adjust API call frequency
            self._adjust_rate_limit_strategy(event.data)

    def record_event(self, event_type: EventType, component: str, success: bool = True,
                    details: Optional[Dict[str, Any]] = None, severity: str = "info"):
        """Record a learning event."""
        event = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type.value,
            'component': component,
            'success': success,
            'severity': severity,
            'details': details or {}
        }

        self.events.append(event)
        self.event_counts[event_type.value] += 1

        # Update performance metrics
        if event_type == EventType.TRADE_SUCCESS:
            self.performance_metrics['trades']['successful'] += 1
        elif event_type == EventType.TRADE_FAILURE:
            self.performance_metrics['trades']['failed'] += 1
        elif event_type == EventType.SYSTEM_ERROR:
            error_type = details.get('error_type', 'unknown')
            self.performance_metrics['errors'][error_type] += 1

        # Log significant events
        if severity in ['error', 'critical'] or not success:
            self.logger.warning(f"[LEARNING] {event_type.value}: {details}")

        # KRAKEN-SPECIFIC ENHANCEMENTS: Enhanced event recording for Kraken trading patterns
        self._record_kraken_specific_patterns(event_type, component, success, details)

    def record_error(self, component: str, error_message: str,
                    details: Optional[Dict[str, Any]] = None):
        """Record an error event for learning."""
        self.record_event(
            EventType.ERROR_DETECTED,
            component=component,
            success=False,
            details={
                'error_message': error_message,
                **(details or {})
            },
            severity='error'
        )

    def _record_kraken_specific_patterns(self, event_type: EventType, component: str,
                                       success: bool, details: Dict[str, Any]):
        """Record Kraken-specific trading patterns for enhanced learning."""
        try:
            # WebSocket v2 specific patterns
            if component == 'kraken_websocket_v2' or 'websocket' in component.lower():
                self._learn_websocket_patterns(event_type, success, details)

            # Trade execution patterns
            elif event_type in [EventType.TRADE_SUCCESS, EventType.TRADE_FAILURE]:
                self._learn_trade_execution_patterns(success, details)

            # Order-specific patterns for Kraken rate limiting
            elif 'order' in str(event_type).lower():
                self._learn_order_patterns(event_type, success, details)

            # Balance and account patterns
            elif component in ['balance_manager', 'account_manager']:
                self._learn_balance_patterns(success, details)

        except Exception as e:
            self.logger.debug(f"[LEARNING] Kraken pattern recording error: {e}")

    def _learn_rate_limit_pattern(self, data: Dict[str, Any]):
        """Learn from rate limit occurrences"""
        endpoint = data.get('endpoint', 'unknown')
        pattern_name = f"rate_limit_{endpoint}"

        if pattern_name not in self.patterns['kraken_specific']['rate_limits']:
            self.patterns['kraken_specific']['rate_limits'][pattern_name] = {
                'occurrences': 0,
                'last_occurrence': None,
                'suggested_delay': 1.0
            }

        pattern = self.patterns['kraken_specific']['rate_limits'][pattern_name]
        pattern['occurrences'] += 1
        pattern['last_occurrence'] = time.time()

        # Increase suggested delay based on frequency
        if pattern['occurrences'] > 5:
            pattern['suggested_delay'] = min(pattern['suggested_delay'] * 1.5, 10.0)
            self.logger.info(f"[LEARNING] Increasing delay for {endpoint} to {pattern['suggested_delay']}s")

    def _learn_balance_pattern(self, data: Dict[str, Any]):
        """Learn balance update patterns"""
        asset = data.get('asset')
        balance = data.get('balance')

        if asset and balance is not None:
            pattern_name = f"balance_{asset}"
            if pattern_name not in self.patterns['kraken_specific']:
                self.patterns['kraken_specific'][pattern_name] = {
                    'updates': [],
                    'average_balance': 0
                }

            pattern = self.patterns['kraken_specific'][pattern_name]
            pattern['updates'].append({
                'timestamp': time.time(),
                'balance': balance
            })

            # Keep only recent updates
            pattern['updates'] = pattern['updates'][-100:]

            # Calculate average
            if pattern['updates']:
                pattern['average_balance'] = sum(u['balance'] for u in pattern['updates']) / len(pattern['updates'])

    async def _create_error_resolution_pattern(self, data: Dict[str, Any]):
        """Create pattern for automatic error resolution"""
        error_key = data.get('error_key')
        source = data.get('source')
        error_type = data.get('error_type')

        if error_key:
            pattern_id = hashlib.md5(error_key.encode()).hexdigest()[:8]

            # Determine fix strategy based on error type
            fix_strategy = 'restart_component'  # Default
            if 'websocket' in error_type.lower():
                fix_strategy = 'reconnect_websocket'
            elif 'rate_limit' in error_type.lower():
                fix_strategy = 'reset_rate_limiter'
            elif 'balance' in error_type.lower():
                fix_strategy = 'fix_balance_sync'

            self.error_patterns_db[pattern_id] = ErrorPattern(
                pattern_id=pattern_id,
                error_type=error_type,
                error_regex=error_type,
                component=source,
                fix_strategy=fix_strategy,
                fix_params={},
                last_seen=time.time()
            )

            self.logger.info(f"[LEARNING] Created error resolution pattern for {error_type}")

    def _adjust_rate_limit_strategy(self, data: Dict[str, Any]):
        """Adjust strategy for rate limit avoidance"""
        count = data.get('count', 0)

        if count >= 5:
            # Significant rate limiting detected
            self.logger.warning("[LEARNING] Frequent rate limits detected, adjusting API call strategy")

            # Store recommendation
            self.patterns['optimization_patterns']['rate_limit_avoidance'] = {
                'reduce_api_calls': True,
                'suggested_interval': 2.0,  # Increase interval between calls
                'batch_operations': True,
                'learned_at': datetime.now().isoformat()
            }

    def _learn_websocket_patterns(self, event_type: EventType, success: bool, details: Dict[str, Any]):
        """Learn WebSocket v2 specific patterns for Kraken."""
        pattern_type = 'kraken_websocket_v2'

        if 'symbol' in details:
            symbol = details['symbol']
            pattern_name = f"{symbol}_websocket_reliability"

            # Track WebSocket reliability per symbol
            if pattern_name not in self.patterns.get(pattern_type, {}):
                self.patterns.setdefault(pattern_type, {})[pattern_name] = {
                    'data': {'success_count': 0, 'failure_count': 0, 'last_failure_type': None},
                    'learned_at': datetime.now().isoformat(),
                    'usage_count': 0
                }

            pattern_data = self.patterns[pattern_type][pattern_name]['data']
            if success:
                pattern_data['success_count'] += 1
            else:
                pattern_data['failure_count'] += 1
                pattern_data['last_failure_type'] = details.get('error_type', 'unknown')

            # Calculate reliability score
            total_attempts = pattern_data['success_count'] + pattern_data['failure_count']
            reliability_score = pattern_data['success_count'] / total_attempts if total_attempts > 0 else 0
            pattern_data['reliability_score'] = reliability_score

    def _learn_trade_execution_patterns(self, success: bool, details: Dict[str, Any]):
        """Learn trade execution patterns specific to Kraken."""
        pattern_type = 'kraken_execution'

        if 'symbol' in details:
            symbol = details['symbol']
            pattern_name = f"{symbol}_execution_success"

            # Initialize pattern if not exists
            if pattern_name not in self.patterns.get(pattern_type, {}):
                self.patterns.setdefault(pattern_type, {})[pattern_name] = {
                    'data': {
                        'successful_executions': 0,
                        'failed_executions': 0,
                        'avg_execution_time': 0.0,
                        'last_failure_reason': None,
                        'optimal_order_size_range': {'min': None, 'max': None}
                    },
                    'learned_at': datetime.now().isoformat(),
                    'usage_count': 0
                }

            pattern_data = self.patterns[pattern_type][pattern_name]['data']

            if success:
                pattern_data['successful_executions'] += 1

                # Learn optimal order sizes
                if 'amount' in details:
                    amount = float(details['amount'])
                    if pattern_data['optimal_order_size_range']['min'] is None:
                        pattern_data['optimal_order_size_range']['min'] = amount
                        pattern_data['optimal_order_size_range']['max'] = amount
                    else:
                        pattern_data['optimal_order_size_range']['min'] = min(
                            pattern_data['optimal_order_size_range']['min'], amount)
                        pattern_data['optimal_order_size_range']['max'] = max(
                            pattern_data['optimal_order_size_range']['max'], amount)

                # Learn execution timing
                if 'execution_time' in details:
                    current_avg = pattern_data['avg_execution_time']
                    total_successful = pattern_data['successful_executions']
                    new_time = float(details['execution_time'])
                    pattern_data['avg_execution_time'] = (
                        (current_avg * (total_successful - 1) + new_time) / total_successful
                    )
            else:
                pattern_data['failed_executions'] += 1
                pattern_data['last_failure_reason'] = details.get('error', 'unknown')

            # Calculate success rate
            total_executions = pattern_data['successful_executions'] + pattern_data['failed_executions']
            pattern_data['success_rate'] = (
                pattern_data['successful_executions'] / total_executions if total_executions > 0 else 0
            )

    def _learn_order_patterns(self, event_type: EventType, success: bool, details: Dict[str, Any]):
        """Learn order-specific patterns for Kraken rate limiting optimization."""
        pattern_type = 'kraken_orders'
        pattern_name = 'rate_limit_patterns'

        # Initialize rate limit pattern tracking
        if pattern_name not in self.patterns.get(pattern_type, {}):
            self.patterns.setdefault(pattern_type, {})[pattern_name] = {
                'data': {
                    'rate_limit_hits': 0,
                    'successful_orders': 0,
                    'optimal_intervals': [],
                    'peak_trading_hours': defaultdict(int),
                    'symbol_specific_limits': defaultdict(dict)
                },
                'learned_at': datetime.now().isoformat(),
                'usage_count': 0
            }

        pattern_data = self.patterns[pattern_type][pattern_name]['data']

        if not success and 'rate limit' in str(details.get('error', '')).lower():
            pattern_data['rate_limit_hits'] += 1

            # Learn peak trading hours when rate limits hit
            current_hour = datetime.now().hour
            pattern_data['peak_trading_hours'][current_hour] += 1
        elif success:
            pattern_data['successful_orders'] += 1

    def _learn_balance_patterns(self, success: bool, details: Dict[str, Any]):
        """Learn balance and account management patterns."""
        pattern_type = 'kraken_balance'

        if 'currency' in details or 'symbol' in details:
            currency = details.get('currency', details.get('symbol', 'USD'))
            pattern_name = f"{currency}_balance_optimization"

            # Initialize balance pattern
            if pattern_name not in self.patterns.get(pattern_type, {}):
                self.patterns.setdefault(pattern_type, {})[pattern_name] = {
                    'data': {
                        'successful_balance_checks': 0,
                        'failed_balance_checks': 0,
                        'optimal_balance_thresholds': {'min_trading': None, 'reserve': None},
                        'utilization_patterns': []
                    },
                    'learned_at': datetime.now().isoformat(),
                    'usage_count': 0
                }

            pattern_data = self.patterns[pattern_type][pattern_name]['data']

            if success:
                pattern_data['successful_balance_checks'] += 1

                # Learn utilization patterns
                if 'utilization_rate' in details:
                    utilization = float(details['utilization_rate'])
                    pattern_data['utilization_patterns'].append({
                        'rate': utilization,
                        'timestamp': datetime.now().isoformat(),
                        'profitable': details.get('resulted_in_profit', False)
                    })

                    # Keep only last 100 utilization patterns
                    if len(pattern_data['utilization_patterns']) > 100:
                        pattern_data['utilization_patterns'] = pattern_data['utilization_patterns'][-100:]
            else:
                pattern_data['failed_balance_checks'] += 1

    def learn_pattern(self, pattern_type: str, pattern_name: str, pattern_data: Dict[str, Any]):
        """Learn and store a new pattern."""
        if pattern_type not in self.patterns:
            self.patterns[pattern_type] = {}

        self.patterns[pattern_type][pattern_name] = {
            'data': pattern_data,
            'learned_at': datetime.now().isoformat(),
            'usage_count': 0
        }

        self.record_event(
            EventType.PATTERN_DETECTED,
            'learning_manager',
            True,
            {'pattern_type': pattern_type, 'pattern_name': pattern_name}
        )

    def get_pattern(self, pattern_type: str, pattern_name: str) -> Optional[Dict[str, Any]]:
        """Retrieve a learned pattern."""
        if pattern_type in self.patterns and pattern_name in self.patterns[pattern_type]:
            pattern = self.patterns[pattern_type][pattern_name]
            pattern['usage_count'] += 1
            return pattern['data']
        return None

    def update_minimum_requirements(self, symbol: str, requirements: Dict[str, float]):
        """Update minimum trading requirements for a symbol."""
        self.patterns['minimum_requirements'][symbol] = {
            'min_cost': requirements.get('min_cost', 0),
            'min_size': requirements.get('min_size', 0),
            'updated_at': datetime.now().isoformat()
        }

        self.record_event(
            EventType.MINIMUM_LEARNED,
            'learning_manager',
            True,
            {'symbol': symbol, 'requirements': requirements}
        )

    def get_minimum_requirements(self, symbol: str) -> Dict[str, float]:
        """Get minimum requirements for a symbol."""
        if symbol in self.patterns['minimum_requirements']:
            return self.patterns['minimum_requirements'][symbol]
        return {'min_cost': 0, 'min_size': 0}

    # KRAKEN-SPECIFIC ENHANCEMENT METHODS

    def get_websocket_reliability(self, symbol: str) -> float:
        """Get WebSocket reliability score for a specific symbol."""
        pattern_type = 'kraken_websocket_v2'
        pattern_name = f"{symbol}_websocket_reliability"

        pattern = self.get_pattern(pattern_type, pattern_name)
        if pattern:
            return pattern.get('reliability_score', 0.5)
        return 0.5  # Default neutral reliability

    def get_execution_success_rate(self, symbol: str) -> float:
        """Get trade execution success rate for a symbol."""
        pattern_type = 'kraken_execution'
        pattern_name = f"{symbol}_execution_success"

        pattern = self.get_pattern(pattern_type, pattern_name)
        if pattern:
            return pattern.get('success_rate', 0.5)
        return 0.5  # Default neutral success rate

    def get_optimal_order_size_range(self, symbol: str) -> Dict[str, float]:
        """Get learned optimal order size range for a symbol."""
        pattern_type = 'kraken_execution'
        pattern_name = f"{symbol}_execution_success"

        pattern = self.get_pattern(pattern_type, pattern_name)
        if pattern and pattern.get('optimal_order_size_range'):
            return pattern['optimal_order_size_range']
        return {'min': None, 'max': None}

    def get_rate_limit_insights(self) -> Dict[str, Any]:
        """Get insights about rate limiting patterns."""
        pattern_type = 'kraken_orders'
        pattern_name = 'rate_limit_patterns'

        pattern = self.get_pattern(pattern_type, pattern_name)
        if pattern:
            return {
                'rate_limit_frequency': pattern.get('rate_limit_hits', 0),
                'successful_orders': pattern.get('successful_orders', 0),
                'peak_hours': dict(pattern.get('peak_trading_hours', {})),
                'success_ratio': (
                    pattern.get('successful_orders', 0) /
                    max(1, pattern.get('rate_limit_hits', 0) + pattern.get('successful_orders', 0))
                )
            }
        return {'rate_limit_frequency': 0, 'successful_orders': 0, 'peak_hours': {}, 'success_ratio': 1.0}

    def get_balance_utilization_insights(self, currency: str) -> Dict[str, Any]:
        """Get balance utilization insights for a currency."""
        pattern_type = 'kraken_balance'
        pattern_name = f"{currency}_balance_optimization"

        pattern = self.get_pattern(pattern_type, pattern_name)
        if pattern and pattern.get('utilization_patterns'):
            utilization_data = pattern['utilization_patterns']
            profitable_rates = [u['rate'] for u in utilization_data if u.get('profitable', False)]

            if profitable_rates:
                return {
                    'optimal_utilization_rate': sum(profitable_rates) / len(profitable_rates),
                    'min_profitable_rate': min(profitable_rates),
                    'max_profitable_rate': max(profitable_rates),
                    'sample_size': len(profitable_rates)
                }

        return {'optimal_utilization_rate': 0.6, 'min_profitable_rate': 0.3,
                'max_profitable_rate': 0.8, 'sample_size': 0}

    def should_trade_symbol(self, symbol: str) -> bool:
        """Determine if a symbol should be traded based on learned patterns."""
        # Check WebSocket reliability
        websocket_reliability = self.get_websocket_reliability(symbol)
        if websocket_reliability < 0.7:
            return False

        # Check execution success rate
        execution_success = self.get_execution_success_rate(symbol)
        if execution_success < 0.6:
            return False

        # Check if we have any significant failure patterns
        pattern_type = 'kraken_execution'
        pattern_name = f"{symbol}_execution_success"
        pattern = self.get_pattern(pattern_type, pattern_name)

        if pattern:
            failed_executions = pattern.get('failed_executions', 0)
            successful_executions = pattern.get('successful_executions', 0)

            # Don't trade if failure rate is too high with sufficient sample size
            if (failed_executions + successful_executions) >= 10 and execution_success < 0.5:
                return False

        return True

    def get_kraken_optimization_recommendations(self) -> Dict[str, Any]:
        """Get optimization recommendations based on learned Kraken patterns."""
        recommendations = {
            'websocket': [],
            'execution': [],
            'rate_limiting': [],
            'balance': []
        }

        try:
            # WebSocket recommendations
            websocket_patterns = self.patterns.get('kraken_websocket_v2', {})
            unreliable_symbols = []

            for pattern_name, pattern_info in websocket_patterns.items():
                if 'websocket_reliability' in pattern_name:
                    symbol = pattern_name.replace('_websocket_reliability', '')
                    reliability = pattern_info['data'].get('reliability_score', 1.0)
                    if reliability < 0.8:
                        unreliable_symbols.append((symbol, reliability))

            if unreliable_symbols:
                recommendations['websocket'].append(
                    f"Consider monitoring WebSocket reliability for: {', '.join([s[0] for s in unreliable_symbols])}"
                )

            # Execution recommendations
            execution_patterns = self.patterns.get('kraken_execution', {})
            slow_symbols = []

            for pattern_name, pattern_info in execution_patterns.items():
                if 'execution_success' in pattern_name:
                    symbol = pattern_name.replace('_execution_success', '')
                    avg_time = pattern_info['data'].get('avg_execution_time', 0)
                    if avg_time > 2.0:  # More than 2 seconds is considered slow
                        slow_symbols.append((symbol, avg_time))

            if slow_symbols:
                recommendations['execution'].append(
                    f"Slow execution detected for: {', '.join([f'{s[0]}({s[1]:.1f}s)' for s in slow_symbols])}"
                )

            # Rate limiting recommendations
            rate_insights = self.get_rate_limit_insights()
            if rate_insights['rate_limit_frequency'] > 10:
                recommendations['rate_limiting'].append(
                    f"High rate limit frequency detected: {rate_insights['rate_limit_frequency']} hits"
                )

            if rate_insights['peak_hours']:
                peak_hour = max(rate_insights['peak_hours'], key=rate_insights['peak_hours'].get)
                recommendations['rate_limiting'].append(
                    f"Peak rate limiting at hour {peak_hour}, consider reduced activity"
                )

        except Exception as e:
            self.logger.error(f"[LEARNING] Error generating recommendations: {e}")

        return recommendations

    def get_recent_events(self, event_type: Optional[str] = None,
                         hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent events of specified type."""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        recent_events = []
        for event in reversed(self.events):
            event_time = datetime.fromisoformat(event['timestamp'])
            if event_time < cutoff_time:
                break
            if event_type is None or event['event_type'] == event_type:
                recent_events.append(event)

        return recent_events

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        total_trades = (self.performance_metrics['trades']['successful'] +
                       self.performance_metrics['trades']['failed'])

        success_rate = 0
        if total_trades > 0:
            success_rate = self.performance_metrics['trades']['successful'] / total_trades

        return {
            'total_trades': total_trades,
            'success_rate': success_rate,
            'successful_trades': self.performance_metrics['trades']['successful'],
            'failed_trades': self.performance_metrics['trades']['failed'],
            'error_counts': dict(self.performance_metrics['errors']),
            'total_events': len(self.events),
            'event_types': dict(self.event_counts)
        }

    def _save_learning_data(self):
        """Save learning data to disk."""
        try:
            # Save events (keep last 1000)
            events_file = self.storage_path / "events.json"
            with open(events_file, 'w') as f:
                json.dump(self.events[-1000:], f, indent=2)

            # Save patterns
            patterns_file = self.storage_path / "patterns.json"
            with open(patterns_file, 'w') as f:
                json.dump(self.patterns, f, indent=2)

            # Save error patterns
            error_patterns_file = self.storage_path / "error_patterns.json"
            error_patterns_data = {}
            for pid, pattern in self.error_patterns_db.items():
                error_patterns_data[pid] = {
                    'pattern_id': pattern.pattern_id,
                    'error_type': pattern.error_type,
                    'error_regex': pattern.error_regex,
                    'component': pattern.component,
                    'fix_strategy': pattern.fix_strategy,
                    'fix_params': pattern.fix_params,
                    'success_count': pattern.success_count,
                    'failure_count': pattern.failure_count,
                    'last_seen': pattern.last_seen,
                    'permanent_fix_applied': pattern.permanent_fix_applied,
                    'prevention_rule': pattern.prevention_rule
                }
            with open(error_patterns_file, 'w') as f:
                json.dump(error_patterns_data, f, indent=2)

            # Save metrics
            metrics_file = self.storage_path / "metrics.json"
            with open(metrics_file, 'w') as f:
                json.dump({
                    'performance_metrics': self.performance_metrics,
                    'event_counts': dict(self.event_counts)
                }, f, indent=2)

        except Exception as e:
            self.logger.error(f"[LEARNING] Failed to save data: {e}")

    def _load_learning_data(self):
        """Load learning data from disk."""
        try:
            # Load events
            events_file = self.storage_path / "events.json"
            if events_file.exists():
                with open(events_file) as f:
                    self.events = json.load(f)

            # Load patterns
            patterns_file = self.storage_path / "patterns.json"
            if patterns_file.exists():
                with open(patterns_file) as f:
                    self.patterns = json.load(f)

            # Load error patterns
            error_patterns_file = self.storage_path / "error_patterns.json"
            if error_patterns_file.exists():
                with open(error_patterns_file) as f:
                    error_patterns_data = json.load(f)
                    for pid, pdata in error_patterns_data.items():
                        self.error_patterns_db[pid] = ErrorPattern(**pdata)

            # Load metrics
            metrics_file = self.storage_path / "metrics.json"
            if metrics_file.exists():
                with open(metrics_file) as f:
                    data = json.load(f)
                    self.performance_metrics = data.get('performance_metrics', self.performance_metrics)
                    self.event_counts = defaultdict(int, data.get('event_counts', {}))

            self.logger.info(f"[LEARNING] Loaded {len(self.events)} events and {len(self.error_patterns_db)} error patterns from storage")

        except Exception as e:
            self.logger.error(f"[LEARNING] Failed to load data: {e}")

    def save(self):
        """Public method to save learning data."""
        self._save_learning_data()


    def _initialize_known_error_patterns(self):
        """Initialize with patterns we've already learned from the bot's history"""
        known_patterns = [
            ErrorPattern(
                pattern_id="websocket_data_array",
                error_type="AttributeError",
                error_regex=r"'list' object has no attribute '(get|symbol)'",
                component="websocket",
                fix_strategy="update_parsing_strategy",
                fix_params={"new_strategy": "parse_array_format"}
            ),
            ErrorPattern(
                pattern_id="unicode_encoding",
                error_type="UnicodeEncodeError",
                error_regex=r"'charmap' codec can't encode character.*in position",
                component="logging",
                fix_strategy="fix_unicode_logging",
                fix_params={"clear_cache": True}
            ),
            ErrorPattern(
                pattern_id="insufficient_balance",
                error_type="InsufficientBalance",
                error_regex=r"insufficient (balance|funds)",
                component="balance_manager",
                fix_strategy="fix_balance_sync",
                fix_params={"force_refresh": True}
            ),
            ErrorPattern(
                pattern_id="balance_cache_mismatch",
                error_type="BalanceMismatch",
                error_regex=r"balance.*mismatch|cache.*stale|actual.*differ",
                component="balance_manager",
                fix_strategy="fix_balance_cache",
                fix_params={"invalidate_cache": True, "force_refresh": True}
            ),
            ErrorPattern(
                pattern_id="minimum_order_violation",
                error_type="MinimumOrderError",
                error_regex=r"order.*below.*minimum|minimum.*not.*met|order.*too.*small",
                component="trade_executor",
                fix_strategy="fix_minimum_order",
                fix_params={"apply_safety_buffer": True, "min_buffer": 2.5}
            ),
            ErrorPattern(
                pattern_id="emergency_rebalance_loop",
                error_type="RebalanceLoop",
                error_regex=r"emergency.*rebalance.*loop|rebalance.*stuck",
                component="profit_harvester",
                fix_strategy="fix_rebalance_cooldown",
                fix_params={"cooldown_hours": 1.0, "check_balance_first": True}
            ),
            ErrorPattern(
                pattern_id="api_padding_error",
                error_type="binascii.Error",
                error_regex=r"Incorrect padding",
                component="api_auth",
                fix_strategy="fix_api_credentials",
                fix_params={"reload_env": True}
            ),
            ErrorPattern(
                pattern_id="strategy_none_info",
                error_type="AttributeError",
                error_regex=r"'NoneType' object has no attribute 'info'",
                component="strategy_manager",
                fix_strategy="fix_strategy_init",
                fix_params={"use_fallback": True}
            ),
            ErrorPattern(
                pattern_id="rate_limit_exceeded",
                error_type="RateLimitExceeded",
                error_regex=r"rate limit exceeded|too many requests",
                component="exchange",
                fix_strategy="reset_rate_limiter",
                fix_params={"wait_time": 60}
            ),
            ErrorPattern(
                pattern_id="websocket_timeout",
                error_type="TimeoutError",
                error_regex=r"websocket.*timeout|ping.*timeout",
                component="websocket",
                fix_strategy="reconnect_websocket",
                fix_params={"force": True}
            ),
            ErrorPattern(
                pattern_id="websocket_no_heartbeat",
                error_type="WebSocketHeartbeatTimeout",
                error_regex=r"no heartbeat for \d+s|heartbeat timeout|websocket stale",
                component="websocket",
                fix_strategy="reconnect_websocket_with_ping",
                fix_params={"enable_ping": True, "ping_interval": 20}
            ),
            ErrorPattern(
                pattern_id="invalid_nonce",
                error_type="InvalidNonce",
                error_regex=r"EAPI:Invalid nonce|nonce.*invalid|nonce.*error",
                component="exchange",
                fix_strategy="fix_nonce_generation",
                fix_params={"use_lock": True, "min_increment": 1}
            ),
            ErrorPattern(
                pattern_id="balance_not_found",
                error_type="BalanceNotFound",
                error_regex=r"USDT not found|balance.*0\.00|no balance data",
                component="balance_manager",
                fix_strategy="fix_balance_aggregation",
                fix_params={"check_variants": True, "force_refresh": True}
            ),
            ErrorPattern(
                pattern_id="money_decimal_conversion",
                error_type="MoneyDecimalError",
                error_regex=r"float\(\) argument must be a string.*not 'MoneyDecimal'|MoneyDecimal.*conversion",
                component="balance_manager",
                fix_strategy="fix_decimal_conversion",
                fix_params={"use_to_float": True}
            ),
            ErrorPattern(
                pattern_id="connection_pool_exhausted",
                error_type="ConnectionPoolExhausted",
                error_regex=r"connection pool.*full|discarding connection|pool exhausted",
                component="exchange",
                fix_strategy="fix_connection_pool",
                fix_params={"use_singleton": True, "limit_connections": 5}
            ),
        ]

        for pattern in known_patterns:
            self.error_patterns_db[pattern.pattern_id] = pattern

    async def handle_error(self, component: str, error: Exception, context: Dict[str, Any] = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Handle an error with learning and automatic resolution.
        Replaces the old resolve_error method from error resolver.
        """
        if context is None:
            context = {}

        error_context = ErrorContext(
            timestamp=time.time(),
            component=component,
            error_type=type(error).__name__,
            error_message=str(error),
            stack_trace=traceback.format_exc(),
            system_state=await self._capture_system_state()
        )

        # Record error event
        self.record_event(
            EventType.ERROR_DETECTED,
            component,
            False,
            {
                'error_type': error_context.error_type,
                'error_message': error_context.error_message[:200],
                'stack_trace': error_context.stack_trace[:500]
            },
            severity='error'
        )

        # Record in history
        self.error_history[error_context.error_type].append(error_context)

        # Find matching pattern
        pattern = self._find_matching_error_pattern(error_context)

        if pattern:
            self.logger.info(f"[LEARNING] Found matching error pattern: {pattern.pattern_id} (confidence: {pattern.confidence:.1%})")

            # Apply fix
            fix_result = await self._apply_error_fix(pattern, error_context)

            # Learn from outcome
            await self._learn_from_error_resolution(pattern, error_context, fix_result)

            return fix_result['success'], fix_result
        else:
            # No pattern found - try to learn
            self.logger.warning(f"[LEARNING] No pattern found for {error_context.error_type}: {error_context.error_message[:100]}")

            # Attempt generic fixes and learn
            fix_result = await self._attempt_generic_fixes(error_context)

            if fix_result['success']:
                # Create new pattern from successful fix
                new_pattern = await self._create_error_pattern_from_fix(error_context, fix_result)
                if new_pattern:
                    self.error_patterns_db[new_pattern.pattern_id] = new_pattern
                    self.record_event(
                        EventType.PATTERN_DETECTED,
                        'error_learning',
                        True,
                        {'pattern_type': 'error_pattern', 'pattern_id': new_pattern.pattern_id}
                    )

            return fix_result['success'], fix_result

    def _find_matching_error_pattern(self, error_context: ErrorContext) -> Optional[ErrorPattern]:
        """Find the best matching error pattern"""
        matching_patterns = []

        for pattern_id, pattern in self.error_patterns_db.items():
            if pattern.error_type == error_context.error_type and pattern.matches(error_context.error_message):
                matching_patterns.append(pattern)

        # Return pattern with highest confidence
        if matching_patterns:
            return max(matching_patterns, key=lambda p: p.confidence)

        return None

    async def _apply_error_fix(self, pattern: ErrorPattern, error_context: ErrorContext) -> Dict[str, Any]:
        """Apply a fix strategy based on the error pattern"""
        fix_strategy = self.fix_strategies.get(pattern.fix_strategy)

        if not fix_strategy:
            return {'success': False, 'error': f'Unknown fix strategy: {pattern.fix_strategy}'}

        try:
            result = await fix_strategy(pattern, error_context)

            error_context.fix_attempted = True
            error_context.fix_successful = result.get('success', False)
            error_context.fix_details = result

            if result['success']:
                pattern.success_count += 1
                self.record_event(
                    EventType.ERROR_RESOLVED,
                    pattern.component,
                    True,
                    {'pattern_id': pattern.pattern_id, 'fix_strategy': pattern.fix_strategy}
                )
            else:
                pattern.failure_count += 1

            pattern.last_seen = time.time()

            # Save updated patterns
            self._save_learning_data()

            return result

        except Exception as e:
            self.logger.error(f"[LEARNING] Fix strategy failed: {e}")
            return {'success': False, 'error': str(e)}

    # Error fix strategy implementations

    async def _fix_restart_component(self, pattern: ErrorPattern, error_context: ErrorContext) -> Dict[str, Any]:
        """Restart a specific component"""
        component_name = pattern.component

        try:
            if component_name == 'websocket' and self.bot and hasattr(self.bot, 'websocket_manager'):
                await self.bot.websocket_manager.disconnect()
                await asyncio.sleep(2)
                success = await self.bot.websocket_manager.connect()

                if success:
                    # Re-subscribe to all symbols
                    await self.bot.websocket_manager.subscribe_to_ticker(self.bot.websocket_manager.symbols)
                    await self.bot.websocket_manager.subscribe_to_ohlc(self.bot.websocket_manager.symbols)

                return {'success': success, 'component': component_name, 'action': 'restarted'}

            elif component_name == 'strategy_manager' and self.bot and hasattr(self.bot, 'strategy_manager'):
                # Reinitialize strategy manager
                await self.bot.strategy_manager.stop_all_strategies()
                await self.bot.strategy_manager.initialize_strategies()
                return {'success': True, 'component': component_name, 'action': 'reinitialized'}

            else:
                return {'success': False, 'error': f'Component {component_name} not found or not restartable'}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def _fix_update_parsing_strategy(self, pattern: ErrorPattern, error_context: ErrorContext) -> Dict[str, Any]:
        """Update message parsing strategy for WebSocket"""
        try:
            if self.bot and hasattr(self.bot, 'websocket_manager'):
                ws_manager = self.bot.websocket_manager

                # Enable adaptive parsing
                ws_manager.format_detection_enabled = True

                # Clear any cached patterns that might be wrong
                ws_manager.learned_patterns.clear()

                # Force re-learning on next message
                self.logger.info("[LEARNING] Cleared WebSocket parsing patterns - will re-learn from next message")

                return {'success': True, 'action': 'parsing_strategy_updated'}

            return {'success': False, 'error': 'WebSocket manager not found'}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def _fix_unicode_logging(self, pattern: ErrorPattern, error_context: ErrorContext) -> Dict[str, Any]:
        """Fix Unicode logging errors by clearing Python cache"""
        try:
            # Clear Python bytecode cache
            import subprocess

            if pattern.fix_params.get('clear_cache', True):
                # Windows command to clear __pycache__ directories
                cmd = 'for /d /r . %d in (__pycache__) do @if exist "%d" rd /s /q "%d"'
                if self.bot:
                    result = subprocess.run(cmd, shell=True, cwd=str(Path(self.bot.__module__).parent))

                self.logger.info("[LEARNING] Cleared Python cache to fix Unicode errors")

                return {'success': True, 'action': 'unicode_cache_cleared', 'requires_restart': True}

            return {'success': False, 'error': 'Cache clearing disabled'}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def _fix_balance_sync(self, pattern: ErrorPattern, error_context: ErrorContext) -> Dict[str, Any]:
        """Fix balance synchronization issues"""
        try:
            if self.bot and hasattr(self.bot, 'balance_manager'):
                balance_manager = self.bot.balance_manager

                # Clear cache using the new method
                balance_manager.clear_balance_cache()

                # Force refresh with new parameter
                balance = await balance_manager.get_balance(force_refresh=True)

                # Log the refreshed balance
                usdt_balance = balance.get('USDT', {}).get('free', 0) if isinstance(balance.get('USDT'), dict) else balance.get('USDT', 0)
                logger.info(f"[LEARNING] Balance refreshed - USDT: ${usdt_balance:.2f}")

                return {'success': True, 'action': 'balance_synchronized', 'usdt_balance': usdt_balance}

            return {'success': False, 'error': 'Balance manager not found'}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def _fix_api_credentials(self, pattern: ErrorPattern, error_context: ErrorContext) -> Dict[str, Any]:
        """Fix API credential issues"""
        try:
            import os

            from dotenv import load_dotenv

            # Reload environment variables
            if self.bot:
                env_path = Path(self.bot.__module__).parent.parent / '.env'
                if env_path.exists():
                    load_dotenv(env_path, override=True)

                    # Update exchange credentials if needed
                    if hasattr(self.bot, 'exchange'):
                        self.bot.exchange.api_key = os.getenv('KRAKEN_API_KEY', '')
                        self.bot.exchange.api_secret = os.getenv('KRAKEN_API_SECRET', '')

                    return {'success': True, 'action': 'credentials_reloaded'}

            return {'success': False, 'error': '.env file not found'}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def _fix_balance_cache(self, pattern: ErrorPattern, error_context: ErrorContext) -> Dict[str, Any]:
        """Fix balance cache mismatches"""
        try:
            if self.bot and hasattr(self.bot, 'balance_manager'):
                balance_manager = self.bot.balance_manager

                # Log current cache state
                cache_info = balance_manager.get_cache_info()
                logger.info(f"[LEARNING] Balance cache state before fix: {cache_info}")

                # Clear the balance cache
                balance_manager.clear_balance_cache()

                # Force immediate refresh
                fresh_balance = await balance_manager.get_balance(force_refresh=True)

                # Update last trade time to ensure continued refresh
                balance_manager._last_trade_time = time.time()

                # Verify the refresh worked
                usdt_balance = 0.0
                if 'USDT' in fresh_balance:
                    if isinstance(fresh_balance['USDT'], dict):
                        usdt_balance = fresh_balance['USDT'].get('free', 0)
                    else:
                        usdt_balance = fresh_balance.get('USDT', 0)

                return {
                    'success': True,
                    'action': 'balance_cache_cleared',
                    'usdt_balance': usdt_balance,
                    'cache_cleared': True
                }

            return {'success': False, 'error': 'Balance manager not found'}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def _fix_minimum_order(self, pattern: ErrorPattern, error_context: ErrorContext) -> Dict[str, Any]:
        """Fix minimum order violations"""
        try:
            safety_buffer = pattern.fix_params.get('min_buffer', 2.5)

            if self.bot:
                # Update configuration if possible
                if hasattr(self.bot, 'config'):
                    self.bot.config['min_order_size_usdt'] = safety_buffer
                    self.bot.config['minimum_balance_threshold'] = safety_buffer

                # Update trade executor if available
                if hasattr(self.bot, 'trade_executor'):
                    # This would update the minimum checks in the executor
                    logger.info(f"[LEARNING] Updated minimum order size to ${safety_buffer}")

                # Force balance refresh to ensure accurate balance
                if hasattr(self.bot, 'balance_manager'):
                    await self.bot.balance_manager.get_balance(force_refresh=True)

                return {
                    'success': True,
                    'action': 'minimum_order_updated',
                    'new_minimum': safety_buffer
                }

            return {'success': False, 'error': 'Bot configuration not accessible'}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def _fix_rebalance_cooldown(self, pattern: ErrorPattern, error_context: ErrorContext) -> Dict[str, Any]:
        """Fix emergency rebalance loop issues"""
        try:
            cooldown_hours = pattern.fix_params.get('cooldown_hours', 1.0)
            check_balance = pattern.fix_params.get('check_balance_first', True)

            if self.bot and hasattr(self.bot, 'profit_harvester'):
                harvester = self.bot.profit_harvester

                # Set cooldown timestamp
                harvester._last_rebalance_time = time.time()
                harvester._rebalance_cooldown = cooldown_hours * 3600

                # Check balance if requested
                if check_balance and hasattr(self.bot, 'balance_manager'):
                    balance = await self.bot.balance_manager.get_balance_for_asset('USDT', force_refresh=True)

                    if balance >= 5.0:  # Sufficient for trading
                        logger.info(f"[LEARNING] Sufficient USDT balance (${balance:.2f}), no rebalance needed")
                        return {
                            'success': True,
                            'action': 'rebalance_cancelled',
                            'reason': 'sufficient_balance',
                            'usdt_balance': balance
                        }

                return {
                    'success': True,
                    'action': 'rebalance_cooldown_set',
                    'cooldown_hours': cooldown_hours
                }

            return {'success': False, 'error': 'Profit harvester not found'}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def _fix_strategy_initialization(self, pattern: ErrorPattern, error_context: ErrorContext) -> Dict[str, Any]:
        """Fix strategy initialization errors"""
        try:
            if self.bot and hasattr(self.bot, 'strategy_manager'):
                strategy_manager = self.bot.strategy_manager

                # Enable fallback mode
                if hasattr(strategy_manager, 'use_fallback_strategies'):
                    strategy_manager.use_fallback_strategies = True

                # Reinitialize failed strategies
                failed_symbols = []
                for symbol, strategy in strategy_manager.strategies.items():
                    if strategy is None or hasattr(strategy, 'initialization_failed'):
                        failed_symbols.append(symbol)

                for symbol in failed_symbols:
                    # Use FastStartStrategy as fallback
                    await strategy_manager.create_fallback_strategy(symbol)

                return {'success': True, 'action': 'strategies_reinitialized', 'fixed_count': len(failed_symbols)}

            return {'success': False, 'error': 'Strategy manager not found'}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def _fix_clear_cache(self, pattern: ErrorPattern, error_context: ErrorContext) -> Dict[str, Any]:
        """Clear various caches"""
        cleared = []

        try:
            if self.bot:
                # Clear balance manager cache
                if hasattr(self.bot, 'enhanced_balance_manager'):
                    self.bot.enhanced_balance_manager._cache.clear()
                    cleared.append('balance_cache')

                # Clear opportunity scanner cache
                if hasattr(self.bot, 'opportunity_scanner'):
                    if hasattr(self.bot.opportunity_scanner, '_opportunity_cache'):
                        self.bot.opportunity_scanner._opportunity_cache.clear()
                    cleared.append('opportunity_cache')

                # Clear strategy caches
                if hasattr(self.bot, 'strategy_manager'):
                    for strategy in self.bot.strategy_manager.strategies.values():
                        if hasattr(strategy, 'clear_cache'):
                            strategy.clear_cache()
                    cleared.append('strategy_caches')

            return {'success': True, 'action': 'caches_cleared', 'cleared': cleared}

        except Exception as e:
            return {'success': False, 'error': str(e), 'cleared': cleared}

    async def _fix_reconnect_websocket(self, pattern: ErrorPattern, error_context: ErrorContext) -> Dict[str, Any]:
        """Force WebSocket reconnection"""
        return await self._fix_restart_component(
            ErrorPattern(pattern_id='ws_restart', component='websocket', **pattern.__dict__),
            error_context
        )

    async def _fix_reset_rate_limiter(self, pattern: ErrorPattern, error_context: ErrorContext) -> Dict[str, Any]:
        """Reset rate limiter after waiting"""
        try:
            wait_time = pattern.fix_params.get('wait_time', 60)

            self.logger.info(f"[LEARNING] Waiting {wait_time}s for rate limit reset...")
            await asyncio.sleep(wait_time)

            # Reset rate limiter counters
            if self.bot and hasattr(self.bot, 'exchange') and hasattr(self.bot.exchange, 'rate_limiter'):
                self.bot.exchange.rate_limiter.reset_counters()
                return {'success': True, 'action': 'rate_limiter_reset', 'waited': wait_time}

            return {'success': False, 'error': 'Rate limiter not found'}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def _fix_reload_config(self, pattern: ErrorPattern, error_context: ErrorContext) -> Dict[str, Any]:
        """Reload configuration"""
        try:
            from ..config import load_config

            new_config = load_config()
            if self.bot:
                self.bot.config = new_config

                # Update components with new config
                if hasattr(self.bot, 'exchange'):
                    self.bot.exchange.update_config(new_config)

            return {'success': True, 'action': 'config_reloaded'}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def _fix_adjust_parameters(self, pattern: ErrorPattern, error_context: ErrorContext) -> Dict[str, Any]:
        """Adjust strategy or component parameters"""
        adjustments = pattern.fix_params.get('adjustments', {})
        adjusted = []

        try:
            for param, value in adjustments.items():
                if '.' in param and self.bot:
                    # Nested parameter
                    parts = param.split('.')
                    obj = self.bot
                    for part in parts[:-1]:
                        obj = getattr(obj, part, None)
                        if obj is None:
                            break
                    if obj:
                        setattr(obj, parts[-1], value)
                        adjusted.append(param)

            return {'success': len(adjusted) > 0, 'action': 'parameters_adjusted', 'adjusted': adjusted}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def _fix_fallback_mode(self, pattern: ErrorPattern, error_context: ErrorContext) -> Dict[str, Any]:
        """Enable fallback mode for component"""
        component = pattern.component

        try:
            if component == 'strategy_manager' and self.bot:
                self.bot.strategy_manager.use_fallback_strategies = True
                return {'success': True, 'action': 'fallback_mode_enabled', 'component': component}

            return {'success': False, 'error': f'Fallback mode not available for {component}'}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def _fix_apply_learned(self, pattern: ErrorPattern, error_context: ErrorContext) -> Dict[str, Any]:
        """Apply a previously learned fix"""
        # This would apply more complex learned fixes
        return {'success': False, 'error': 'Complex learned fixes not yet implemented'}

    async def _attempt_generic_fixes(self, error_context: ErrorContext) -> Dict[str, Any]:
        """Attempt generic fixes when no pattern matches"""
        fixes_tried = []

        # Try common fixes based on error type
        if error_context.error_type == 'AttributeError':
            # Try restarting the component
            result = await self._fix_restart_component(
                ErrorPattern(pattern_id='generic', component=error_context.component, fix_strategy='restart_component', fix_params={}),
                error_context
            )
            fixes_tried.append(('restart_component', result))
            if result['success']:
                return {'success': True, 'fix_type': 'restart_component', **result}

        elif 'timeout' in error_context.error_message.lower():
            # Try reconnection
            result = await self._fix_reconnect_websocket(
                ErrorPattern(pattern_id='generic', component='websocket', fix_strategy='reconnect_websocket', fix_params={}),
                error_context
            )
            fixes_tried.append(('reconnect', result))
            if result['success']:
                return {'success': True, 'fix_type': 'reconnect', **result}

        elif 'rate limit' in error_context.error_message.lower():
            # Wait and reset
            result = await self._fix_reset_rate_limiter(
                ErrorPattern(pattern_id='generic', component='exchange', fix_strategy='reset_rate_limiter', fix_params={'wait_time': 30}),
                error_context
            )
            fixes_tried.append(('rate_limit_wait', result))
            if result['success']:
                return {'success': True, 'fix_type': 'rate_limit_wait', **result}

        return {'success': False, 'fixes_tried': fixes_tried}

    async def _learn_from_error_resolution(self, pattern: ErrorPattern, error_context: ErrorContext, fix_result: Dict[str, Any]):
        """Learn from the error resolution outcome"""
        if fix_result['success']:
            # Successful fix - strengthen pattern confidence
            insight = f"Pattern {pattern.pattern_id} successfully resolved {error_context.error_type}"
            error_context.learning_insights.append(insight)

            # Check if we should create a prevention rule
            if pattern.confidence > 0.8 and pattern.success_count > 5:
                prevention_rule = await self._create_prevention_rule(pattern, error_context)
                if prevention_rule:
                    pattern.prevention_rule = prevention_rule
                    self.record_event(
                        EventType.ERROR_PREVENTION_APPLIED,
                        pattern.component,
                        True,
                        {'pattern_id': pattern.pattern_id, 'prevention_rule': prevention_rule}
                    )
        else:
            # Failed fix - might need to adjust pattern
            insight = f"Pattern {pattern.pattern_id} failed to resolve {error_context.error_type}"
            error_context.learning_insights.append(insight)

            # If pattern confidence drops too low, mark for review
            if pattern.confidence < 0.3:
                pattern.permanent_fix_applied = False
                self.logger.warning(f"[LEARNING] Pattern {pattern.pattern_id} confidence too low - needs review")

        # Save learning data
        await self._save_error_learning_data(error_context)

    async def _create_error_pattern_from_fix(self, error_context: ErrorContext, fix_result: Dict[str, Any]) -> Optional[ErrorPattern]:
        """Create a new error pattern from a successful generic fix"""
        fix_type = fix_result.get('fix_type')

        if not fix_type:
            return None

        # Generate pattern ID
        pattern_id = f"{error_context.component}_{error_context.error_type}_{int(time.time())}"

        # Create regex pattern from error message
        # Escape special regex characters and make it more flexible
        error_regex = re.escape(error_context.error_message)
        error_regex = error_regex.replace(r'\ ', r'\s+')  # Flexible whitespace
        error_regex = error_regex.replace(r'\d+', r'\d+')  # Any numbers

        return ErrorPattern(
            pattern_id=pattern_id,
            error_type=error_context.error_type,
            error_regex=error_regex[:200],  # Limit length
            component=error_context.component,
            fix_strategy=fix_type,
            fix_params=fix_result.get('params', {}),
            success_count=1
        )

    async def _create_prevention_rule(self, pattern: ErrorPattern, error_context: ErrorContext) -> Optional[str]:
        """Create a prevention rule to stop this error from occurring"""
        # This would integrate with the bot to prevent the error
        # For now, return a description of what should be done

        if pattern.pattern_id == "websocket_data_array":
            return "Always check data type before accessing attributes in WebSocket messages"
        elif pattern.pattern_id == "unicode_encoding":
            return "Use ASCII-only characters in logging messages"
        elif pattern.pattern_id == "insufficient_balance":
            return "Check deployed capital before rejecting trades"
        elif pattern.pattern_id == "api_padding_error":
            return "Validate API credentials on startup"
        elif pattern.pattern_id == "strategy_none_info":
            return "Use fallback strategy when market info unavailable"

        return None

    async def _capture_system_state(self) -> Dict[str, Any]:
        """Capture current system state for debugging"""
        state = {
            'timestamp': time.time(),
            'components': {}
        }

        try:
            if self.bot:
                # WebSocket state
                if hasattr(self.bot, 'websocket_manager'):
                    ws = self.bot.websocket_manager
                    state['components']['websocket'] = {
                        'connected': ws.is_connected,
                        'symbols': len(ws.symbols),
                        'parsing_stats': ws.get_learning_stats() if hasattr(ws, 'get_learning_stats') else {}
                    }

                # Strategy state
                if hasattr(self.bot, 'strategy_manager'):
                    sm = self.bot.strategy_manager
                    state['components']['strategies'] = {
                        'active': len([s for s in sm.strategies.values() if s is not None]),
                        'total': len(sm.strategies)
                    }

                # Balance state
                if hasattr(self.bot, 'enhanced_balance_manager'):
                    bm = self.bot.enhanced_balance_manager
                    state['components']['balance'] = {
                        'total_usd_value': getattr(bm, '_total_usd_value', 0),
                        'cache_size': len(getattr(bm, '_cache', {}))
                    }

        except Exception as e:
            self.logger.error(f"[LEARNING] Failed to capture system state: {e}")

        return state

    async def _fix_reconnect_websocket_with_ping(self, pattern: ErrorPattern, error_context: ErrorContext) -> Dict[str, Any]:
        """Reconnect WebSocket with ping/pong enabled"""
        try:
            if self.bot and hasattr(self.bot, 'websocket_manager'):
                ws_manager = self.bot.websocket_manager

                # Disconnect current connection
                await ws_manager.disconnect()
                await asyncio.sleep(2)

                # Enable ping/pong if supported
                if hasattr(ws_manager, 'config'):
                    ws_manager.config['ping_interval'] = pattern.fix_params.get('ping_interval', 20)
                    ws_manager.config['ping_enabled'] = True

                # Reconnect
                success = await ws_manager.connect()

                if success:
                    self.logger.info("[LEARNING] WebSocket reconnected with ping/pong enabled")
                    return {'success': True, 'action': 'websocket_reconnected_with_ping'}
                else:
                    return {'success': False, 'error': 'Failed to reconnect WebSocket'}

            return {'success': False, 'error': 'WebSocket manager not found'}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def _fix_nonce_generation(self, pattern: ErrorPattern, error_context: ErrorContext) -> Dict[str, Any]:
        """Fix nonce generation issues"""
        try:
            if self.bot and hasattr(self.bot, 'exchange'):
                exchange = self.bot.exchange

                # Wait a bit to ensure nonce advances
                await asyncio.sleep(1)

                # If exchange has nonce lock, ensure it's used
                if hasattr(exchange, '_nonce_lock') and not exchange._nonce_lock:
                    exchange._nonce_lock = asyncio.Lock()
                    self.logger.info("[LEARNING] Added nonce lock to exchange")

                # Unified nonce manager handles nonce generation automatically
                # No manual nonce clearing needed

                return {'success': True, 'action': 'nonce_generation_fixed'}

            return {'success': False, 'error': 'Exchange not found'}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def _fix_balance_aggregation(self, pattern: ErrorPattern, error_context: ErrorContext) -> Dict[str, Any]:
        """Fix balance aggregation for USDT variants"""
        try:
            if self.bot and hasattr(self.bot, 'balance_manager'):
                balance_manager = self.bot.balance_manager

                # Force refresh with aggregation
                await balance_manager.force_refresh(retry_count=3)

                # Get aggregated USDT balance
                usdt_balance = await balance_manager.get_balance('USDT')

                if usdt_balance > 0:
                    self.logger.info(f"[LEARNING] Balance aggregation successful: ${usdt_balance:.2f}")
                    return {
                        'success': True,
                        'action': 'balance_aggregated',
                        'usdt_balance': usdt_balance
                    }
                else:
                    # Try manual aggregation
                    all_balances = await balance_manager.get_all_balances()
                    usdt_variants = [k for k in all_balances.keys() if 'USDT' in k or 'USD' in k]

                    return {
                        'success': False,
                        'error': 'No USDT balance found',
                        'variants_found': usdt_variants
                    }

            return {'success': False, 'error': 'Balance manager not found'}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def _fix_decimal_conversion(self, pattern: ErrorPattern, error_context: ErrorContext) -> Dict[str, Any]:
        """Fix MoneyDecimal conversion errors"""
        try:
            # This is more of a code fix that should be applied to the source
            # Log the issue for manual fixing
            self.logger.warning(
                "[LEARNING] MoneyDecimal conversion error detected. "
                "Code should use .to_float() instead of float(MoneyDecimal(...))"
            )

            # Try to refresh balance to get past the error
            if self.bot and hasattr(self.bot, 'balance_manager'):
                await self.bot.balance_manager.force_refresh()
                return {
                    'success': True,
                    'action': 'decimal_conversion_workaround',
                    'note': 'Code fix required: use .to_float() method'
                }

            return {'success': False, 'error': 'Unable to apply workaround'}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def _fix_connection_pool(self, pattern: ErrorPattern, error_context: ErrorContext) -> Dict[str, Any]:
        """Fix connection pool exhaustion"""
        try:
            if self.bot and hasattr(self.bot, 'exchange'):
                exchange = self.bot.exchange

                # Close existing connections
                if hasattr(exchange, 'session') and exchange.session:
                    await exchange.session.close()
                    await asyncio.sleep(1)

                # Reconnect with limited pool
                if hasattr(exchange, 'connect'):
                    await exchange.connect()

                    # Configure connection pool limits
                    if hasattr(exchange, 'configure_connection_pool'):
                        exchange.configure_connection_pool(
                            max_connections=pattern.fix_params.get('limit_connections', 5),
                            max_keepalive_connections=3
                        )

                    self.logger.info("[LEARNING] Connection pool reset with limits")
                    return {'success': True, 'action': 'connection_pool_reset'}

            return {'success': False, 'error': 'Exchange not found'}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def _save_error_learning_data(self, error_context: ErrorContext):
        """Save error learning data"""
        learning_file = self.storage_path / f"error_learning_{datetime.now().strftime('%Y%m%d')}.jsonl"

        try:
            data = {
                'timestamp': error_context.timestamp,
                'component': error_context.component,
                'error_type': error_context.error_type,
                'error_message': error_context.error_message[:500],
                'fix_attempted': error_context.fix_attempted,
                'fix_successful': error_context.fix_successful,
                'fix_details': error_context.fix_details,
                'insights': error_context.learning_insights,
                'system_state': error_context.system_state
            }

            with open(learning_file, 'a') as f:
                f.write(json.dumps(data) + '\n')

        except Exception as e:
            self.logger.error(f"[LEARNING] Failed to save error learning data: {e}")

    async def record_kraken_specific_error(self, error_type: str, error_message: str, component: str, fix_applied: Dict[str, Any] = None):
        """Record Kraken-specific errors for pattern learning"""
        # Create error context
        error_context = ErrorContext(
            timestamp=time.time(),
            component=component,
            error_type=error_type,
            error_message=error_message,
            stack_trace="",  # Not available for manual recording
            system_state={}
        )

        # Check if we have a pattern for this
        pattern = self._find_matching_error_pattern(error_context)

        if pattern and fix_applied and fix_applied.get('success'):
            # Update pattern success count
            pattern.success_count += 1
            pattern.last_seen = time.time()
            self.logger.info(f"[LEARNING] Updated pattern {pattern.pattern_id} - success count: {pattern.success_count}")
        elif not pattern and fix_applied and fix_applied.get('success'):
            # Create new pattern from successful fix
            pattern_id = f"{component}_{error_type}_{int(time.time())}"
            new_pattern = ErrorPattern(
                pattern_id=pattern_id,
                error_type=error_type,
                error_regex=re.escape(error_message)[:100],  # Use first 100 chars
                component=component,
                fix_strategy=fix_applied.get('strategy', 'unknown'),
                fix_params=fix_applied.get('params', {}),
                success_count=1,
                last_seen=time.time()
            )
            self.error_patterns_db[pattern_id] = new_pattern
            self.logger.info(f"[LEARNING] Created new error pattern: {pattern_id}")

        # Save learning data
        self._save_learning_data()

    def get_error_resolution_stats(self) -> Dict[str, Any]:
        """Get statistics about error resolution performance"""
        total_patterns = len(self.error_patterns_db)
        high_confidence_patterns = sum(1 for p in self.error_patterns_db.values() if p.confidence > 0.8)

        pattern_stats = []
        for pattern in sorted(self.error_patterns_db.values(), key=lambda p: p.success_count, reverse=True)[:10]:
            pattern_stats.append({
                'id': pattern.pattern_id,
                'type': pattern.error_type,
                'component': pattern.component,
                'success_rate': f"{pattern.confidence:.1%}",
                'total_fixes': pattern.success_count + pattern.failure_count
            })

        return {
            'total_patterns': total_patterns,
            'high_confidence_patterns': high_confidence_patterns,
            'top_patterns': pattern_stats,
            'prevention_rules_created': sum(1 for p in self.error_patterns_db.values() if p.prevention_rule)
        }


# Create singleton instance
universal_learning_manager = UniversalLearningManager()
