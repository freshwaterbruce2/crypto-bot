#!/usr/bin/env python3
"""
Complete System Validation Runner
Executes all validation tests and generates comprehensive production readiness report
"""

import asyncio
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from validation.final_report_generator import FinalValidationReportGenerator


async def main():
    """Run complete system validation"""
    print("🚀 CRYPTO TRADING BOT - COMPLETE SYSTEM VALIDATION")
    print("=" * 80)
    print("This will run comprehensive validation tests to assess production readiness.")
    print("Expected duration: 5-10 minutes")
    print("=" * 80)
    
    start_time = time.time()
    
    try:
        # Initialize validation generator
        generator = FinalValidationReportGenerator()
        
        # Run complete validation
        print("\n📋 Starting validation test suites...")
        validation_results = await generator.generate_complete_validation_report()
        
        total_time = time.time() - start_time
        
        # Print final summary
        executive_summary = validation_results["executive_summary"]
        
        print(f"\n{'='*80}")
        print("🎯 VALIDATION COMPLETE")
        print(f"{'='*80}")
        print(f"⏱️  Total Time: {total_time:.1f} seconds")
        print(f"📊 Confidence: {executive_summary['confidence_level']}")
        print(f"✅ Success Rate: {executive_summary['tests_passed']}")
        print(f"🚨 Critical Issues: {executive_summary['critical_issues']}")
        print(f"🎯 Status: {executive_summary['system_status']}")
        
        if executive_summary['production_ready']:
            print(f"\n🎉 RESULT: APPROVED FOR PRODUCTION")
            print("   Your trading bot has passed all validation tests!")
            print("   Ready for live trading deployment.")
            return 0
        else:
            print(f"\n⛔ RESULT: NOT READY FOR PRODUCTION")
            print("   Please address the issues identified in the validation report.")
            print("   Run validation again after implementing fixes.")
            return 1
            
    except KeyboardInterrupt:
        print("\n⏹️  Validation interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Validation failed with error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)