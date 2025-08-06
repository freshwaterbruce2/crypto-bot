"""
Balance Validator System
=======================

Comprehensive balance validation and consistency checking system for the crypto 
trading bot. Ensures data integrity across different sources (WebSocket, REST API)
and provides validation rules for balance data.

Features:
- Cross-source balance validation
- Decimal precision validation
- Balance consistency checks
- Threshold-based validation rules
- Historical balance trend validation
- Comprehensive validation reporting
"""

import logging
import time
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from ..utils.decimal_precision_fix import safe_decimal

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Validation result severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationRule:
    """Individual validation rule configuration"""
    name: str
    enabled: bool = True
    severity: ValidationSeverity = ValidationSeverity.WARNING
    threshold: Optional[Decimal] = None
    description: str = ""

    def __post_init__(self):
        if self.threshold is not None:
            self.threshold = safe_decimal(self.threshold)


@dataclass
class ValidationIssue:
    """Individual validation issue"""
    rule_name: str
    severity: ValidationSeverity
    message: str
    asset: Optional[str] = None
    current_value: Optional[Decimal] = None
    expected_value: Optional[Decimal] = None
    timestamp: float = field(default_factory=time.time)

    def __post_init__(self):
        if self.current_value is not None:
            self.current_value = safe_decimal(self.current_value)
        if self.expected_value is not None:
            self.expected_value = safe_decimal(self.expected_value)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            'rule_name': self.rule_name,
            'severity': self.severity.value,
            'message': self.message,
            'asset': self.asset,
            'current_value': float(self.current_value) if self.current_value else None,
            'expected_value': float(self.expected_value) if self.expected_value else None,
            'timestamp': self.timestamp
        }


@dataclass
class BalanceValidationResult:
    """Result of balance validation"""
    is_valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    validation_duration_ms: float = 0.0
    total_assets_validated: int = 0

    def has_errors(self) -> bool:
        """Check if there are any error-level issues"""
        return any(issue.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]
                  for issue in self.issues)

    def has_warnings(self) -> bool:
        """Check if there are any warning-level issues"""
        return any(issue.severity == ValidationSeverity.WARNING for issue in self.issues)

    def get_issues_by_severity(self, severity: ValidationSeverity) -> List[ValidationIssue]:
        """Get issues filtered by severity"""
        return [issue for issue in self.issues if issue.severity == severity]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            'is_valid': self.is_valid,
            'has_errors': self.has_errors(),
            'has_warnings': self.has_warnings(),
            'total_issues': len(self.issues),
            'issues': [issue.to_dict() for issue in self.issues],
            'timestamp': self.timestamp,
            'validation_duration_ms': self.validation_duration_ms,
            'total_assets_validated': self.total_assets_validated,
            'summary': {
                'critical': len(self.get_issues_by_severity(ValidationSeverity.CRITICAL)),
                'error': len(self.get_issues_by_severity(ValidationSeverity.ERROR)),
                'warning': len(self.get_issues_by_severity(ValidationSeverity.WARNING)),
                'info': len(self.get_issues_by_severity(ValidationSeverity.INFO))
            }
        }


