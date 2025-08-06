#!/usr/bin/env python3
"""
Crypto Trading Bot - Security Validation Suite 2025
===================================================

Comprehensive security validation following 2025 enterprise security standards.
Validates all critical security implementations and generates compliance report.

Security Areas Validated:
1. SSL/TLS Configuration (TLS 1.3+ enforcement)
2. Credential Management (AES-256 encryption)
3. Logging Security (credential sanitization)
4. Transport Layer Security
5. Memory Protection
6. Code Vulnerability Scanning
7. Compliance Verification

Usage:
    python security_validation_2025.py
    python security_validation_2025.py --detailed
    python security_validation_2025.py --export-report
"""

import json
import logging
import os
import re
import ssl
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add src directory to path for imports
current_dir = Path(__file__).parent
src_dir = current_dir / "src"
sys.path.insert(0, str(src_dir))

# Import our security modules
try:
    from src.auth.secure_credential_storage import SecureCredentialStorage, SecureString
    from src.utils.secure_logging import SecureLogFormatter, setup_secure_logging
    from src.utils.secure_transport import SecureSSLContextManager, validate_tls_connection
    from src.websocket.websocket_v2_manager import WebSocketV2Manager
    SECURITY_MODULES_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import security modules: {e}")
    SECURITY_MODULES_AVAILABLE = False


@dataclass
class SecurityTestResult:
    """Result of a security test"""
    test_name: str
    passed: bool
    severity: str  # "CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"
    message: str
    details: Optional[Dict[str, Any]] = None
    remediation: Optional[str] = None


@dataclass
class SecurityReport:
    """Comprehensive security validation report"""
    timestamp: datetime
    overall_status: str
    security_score: float
    total_tests: int
    passed_tests: int
    failed_tests: int
    critical_issues: int
    high_issues: int
    medium_issues: int
    low_issues: int
    test_results: List[SecurityTestResult]
    compliance_status: Dict[str, bool]
    recommendations: List[str]


