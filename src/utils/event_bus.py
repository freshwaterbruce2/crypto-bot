"""
Unified Event Bus for Component Communication
============================================

Provides a centralized event system for all components to communicate,
enabling better integration and automatic error pattern detection.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Types of events in the system"""
    # Trading events
    TRADE_EXECUTED = "trade_executed"
    TRADE_FAILED = "trade_failed"
    ORDER_PLACED = "order_placed"
    ORDER_FILLED = "order_filled"
    ORDER_CANCELLED = "order_cancelled"

    # Balance events
    BALANCE_UPDATED = "balance_updated"
    BALANCE_ERROR = "balance_error"
    INSUFFICIENT_FUNDS = "insufficient_funds"

    # WebSocket events
    WEBSOCKET_CONNECTED = "websocket_connected"
    WEBSOCKET_DISCONNECTED = "websocket_disconnected"
    WEBSOCKET_ERROR = "websocket_error"
    PRIVATE_CHANNEL_CONNECTED = "private_channel_connected"
    PRIVATE_CHANNEL_ERROR = "private_channel_error"

    # Rate limit events
    RATE_LIMIT_WARNING = "rate_limit_warning"
    RATE_LIMIT_ERROR = "rate_limit_error"
    RATE_LIMIT_BACKOFF = "rate_limit_backoff"

    # Strategy events
    SIGNAL_GENERATED = "signal_generated"
    SIGNAL_REJECTED = "signal_rejected"
    STRATEGY_ERROR = "strategy_error"

    # Learning events
    PATTERN_DETECTED = "pattern_detected"
    LEARNING_UPDATE = "learning_update"
    MINIMUM_LEARNED = "minimum_learned"

    # System events
    COMPONENT_INITIALIZED = "component_initialized"
    COMPONENT_ERROR = "component_error"
    HEALTH_CHECK = "health_check"


