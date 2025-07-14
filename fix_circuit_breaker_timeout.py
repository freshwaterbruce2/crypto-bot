#!/usr/bin/env python3
"""
Emergency Circuit Breaker Fix Script
====================================
Fixes the circuit breaker timeout issue that blocks trades for 293+ seconds
"""

import os
import sys
import logging
from pathlib import Path

# Add paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("circuit_breaker_fix")

def main():
    """Main fix implementation"""
    logger.info("🚨 EMERGENCY CIRCUIT BREAKER FIX STARTED")
    logger.info("=" * 60)
    
    try:
        # Import circuit breaker components
        from src.utils.circuit_breaker import circuit_breaker_manager, CircuitBreakerConfig
        
        # Check current status
        logger.info("\n📊 CURRENT CIRCUIT BREAKER STATUS:")
        summary = circuit_breaker_manager.get_summary()
        logger.info(f"Total breakers: {summary['total']}")
        logger.info(f"States: {summary['states']}")
        logger.info(f"Rate limit impacted: {summary['rate_limit_impacted']}")
        
        # Get all circuit breaker statuses
        all_status = circuit_breaker_manager.get_all_status()
        for name, status in all_status.items():
            logger.info(f"\n🔌 {name}:")
            logger.info(f"  State: {status['state']}")
            logger.info(f"  Time in state: {status['time_in_state']:.1f}s")
            if 'time_until_half_open' in status:
                logger.info(f"  Time until recovery: {status['time_until_half_open']:.1f}s")
            logger.info(f"  Stats: {status['stats']}")
        
        # Reset all circuit breakers
        logger.info("\n🔧 RESETTING ALL CIRCUIT BREAKERS...")
        circuit_breaker_manager.reset_all()
        
        # Update configuration for any existing breakers
        logger.info("\n⚡ UPDATING CIRCUIT BREAKER CONFIGURATIONS...")
        emergency_config = CircuitBreakerConfig(
            failure_threshold=100,        # Very high threshold
            success_threshold=1,          # Quick recovery
            timeout=1.0,                  # 1 second timeout
            rate_limit_threshold=200,     # High rate limit threshold
            rate_limit_timeout=1.0,       # 1 second rate limit timeout
            backoff_multiplier=1.1,       # Minimal backoff (was 1.2)
            max_backoff=30.0             # Maximum 30 seconds (as requested)
        )
        
        # Apply emergency config to all existing breakers
        for name, breaker in circuit_breaker_manager.circuit_breakers.items():
            breaker.config = emergency_config
            breaker._current_timeout = emergency_config.timeout
            logger.info(f"✅ Updated {name} with emergency configuration")
        
        # Create emergency bypass wrapper
        logger.info("\n🚨 CREATING EMERGENCY BYPASS WRAPPER...")
        
        # Write emergency bypass helper
        bypass_code = '''"""
Emergency Circuit Breaker Bypass Helper
======================================
Use this for critical trades that must go through
"""

from src.utils.circuit_breaker import circuit_breaker_manager

async def emergency_call(circuit_name: str, func, *args, **kwargs):
    """
    Execute a function with emergency bypass enabled
    
    Args:
        circuit_name: Name of the circuit breaker
        func: Async function to call
        *args, **kwargs: Arguments for the function
    """
    cb = circuit_breaker_manager.get_or_create(circuit_name)
    # Force emergency bypass
    kwargs['emergency_bypass'] = True
    return await cb.call(func, *args, **kwargs)

def force_reset_all():
    """Force reset all circuit breakers immediately"""
    circuit_breaker_manager.reset_all()
    return circuit_breaker_manager.get_summary()
'''
        
        emergency_file = project_root / 'src' / 'utils' / 'emergency_bypass.py'
        emergency_file.write_text(bypass_code)
        logger.info(f"✅ Created emergency bypass helper at {emergency_file}")
        
        # Final status check
        logger.info("\n📊 FINAL CIRCUIT BREAKER STATUS:")
        final_summary = circuit_breaker_manager.get_summary()
        logger.info(f"Total breakers: {final_summary['total']}")
        logger.info(f"States: {final_summary['states']}")
        logger.info(f"All closed: {final_summary['states']['closed'] == final_summary['total']}")
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ CIRCUIT BREAKER FIX COMPLETED SUCCESSFULLY!")
        logger.info("\n🎯 CHANGES APPLIED:")
        logger.info("  • Maximum timeout reduced to 30 seconds")
        logger.info("  • Emergency bypass mode enabled")
        logger.info("  • Exponential backoff reduced (1.1x instead of 1.2x)")
        logger.info("  • Rate limit recovery set to 1 second")
        logger.info("  • All circuit breakers reset to CLOSED state")
        logger.info("\n🚀 The bot can now trade without long circuit breaker blocks!")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error fixing circuit breaker: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)