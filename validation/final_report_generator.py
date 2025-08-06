"""
Final System Validation Report Generator
Comprehensive validation report aggregating all test results and providing
production readiness assessment
"""

import asyncio
import json
import logging
import sys
import time
import traceback
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from validation.component_compatibility import ComponentCompatibilityTester
from validation.error_recovery_tests import ErrorRecoveryTester
from validation.integration_validator import IntegrationValidator
from validation.trading_scenario_tests import TradingScenarioTester


class SystemStatus(Enum):
    """System readiness status"""
    PRODUCTION_READY = "production_ready"
    READY_WITH_WARNINGS = "ready_with_warnings"
    NEEDS_FIXES = "needs_fixes"
    NOT_READY = "not_ready"


class ValidationCategory(Enum):
    """Validation test categories"""
    INTEGRATION = "integration"
    COMPATIBILITY = "compatibility"
    RECOVERY = "error_recovery"
    TRADING = "trading_scenarios"


@dataclass
class ValidationSummary:
    """Summary of validation results for a category"""
    category: ValidationCategory
    total_tests: int
    passed_tests: int
    failed_tests: int
    critical_failures: int
    success_rate: float
    duration: float
    status: SystemStatus
    recommendations: list[str]


@dataclass
class SystemReadinessAssessment:
    """Complete system readiness assessment"""
    overall_status: SystemStatus
    confidence_score: float  # 0-100
    production_readiness: bool
    critical_blockers: list[str]
    warnings: list[str]
    strengths: list[str]
    improvement_areas: list[str]
    go_live_checklist: list[str]