class SecurityValidator:
    """
    Comprehensive security validation system for the crypto trading bot.
    
    Validates all security implementations against 2025 enterprise standards.
    """

    def __init__(self):
        """Initialize security validator"""
        self.results: List[SecurityTestResult] = []
        self.start_time = datetime.utcnow()

        # Set up secure logging for validation
        self.logger = setup_secure_logging("security_validator", logging.INFO)

        print("🔒 Crypto Trading Bot - Security Validation Suite 2025")
        print("=" * 60)
        print(f"Validation started at: {self.start_time.isoformat()}")
        print("")

    def add_result(
        self,
        test_name: str,
        passed: bool,
        severity: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        remediation: Optional[str] = None
    ):
        """Add a test result"""
        result = SecurityTestResult(
            test_name=test_name,
            passed=passed,
            severity=severity,
            message=message,
            details=details,
            remediation=remediation
        )
        self.results.append(result)

        # Print result
        status = "✅ PASS" if passed else "❌ FAIL"
        severity_icon = {
            "CRITICAL": "🔴",
            "HIGH": "🟠",
            "MEDIUM": "🟡",
            "LOW": "🔵",
            "INFO": "ℹ️"
        }.get(severity, "")

        print(f"{status} {severity_icon} [{severity}] {test_name}")
        print(f"    {message}")
        if details:
            for key, value in details.items():
                print(f"    📊 {key}: {value}")
        if not passed and remediation:
            print(f"    🔧 Remediation: {remediation}")
        print()

    def validate_ssl_tls_configuration(self):
        """Validate SSL/TLS configuration"""
        print("🔐 Validating SSL/TLS Configuration")
        print("-" * 40)

        if not SECURITY_MODULES_AVAILABLE:
            self.add_result(
                "SSL/TLS Module Import",
                False,
                "CRITICAL",
                "Security modules not available for testing",
                remediation="Ensure all dependencies are installed"
            )
            return

        # Test secure transport manager
        try:
            transport = SecureSSLContextManager()
            context = transport.create_secure_context(purpose="client")

            # Validate TLS version requirements
            min_version = context.minimum_version
            max_version = context.maximum_version

            tls_13_enforced = (
                min_version == ssl.TLSVersion.TLSv1_3 and
                max_version == ssl.TLSVersion.TLSv1_3
            )

            self.add_result(
                "TLS 1.3 Enforcement",
                tls_13_enforced,
                "CRITICAL" if not tls_13_enforced else "INFO",
                f"TLS version range: {min_version.name} - {max_version.name}",
                details={"min_version": min_version.name, "max_version": max_version.name},
                remediation="Update SSL context to enforce TLS 1.3+ only" if not tls_13_enforced else None
            )

            # Validate certificate verification
            cert_verification = (
                context.verify_mode == ssl.CERT_REQUIRED and
                context.check_hostname == True
            )

            self.add_result(
                "Certificate Verification",
                cert_verification,
                "CRITICAL" if not cert_verification else "INFO",
                f"Verify mode: {context.verify_mode}, Hostname check: {context.check_hostname}",
                details={
                    "verify_mode": str(context.verify_mode),
                    "check_hostname": context.check_hostname
                },
                remediation="Enable strict certificate verification" if not cert_verification else None
            )

            # Test live TLS connections
            test_hosts = ["api.kraken.com", "ws.kraken.com"]
            for host in test_hosts:
                try:
                    result = validate_tls_connection(host, 443)
                    is_secure = result.get('connection_secure', False)
                    tls_version = result.get('tls_version', 'Unknown')

                    self.add_result(
                        f"Live TLS Test - {host}",
                        is_secure,
                        "HIGH" if not is_secure else "INFO",
                        f"TLS {tls_version}, Secure: {is_secure}",
                        details=result,
                        remediation="Check network connectivity and certificate validity" if not is_secure else None
                    )
                except Exception as e:
                    self.add_result(
                        f"Live TLS Test - {host}",
                        False,
                        "MEDIUM",
                        f"Connection test failed: {str(e)}",
                        remediation="Verify network connectivity"
                    )

        except Exception as e:
            self.add_result(
                "SSL/TLS Context Creation",
                False,
                "CRITICAL",
                f"Failed to create secure SSL context: {str(e)}",
                remediation="Check SSL/TLS implementation and dependencies"
            )

    def validate_credential_management(self):
        """Validate credential management security"""
        print("🔑 Validating Credential Management")
        print("-" * 40)

        if not SECURITY_MODULES_AVAILABLE:
            self.add_result(
                "Credential Management Module",
                False,
                "CRITICAL",
                "Credential management modules not available",
                remediation="Install required cryptographic dependencies"
            )
            return

        # Test secure credential storage
        try:
            storage = SecureCredentialStorage()
            status = storage.get_security_status()

            # Validate encryption algorithm
            encryption_secure = status.get('encryption_algorithm') == 'AES-256-GCM'
            self.add_result(
                "Encryption Algorithm",
                encryption_secure,
                "CRITICAL" if not encryption_secure else "INFO",
                f"Using {status.get('encryption_algorithm', 'Unknown')} encryption",
                details={"algorithm": status.get('encryption_algorithm')},
                remediation="Upgrade to AES-256-GCM encryption" if not encryption_secure else None
            )

            # Validate key derivation
            kdf_iterations = status.get('key_derivation_iterations', 0)
            kdf_secure = kdf_iterations >= 100000
            self.add_result(
                "Key Derivation Strength",
                kdf_secure,
                "HIGH" if not kdf_secure else "INFO",
                f"Using {kdf_iterations:,} PBKDF2 iterations",
                details={"iterations": kdf_iterations},
                remediation="Increase PBKDF2 iterations to 100,000+" if not kdf_secure else None
            )

            # Test credential storage and retrieval
            test_api_key = "test_key_" + os.urandom(16).hex()
            test_secret = "test_secret_" + os.urandom(32).hex()

            storage_success = storage.store_credential('security_test', test_api_key, test_secret)
            self.add_result(
                "Credential Storage",
                storage_success,
                "HIGH" if not storage_success else "INFO",
                "Credential storage functionality",
                remediation="Fix credential storage implementation" if not storage_success else None
            )

            if storage_success:
                retrieved = storage.retrieve_credential('security_test')
                retrieval_success = (
                    retrieved is not None and
                    retrieved[0] == test_api_key and
                    retrieved[1] == test_secret
                )
                self.add_result(
                    "Credential Retrieval",
                    retrieval_success,
                    "HIGH" if not retrieval_success else "INFO",
                    "Credential retrieval functionality",
                    remediation="Fix credential retrieval implementation" if not retrieval_success else None
                )

            # Test SecureString implementation
            try:
                secure_str = SecureString("test_sensitive_data")
                retrieved_value = secure_str.get_value()
                secure_string_works = retrieved_value == "test_sensitive_data"

                self.add_result(
                    "SecureString Implementation",
                    secure_string_works,
                    "MEDIUM" if not secure_string_works else "INFO",
                    "SecureString memory protection",
                    remediation="Fix SecureString implementation" if not secure_string_works else None
                )
            except Exception as e:
                self.add_result(
                    "SecureString Implementation",
                    False,
                    "MEDIUM",
                    f"SecureString test failed: {str(e)}",
                    remediation="Review SecureString implementation"
                )

        except Exception as e:
            self.add_result(
                "Credential Management System",
                False,
                "CRITICAL",
                f"Credential management test failed: {str(e)}",
                remediation="Review and fix credential management implementation"
            )

    def validate_logging_security(self):
        """Validate logging security and credential sanitization"""
        print("📝 Validating Logging Security")
        print("-" * 40)

        if not SECURITY_MODULES_AVAILABLE:
            self.add_result(
                "Secure Logging Module",
                False,
                "HIGH",
                "Secure logging modules not available",
                remediation="Install secure logging dependencies"
            )
            return

        # Test secure log formatter
        try:
            formatter = SecureLogFormatter()

            # Test credential sanitization
            test_messages = [
                ("API Key exposure", "API_KEY=sk_test_1234567890abcdef1234567890abcdef12345678", True),
                ("Bearer token exposure", "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", True),
                ("Private key exposure", "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQ", True),
                ("Normal message", "Successfully connected to exchange", False),
                ("Email in logs", "User test@example.com logged in", False),  # Should be masked if enabled
            ]

            sanitization_working = True
            sanitized_count = 0

            for test_name, message, should_sanitize in test_messages:
                # Create a mock log record
                import logging
                record = logging.LogRecord(
                    name="test",
                    level=logging.INFO,
                    pathname="",
                    lineno=0,
                    msg=message,
                    args=(),
                    exc_info=None
                )

                sanitized_message, detected_patterns = formatter._sanitize_message(message)
                was_sanitized = len(detected_patterns) > 0

                if should_sanitize and not was_sanitized:
                    sanitization_working = False
                    self.add_result(
                        f"Credential Sanitization - {test_name}",
                        False,
                        "HIGH",
                        f"Failed to sanitize: {message[:50]}...",
                        remediation="Update sanitization patterns"
                    )
                elif was_sanitized:
                    sanitized_count += 1
                    self.add_result(
                        f"Credential Sanitization - {test_name}",
                        True,
                        "INFO",
                        f"Successfully sanitized {len(detected_patterns)} pattern(s)",
                        details={"patterns": detected_patterns}
                    )

            # Overall sanitization assessment
            self.add_result(
                "Overall Log Sanitization",
                sanitization_working,
                "HIGH" if not sanitization_working else "INFO",
                f"Sanitized {sanitized_count} test messages",
                details={"sanitized_messages": sanitized_count},
                remediation="Review and enhance sanitization patterns" if not sanitization_working else None
            )

        except Exception as e:
            self.add_result(
                "Logging Security System",
                False,
                "HIGH",
                f"Logging security test failed: {str(e)}",
                remediation="Review secure logging implementation"
            )

    def validate_websocket_security(self):
        """Validate WebSocket security configuration"""
        print("🌐 Validating WebSocket Security")
        print("-" * 40)

        # Check WebSocket V2 manager configuration
        try:
            # This is a static analysis since we can't easily test live connections
            websocket_file = current_dir / "src" / "websocket" / "websocket_v2_manager.py"
            if websocket_file.exists():
                content = websocket_file.read_text()

                # Check for secure SSL context usage
                uses_secure_transport = "create_secure_websocket_ssl_context" in content
                self.add_result(
                    "WebSocket Secure Transport",
                    uses_secure_transport,
                    "HIGH" if not uses_secure_transport else "INFO",
                    "WebSocket uses secure transport implementation",
                    remediation="Update WebSocket to use secure transport" if not uses_secure_transport else None
                )

                # Check for disabled certificate verification (security vulnerability)
                has_cert_disabled = "ssl.CERT_NONE" in content or "verify_mode = ssl.CERT_NONE" in content
                self.add_result(
                    "WebSocket Certificate Verification",
                    not has_cert_disabled,
                    "CRITICAL" if has_cert_disabled else "INFO",
                    "Certificate verification status in WebSocket",
                    remediation="Remove certificate verification bypasses" if has_cert_disabled else None
                )

                # Check for hostname verification
                has_hostname_check = "check_hostname = True" in content or "check_hostname=True" in content
                hostname_disabled = "check_hostname = False" in content or "check_hostname=False" in content

                self.add_result(
                    "WebSocket Hostname Verification",
                    has_hostname_check and not hostname_disabled,
                    "HIGH" if hostname_disabled else "INFO",
                    "Hostname verification in WebSocket connections",
                    remediation="Enable hostname verification for WebSocket" if hostname_disabled else None
                )

            else:
                self.add_result(
                    "WebSocket Configuration File",
                    False,
                    "MEDIUM",
                    "WebSocket V2 manager file not found",
                    remediation="Verify WebSocket implementation files exist"
                )

        except Exception as e:
            self.add_result(
                "WebSocket Security Analysis",
                False,
                "MEDIUM",
                f"WebSocket security analysis failed: {str(e)}",
                remediation="Review WebSocket implementation"
            )

    def scan_for_hardcoded_secrets(self):
        """Scan codebase for hardcoded secrets and credentials"""
        print("🔍 Scanning for Hardcoded Secrets")
        print("-" * 40)

        try:
            # Patterns for detecting potential secrets
            secret_patterns = [
                (r'api_key\s*=\s*["\'][^"\']{20,}["\']', "Hardcoded API Key"),
                (r'secret\s*=\s*["\'][^"\']{20,}["\']', "Hardcoded Secret"),
                (r'password\s*=\s*["\'][^"\']{8,}["\']', "Hardcoded Password"),
                (r'token\s*=\s*["\'][^"\']{20,}["\']', "Hardcoded Token"),
                (r'["\'][A-Za-z0-9+/]{40,}={0,2}["\']', "Potential Base64 Secret"),
                (r'sk_[a-zA-Z0-9]{20,}', "API Key Pattern"),
                (r'-----BEGIN[A-Z\s]+PRIVATE KEY-----', "Private Key"),
            ]

            src_dir = current_dir / "src"
            issues_found = []

            if src_dir.exists():
                for py_file in src_dir.rglob("*.py"):
                    try:
                        content = py_file.read_text(encoding='utf-8')
                        for pattern, description in secret_patterns:
                            matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
                            for match in matches:
                                # Skip test files and comments
                                line = content[:match.start()].count('\n') + 1
                                context = content.split('\n')[line-1] if line <= len(content.split('\n')) else ""

                                # Skip if it's in a comment or test file
                                if not (context.strip().startswith('#') or 'test' in py_file.name.lower()):
                                    issues_found.append({
                                        'file': str(py_file.relative_to(current_dir)),
                                        'line': line,
                                        'type': description,
                                        'context': context.strip()[:100]
                                    })
                    except Exception:
                        # Continue with other files if one fails
                        continue

            secrets_found = len(issues_found) > 0
            self.add_result(
                "Hardcoded Secrets Scan",
                not secrets_found,
                "CRITICAL" if secrets_found else "INFO",
                f"Found {len(issues_found)} potential hardcoded secret(s)",
                details={"issues": issues_found[:5]},  # Show first 5
                remediation="Remove hardcoded secrets and use environment variables or secure storage" if secrets_found else None
            )

        except Exception as e:
            self.add_result(
                "Secret Scanning",
                False,
                "MEDIUM",
                f"Secret scanning failed: {str(e)}",
                remediation="Manually review code for hardcoded secrets"
            )

    def validate_dependency_security(self):
        """Validate security of dependencies"""
        print("📦 Validating Dependency Security")
        print("-" * 40)

        # Check for requirements.txt
        requirements_file = current_dir / "requirements.txt"
        if requirements_file.exists():
            try:
                content = requirements_file.read_text()

                # Check for pinned versions
                lines = [line.strip() for line in content.split('\n') if line.strip() and not line.startswith('#')]
                pinned_count = sum(1 for line in lines if '==' in line or '>=' in line)
                total_deps = len(lines)

                pinning_ratio = pinned_count / max(total_deps, 1)
                good_pinning = pinning_ratio >= 0.8

                self.add_result(
                    "Dependency Version Pinning",
                    good_pinning,
                    "MEDIUM" if not good_pinning else "INFO",
                    f"{pinned_count}/{total_deps} dependencies have pinned versions",
                    details={
                        "pinned_dependencies": pinned_count,
                        "total_dependencies": total_deps,
                        "pinning_ratio": f"{pinning_ratio:.2%}"
                    },
                    remediation="Pin dependency versions to prevent supply chain attacks" if not good_pinning else None
                )

                # Check for known vulnerable packages (simplified check)
                vulnerable_packages = ['urllib3<1.26.5', 'requests<2.25.0', 'cryptography<3.0']
                vulnerabilities = []
                for line in lines:
                    for vuln in vulnerable_packages:
                        if vuln.split('<')[0] in line:
                            vulnerabilities.append(line)

                self.add_result(
                    "Known Vulnerable Dependencies",
                    len(vulnerabilities) == 0,
                    "HIGH" if len(vulnerabilities) > 0 else "INFO",
                    f"Found {len(vulnerabilities)} potentially vulnerable dependencies",
                    details={"vulnerable": vulnerabilities},
                    remediation="Update vulnerable dependencies to latest secure versions" if vulnerabilities else None
                )

            except Exception as e:
                self.add_result(
                    "Requirements Analysis",
                    False,
                    "LOW",
                    f"Failed to analyze requirements.txt: {str(e)}"
                )
        else:
            self.add_result(
                "Requirements File",
                False,
                "LOW",
                "No requirements.txt file found",
                remediation="Create requirements.txt with pinned dependency versions"
            )

    def generate_compliance_report(self) -> SecurityReport:
        """Generate comprehensive security compliance report"""
        end_time = datetime.utcnow()

        # Calculate statistics
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.passed)
        failed_tests = total_tests - passed_tests

        # Count by severity
        critical_issues = sum(1 for r in self.results if not r.passed and r.severity == "CRITICAL")
        high_issues = sum(1 for r in self.results if not r.passed and r.severity == "HIGH")
        medium_issues = sum(1 for r in self.results if not r.passed and r.severity == "MEDIUM")
        low_issues = sum(1 for r in self.results if not r.passed and r.severity == "LOW")

        # Calculate security score (weighted by severity)
        severity_weights = {"CRITICAL": 10, "HIGH": 5, "MEDIUM": 2, "LOW": 1, "INFO": 0}
        max_score = sum(severity_weights.get(r.severity, 0) for r in self.results)
        achieved_score = sum(severity_weights.get(r.severity, 0) for r in self.results if r.passed)
        security_score = (achieved_score / max(max_score, 1)) * 100

        # Determine overall status
        if critical_issues > 0:
            overall_status = "CRITICAL - Immediate Action Required"
        elif high_issues > 0:
            overall_status = "HIGH RISK - Address Issues Soon"
        elif medium_issues > 0:
            overall_status = "MEDIUM RISK - Plan Remediation"
        elif low_issues > 0:
            overall_status = "LOW RISK - Minor Issues"
        else:
            overall_status = "SECURE - All Tests Passed"

        # Compliance status
        compliance_status = {
            "TLS_1_3_Enforcement": not any(r for r in self.results if "TLS 1.3" in r.test_name and not r.passed),
            "Certificate_Validation": not any(r for r in self.results if "Certificate Verification" in r.test_name and not r.passed),
            "Credential_Encryption": not any(r for r in self.results if "Encryption Algorithm" in r.test_name and not r.passed),
            "Log_Sanitization": not any(r for r in self.results if "Log Sanitization" in r.test_name and not r.passed),
            "No_Hardcoded_Secrets": not any(r for r in self.results if "Hardcoded Secrets" in r.test_name and not r.passed),
            "Secure_Dependencies": not any(r for r in self.results if "Vulnerable Dependencies" in r.test_name and not r.passed),
        }

        # Generate recommendations
        recommendations = []
        if critical_issues > 0:
            recommendations.append("🔴 URGENT: Address all CRITICAL security issues immediately")
        if high_issues > 0:
            recommendations.append("🟠 HIGH: Plan to fix HIGH severity issues within 48 hours")
        if medium_issues > 0:
            recommendations.append("🟡 MEDIUM: Schedule remediation for MEDIUM severity issues")

        recommendations.extend([
            "🔒 Implement continuous security monitoring",
            "📋 Schedule regular security audits (monthly)",
            "🔄 Set up automated dependency vulnerability scanning",
            "📚 Provide security training for development team",
            "🛡️ Consider implementing additional security controls (WAF, DDoS protection)",
        ])

        return SecurityReport(
            timestamp=end_time,
            overall_status=overall_status,
            security_score=round(security_score, 2),
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            critical_issues=critical_issues,
            high_issues=high_issues,
            medium_issues=medium_issues,
            low_issues=low_issues,
            test_results=self.results,
            compliance_status=compliance_status,
            recommendations=recommendations
        )

    def run_full_validation(self) -> SecurityReport:
        """Run complete security validation suite"""
        print("🚀 Starting Comprehensive Security Validation")
        print("=" * 60)
        print()

        # Run all validation tests
        self.validate_ssl_tls_configuration()
        self.validate_credential_management()
        self.validate_logging_security()
        self.validate_websocket_security()
        self.scan_for_hardcoded_secrets()
        self.validate_dependency_security()

        # Generate report
        report = self.generate_compliance_report()

        # Print summary
        print("🎯 Security Validation Summary")
        print("=" * 60)
        print(f"Overall Status: {report.overall_status}")
        print(f"Security Score: {report.security_score}%")
        print(f"Tests: {report.passed_tests}/{report.total_tests} passed")
        print()
        print("Issue Breakdown:")
        print(f"  🔴 Critical: {report.critical_issues}")
        print(f"  🟠 High:     {report.high_issues}")
        print(f"  🟡 Medium:   {report.medium_issues}")
        print(f"  🔵 Low:      {report.low_issues}")
        print()

        # Compliance status
        print("📋 Compliance Status:")
        for requirement, status in report.compliance_status.items():
            status_icon = "✅" if status else "❌"
            print(f"  {status_icon} {requirement.replace('_', ' ')}")
        print()

        # Recommendations
        if report.recommendations:
            print("🔧 Recommendations:")
            for i, rec in enumerate(report.recommendations[:5], 1):
                print(f"  {i}. {rec}")
            print()

        print(f"Validation completed in {(report.timestamp - self.start_time).total_seconds():.2f} seconds")

        return report