@dataclass
class Event:
    """Event data structure"""
    type: EventType
    source: str  # Component that generated the event
    data: dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary"""
        return {
            'type': self.type.value,
            'source': self.source,
            'data': self.data,
            'timestamp': self.timestamp.isoformat(),
            'correlation_id': self.correlation_id
        }

    def to_json(self) -> str:
        """Convert event to JSON string"""
        return json.dumps(self.to_dict())


class EventBus:
    """
    Centralized event bus for component communication.

    All components can publish events and subscribe to specific event types.
    The learning system can monitor all events for pattern detection.
    """

    def __init__(self):
        self._subscribers: dict[EventType, list[Callable]] = {}
        self._event_history: list[Event] = []
        self._max_history = 1000
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._processing = False
        self._processor_task = None

        # Event metrics
        self._event_counts: dict[EventType, int] = {}
        self._error_patterns: dict[str, int] = {}

        logger.info("[EVENT_BUS] Unified event bus initialized")

    async def start(self):
        """Start the event processor"""
        if not self._processing:
            self._processing = True
            self._processor_task = asyncio.create_task(self._process_events())
            logger.info("[EVENT_BUS] Event processor started")

    async def stop(self):
        """Stop the event processor"""
        self._processing = False
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
        logger.info("[EVENT_BUS] Event processor stopped")

    def subscribe(self, event_type: EventType, callback: Callable):
        """
        Subscribe to a specific event type.

        Args:
            event_type: Type of event to subscribe to
            callback: Async function to call when event occurs
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []

        self._subscribers[event_type].append(callback)
        logger.debug(f"[EVENT_BUS] Subscribed to {event_type.value}")

    def unsubscribe(self, event_type: EventType, callback: Callable):
        """Unsubscribe from an event type"""
        if event_type in self._subscribers:
            self._subscribers[event_type].remove(callback)

    async def publish(self, event: Event):
        """
        Publish an event to the bus.

        Args:
            event: Event to publish
        """
        # Add to queue for processing
        await self._event_queue.put(event)

        # Update metrics
        self._event_counts[event.type] = self._event_counts.get(event.type, 0) + 1

        # Track error patterns
        if 'error' in event.type.value.lower():
            error_key = f"{event.source}:{event.type.value}"
            self._error_patterns[error_key] = self._error_patterns.get(error_key, 0) + 1

    async def _process_events(self):
        """Process events from the queue"""
        while self._processing:
            try:
                # Get event with timeout to allow checking _processing flag
                event = await asyncio.wait_for(self._event_queue.get(), timeout=1.0)

                # Add to history
                self._event_history.append(event)
                if len(self._event_history) > self._max_history:
                    self._event_history.pop(0)

                # Log important events
                if event.type in [
                    EventType.TRADE_FAILED,
                    EventType.WEBSOCKET_ERROR,
                    EventType.RATE_LIMIT_ERROR,
                    EventType.COMPONENT_ERROR
                ]:
                    logger.warning(f"[EVENT_BUS] {event.type.value} from {event.source}: {event.data}")
                else:
                    logger.debug(f"[EVENT_BUS] {event.type.value} from {event.source}")

                # Notify subscribers
                if event.type in self._subscribers:
                    for callback in self._subscribers[event.type]:
                        try:
                            await callback(event)
                        except Exception as e:
                            logger.error(f"[EVENT_BUS] Subscriber error: {e}")

                # Check for patterns
                await self._check_patterns(event)

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"[EVENT_BUS] Event processing error: {e}")

    async def _check_patterns(self, event: Event):
        """Check for error patterns that need attention"""
        # Check for repeated errors
        if 'error' in event.type.value.lower():
            error_key = f"{event.source}:{event.type.value}"
            count = self._error_patterns.get(error_key, 0)

            # Alert on repeated errors
            if count == 5:
                pattern_event = Event(
                    type=EventType.PATTERN_DETECTED,
                    source="event_bus",
                    data={
                        'pattern': 'repeated_error',
                        'error_key': error_key,
                        'count': count,
                        'source': event.source,
                        'error_type': event.type.value
                    }
                )
                await self.publish(pattern_event)

            # Check for rate limit patterns
            if event.type == EventType.RATE_LIMIT_ERROR:
                # Count recent rate limit errors
                recent_rate_limits = sum(
                    1 for e in self._event_history[-50:]
                    if e.type == EventType.RATE_LIMIT_ERROR
                )

                if recent_rate_limits >= 3:
                    pattern_event = Event(
                        type=EventType.PATTERN_DETECTED,
                        source="event_bus",
                        data={
                            'pattern': 'frequent_rate_limits',
                            'count': recent_rate_limits,
                            'recommendation': 'reduce_api_calls'
                        }
                    )
                    await self.publish(pattern_event)

    def get_event_history(self, event_type: Optional[EventType] = None,
                         source: Optional[str] = None,
                         limit: int = 100) -> list[Event]:
        """
        Get event history with optional filtering.

        Args:
            event_type: Filter by event type
            source: Filter by source component
            limit: Maximum number of events to return

        Returns:
            List of events matching the criteria
        """
        history = self._event_history

        if event_type:
            history = [e for e in history if e.type == event_type]

        if source:
            history = [e for e in history if e.source == source]

        return history[-limit:]

    def get_metrics(self) -> dict[str, Any]:
        """Get event bus metrics"""
        return {
            'total_events': sum(self._event_counts.values()),
            'event_counts': {k.value: v for k, v in self._event_counts.items()},
            'error_patterns': self._error_patterns,
            'queue_size': self._event_queue.qsize(),
            'history_size': len(self._event_history)
        }

    def clear_metrics(self):
        """Clear event metrics (useful for testing)"""
        self._event_counts.clear()
        self._error_patterns.clear()


# Global event bus instance
_event_bus = EventBus()


def get_event_bus() -> EventBus:
    """Get the global event bus instance"""
    return _event_bus


# Convenience functions
async def publish_event(event_type: EventType, source: str, data: dict[str, Any],
                       correlation_id: Optional[str] = None):
    """Publish an event to the global event bus"""
    event = Event(
        type=event_type,
        source=source,
        data=data,
        correlation_id=correlation_id
    )
    await _event_bus.publish(event)


def subscribe_to_event(event_type: EventType, callback: Callable):
    """Subscribe to events on the global event bus"""
    _event_bus.subscribe(event_type, callback)