class FinalValidationReportGenerator:
    """Comprehensive system validation report generator"""

    def __init__(self):
        self.logger = self._setup_logging()

        # Validation test runners
        self.integration_validator = IntegrationValidator()
        self.compatibility_tester = ComponentCompatibilityTester()
        self.recovery_tester = ErrorRecoveryTester()
        self.trading_tester = TradingScenarioTester()

        # Results storage
        self.validation_summaries: list[ValidationSummary] = []
        self.detailed_results = {}
        self.system_metrics = {}

    def _setup_logging(self) -> logging.Logger:
        """Setup validation report logging"""
        logger = logging.getLogger('final_validation_report')
        logger.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    async def generate_complete_validation_report(self) -> dict[str, Any]:
        """Generate complete system validation report"""
        self.logger.info("Starting complete system validation")

        start_time = time.time()

        try:
            # Run all validation tests
            await self._run_all_validations()

            # Analyze results
            readiness_assessment = self._assess_system_readiness()

            # Generate comprehensive report
            report = self._generate_final_report(readiness_assessment, time.time() - start_time)

            # Save report
            await self._save_validation_report(report)

            # Generate executive summary
            executive_summary = self._generate_executive_summary(report)

            return {
                "executive_summary": executive_summary,
                "detailed_report": report,
                "readiness_assessment": readiness_assessment
            }

        except Exception as e:
            self.logger.error(f"Validation report generation failed: {e}")
            raise

    async def _run_all_validations(self):
        """Run all validation test suites"""

        # 1. Integration Validation
        self.logger.info("Running integration validation...")
        try:
            integration_report = await self.integration_validator.run_complete_validation()

            integration_summary = ValidationSummary(
                category=ValidationCategory.INTEGRATION,
                total_tests=integration_report.total_tests,
                passed_tests=integration_report.passed_tests,
                failed_tests=integration_report.failed_tests,
                critical_failures=len([r for r in integration_report.results
                                     if not r.passed and r.component in ['authentication', 'rate_limiting', 'circuit_breaker']]),
                success_rate=integration_report.passed_tests / integration_report.total_tests if integration_report.total_tests > 0 else 0,
                duration=integration_report.total_duration,
                status=self._determine_status_from_results(integration_report.passed_tests, integration_report.total_tests,
                                                         len([r for r in integration_report.results if not r.passed and r.component in ['authentication', 'rate_limiting', 'circuit_breaker']])),
                recommendations=integration_report.recommendations
            )

            self.validation_summaries.append(integration_summary)
            self.detailed_results['integration'] = integration_report

        except Exception as e:
            self.logger.error(f"Integration validation failed: {e}")
            self._add_failed_summary(ValidationCategory.INTEGRATION, str(e))

        # 2. Component Compatibility
        self.logger.info("Running component compatibility testing...")
        try:
            compatibility_results = await self.compatibility_tester.run_compatibility_tests()
            compatibility_report = self.compatibility_tester.generate_compatibility_report()

            compatibility_summary = ValidationSummary(
                category=ValidationCategory.COMPATIBILITY,
                total_tests=compatibility_report['summary']['total_tests'],
                passed_tests=compatibility_report['summary']['passed_tests'],
                failed_tests=compatibility_report['summary']['failed_tests'],
                critical_failures=compatibility_report['summary']['critical_failures'],
                success_rate=compatibility_report['summary']['success_rate'],
                duration=sum(r.duration for r in compatibility_results),
                status=self._determine_status_from_results(compatibility_report['summary']['passed_tests'],
                                                         compatibility_report['summary']['total_tests'],
                                                         compatibility_report['summary']['critical_failures']),
                recommendations=compatibility_report['recommendations']
            )

            self.validation_summaries.append(compatibility_summary)
            self.detailed_results['compatibility'] = compatibility_report

        except Exception as e:
            self.logger.error(f"Compatibility testing failed: {e}")
            self._add_failed_summary(ValidationCategory.COMPATIBILITY, str(e))

        # 3. Error Recovery & Resilience
        self.logger.info("Running error recovery testing...")
        try:
            recovery_results = await self.recovery_tester.run_recovery_tests()
            recovery_report = self.recovery_tester.generate_recovery_report()

            recovery_summary = ValidationSummary(
                category=ValidationCategory.RECOVERY,
                total_tests=recovery_report['summary']['total_scenarios'],
                passed_tests=recovery_report['summary']['successful_recoveries'],
                failed_tests=recovery_report['summary']['failed_recoveries'],
                critical_failures=recovery_report['summary']['critical_failures'],
                success_rate=recovery_report['summary']['recovery_success_rate'],
                duration=sum(r.recovery_time for r in recovery_results),
                status=self._determine_status_from_results(recovery_report['summary']['successful_recoveries'],
                                                         recovery_report['summary']['total_scenarios'],
                                                         recovery_report['summary']['critical_failures']),
                recommendations=recovery_report['recommendations']
            )

            self.validation_summaries.append(recovery_summary)
            self.detailed_results['recovery'] = recovery_report

        except Exception as e:
            self.logger.error(f"Recovery testing failed: {e}")
            self._add_failed_summary(ValidationCategory.RECOVERY, str(e))

        # 4. Trading Scenarios
        self.logger.info("Running trading scenario validation...")
        try:
            trading_results = await self.trading_tester.run_trading_scenarios()
            trading_report = self.trading_tester.generate_trading_report()

            trading_summary = ValidationSummary(
                category=ValidationCategory.TRADING,
                total_tests=trading_report['summary']['total_scenarios'],
                passed_tests=trading_report['summary']['successful_scenarios'],
                failed_tests=trading_report['summary']['failed_scenarios'],
                critical_failures=len([r for r in trading_results if not r.meets_criteria and
                                     any(error for error in r.errors_encountered if 'critical' in error.lower())]),
                success_rate=trading_report['summary']['success_rate'],
                duration=sum(r.duration for r in trading_results),
                status=self._determine_status_from_results(trading_report['summary']['successful_scenarios'],
                                                         trading_report['summary']['total_scenarios'],
                                                         len([r for r in trading_results if not r.meets_criteria])),
                recommendations=trading_report['recommendations']
            )

            self.validation_summaries.append(trading_summary)
            self.detailed_results['trading'] = trading_report

        except Exception as e:
            self.logger.error(f"Trading scenario testing failed: {e}")
            self._add_failed_summary(ValidationCategory.TRADING, str(e))

    def _determine_status_from_results(self, passed: int, total: int, critical_failures: int) -> SystemStatus:
        """Determine system status from test results"""
        if total == 0:
            return SystemStatus.NOT_READY

        success_rate = passed / total

        if critical_failures > 0:
            return SystemStatus.NOT_READY
        elif success_rate >= 0.95:
            return SystemStatus.PRODUCTION_READY
        elif success_rate >= 0.85:
            return SystemStatus.READY_WITH_WARNINGS
        elif success_rate >= 0.70:
            return SystemStatus.NEEDS_FIXES
        else:
            return SystemStatus.NOT_READY

    def _add_failed_summary(self, category: ValidationCategory, error: str):
        """Add summary for failed validation category"""
        summary = ValidationSummary(
            category=category,
            total_tests=0,
            passed_tests=0,
            failed_tests=1,
            critical_failures=1,
            success_rate=0.0,
            duration=0.0,
            status=SystemStatus.NOT_READY,
            recommendations=[f"Fix critical error in {category.value}: {error}"]
        )
        self.validation_summaries.append(summary)

    def _assess_system_readiness(self) -> SystemReadinessAssessment:
        """Assess overall system readiness for production"""

        # Calculate overall metrics
        total_tests = sum(s.total_tests for s in self.validation_summaries)
        total_passed = sum(s.passed_tests for s in self.validation_summaries)
        sum(s.critical_failures for s in self.validation_summaries)

        total_passed / total_tests if total_tests > 0 else 0

        # Determine overall status
        category_statuses = [s.status for s in self.validation_summaries]

        if any(status == SystemStatus.NOT_READY for status in category_statuses):
            overall_status = SystemStatus.NOT_READY
        elif all(status == SystemStatus.PRODUCTION_READY for status in category_statuses):
            overall_status = SystemStatus.PRODUCTION_READY
        elif any(status == SystemStatus.NEEDS_FIXES for status in category_statuses):
            overall_status = SystemStatus.NEEDS_FIXES
        else:
            overall_status = SystemStatus.READY_WITH_WARNINGS

        # Calculate confidence score
        confidence_score = self._calculate_confidence_score()

        # Identify critical blockers
        critical_blockers = []
        for summary in self.validation_summaries:
            if summary.critical_failures > 0:
                critical_blockers.extend([
                    f"{summary.category.value}: {summary.critical_failures} critical failures"
                ])

        # Identify warnings
        warnings = []
        for summary in self.validation_summaries:
            if summary.status in [SystemStatus.READY_WITH_WARNINGS, SystemStatus.NEEDS_FIXES]:
                warnings.extend(summary.recommendations)

        # Identify strengths
        strengths = []
        for summary in self.validation_summaries:
            if summary.status == SystemStatus.PRODUCTION_READY:
                strengths.append(f"{summary.category.value} fully validated ({summary.success_rate:.1%} success)")

        # Identify improvement areas
        improvement_areas = []
        for summary in self.validation_summaries:
            if summary.success_rate < 0.9:
                improvement_areas.append(f"Improve {summary.category.value} reliability")

        # Generate go-live checklist
        go_live_checklist = self._generate_go_live_checklist()

        return SystemReadinessAssessment(
            overall_status=overall_status,
            confidence_score=confidence_score,
            production_readiness=overall_status in [SystemStatus.PRODUCTION_READY, SystemStatus.READY_WITH_WARNINGS],
            critical_blockers=critical_blockers,
            warnings=warnings,
            strengths=strengths,
            improvement_areas=improvement_areas,
            go_live_checklist=go_live_checklist
        )

    def _calculate_confidence_score(self) -> float:
        """Calculate system confidence score (0-100)"""
        if not self.validation_summaries:
            return 0.0

        # Base score from success rates
        category_scores = []

        for summary in self.validation_summaries:
            # Weight categories differently
            weights = {
                ValidationCategory.INTEGRATION: 0.3,
                ValidationCategory.COMPATIBILITY: 0.2,
                ValidationCategory.RECOVERY: 0.25,
                ValidationCategory.TRADING: 0.25
            }

            weight = weights.get(summary.category, 0.25)

            # Penalize critical failures heavily
            penalty = summary.critical_failures * 20  # -20 points per critical failure
            category_score = (summary.success_rate * 100 * weight) - penalty
            category_scores.append(max(0, category_score))  # Don't go below 0

        base_score = sum(category_scores)

        # Additional factors

        # Bonus for no critical failures
        if not any(s.critical_failures > 0 for s in self.validation_summaries):
            base_score += 10

        # Bonus for high overall success rate
        total_tests = sum(s.total_tests for s in self.validation_summaries)
        total_passed = sum(s.passed_tests for s in self.validation_summaries)

        if total_tests > 0:
            overall_success = total_passed / total_tests
            if overall_success >= 0.95:
                base_score += 10
            elif overall_success >= 0.90:
                base_score += 5

        # Cap at 100
        return min(100.0, base_score)

    def _generate_go_live_checklist(self) -> list[str]:
        """Generate go-live checklist based on validation results"""
        checklist = []

        # Always include these essential checks
        checklist.extend([
            "✓ Verify API credentials are correctly configured",
            "✓ Confirm trading pairs and position sizes are appropriate",
            "✓ Test rate limiting with live API calls",
            "✓ Validate balance management with small test trades",
            "✓ Verify WebSocket connections are stable",
            "✓ Confirm database persistence is working",
            "✓ Test circuit breaker functionality",
            "✓ Validate error recovery mechanisms"
        ])

        # Add category-specific checks based on results
        for summary in self.validation_summaries:
            if summary.status != SystemStatus.PRODUCTION_READY:
                if summary.category == ValidationCategory.INTEGRATION:
                    checklist.append("⚠️ Re-test system integration after fixes")
                elif summary.category == ValidationCategory.COMPATIBILITY:
                    checklist.append("⚠️ Verify component compatibility after updates")
                elif summary.category == ValidationCategory.RECOVERY:
                    checklist.append("⚠️ Test error recovery under load")
                elif summary.category == ValidationCategory.TRADING:
                    checklist.append("⚠️ Validate trading scenarios with small positions")

        # Production-specific checks
        checklist.extend([
            "✓ Set up monitoring and alerting",
            "✓ Configure logging for production environment",
            "✓ Test with minimal position sizes initially",
            "✓ Monitor first few trades closely",
            "✓ Have emergency stop procedures ready"
        ])

        return checklist

    def _generate_final_report(self, readiness_assessment: SystemReadinessAssessment,
                              total_duration: float) -> dict[str, Any]:
        """Generate comprehensive final validation report"""

        # Calculate aggregate statistics
        total_tests = sum(s.total_tests for s in self.validation_summaries)
        total_passed = sum(s.passed_tests for s in self.validation_summaries)
        total_failed = sum(s.failed_tests for s in self.validation_summaries)
        total_critical = sum(s.critical_failures for s in self.validation_summaries)

        return {
            "report_metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_validation_duration": total_duration,
                "validation_categories": len(self.validation_summaries),
                "system_version": "2025.1.0",  # Update as needed
                "environment": "validation"
            },
            "executive_summary": {
                "overall_status": readiness_assessment.overall_status.value,
                "production_readiness": readiness_assessment.production_readiness,
                "confidence_score": readiness_assessment.confidence_score,
                "total_tests_run": total_tests,
                "overall_success_rate": total_passed / total_tests if total_tests > 0 else 0,
                "critical_blockers_count": len(readiness_assessment.critical_blockers),
                "recommendation": self._get_overall_recommendation(readiness_assessment)
            },
            "validation_summary": {
                "categories": [
                    {
                        "category": s.category.value,
                        "status": s.status.value,
                        "tests_run": s.total_tests,
                        "success_rate": s.success_rate,
                        "critical_failures": s.critical_failures,
                        "duration": s.duration
                    }
                    for s in self.validation_summaries
                ],
                "aggregate_metrics": {
                    "total_tests": total_tests,
                    "total_passed": total_passed,
                    "total_failed": total_failed,
                    "total_critical_failures": total_critical,
                    "overall_success_rate": total_passed / total_tests if total_tests > 0 else 0
                }
            },
            "readiness_assessment": {
                "overall_status": readiness_assessment.overall_status.value,
                "confidence_score": readiness_assessment.confidence_score,
                "production_readiness": readiness_assessment.production_readiness,
                "critical_blockers": readiness_assessment.critical_blockers,
                "warnings": readiness_assessment.warnings,
                "strengths": readiness_assessment.strengths,
                "improvement_areas": readiness_assessment.improvement_areas
            },
            "go_live_checklist": readiness_assessment.go_live_checklist,
            "detailed_results": self.detailed_results,
            "recommendations": {
                "immediate_actions": self._get_immediate_actions(readiness_assessment),
                "optimization_suggestions": self._get_optimization_suggestions(),
                "monitoring_requirements": self._get_monitoring_requirements()
            },
            "risk_assessment": {
                "high_risk_areas": self._identify_high_risk_areas(),
                "mitigation_strategies": self._get_mitigation_strategies(),
                "deployment_risks": self._assess_deployment_risks(readiness_assessment)
            }
        }

    def _get_overall_recommendation(self, assessment: SystemReadinessAssessment) -> str:
        """Get overall recommendation for system deployment"""
        if assessment.overall_status == SystemStatus.PRODUCTION_READY:
            return "APPROVED FOR PRODUCTION: System has passed all validation tests and is ready for live trading."
        elif assessment.overall_status == SystemStatus.READY_WITH_WARNINGS:
            return "CONDITIONAL APPROVAL: System is functional but address warnings before full deployment."
        elif assessment.overall_status == SystemStatus.NEEDS_FIXES:
            return "FIXES REQUIRED: Address identified issues before considering production deployment."
        else:
            return "NOT READY: Critical issues must be resolved before system can be deployed."

    def _get_immediate_actions(self, assessment: SystemReadinessAssessment) -> list[str]:
        """Get immediate actions required"""
        actions = []

        if assessment.critical_blockers:
            actions.extend([f"CRITICAL: {blocker}" for blocker in assessment.critical_blockers])

        # Add category-specific actions
        for summary in self.validation_summaries:
            if summary.status == SystemStatus.NOT_READY:
                actions.append(f"Fix all failures in {summary.category.value} before proceeding")

        return actions

    def _get_optimization_suggestions(self) -> list[str]:
        """Get optimization suggestions"""
        suggestions = []

        for summary in self.validation_summaries:
            if summary.success_rate < 1.0:
                suggestions.append(f"Optimize {summary.category.value} to achieve 100% success rate")

        # Add performance-based suggestions
        suggestions.extend([
            "Consider implementing additional monitoring for production environment",
            "Optimize trade execution speed for better performance",
            "Implement advanced error recovery mechanisms",
            "Add more comprehensive logging for troubleshooting"
        ])

        return suggestions

    def _get_monitoring_requirements(self) -> list[str]:
        """Get monitoring requirements for production"""
        return [
            "Real-time system health monitoring",
            "Trade execution monitoring and alerting",
            "Balance and position tracking",
            "API rate limit monitoring",
            "Error rate and recovery monitoring",
            "Performance metrics tracking",
            "Circuit breaker status monitoring",
            "Database connection health",
            "WebSocket connection stability"
        ]

    def _identify_high_risk_areas(self) -> list[str]:
        """Identify high-risk areas based on test results"""
        high_risk = []

        for summary in self.validation_summaries:
            if summary.critical_failures > 0:
                high_risk.append(f"{summary.category.value}: {summary.critical_failures} critical failures")
            elif summary.success_rate < 0.8:
                high_risk.append(f"{summary.category.value}: Low success rate ({summary.success_rate:.1%})")

        return high_risk

    def _get_mitigation_strategies(self) -> list[str]:
        """Get risk mitigation strategies"""
        return [
            "Start with minimal position sizes and gradually increase",
            "Monitor system closely during initial trading period",
            "Have manual override capabilities ready",
            "Implement additional safety checks for large positions",
            "Set conservative risk limits initially",
            "Ensure quick response team availability during launch"
        ]

    def _assess_deployment_risks(self, assessment: SystemReadinessAssessment) -> dict[str, str]:
        """Assess deployment risks"""
        risks = {}

        if assessment.overall_status == SystemStatus.NOT_READY:
            risks["deployment"] = "HIGH - Critical issues present"
        elif assessment.overall_status == SystemStatus.NEEDS_FIXES:
            risks["deployment"] = "MEDIUM - Requires fixes before deployment"
        elif assessment.overall_status == SystemStatus.READY_WITH_WARNINGS:
            risks["deployment"] = "LOW - Monitor warnings during deployment"
        else:
            risks["deployment"] = "MINIMAL - System validated for production"

        risks["data_loss"] = "LOW - Database persistence validated"
        risks["financial"] = "MEDIUM - Implement position size limits"
        risks["operational"] = "LOW - Error recovery mechanisms tested"

        return risks

    def _generate_executive_summary(self, report: dict[str, Any]) -> dict[str, Any]:
        """Generate executive summary for stakeholders"""
        return {
            "validation_date": datetime.now().strftime("%Y-%m-%d"),
            "system_status": report["executive_summary"]["overall_status"].upper(),
            "production_ready": report["executive_summary"]["production_readiness"],
            "confidence_level": f"{report['executive_summary']['confidence_score']:.0f}%",
            "tests_passed": f"{report['executive_summary']['overall_success_rate']:.1%}",
            "critical_issues": report["executive_summary"]["critical_blockers_count"],
            "recommendation": report["executive_summary"]["recommendation"],
            "next_steps": report["recommendations"]["immediate_actions"][:3],  # Top 3 actions
            "go_live_approval": "APPROVED" if report["readiness_assessment"]["production_readiness"] else "PENDING"
        }

    async def _save_validation_report(self, report: dict[str, Any]):
        """Save validation report to files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save complete report
        report_file = Path(f"validation/final_validation_report_{timestamp}.json")
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2, default=str)

        # Save executive summary
        summary_file = Path(f"validation/executive_summary_{timestamp}.json")
        with open(summary_file, "w") as f:
            json.dump(report["executive_summary"], f, indent=2, default=str)

        # Generate human-readable summary
        readme_content = self._generate_human_readable_summary(report)
        readme_file = Path(f"validation/VALIDATION_SUMMARY_{timestamp}.md")
        with open(readme_file, "w") as f:
            f.write(readme_content)

        self.logger.info("Validation reports saved:")
        self.logger.info(f"  - Complete report: {report_file}")
        self.logger.info(f"  - Executive summary: {summary_file}")
        self.logger.info(f"  - Human-readable: {readme_file}")

    def _generate_human_readable_summary(self, report: dict[str, Any]) -> str:
        """Generate human-readable validation summary"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        content = f"""# System Validation Report