def main():
    """Main entry point for security validation"""
    import argparse

    parser = argparse.ArgumentParser(description="Crypto Trading Bot Security Validation Suite")
    parser.add_argument("--detailed", action="store_true", help="Show detailed test results")
    parser.add_argument("--export-report", action="store_true", help="Export JSON report")
    parser.add_argument("--output", help="Output file for JSON report")

    args = parser.parse_args()

    # Run validation
    validator = SecurityValidator()
    report = validator.run_full_validation()

    # Export report if requested
    if args.export_report:
        output_file = args.output or f"security_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        # Convert report to JSON-serializable format
        report_dict = asdict(report)
        report_dict['timestamp'] = report.timestamp.isoformat()
        report_dict['test_results'] = [asdict(r) for r in report.test_results]

        with open(output_file, 'w') as f:
            json.dump(report_dict, f, indent=2)

        print(f"📄 Security report exported to: {output_file}")

    # Show detailed results if requested
    if args.detailed:
        print("\n📊 Detailed Test Results")
        print("=" * 60)
        for result in report.test_results:
            status = "PASS" if result.passed else "FAIL"
            print(f"[{result.severity}] {result.test_name}: {status}")
            print(f"  Message: {result.message}")
            if result.details:
                print(f"  Details: {result.details}")
            if result.remediation:
                print(f"  Remediation: {result.remediation}")
            print()

    # Exit with appropriate code
    if report.critical_issues > 0:
        sys.exit(2)  # Critical issues
    elif report.high_issues > 0:
        sys.exit(1)  # High issues
    else:
        sys.exit(0)  # Success


if __name__ == "__main__":
    main()
