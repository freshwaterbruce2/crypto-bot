#!/usr/bin/env python3
"""Test nonce fix for Kraken API authentication."""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.utils.consolidated_nonce_manager import ConsolidatedNonceManager
from src.exchange.native_kraken_exchange import NativeKrakenExchange

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)-8s] [%(name)s] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)


async def test_nonce_generation():
    """Test nonce generation with proper millisecond timestamps."""
    logger.info("Testing nonce generation...")
    
    # Get nonce manager instance
    nonce_manager = ConsolidatedNonceManager.get_instance()
    
    # Generate 5 nonces to test incrementing
    nonces = []
    for i in range(5):
        nonce = nonce_manager.get_nonce(f"test_{i}")
        nonces.append(int(nonce))
        logger.info(f"Generated nonce {i+1}: {nonce}")
        await asyncio.sleep(0.1)  # Small delay between nonces
    
    # Verify nonces are increasing
    for i in range(1, len(nonces)):
        if nonces[i] <= nonces[i-1]:
            logger.error(f"Nonce not increasing! {nonces[i-1]} -> {nonces[i]}")
            return False
        else:
            logger.info(f"✓ Nonce properly increased: {nonces[i-1]} -> {nonces[i]} (diff: {nonces[i] - nonces[i-1]})")
    
    logger.info("✓ All nonces properly incremented")
    return True


async def test_api_call():
    """Test actual API call with the nonce fix."""
    logger.info("Testing API call with fixed nonce...")
    
    try:
        # Initialize exchange
        exchange = NativeKrakenExchange()
        
        # Test getting WebSocket token (requires authentication)
        logger.info("Getting WebSocket token...")
        token = await exchange.get_websocket_token()
        
        if token:
            logger.info(f"✓ Successfully got WebSocket token: {token[:20]}...")
            return True
        else:
            logger.error("Failed to get WebSocket token")
            return False
            
    except Exception as e:
        logger.error(f"API call failed: {e}")
        return False


async def main():
    """Run all tests."""
    logger.info("=" * 60)
    logger.info("KRAKEN NONCE FIX TEST")
    logger.info("=" * 60)
    
    # Test 1: Nonce generation
    logger.info("\nTest 1: Nonce Generation")
    logger.info("-" * 40)
    test1_passed = await test_nonce_generation()
    
    # Test 2: API call
    logger.info("\nTest 2: API Call with Authentication")
    logger.info("-" * 40)
    test2_passed = await test_api_call()
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST RESULTS")
    logger.info("=" * 60)
    logger.info(f"Nonce Generation: {'✓ PASSED' if test1_passed else '✗ FAILED'}")
    logger.info(f"API Call: {'✓ PASSED' if test2_passed else '✗ FAILED'}")
    
    if test1_passed and test2_passed:
        logger.info("\n✓ ALL TESTS PASSED - Nonce fix successful!")
        return 0
    else:
        logger.error("\n✗ SOME TESTS FAILED - Please check the logs")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)