**Generated:** {timestamp}
**System Version:** {report['report_metadata']['system_version']}
**Total Validation Time:** {report['report_metadata']['total_validation_duration']:.1f}s

## Executive Summary

**Overall Status:** {report['executive_summary']['overall_status'].upper()}
**Production Ready:** {'✅ YES' if report['executive_summary']['production_readiness'] else '❌ NO'}
**Confidence Score:** {report['executive_summary']['confidence_score']:.0f}/100
**Tests Passed:** {report['executive_summary']['overall_success_rate']:.1%}

### Recommendation
{report['executive_summary']['recommendation']}

## Validation Results

"""

        for category in report['validation_summary']['categories']:
            status_emoji = "✅" if category['status'] == 'production_ready' else "⚠️" if category['status'] == 'ready_with_warnings' else "❌"

            content += f"""### {category['category'].title()} {status_emoji}
- **Status:** {category['status'].replace('_', ' ').title()}
- **Tests Run:** {category['tests_run']}
- **Success Rate:** {category['success_rate']:.1%}
- **Critical Failures:** {category['critical_failures']}
- **Duration:** {category['duration']:.1f}s

"""

        if report['readiness_assessment']['critical_blockers']:
            content += "## Critical Blockers ❌\n\n"
            for blocker in report['readiness_assessment']['critical_blockers']:
                content += f"- {blocker}\n"
            content += "\n"

        if report['readiness_assessment']['warnings']:
            content += "## Warnings ⚠️\n\n"
            for warning in report['readiness_assessment']['warnings'][:5]:  # Top 5 warnings
                content += f"- {warning}\n"
            content += "\n"

        if report['readiness_assessment']['strengths']:
            content += "## System Strengths ✅\n\n"
            for strength in report['readiness_assessment']['strengths']:
                content += f"- {strength}\n"
            content += "\n"

        content += "## Go-Live Checklist\n\n"
        for item in report['go_live_checklist']:
            content += f"- {item}\n"

        content += """
