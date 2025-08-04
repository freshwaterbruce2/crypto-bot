"""
Failure Detection and Analysis System
====================================

Intelligent failure detection system that analyzes error patterns,
classifies failures, and provides insights for circuit breaker decisions.

Features:
- Pattern recognition for different failure types
- Failure classification and categorization
- Trend analysis and prediction
- Root cause analysis hints
- Integration with circuit breaker state decisions
- Machine learning-based failure prediction
- Historical failure pattern analysis
"""

import json
import logging
import re
import statistics
import time
from collections import defaultdict, deque, Counter
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Pattern, Union
import threading

logger = logging.getLogger(__name__)


class FailureCategory(Enum):
    """Categories of failures for classification."""
    NETWORK = "NETWORK"
    TIMEOUT = "TIMEOUT"
    AUTHENTICATION = "AUTHENTICATION"
    RATE_LIMIT = "RATE_LIMIT"
    SERVER_ERROR = "SERVER_ERROR"
    CLIENT_ERROR = "CLIENT_ERROR"
    VALIDATION = "VALIDATION"
    RESOURCE_EXHAUSTION = "RESOURCE_EXHAUSTION"
    DEPENDENCY = "DEPENDENCY"
    UNKNOWN = "UNKNOWN"


class FailureSeverity(Enum):
    """Severity levels for failures."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class FailurePattern:
    """
    Pattern definition for failure detection.
    
    Attributes:
        name: Pattern name
        category: Failure category
        severity: Failure severity
        regex_patterns: List of regex patterns to match
        keywords: Keywords to look for in error messages
        http_status_codes: HTTP status codes associated with this pattern
        exception_types: Exception types associated with this pattern
        frequency_threshold: Minimum frequency to trigger pattern
        time_window: Time window for frequency calculation
        description: Human-readable description
    """
    name: str
    category: FailureCategory
    severity: FailureSeverity
    regex_patterns: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    http_status_codes: List[int] = field(default_factory=list)
    exception_types: List[str] = field(default_factory=list)
    frequency_threshold: int = 3
    time_window: float = 300.0  # 5 minutes
    description: str = ""


@dataclass
class FailureEvent:
    """
    Individual failure event information.
    
    Attributes:
        timestamp: When the failure occurred
        service_name: Service that failed
        error_message: Error message
        exception_type: Type of exception
        http_status_code: HTTP status code if applicable
        response_time_ms: Response time in milliseconds
        context: Additional context information
        stack_trace: Stack trace if available
        metadata: Additional metadata
    """
    timestamp: float
    service_name: str
    error_message: str
    exception_type: Optional[str] = None
    http_status_code: Optional[int] = None
    response_time_ms: Optional[float] = None
    context: Dict[str, Any] = field(default_factory=dict)
    stack_trace: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FailureAnalysis:
    """
    Analysis result for a set of failures.
    
    Attributes:
        service_name: Service being analyzed
        analysis_timestamp: When analysis was performed
        total_failures: Total number of failures analyzed
        time_window: Time window of analysis
        detected_patterns: Patterns detected in failures
        failure_rate: Failure rate (failures per minute)
        trend: Trend analysis (increasing, decreasing, stable)
        severity_distribution: Distribution of failure severities
        category_distribution: Distribution of failure categories
        recommendations: Recommended actions
        confidence_score: Confidence in the analysis (0.0 to 1.0)
    """
    service_name: str
    analysis_timestamp: float
    total_failures: int
    time_window: float
    detected_patterns: List[str] = field(default_factory=list)
    failure_rate: float = 0.0
    trend: str = "stable"
    severity_distribution: Dict[str, int] = field(default_factory=dict)
    category_distribution: Dict[str, int] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    confidence_score: float = 0.0


class FailureClassifier:
    """
    Classifies failures based on patterns and machine learning.
    
    Uses predefined patterns and statistical analysis to classify
    failures into categories and determine their severity.
    """
    
    def __init__(self):
        """Initialize failure classifier with default patterns."""
        self.patterns: List[FailurePattern] = []
        self._compiled_patterns: Dict[str, List[Pattern]] = {}
        self._initialize_default_patterns()
        self._compile_patterns()
        
        logger.info(f"Failure classifier initialized with {len(self.patterns)} patterns")
    
    def _initialize_default_patterns(self) -> None:
        """
        Initialize default failure patterns.
        """
        # Network-related failures
        self.patterns.append(FailurePattern(
            name="connection_timeout",
            category=FailureCategory.NETWORK,
            severity=FailureSeverity.HIGH,
            regex_patterns=[
                r"connection\s+timeout",
                r"connect\s+timed\s+out",
                r"timeout\s+error"
            ],
            keywords=["timeout", "connection", "network"],
            description="Network connection timeout"
        ))
        
        self.patterns.append(FailurePattern(
            name="connection_refused",
            category=FailureCategory.NETWORK,
            severity=FailureSeverity.CRITICAL,
            regex_patterns=[
                r"connection\s+refused",
                r"connection\s+reset",
                r"no\s+route\s+to\s+host"
            ],
            keywords=["refused", "reset", "unreachable"],
            description="Network connection refused or reset"
        ))
        
        # Authentication failures
        self.patterns.append(FailurePattern(
            name="auth_failure",
            category=FailureCategory.AUTHENTICATION,
            severity=FailureSeverity.HIGH,
            regex_patterns=[
                r"authentication\s+failed",
                r"invalid\s+credentials",
                r"unauthorized"
            ],
            keywords=["auth", "credentials", "unauthorized", "forbidden"],
            http_status_codes=[401, 403],
            description="Authentication or authorization failure"
        ))
        
        # Rate limiting
        self.patterns.append(FailurePattern(
            name="rate_limit_exceeded",
            category=FailureCategory.RATE_LIMIT,
            severity=FailureSeverity.MEDIUM,
            regex_patterns=[
                r"rate\s+limit\s+exceeded",
                r"too\s+many\s+requests",
                r"quota\s+exceeded"
            ],
            keywords=["rate", "limit", "quota", "throttle"],
            http_status_codes=[429],
            description="Rate limit or quota exceeded"
        ))
        
        # Server errors
        self.patterns.append(FailurePattern(
            name="server_error",
            category=FailureCategory.SERVER_ERROR,
            severity=FailureSeverity.HIGH,
            regex_patterns=[
                r"internal\s+server\s+error",
                r"service\s+unavailable",
                r"bad\s+gateway"
            ],
            keywords=["server", "internal", "unavailable", "gateway"],
            http_status_codes=[500, 502, 503, 504],
            description="Server-side error"
        ))
        
        # Timeout patterns
        self.patterns.append(FailurePattern(
            name="request_timeout",
            category=FailureCategory.TIMEOUT,
            severity=FailureSeverity.MEDIUM,
            regex_patterns=[
                r"request\s+timeout",
                r"read\s+timeout",
                r"operation\s+timeout"
            ],
            keywords=["timeout", "timed out"],
            http_status_codes=[408, 504],
            description="Request or operation timeout"
        ))
        
        # Resource exhaustion
        self.patterns.append(FailurePattern(
            name="resource_exhaustion",
            category=FailureCategory.RESOURCE_EXHAUSTION,
            severity=FailureSeverity.CRITICAL,
            regex_patterns=[
                r"out\s+of\s+memory",
                r"memory\s+exhausted",
                r"disk\s+full",
                r"no\s+space\s+left"
            ],
            keywords=["memory", "disk", "space", "exhausted"],
            description="System resource exhaustion"
        ))
        
        # Validation errors
        self.patterns.append(FailurePattern(
            name="validation_error",
            category=FailureCategory.VALIDATION,
            severity=FailureSeverity.LOW,
            regex_patterns=[
                r"validation\s+error",
                r"invalid\s+input",
                r"bad\s+request"
            ],
            keywords=["validation", "invalid", "malformed"],
            http_status_codes=[400, 422],
            description="Input validation error"
        ))
    
    def _compile_patterns(self) -> None:
        """
        Compile regex patterns for efficient matching.
        """
        for pattern in self.patterns:
            compiled = []
            for regex_pattern in pattern.regex_patterns:
                try:
                    compiled.append(re.compile(regex_pattern, re.IGNORECASE))
                except re.error as e:
                    logger.warning(f"Invalid regex pattern '{regex_pattern}': {e}")
            
            self._compiled_patterns[pattern.name] = compiled
    
    def classify_failure(self, failure_event: FailureEvent) -> Tuple[FailureCategory, FailureSeverity, List[str]]:
        """
        Classify a failure event.
        
        Args:
            failure_event: Failure event to classify
            
        Returns:
            Tuple of (category, severity, matched_patterns)
        """
        matched_patterns = []
        category_scores = defaultdict(int)
        severity_scores = defaultdict(int)
        
        error_text = (failure_event.error_message or "").lower()
        exception_type = (failure_event.exception_type or "").lower()
        
        for pattern in self.patterns:
            score = 0
            
            # Check regex patterns
            if self._compiled_patterns.get(pattern.name):
                for compiled_pattern in self._compiled_patterns[pattern.name]:
                    if compiled_pattern.search(error_text):
                        score += 3
                        break
            
            # Check keywords
            for keyword in pattern.keywords:
                if keyword.lower() in error_text or keyword.lower() in exception_type:
                    score += 1
            
            # Check HTTP status codes
            if (failure_event.http_status_code and 
                failure_event.http_status_code in pattern.http_status_codes):
                score += 2
            
            # Check exception types
            if exception_type:
                for exc_type in pattern.exception_types:
                    if exc_type.lower() in exception_type:
                        score += 2
                        break
            
            # If pattern matches, add to results
            if score > 0:
                matched_patterns.append(pattern.name)
                category_scores[pattern.category] += score
                severity_scores[pattern.severity] += score
        
        # Determine best category and severity
        if category_scores:
            best_category = max(category_scores.items(), key=lambda x: x[1])[0]
            best_severity = max(severity_scores.items(), key=lambda x: x[1])[0]
        else:
            best_category = FailureCategory.UNKNOWN
            best_severity = FailureSeverity.MEDIUM
        
        logger.debug(
            f"Classified failure: category={best_category.value}, "
            f"severity={best_severity.value}, patterns={matched_patterns}"
        )
        
        return best_category, best_severity, matched_patterns
    
    def add_pattern(self, pattern: FailurePattern) -> None:
        """
        Add a custom failure pattern.
        
        Args:
            pattern: Failure pattern to add
        """
        self.patterns.append(pattern)
        
        # Compile regex patterns for this pattern
        compiled = []
        for regex_pattern in pattern.regex_patterns:
            try:
                compiled.append(re.compile(regex_pattern, re.IGNORECASE))
            except re.error as e:
                logger.warning(f"Invalid regex pattern '{regex_pattern}': {e}")
        
        self._compiled_patterns[pattern.name] = compiled
        
        logger.info(f"Added custom failure pattern: {pattern.name}")
    
    def remove_pattern(self, pattern_name: str) -> bool:
        """
        Remove a failure pattern.
        
        Args:
            pattern_name: Name of pattern to remove
            
        Returns:
            True if pattern was removed, False if not found
        """
        for i, pattern in enumerate(self.patterns):
            if pattern.name == pattern_name:
                self.patterns.pop(i)
                self._compiled_patterns.pop(pattern_name, None)
                logger.info(f"Removed failure pattern: {pattern_name}")
                return True
        
        return False
    
    def get_patterns(self) -> List[FailurePattern]:
        """
        Get all failure patterns.
        
        Returns:
            List of failure patterns
        """
        return self.patterns.copy()


class FailureDetector:
    """
    Main failure detection and analysis system.
    
    Collects failure events, analyzes patterns, and provides insights
    for circuit breaker decision making.
    """
    
    def __init__(
        self,
        analysis_window: float = 300.0,  # 5 minutes
        max_events_per_service: int = 1000,
        storage_path: Optional[str] = None
    ):
        """
        Initialize failure detector.
        
        Args:
            analysis_window: Time window for failure analysis in seconds
            max_events_per_service: Maximum failure events to keep per service
            storage_path: Path for persistent storage
        """
        self.analysis_window = analysis_window
        self.max_events_per_service = max_events_per_service
        self.storage_path = Path(storage_path) if storage_path else None
        
        # Components
        self.classifier = FailureClassifier()
        
        # Event storage
        self.failure_events: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=max_events_per_service)
        )
        
        # Analysis cache
        self.analysis_cache: Dict[str, FailureAnalysis] = {}
        self._cache_ttl = 60.0  # 1 minute
        
        # Pattern tracking
        self.pattern_statistics: Dict[str, Dict[str, int]] = defaultdict(
            lambda: defaultdict(int)
        )
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Load persistent state
        if self.storage_path:
            self._load_state()
        
        logger.info(f"Failure detector initialized with {analysis_window}s analysis window")
    
    def record_failure(
        self,
        service_name: str,
        error_message: str,
        exception_type: Optional[str] = None,
        http_status_code: Optional[int] = None,
        response_time_ms: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None,
        stack_trace: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> FailureEvent:
        """
        Record a failure event.
        
        Args:
            service_name: Name of the service that failed
            error_message: Error message
            exception_type: Type of exception
            http_status_code: HTTP status code if applicable
            response_time_ms: Response time in milliseconds
            context: Additional context information
            stack_trace: Stack trace if available
            metadata: Additional metadata
            
        Returns:
            Created failure event
        """
        with self._lock:
            failure_event = FailureEvent(
                timestamp=time.time(),
                service_name=service_name,
                error_message=error_message,
                exception_type=exception_type,
                http_status_code=http_status_code,
                response_time_ms=response_time_ms,
                context=context or {},
                stack_trace=stack_trace,
                metadata=metadata or {}
            )
            
            # Store the event
            self.failure_events[service_name].append(failure_event)
            
            # Classify the failure
            category, severity, patterns = self.classifier.classify_failure(failure_event)
            
            # Update pattern statistics
            for pattern in patterns:
                self.pattern_statistics[service_name][pattern] += 1
            
            # Invalidate analysis cache for this service
            self.analysis_cache.pop(service_name, None)
            
            logger.debug(
                f"Recorded failure for {service_name}: "
                f"category={category.value}, severity={severity.value}, "
                f"patterns={patterns}"
            )
            
            return failure_event
    
    def analyze_failures(
        self,
        service_name: str,
        time_window: Optional[float] = None
    ) -> FailureAnalysis:
        """
        Analyze failures for a specific service.
        
        Args:
            service_name: Service to analyze
            time_window: Analysis time window (defaults to configured window)
            
        Returns:
            Failure analysis result
        """
        with self._lock:
            # Check cache first
            cached_analysis = self.analysis_cache.get(service_name)
            if (cached_analysis and 
                (time.time() - cached_analysis.analysis_timestamp) < self._cache_ttl):
                return cached_analysis
            
            analysis_window = time_window or self.analysis_window
            current_time = time.time()
            window_start = current_time - analysis_window
            
            # Get recent failures
            all_failures = list(self.failure_events.get(service_name, []))
            recent_failures = [
                f for f in all_failures
                if f.timestamp >= window_start
            ]
            
            if not recent_failures:
                analysis = FailureAnalysis(
                    service_name=service_name,
                    analysis_timestamp=current_time,
                    total_failures=0,
                    time_window=analysis_window
                )
                self.analysis_cache[service_name] = analysis
                return analysis
            
            # Classify all recent failures
            category_counts = defaultdict(int)
            severity_counts = defaultdict(int)
            detected_patterns = set()
            
            for failure in recent_failures:
                category, severity, patterns = self.classifier.classify_failure(failure)
                category_counts[category.value] += 1
                severity_counts[severity.value] += 1
                detected_patterns.update(patterns)
            
            # Calculate failure rate (failures per minute)
            failure_rate = len(recent_failures) / (analysis_window / 60.0)
            
            # Analyze trend
            trend = self._analyze_trend(recent_failures, analysis_window)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(
                recent_failures, category_counts, severity_counts, failure_rate
            )
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence(
                recent_failures, detected_patterns, category_counts
            )
            
            # Create analysis
            analysis = FailureAnalysis(
                service_name=service_name,
                analysis_timestamp=current_time,
                total_failures=len(recent_failures),
                time_window=analysis_window,
                detected_patterns=list(detected_patterns),
                failure_rate=failure_rate,
                trend=trend,
                severity_distribution=dict(severity_counts),
                category_distribution=dict(category_counts),
                recommendations=recommendations,
                confidence_score=confidence_score
            )
            
            # Cache the analysis
            self.analysis_cache[service_name] = analysis
            
            logger.info(
                f"Analyzed {len(recent_failures)} failures for {service_name}: "
                f"rate={failure_rate:.2f}/min, trend={trend}, confidence={confidence_score:.2f}"
            )
            
            return analysis
    
    def _analyze_trend(
        self,
        failures: List[FailureEvent],
        time_window: float
    ) -> str:
        """
        Analyze failure trend over time.
        
        Args:
            failures: List of failure events
            time_window: Analysis time window
            
        Returns:
            Trend description (increasing, decreasing, stable)
        """
        if len(failures) < 4:
            return "stable"
        
        # Split time window into segments and count failures per segment
        current_time = time.time()
        segments = 4
        segment_duration = time_window / segments
        segment_counts = [0] * segments
        
        for failure in failures:
            segment_index = int((current_time - failure.timestamp) / segment_duration)
            if 0 <= segment_index < segments:
                # Reverse index to get chronological order
                segment_counts[segments - 1 - segment_index] += 1
        
        # Calculate trend using linear regression slope
        x_values = list(range(segments))
        if sum(segment_counts) == 0:
            return "stable"
        
        try:
            # Simple slope calculation
            n = len(x_values)
            sum_x = sum(x_values)
            sum_y = sum(segment_counts)
            sum_xy = sum(x * y for x, y in zip(x_values, segment_counts))
            sum_x2 = sum(x * x for x in x_values)
            
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
            
            if slope > 0.5:
                return "increasing"
            elif slope < -0.5:
                return "decreasing"
            else:
                return "stable"
        
        except (ZeroDivisionError, ValueError):
            return "stable"
    
    def _generate_recommendations(
        self,
        failures: List[FailureEvent],
        category_counts: Dict[str, int],
        severity_counts: Dict[str, int],
        failure_rate: float
    ) -> List[str]:
        """
        Generate recommendations based on failure analysis.
        
        Args:
            failures: List of failure events
            category_counts: Count by category
            severity_counts: Count by severity
            failure_rate: Failure rate per minute
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        # High failure rate
        if failure_rate > 10.0:  # More than 10 failures per minute
            recommendations.append("Consider opening circuit breaker due to high failure rate")
        
        # Critical severity failures
        if severity_counts.get('CRITICAL', 0) > 0:
            recommendations.append("Critical failures detected - immediate attention required")
        
        # Network issues
        if category_counts.get('NETWORK', 0) > category_counts.get('SERVER_ERROR', 0):
            recommendations.append("Network connectivity issues detected - check network infrastructure")
        
        # Authentication issues
        if category_counts.get('AUTHENTICATION', 0) > 2:
            recommendations.append("Authentication failures detected - verify API credentials")
        
        # Rate limiting
        if category_counts.get('RATE_LIMIT', 0) > 1:
            recommendations.append("Rate limiting detected - implement backoff strategy")
        
        # Server errors
        if category_counts.get('SERVER_ERROR', 0) > 3:
            recommendations.append("Server errors detected - downstream service may be unhealthy")
        
        # Timeout patterns
        if category_counts.get('TIMEOUT', 0) > 2:
            recommendations.append("Timeout issues detected - consider increasing timeout values")
        
        # Resource exhaustion
        if category_counts.get('RESOURCE_EXHAUSTION', 0) > 0:
            recommendations.append("Resource exhaustion detected - scale up resources or optimize usage")
        
        return recommendations
    
    def _calculate_confidence(
        self,
        failures: List[FailureEvent],
        detected_patterns: set,
        category_counts: Dict[str, int]
    ) -> float:
        """
        Calculate confidence score for the analysis.
        
        Args:
            failures: List of failure events
            detected_patterns: Set of detected patterns
            category_counts: Count by category
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        confidence = 0.0
        
        # Base confidence on number of failures
        if len(failures) >= 10:
            confidence += 0.4
        elif len(failures) >= 5:
            confidence += 0.2
        elif len(failures) >= 2:
            confidence += 0.1
        
        # Increase confidence if patterns were detected
        if detected_patterns:
            confidence += 0.3
        
        # Increase confidence if failures are categorized (not UNKNOWN)
        unknown_count = category_counts.get('UNKNOWN', 0)
        total_count = sum(category_counts.values())
        if total_count > 0:
            categorized_ratio = 1.0 - (unknown_count / total_count)
            confidence += 0.3 * categorized_ratio
        
        return min(1.0, confidence)
    
    def get_failure_statistics(
        self,
        service_name: Optional[str] = None,
        time_window: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Get failure statistics.
        
        Args:
            service_name: Specific service (None for all services)
            time_window: Time window for statistics
            
        Returns:
            Failure statistics
        """
        with self._lock:
            time_window = time_window or self.analysis_window
            current_time = time.time()
            window_start = current_time - time_window
            
            if service_name:
                services = [service_name] if service_name in self.failure_events else []
            else:
                services = list(self.failure_events.keys())
            
            stats = {
                'time_window': time_window,
                'services': {},
                'global_stats': {
                    'total_failures': 0,
                    'total_services': len(services),
                    'category_distribution': defaultdict(int),
                    'severity_distribution': defaultdict(int),
                    'pattern_frequency': defaultdict(int)
                }
            }
            
            for svc_name in services:
                failures = [
                    f for f in self.failure_events[svc_name]
                    if f.timestamp >= window_start
                ]
                
                if not failures:
                    continue
                
                # Classify failures
                category_counts = defaultdict(int)
                severity_counts = defaultdict(int)
                pattern_counts = defaultdict(int)
                
                for failure in failures:
                    category, severity, patterns = self.classifier.classify_failure(failure)
                    category_counts[category.value] += 1
                    severity_counts[severity.value] += 1
                    
                    for pattern in patterns:
                        pattern_counts[pattern] += 1
                
                # Service-specific stats
                stats['services'][svc_name] = {
                    'failure_count': len(failures),
                    'failure_rate': len(failures) / (time_window / 60.0),
                    'category_distribution': dict(category_counts),
                    'severity_distribution': dict(severity_counts),
                    'pattern_frequency': dict(pattern_counts),
                    'avg_response_time': statistics.mean([
                        f.response_time_ms for f in failures
                        if f.response_time_ms is not None
                    ]) if any(f.response_time_ms for f in failures) else 0.0
                }
                
                # Update global stats
                stats['global_stats']['total_failures'] += len(failures)
                
                for category, count in category_counts.items():
                    stats['global_stats']['category_distribution'][category] += count
                
                for severity, count in severity_counts.items():
                    stats['global_stats']['severity_distribution'][severity] += count
                
                for pattern, count in pattern_counts.items():
                    stats['global_stats']['pattern_frequency'][pattern] += count
            
            # Convert defaultdicts to regular dicts for JSON serialization
            stats['global_stats']['category_distribution'] = dict(
                stats['global_stats']['category_distribution']
            )
            stats['global_stats']['severity_distribution'] = dict(
                stats['global_stats']['severity_distribution']
            )
            stats['global_stats']['pattern_frequency'] = dict(
                stats['global_stats']['pattern_frequency']
            )
            
            return stats
    
    def should_open_circuit(
        self,
        service_name: str,
        failure_threshold: int = 5,
        time_window: Optional[float] = None
    ) -> Tuple[bool, str, FailureAnalysis]:
        """
        Determine if circuit breaker should open based on failure analysis.
        
        Args:
            service_name: Service to check
            failure_threshold: Minimum failures to consider opening circuit
            time_window: Analysis time window
            
        Returns:
            Tuple of (should_open, reason, analysis)
        """
        analysis = self.analyze_failures(service_name, time_window)
        
        # No failures - circuit should remain closed
        if analysis.total_failures == 0:
            return False, "No failures detected", analysis
        
        # Below threshold - circuit should remain closed
        if analysis.total_failures < failure_threshold:
            return False, f"Failures ({analysis.total_failures}) below threshold ({failure_threshold})", analysis
        
        # High failure rate
        if analysis.failure_rate > 10.0:  # More than 10 failures per minute
            return True, f"High failure rate: {analysis.failure_rate:.2f} failures/minute", analysis
        
        # Critical failures
        critical_count = analysis.severity_distribution.get('CRITICAL', 0)
        if critical_count > 0:
            critical_ratio = critical_count / analysis.total_failures
            if critical_ratio > 0.5:  # More than 50% critical
                return True, f"High critical failure ratio: {critical_ratio:.1%}", analysis
        
        # Network or dependency issues
        network_count = analysis.category_distribution.get('NETWORK', 0)
        dependency_count = analysis.category_distribution.get('DEPENDENCY', 0)
        infrastructure_failures = network_count + dependency_count
        
        if infrastructure_failures > analysis.total_failures * 0.7:  # More than 70%
            return True, "Predominantly infrastructure failures detected", analysis
        
        # Increasing trend with high failure rate
        if analysis.trend == "increasing" and analysis.failure_rate > 5.0:
            return True, f"Increasing failure trend with rate {analysis.failure_rate:.2f}/minute", analysis
        
        # Resource exhaustion
        if analysis.category_distribution.get('RESOURCE_EXHAUSTION', 0) > 0:
            return True, "Resource exhaustion detected", analysis
        
        return False, "Failure pattern does not warrant circuit opening", analysis
    
    def clear_failures(self, service_name: Optional[str] = None) -> None:
        """
        Clear failure events.
        
        Args:
            service_name: Service to clear (None for all services)
        """
        with self._lock:
            if service_name:
                if service_name in self.failure_events:
                    self.failure_events[service_name].clear()
                    self.pattern_statistics.pop(service_name, None)
                    self.analysis_cache.pop(service_name, None)
                    logger.info(f"Cleared failures for service: {service_name}")
            else:
                self.failure_events.clear()
                self.pattern_statistics.clear()
                self.analysis_cache.clear()
                logger.info("Cleared all failure events")
    
    def _save_state(self) -> None:
        """
        Save failure detector state to persistent storage.
        """
        if not self.storage_path:
            return
        
        try:
            # Prepare state data
            state_data = {
                'failure_events': {},
                'pattern_statistics': dict(self.pattern_statistics),
                'timestamp': time.time()
            }
            
            # Save recent failure events (last 100 per service)
            for service_name, events in self.failure_events.items():
                recent_events = list(events)[-100:]  # Keep last 100
                state_data['failure_events'][service_name] = [
                    asdict(event) for event in recent_events
                ]
            
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.storage_path, 'w') as f:
                json.dump(state_data, f, indent=2)
            
            logger.debug(f"Failure detector state saved to {self.storage_path}")
        
        except Exception as e:
            logger.error(f"Failed to save failure detector state: {e}")
    
    def _load_state(self) -> None:
        """
        Load failure detector state from persistent storage.
        """
        if not self.storage_path or not self.storage_path.exists():
            return
        
        try:
            with open(self.storage_path, 'r') as f:
                state_data = json.load(f)
            
            # Check if state is recent (within 24 hours)
            current_time = time.time()
            saved_time = state_data.get('timestamp', 0)
            
            if (current_time - saved_time) < 86400:  # 24 hours
                # Restore failure events
                if 'failure_events' in state_data:
                    for service_name, events_data in state_data['failure_events'].items():
                        events = deque(maxlen=self.max_events_per_service)
                        
                        for event_data in events_data:
                            event = FailureEvent(
                                timestamp=event_data['timestamp'],
                                service_name=event_data['service_name'],
                                error_message=event_data['error_message'],
                                exception_type=event_data.get('exception_type'),
                                http_status_code=event_data.get('http_status_code'),
                                response_time_ms=event_data.get('response_time_ms'),
                                context=event_data.get('context', {}),
                                stack_trace=event_data.get('stack_trace'),
                                metadata=event_data.get('metadata', {})
                            )
                            events.append(event)
                        
                        self.failure_events[service_name] = events
                
                # Restore pattern statistics
                if 'pattern_statistics' in state_data:
                    for service_name, patterns in state_data['pattern_statistics'].items():
                        self.pattern_statistics[service_name] = defaultdict(int)
                        self.pattern_statistics[service_name].update(patterns)
                
                total_events = sum(len(events) for events in self.failure_events.values())
                logger.info(
                    f"Failure detector state loaded: {len(self.failure_events)} services, "
                    f"{total_events} events"
                )
            else:
                logger.info("Failure detector state too old, starting fresh")
        
        except Exception as e:
            logger.error(f"Failed to load failure detector state: {e}")
    
    def cleanup(self) -> None:
        """
        Cleanup failure detector resources.
        """
        if self.storage_path:
            self._save_state()
        
        logger.info("Failure detector cleanup completed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()
