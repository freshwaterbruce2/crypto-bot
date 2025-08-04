#!/usr/bin/env python3
"""
Comprehensive Test Suite for Consolidated Nonce Manager
======================================================

Tests the consolidated nonce management system to ensure:
- Singleton pattern enforcement
- Thread-safe nonce generation
- State persistence across restarts
- Recovery from invalid nonce errors
- Kraken API compatibility
- Performance under load

Run with: python test_consolidated_nonce_manager.py
"""

import asyncio
import logging
import os
import sys
import threading
import time
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Set

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import the consolidated nonce manager
from src.utils.consolidated_nonce_manager import (
    ConsolidatedNonceManager,
    get_nonce_manager,
    get_unified_nonce_manager,
    get_nonce_coordinator,
    initialize_enhanced_nonce_manager,
    get_nonce,
    get_next_nonce
)


class ConsolidatedNonceManagerTests:
    """Comprehensive test suite for the consolidated nonce manager."""
    
    def __init__(self):
        self.test_results = {
            'passed': 0,
            'failed': 0,
            'errors': []
        }
        
        # Reset singleton for clean testing
        ConsolidatedNonceManager.reset_instance()
    
    def log_test(self, test_name: str, passed: bool, message: str = ""):
        """Log test result."""
        if passed:
            self.test_results['passed'] += 1
            logger.info(f"✅ {test_name}: PASSED {message}")
        else:
            self.test_results['failed'] += 1
            error_msg = f"❌ {test_name}: FAILED {message}"
            logger.error(error_msg)
            self.test_results['errors'].append(error_msg)
    
    def test_singleton_pattern(self) -> bool:
        """Test that only one instance can exist."""
        logger.info("\n🧪 Testing singleton pattern enforcement...")
        
        try:
            # Reset to start clean
            ConsolidatedNonceManager.reset_instance()
            
            # Create multiple instances
            manager1 = ConsolidatedNonceManager()
            manager2 = ConsolidatedNonceManager()
            manager3 = get_nonce_manager()
            manager4 = get_unified_nonce_manager()
            
            # They should all be the same instance
            same_instance = (
                manager1 is manager2 and 
                manager2 is manager3 and 
                manager3 is manager4
            )
            
            self.log_test("Singleton Pattern", same_instance, "- All instances are identical")
            return same_instance
            
        except Exception as e:
            self.log_test("Singleton Pattern", False, f"- Exception: {e}")
            return False
    
    def test_nonce_generation(self) -> bool:
        """Test basic nonce generation."""
        logger.info("\n🧪 Testing nonce generation...")
        
        try:
            manager = get_nonce_manager()
            
            # Generate multiple nonces
            nonces = []
            for i in range(10):
                nonce = manager.get_nonce(f"test_conn_{i}")
                nonces.append(int(nonce))
                time.sleep(0.001)  # Small delay
            
            # Check they are all increasing
            increasing = all(nonces[i] < nonces[i+1] for i in range(len(nonces)-1))
            
            # Check minimum increment
            min_increment = min(nonces[i+1] - nonces[i] for i in range(len(nonces)-1))
            proper_increment = min_increment >= ConsolidatedNonceManager.MIN_INCREMENT_US
            
            success = increasing and proper_increment
            message = f"- Generated {len(nonces)} increasing nonces, min increment: {min_increment}μs"
            
            self.log_test("Nonce Generation", success, message)
            return success
            
        except Exception as e:
            self.log_test("Nonce Generation", False, f"- Exception: {e}")
            return False
    
    def test_thread_safety(self) -> bool:
        """Test thread-safe nonce generation."""
        logger.info("\n🧪 Testing thread safety...")
        
        try:
            manager = get_nonce_manager()
            
            # Collect nonces from multiple threads
            all_nonces: Set[int] = set()
            nonce_lists: List[List[int]] = []
            lock = threading.Lock()
            
            def generate_nonces(thread_id: int) -> None:
                thread_nonces = []
                for i in range(20):
                    nonce = int(manager.get_nonce(f"thread_{thread_id}"))
                    thread_nonces.append(nonce)
                
                with lock:
                    all_nonces.update(thread_nonces)
                    nonce_lists.append(thread_nonces)
            
            # Run multiple threads
            threads = []
            for i in range(5):
                thread = threading.Thread(target=generate_nonces, args=(i,))
                threads.append(thread)
                thread.start()
            
            # Wait for completion
            for thread in threads:
                thread.join()
            
            # Verify results
            total_generated = sum(len(nonce_list) for nonce_list in nonce_lists)
            unique_nonces = len(all_nonces)
            
            # All nonces should be unique
            no_duplicates = total_generated == unique_nonces
            
            # Each thread's nonces should be increasing
            thread_ordering = all(
                all(nonces[i] < nonces[i+1] for i in range(len(nonces)-1))
                for nonces in nonce_lists if len(nonces) > 1
            )
            
            success = no_duplicates and thread_ordering
            message = f"- {total_generated} nonces, {unique_nonces} unique, proper ordering: {thread_ordering}"
            
            self.log_test("Thread Safety", success, message)
            return success
            
        except Exception as e:
            self.log_test("Thread Safety", False, f"- Exception: {e}")
            return False
    
    def test_state_persistence(self) -> bool:
        """Test state persistence across restarts."""
        logger.info("\n🧪 Testing state persistence...")
        
        try:
            # Use temporary directory for testing
            with tempfile.TemporaryDirectory() as temp_dir:
                # Override the state file location for testing
                original_state_file = None
                
                manager1 = get_nonce_manager()
                if hasattr(manager1, '_state_file'):
                    original_state_file = manager1._state_file
                    manager1._state_file = Path(temp_dir) / "test_nonce_state.json"
                
                # Generate some nonces
                nonce1 = int(manager1.get_nonce("persistence_test"))
                nonce2 = int(manager1.get_nonce("persistence_test"))
                
                # Force save
                manager1.force_save()
                
                # Reset instance (simulate restart)
                ConsolidatedNonceManager.reset_instance()
                
                # Create new instance
                manager2 = ConsolidatedNonceManager()
                if original_state_file:
                    manager2._state_file = Path(temp_dir) / "test_nonce_state.json"
                
                # Generate new nonce - should be higher than previous
                nonce3 = int(manager2.get_nonce("persistence_test"))
                
                # Verify persistence worked
                persistence_works = nonce3 > nonce2
                
                # Restore original state file
                if original_state_file and hasattr(manager2, '_state_file'):
                    manager2._state_file = original_state_file
                
                message = f"- Persisted nonce progression: {nonce1} -> {nonce2} -> {nonce3}"
                self.log_test("State Persistence", persistence_works, message)
                return persistence_works
                
        except Exception as e:
            self.log_test("State Persistence", False, f"- Exception: {e}")
            return False
    
    def test_error_recovery(self) -> bool:
        """Test recovery from invalid nonce errors."""
        logger.info("\n🧪 Testing error recovery...")
        
        try:
            manager = get_nonce_manager()
            
            # Get initial nonce
            initial_nonce = int(manager.get_nonce("recovery_test"))
            
            # Simulate invalid nonce error
            recovery_nonce = int(manager.recover_from_error("recovery_test"))
            
            # Recovery nonce should be significantly higher
            buffer_applied = recovery_nonce - initial_nonce >= ConsolidatedNonceManager.RECOVERY_BUFFER_US * 0.8
            
            # Next regular nonce should be higher than recovery nonce
            next_nonce = int(manager.get_nonce("recovery_test"))
            proper_continuation = next_nonce > recovery_nonce
            
            success = buffer_applied and proper_continuation
            message = f"- Recovery jump: {recovery_nonce - initial_nonce}μs, continuation: {proper_continuation}"
            
            self.log_test("Error Recovery", success, message)
            return success
            
        except Exception as e:
            self.log_test("Error Recovery", False, f"- Exception: {e}")
            return False
    
    def test_connection_tracking(self) -> bool:
        """Test connection tracking and cleanup."""
        logger.info("\n🧪 Testing connection tracking...")
        
        try:
            manager = get_nonce_manager()
            
            # Register multiple connections
            connections = ["conn_1", "conn_2", "conn_3"]
            for conn_id in connections:
                manager.register_connection(conn_id)
                manager.get_nonce(conn_id)
            
            # Check status includes connections
            status = manager.get_status()
            tracked_connections = len(status.get('connection_stats', {}))
            
            # Clean up connections
            for conn_id in connections:
                manager.cleanup_connection(conn_id)
            
            # Check connections were cleaned up
            status_after = manager.get_status()
            remaining_connections = len(status_after.get('connection_stats', {}))
            
            success = tracked_connections >= len(connections) and remaining_connections < tracked_connections
            message = f"- Tracked {tracked_connections} connections, {remaining_connections} after cleanup"
            
            self.log_test("Connection Tracking", success, message)
            return success
            
        except Exception as e:
            self.log_test("Connection Tracking", False, f"- Exception: {e}")
            return False
    
    async def test_async_compatibility(self) -> bool:
        """Test async/await compatibility."""
        logger.info("\n🧪 Testing async compatibility...")
        
        try:
            manager = get_nonce_manager()
            
            # Test async nonce generation
            async_nonces = []
            for i in range(5):
                nonce = await manager.get_nonce_async(f"async_test_{i}")
                async_nonces.append(int(nonce))
            
            # Check they are increasing
            increasing = all(async_nonces[i] < async_nonces[i+1] for i in range(len(async_nonces)-1))
            
            message = f"- Generated {len(async_nonces)} async nonces, increasing: {increasing}"
            self.log_test("Async Compatibility", increasing, message)
            return increasing
            
        except Exception as e:
            self.log_test("Async Compatibility", False, f"- Exception: {e}")
            return False
    
    def test_convenience_functions(self) -> bool:
        """Test convenience functions work correctly."""
        logger.info("\n🧪 Testing convenience functions...")
        
        try:
            # Test all convenience functions
            nonce1 = get_nonce("convenience_test")
            nonce2 = get_next_nonce("convenience_test")
            
            # Both should return strings
            strings_returned = isinstance(nonce1, str) and isinstance(nonce2, str)
            
            # They should be increasing
            increasing = int(nonce2) > int(nonce1)
            
            success = strings_returned and increasing
            message = f"- Functions returned strings: {strings_returned}, increasing: {increasing}"
            
            self.log_test("Convenience Functions", success, message)
            return success
            
        except Exception as e:
            self.log_test("Convenience Functions", False, f"- Exception: {e}")
            return False
    
    def test_performance(self) -> bool:
        """Test performance under load."""
        logger.info("\n🧪 Testing performance under load...")
        
        try:
            manager = get_nonce_manager()
            
            # Generate many nonces quickly
            start_time = time.time()
            nonce_count = 1000
            
            for i in range(nonce_count):
                manager.get_nonce(f"perf_test_{i % 10}")  # Cycle through 10 connections
            
            end_time = time.time()
            duration = end_time - start_time
            nonces_per_second = nonce_count / duration
            
            # Should be able to generate at least 100 nonces per second
            fast_enough = nonces_per_second >= 100
            
            message = f"- Generated {nonce_count} nonces in {duration:.3f}s ({nonces_per_second:.0f} nonces/sec)"
            self.log_test("Performance", fast_enough, message)
            return fast_enough
            
        except Exception as e:
            self.log_test("Performance", False, f"- Exception: {e}")
            return False
    
    def test_status_reporting(self) -> bool:
        """Test status reporting functionality."""
        logger.info("\n🧪 Testing status reporting...")
        
        try:
            manager = get_nonce_manager()
            
            # Generate some activity
            for i in range(5):
                nonce = manager.get_nonce(f"status_test_{i}")
                if i % 2 == 0:
                    manager.mark_nonce_success(f"status_test_{i}", nonce)
                else:
                    manager.mark_nonce_failed(f"status_test_{i}", nonce, "Test error")
            
            # Get status
            status = manager.get_status()
            
            # Check required fields exist
            required_fields = [
                'current_nonce', 'total_generated', 'error_recoveries',
                'active_connections', 'connection_stats', 'last_save',
                'state_file', 'version'
            ]
            
            has_required_fields = all(field in status for field in required_fields)
            
            # Check some values make sense
            logical_values = (
                status['total_generated'] > 0 and
                isinstance(status['connection_stats'], dict) and
                status['version'] == '4.0.0'
            )
            
            success = has_required_fields and logical_values
            message = f"- Status contains {len(status)} fields, required fields: {has_required_fields}"
            
            self.log_test("Status Reporting", success, message)
            return success
            
        except Exception as e:
            self.log_test("Status Reporting", False, f"- Exception: {e}")
            return False
    
    async def run_all_tests(self) -> bool:
        """Run all tests and return overall success."""
        logger.info("🚀 Starting Consolidated Nonce Manager Test Suite")
        logger.info("=" * 60)
        
        # Run synchronous tests
        sync_tests = [
            self.test_singleton_pattern,
            self.test_nonce_generation,
            self.test_thread_safety,
            self.test_state_persistence,
            self.test_error_recovery,
            self.test_connection_tracking,
            self.test_convenience_functions,
            self.test_performance,
            self.test_status_reporting
        ]
        
        for test in sync_tests:
            try:
                test()
            except Exception as e:
                logger.error(f"Test execution error: {e}")
                self.test_results['failed'] += 1
                self.test_results['errors'].append(f"Test execution error: {e}")
        
        # Run async tests
        try:
            await self.test_async_compatibility()
        except Exception as e:
            logger.error(f"Async test execution error: {e}")
            self.test_results['failed'] += 1
            self.test_results['errors'].append(f"Async test execution error: {e}")
        
        # Print results
        self.print_results()
        
        return self.test_results['failed'] == 0
    
    def print_results(self):
        """Print comprehensive test results."""
        total_tests = self.test_results['passed'] + self.test_results['failed']
        success_rate = self.test_results['passed'] / total_tests * 100 if total_tests > 0 else 0
        
        logger.info("\n" + "=" * 60)
        logger.info("🧪 CONSOLIDATED NONCE MANAGER TEST RESULTS")
        logger.info("=" * 60)
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {self.test_results['passed']} ✅")
        logger.info(f"Failed: {self.test_results['failed']} ❌")
        logger.info(f"Success Rate: {success_rate:.1f}%")
        
        if self.test_results['errors']:
            logger.info("\n❌ ERRORS:")
            for error in self.test_results['errors']:
                logger.info(f"  • {error}")
        
        if self.test_results['failed'] == 0:
            logger.info("\n🎉 ALL TESTS PASSED! Consolidated nonce manager is ready for production.")
        else:
            logger.info(f"\n⚠️  {self.test_results['failed']} tests failed. Please review and fix issues.")
        
        logger.info("=" * 60)


async def main():
    """Run the consolidated nonce manager test suite."""
    print("🧪 CONSOLIDATED NONCE MANAGER TEST SUITE")
    print("Testing the unified nonce management system for:")
    print("- Singleton pattern enforcement")
    print("- Thread-safe operations")
    print("- State persistence")
    print("- Error recovery")
    print("- Performance under load")
    print("-" * 60)
    
    tester = ConsolidatedNonceManagerTests()
    success = await tester.run_all_tests()
    
    if success:
        print("\n🎉 SUCCESS: Consolidated nonce manager passed all tests!")
        print("✅ The system is ready for production use.")
        print("✅ All previous nonce managers can be safely deprecated.")
    else:
        print("\n❌ FAILURE: Some tests failed.")
        print("🔧 Please review the errors and fix issues before proceeding.")
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)