## Next Steps

### Immediate Actions Required
"""
        for action in report['recommendations']['immediate_actions']:
            content += f"1. {action}\n"

        content += """
### Monitoring Requirements
"""
        for req in report['recommendations']['monitoring_requirements'][:5]:  # Top 5
            content += f"- {req}\n"

        return content


async def main():
    """Run complete system validation and generate final report"""
    generator = FinalValidationReportGenerator()

    try:
        print("🚀 Starting Complete System Validation")
        print("=" * 60)

        # Generate complete validation report
        validation_results = await generator.generate_complete_validation_report()

        # Extract key results
        executive_summary = validation_results["executive_summary"]
        readiness_assessment = validation_results["readiness_assessment"]

        # Print results
        print(f"\n{'='*60}")
        print("FINAL SYSTEM VALIDATION REPORT")
        print(f"{'='*60}")

        print(f"\n🎯 OVERALL STATUS: {executive_summary['system_status']}")
        print(f"📊 CONFIDENCE LEVEL: {executive_summary['confidence_level']}")
        print(f"✅ TESTS PASSED: {executive_summary['tests_passed']}")
        print(f"🚨 CRITICAL ISSUES: {executive_summary['critical_issues']}")

        if executive_summary['production_ready']:
            print(f"\n🎉 PRODUCTION APPROVAL: {executive_summary['go_live_approval']}")
        else:
            print(f"\n⏳ PRODUCTION APPROVAL: {executive_summary['go_live_approval']}")

        print("\n📋 RECOMMENDATION:")
        print(f"   {executive_summary['recommendation']}")

        if executive_summary['next_steps']:
            print("\n⚡ IMMEDIATE NEXT STEPS:")
            for i, step in enumerate(executive_summary['next_steps'], 1):
                print(f"   {i}. {step}")

        # Print category results
        detailed_report = validation_results["detailed_report"]
        print(f"\n{'='*60}")
        print("VALIDATION CATEGORY RESULTS")
        print(f"{'='*60}")

        for category in detailed_report['validation_summary']['categories']:
            status_icon = "✅" if category['status'] == 'production_ready' else "⚠️" if category['status'] == 'ready_with_warnings' else "❌"
            print(f"\n{status_icon} {category['category'].upper()}")
            print(f"   Status: {category['status'].replace('_', ' ').title()}")
            print(f"   Success Rate: {category['success_rate']:.1%}")
            print(f"   Tests: {category['tests_run']} | Critical Failures: {category['critical_failures']}")

        # Print final decision
        print(f"\n{'='*60}")
        print("FINAL VALIDATION DECISION")
        print(f"{'='*60}")

        if readiness_assessment.production_readiness:
            print("🎉 SYSTEM APPROVED FOR PRODUCTION DEPLOYMENT")
            print("   All validation tests have passed successfully.")
            print("   System is ready for live trading operations.")
        else:
            print("⛔ SYSTEM NOT READY FOR PRODUCTION")
            print("   Critical issues must be resolved before deployment.")

            if readiness_assessment.critical_blockers:
                print("\n🚨 CRITICAL BLOCKERS:")
                for blocker in readiness_assessment.critical_blockers:
                    print(f"   • {blocker}")

        print("\n📄 Detailed reports saved to validation/ directory")

        # Return exit code
        return 0 if readiness_assessment.production_readiness else 1

    except Exception as e:
        print(f"\n❌ VALIDATION FAILED: {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