class BalanceValidator:
    """
    Comprehensive balance validation system
    """

    def __init__(self):
        """Initialize balance validator with default rules"""
        self.rules: Dict[str, ValidationRule] = {}
        self.validation_history: List[BalanceValidationResult] = []
        self.max_history_size = 1000

        # Initialize default validation rules
        self._setup_default_rules()

        logger.info("[BALANCE_VALIDATOR] Initialized with default validation rules")

    def _setup_default_rules(self):
        """Setup default validation rules"""

        # Balance value validation
        self.rules['negative_balance'] = ValidationRule(
            name='negative_balance',
            severity=ValidationSeverity.ERROR,
            description="Balance values should not be negative"
        )

        self.rules['negative_free_balance'] = ValidationRule(
            name='negative_free_balance',
            severity=ValidationSeverity.WARNING,
            description="Free balance should not be negative"
        )

        # Decimal precision validation
        self.rules['precision_overflow'] = ValidationRule(
            name='precision_overflow',
            severity=ValidationSeverity.WARNING,
            description="Balance precision exceeds recommended limits"
        )

        # Hold trade validation
        self.rules['hold_exceeds_balance'] = ValidationRule(
            name='hold_exceeds_balance',
            severity=ValidationSeverity.ERROR,
            description="Hold trade amount cannot exceed total balance"
        )

        # Source consistency validation
        self.rules['source_inconsistency'] = ValidationRule(
            name='source_inconsistency',
            severity=ValidationSeverity.WARNING,
            threshold=safe_decimal("0.01"),  # 1% threshold
            description="Balance values differ significantly between sources"
        )

        # Balance magnitude validation
        self.rules['unrealistic_balance'] = ValidationRule(
            name='unrealistic_balance',
            severity=ValidationSeverity.WARNING,
            threshold=safe_decimal("1000000"),  # 1M threshold
            description="Balance value appears unrealistically high"
        )

        # Zero balance validation
        self.rules['all_zero_balances'] = ValidationRule(
            name='all_zero_balances',
            severity=ValidationSeverity.WARNING,
            description="All balances are zero, which may indicate a data issue"
        )

        # Timestamp validation
        self.rules['stale_data'] = ValidationRule(
            name='stale_data',
            severity=ValidationSeverity.WARNING,
            threshold=safe_decimal("300"),  # 5 minutes
            description="Balance data is older than acceptable threshold"
        )

    def add_rule(self, rule: ValidationRule):
        """Add or update a validation rule"""
        self.rules[rule.name] = rule
        logger.info(f"[BALANCE_VALIDATOR] Added rule: {rule.name}")

    def remove_rule(self, rule_name: str) -> bool:
        """Remove a validation rule"""
        if rule_name in self.rules:
            del self.rules[rule_name]
            logger.info(f"[BALANCE_VALIDATOR] Removed rule: {rule_name}")
            return True
        return False

    def enable_rule(self, rule_name: str) -> bool:
        """Enable a validation rule"""
        if rule_name in self.rules:
            self.rules[rule_name].enabled = True
            logger.info(f"[BALANCE_VALIDATOR] Enabled rule: {rule_name}")
            return True
        return False

    def disable_rule(self, rule_name: str) -> bool:
        """Disable a validation rule"""
        if rule_name in self.rules:
            self.rules[rule_name].enabled = False
            logger.info(f"[BALANCE_VALIDATOR] Disabled rule: {rule_name}")
            return True
        return False

    def validate_single_balance(self,
                               asset: str,
                               balance: Union[Decimal, float, str],
                               hold_trade: Union[Decimal, float, str] = 0,
                               source: str = 'unknown',
                               timestamp: Optional[float] = None) -> BalanceValidationResult:
        """
        Validate a single balance entry
        
        Args:
            asset: Asset symbol
            balance: Total balance
            hold_trade: Amount held in trades
            source: Source of balance data
            timestamp: Timestamp of balance data
            
        Returns:
            Validation result
        """
        start_time = time.time()
        issues = []

        try:
            # Convert to decimal for validation
            balance_decimal = safe_decimal(balance)
            hold_decimal = safe_decimal(hold_trade)
            free_balance = balance_decimal - hold_decimal

            current_time = time.time()
            data_timestamp = timestamp or current_time

            # Run validation rules
            issues.extend(self._validate_balance_values(asset, balance_decimal, hold_decimal, free_balance))
            issues.extend(self._validate_precision(asset, balance_decimal, hold_decimal))
            issues.extend(self._validate_relationships(asset, balance_decimal, hold_decimal, free_balance))
            issues.extend(self._validate_timestamp(asset, data_timestamp, current_time))
            issues.extend(self._validate_magnitude(asset, balance_decimal))

        except Exception as e:
            issues.append(ValidationIssue(
                rule_name='validation_error',
                severity=ValidationSeverity.ERROR,
                message=f"Validation failed: {e}",
                asset=asset
            ))

        # Determine overall validity
        is_valid = not any(issue.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]
                          for issue in issues)

        validation_duration = (time.time() - start_time) * 1000  # Convert to ms

        result = BalanceValidationResult(
            is_valid=is_valid,
            issues=issues,
            validation_duration_ms=validation_duration,
            total_assets_validated=1
        )

        self._record_validation_result(result)

        return result

    def validate_multiple_balances(self,
                                  balances: Dict[str, Dict[str, Any]]) -> BalanceValidationResult:
        """
        Validate multiple balance entries
        
        Args:
            balances: Dictionary of balance data keyed by asset
            
        Returns:
            Validation result
        """
        start_time = time.time()
        all_issues = []
        valid_count = 0

        try:
            # Validate each balance individually
            for asset, balance_data in balances.items():
                try:
                    balance = balance_data.get('balance', 0)
                    hold_trade = balance_data.get('hold_trade', 0)
                    source = balance_data.get('source', 'unknown')
                    timestamp = balance_data.get('timestamp')

                    result = self.validate_single_balance(asset, balance, hold_trade, source, timestamp)
                    all_issues.extend(result.issues)

                    if result.is_valid:
                        valid_count += 1

                except Exception as e:
                    all_issues.append(ValidationIssue(
                        rule_name='balance_processing_error',
                        severity=ValidationSeverity.ERROR,
                        message=f"Failed to process balance: {e}",
                        asset=asset
                    ))

            # Run cross-balance validations
            all_issues.extend(self._validate_cross_balance_consistency(balances))

        except Exception as e:
            all_issues.append(ValidationIssue(
                rule_name='validation_system_error',
                severity=ValidationSeverity.CRITICAL,
                message=f"Validation system error: {e}"
            ))

        # Determine overall validity
        is_valid = not any(issue.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]
                          for issue in all_issues)

        validation_duration = (time.time() - start_time) * 1000  # Convert to ms

        result = BalanceValidationResult(
            is_valid=is_valid,
            issues=all_issues,
            validation_duration_ms=validation_duration,
            total_assets_validated=len(balances)
        )

        self._record_validation_result(result)

        return result

    def compare_balance_sources(self,
                               balances_a: Dict[str, Dict[str, Any]],
                               balances_b: Dict[str, Dict[str, Any]],
                               source_a: str = 'source_a',
                               source_b: str = 'source_b') -> BalanceValidationResult:
        """
        Compare balances from two different sources
        
        Args:
            balances_a: First set of balance data
            balances_b: Second set of balance data
            source_a: Name of first source
            source_b: Name of second source
            
        Returns:
            Validation result
        """
        start_time = time.time()
        issues = []

        try:
            # Get all assets from both sources
            all_assets = set(balances_a.keys()) | set(balances_b.keys())

            for asset in all_assets:
                balance_a = balances_a.get(asset)
                balance_b = balances_b.get(asset)

                if balance_a is None:
                    issues.append(ValidationIssue(
                        rule_name='missing_balance_source_a',
                        severity=ValidationSeverity.WARNING,
                        message=f"Asset {asset} missing from {source_a}",
                        asset=asset
                    ))
                    continue

                if balance_b is None:
                    issues.append(ValidationIssue(
                        rule_name='missing_balance_source_b',
                        severity=ValidationSeverity.WARNING,
                        message=f"Asset {asset} missing from {source_b}",
                        asset=asset
                    ))
                    continue

                # Compare balance values
                try:
                    bal_a = safe_decimal(balance_a.get('balance', 0))
                    bal_b = safe_decimal(balance_b.get('balance', 0))

                    if bal_a != bal_b:
                        # Calculate percentage difference
                        if bal_a > 0:
                            diff_percent = abs(bal_b - bal_a) / bal_a * 100
                        else:
                            diff_percent = 100 if bal_b > 0 else 0

                        # Check if difference exceeds threshold
                        threshold_rule = self.rules.get('source_inconsistency')
                        if threshold_rule and threshold_rule.enabled:
                            if diff_percent > float(threshold_rule.threshold):
                                issues.append(ValidationIssue(
                                    rule_name='source_inconsistency',
                                    severity=threshold_rule.severity,
                                    message=f"Balance inconsistency for {asset}: {source_a}={bal_a}, {source_b}={bal_b} ({diff_percent:.2f}% diff)",
                                    asset=asset,
                                    current_value=bal_b,
                                    expected_value=bal_a
                                ))

                except Exception as e:
                    issues.append(ValidationIssue(
                        rule_name='comparison_error',
                        severity=ValidationSeverity.ERROR,
                        message=f"Failed to compare {asset}: {e}",
                        asset=asset
                    ))

        except Exception as e:
            issues.append(ValidationIssue(
                rule_name='source_comparison_error',
                severity=ValidationSeverity.ERROR,
                message=f"Source comparison failed: {e}"
            ))

        is_valid = not any(issue.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]
                          for issue in issues)

        validation_duration = (time.time() - start_time) * 1000

        result = BalanceValidationResult(
            is_valid=is_valid,
            issues=issues,
            validation_duration_ms=validation_duration,
            total_assets_validated=len(set(balances_a.keys()) | set(balances_b.keys()))
        )

        self._record_validation_result(result)

        return result

    def _validate_balance_values(self, asset: str, balance: Decimal, hold: Decimal, free: Decimal) -> List[ValidationIssue]:
        """Validate balance values for correctness"""
        issues = []

        # Check for negative balance
        if self.rules.get('negative_balance', ValidationRule('', False)).enabled and balance < 0:
            issues.append(ValidationIssue(
                rule_name='negative_balance',
                severity=self.rules['negative_balance'].severity,
                message=f"Negative balance detected for {asset}: {balance}",
                asset=asset,
                current_value=balance
            ))

        # Check for negative free balance
        if self.rules.get('negative_free_balance', ValidationRule('', False)).enabled and free < 0:
            issues.append(ValidationIssue(
                rule_name='negative_free_balance',
                severity=self.rules['negative_free_balance'].severity,
                message=f"Negative free balance for {asset}: {free}",
                asset=asset,
                current_value=free
            ))

        return issues

    def _validate_precision(self, asset: str, balance: Decimal, hold: Decimal) -> List[ValidationIssue]:
        """Validate decimal precision"""
        issues = []

        if not self.rules.get('precision_overflow', ValidationRule('', False)).enabled:
            return issues

        # Check for excessive decimal places (more than 12)
        for value, name in [(balance, 'balance'), (hold, 'hold')]:
            if value != 0:
                _, digits, exponent = value.as_tuple()
                if exponent < -12:  # More than 12 decimal places
                    issues.append(ValidationIssue(
                        rule_name='precision_overflow',
                        severity=self.rules['precision_overflow'].severity,
                        message=f"Excessive precision in {name} for {asset}: {value}",
                        asset=asset,
                        current_value=value
                    ))

        return issues

    def _validate_relationships(self, asset: str, balance: Decimal, hold: Decimal, free: Decimal) -> List[ValidationIssue]:
        """Validate relationships between balance values"""
        issues = []

        # Check if hold exceeds balance
        if self.rules.get('hold_exceeds_balance', ValidationRule('', False)).enabled and hold > balance:
            issues.append(ValidationIssue(
                rule_name='hold_exceeds_balance',
                severity=self.rules['hold_exceeds_balance'].severity,
                message=f"Hold amount exceeds balance for {asset}: hold={hold}, balance={balance}",
                asset=asset,
                current_value=hold,
                expected_value=balance
            ))

        return issues

    def _validate_timestamp(self, asset: str, data_timestamp: float, current_time: float) -> List[ValidationIssue]:
        """Validate timestamp freshness"""
        issues = []

        stale_rule = self.rules.get('stale_data')
        if not stale_rule or not stale_rule.enabled:
            return issues

        age_seconds = current_time - data_timestamp
        if age_seconds > float(stale_rule.threshold):
            issues.append(ValidationIssue(
                rule_name='stale_data',
                severity=stale_rule.severity,
                message=f"Stale balance data for {asset}: {age_seconds:.1f}s old",
                asset=asset,
                current_value=safe_decimal(age_seconds)
            ))

        return issues

    def _validate_magnitude(self, asset: str, balance: Decimal) -> List[ValidationIssue]:
        """Validate balance magnitude for reasonableness"""
        issues = []

        unrealistic_rule = self.rules.get('unrealistic_balance')
        if not unrealistic_rule or not unrealistic_rule.enabled:
            return issues

        if balance > unrealistic_rule.threshold:
            issues.append(ValidationIssue(
                rule_name='unrealistic_balance',
                severity=unrealistic_rule.severity,
                message=f"Unrealistically high balance for {asset}: {balance}",
                asset=asset,
                current_value=balance
            ))

        return issues

    def _validate_cross_balance_consistency(self, balances: Dict[str, Dict[str, Any]]) -> List[ValidationIssue]:
        """Validate consistency across all balances"""
        issues = []

        # Check if all balances are zero
        all_zero_rule = self.rules.get('all_zero_balances')
        if all_zero_rule and all_zero_rule.enabled:
            non_zero_count = 0
            for balance_data in balances.values():
                if safe_decimal(balance_data.get('balance', 0)) > 0:
                    non_zero_count += 1

            if non_zero_count == 0 and len(balances) > 0:
                issues.append(ValidationIssue(
                    rule_name='all_zero_balances',
                    severity=all_zero_rule.severity,
                    message=f"All {len(balances)} balances are zero"
                ))

        return issues

    def _record_validation_result(self, result: BalanceValidationResult):
        """Record validation result in history"""
        self.validation_history.append(result)

        # Trim history if too large
        if len(self.validation_history) > self.max_history_size:
            self.validation_history = self.validation_history[-self.max_history_size//2:]

        # Log summary
        if result.issues:
            severity_counts = {sev.value: len(result.get_issues_by_severity(sev)) for sev in ValidationSeverity}
            logger.info(f"[BALANCE_VALIDATOR] Validation completed: {severity_counts}")

    def get_validation_statistics(self) -> Dict[str, Any]:
        """Get validation statistics"""
        if not self.validation_history:
            return {'total_validations': 0}

        total_validations = len(self.validation_history)
        valid_validations = sum(1 for result in self.validation_history if result.is_valid)

        recent_results = self.validation_history[-100:]  # Last 100 validations
        avg_duration = sum(result.validation_duration_ms for result in recent_results) / len(recent_results)

        return {
            'total_validations': total_validations,
            'valid_validations': valid_validations,
            'validation_success_rate': valid_validations / total_validations * 100,
            'average_duration_ms': avg_duration,
            'enabled_rules': [name for name, rule in self.rules.items() if rule.enabled],
            'total_rules': len(self.rules)
        }
