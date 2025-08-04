"""
Test Kraken Nonce Manager - Comprehensive tests for thread-safe nonce generation

Tests cover thread safety, sequential generation, connection isolation,
and edge cases for the nonce management system.
"""

import unittest
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.kraken_nonce_manager import KrakenNonceManager, get_nonce_manager


class TestKrakenNonceManager(unittest.TestCase):
    """Test the Kraken nonce manager functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.manager = KrakenNonceManager(cleanup_after_seconds=60)
    
    def test_basic_nonce_generation(self):
        """Test basic nonce generation for a single connection"""
        conn_id = "test_conn_1"
        
        # Get first nonce
        nonce1 = self.manager.get_nonce(conn_id)
        self.assertIsInstance(nonce1, int)
        self.assertGreater(nonce1, 0)
        
        # Get second nonce
        nonce2 = self.manager.get_nonce(conn_id)
        self.assertEqual(nonce2, nonce1 + 1)
        
        # Get third nonce
        nonce3 = self.manager.get_nonce(conn_id)
        self.assertEqual(nonce3, nonce2 + 1)
    
    def test_multiple_connections(self):
        """Test nonce generation for multiple connections"""
        conn1 = "conn_1"
        conn2 = "conn_2"
        
        # Get nonces for different connections
        nonce1_1 = self.manager.get_nonce(conn1)
        nonce2_1 = self.manager.get_nonce(conn2)
        
        # They should be different (offset by 1000)
        self.assertNotEqual(nonce1_1, nonce2_1)
        self.assertGreater(abs(nonce2_1 - nonce1_1), 500)
        
        # Sequential for same connection
        nonce1_2 = self.manager.get_nonce(conn1)
        nonce2_2 = self.manager.get_nonce(conn2)
        
        self.assertEqual(nonce1_2, nonce1_1 + 1)
        self.assertEqual(nonce2_2, nonce2_1 + 1)
    
    def test_thread_safety(self):
        """Test thread-safe nonce generation"""
        conn_id = "thread_test"
        num_threads = 10
        nonces_per_thread = 100
        
        all_nonces = []
        lock = threading.Lock()
        
        def generate_nonces():
            thread_nonces = []
            for _ in range(nonces_per_thread):
                nonce = self.manager.get_nonce(conn_id)
                thread_nonces.append(nonce)
            
            with lock:
                all_nonces.extend(thread_nonces)
        
        # Run threads
        threads = []
        for _ in range(num_threads):
            thread = threading.Thread(target=generate_nonces)
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify all nonces are unique
        self.assertEqual(len(all_nonces), num_threads * nonces_per_thread)
        self.assertEqual(len(set(all_nonces)), len(all_nonces))
        
        # Verify they're sequential when sorted
        sorted_nonces = sorted(all_nonces)
        for i in range(1, len(sorted_nonces)):
            self.assertEqual(sorted_nonces[i], sorted_nonces[i-1] + 1)
    
    def test_batch_nonce_generation(self):
        """Test batch nonce generation"""
        conn_id = "batch_test"
        batch_size = 10
        
        # Get batch
        nonces = self.manager.get_batch_nonces(conn_id, batch_size)
        
        self.assertEqual(len(nonces), batch_size)
        
        # Verify sequential
        for i in range(1, len(nonces)):
            self.assertEqual(nonces[i], nonces[i-1] + 1)
        
        # Next single nonce should continue sequence
        next_nonce = self.manager.get_nonce(conn_id)
        self.assertEqual(next_nonce, nonces[-1] + 1)
    
    def test_connection_reset(self):
        """Test connection reset functionality"""
        conn_id = "reset_test"
        
        # Generate some nonces
        nonce1 = self.manager.get_nonce(conn_id)
        nonce2 = self.manager.get_nonce(conn_id)
        
        # Reset connection
        self.manager.reset_connection(conn_id)
        
        # New nonce should be much higher
        nonce3 = self.manager.get_nonce(conn_id)
        self.assertGreater(nonce3, nonce2 + 1000)
    
    def test_connection_removal(self):
        """Test connection removal"""
        conn_id = "remove_test"
        
        # Generate nonce
        nonce1 = self.manager.get_nonce(conn_id)
        
        # Remove connection
        self.manager.remove_connection(conn_id)
        
        # New nonce should start fresh
        nonce2 = self.manager.get_nonce(conn_id)
        self.assertNotEqual(nonce2, nonce1 + 1)
    
    def test_microsecond_precision(self):
        """Test that nonces have microsecond precision"""
        conn_id = "precision_test"
        
        # Get nonce
        nonce = self.manager.get_nonce(conn_id)
        
        # Should be at least microsecond timestamp
        current_microseconds = int(time.time() * 1000000)
        self.assertGreater(nonce, current_microseconds - 1000000)  # Within last second
        self.assertLess(nonce, current_microseconds + 1000000)     # Not too far ahead
    
    def test_nonce_validation(self):
        """Test nonce sequence validation"""
        conn_id = "validation_test"
        
        # Valid sequence
        valid_nonces = [100, 101, 102, 103]
        self.assertTrue(self.manager.validate_nonce_sequence(conn_id, valid_nonces))
        
        # Invalid sequence (gap)
        invalid_nonces = [100, 101, 103, 104]
        self.assertFalse(self.manager.validate_nonce_sequence(conn_id, invalid_nonces))
        
        # Invalid sequence (duplicate)
        duplicate_nonces = [100, 101, 101, 102]
        self.assertFalse(self.manager.validate_nonce_sequence(conn_id, duplicate_nonces))
    
    def test_statistics(self):
        """Test statistics tracking"""
        conn1 = "stats_test_1"
        conn2 = "stats_test_2"
        
        # Generate some nonces
        for _ in range(5):
            self.manager.get_nonce(conn1)
        
        for _ in range(3):
            self.manager.get_nonce(conn2)
        
        self.manager.get_batch_nonces(conn1, 10)
        
        # Get statistics
        stats = self.manager.get_statistics()
        
        self.assertEqual(stats['active_connections'], 2)
        self.assertEqual(stats['total_nonces'], 18)  # 5 + 3 + 10
        self.assertEqual(stats['batch_operations'], 1)
        self.assertIn('connections', stats)
        self.assertEqual(len(stats['connections']), 2)
    
    def test_concurrent_batch_operations(self):
        """Test concurrent batch operations from multiple threads"""
        num_threads = 5
        batches_per_thread = 10
        batch_size = 50
        
        all_nonces = []
        lock = threading.Lock()
        
        def generate_batches(thread_id):
            conn_id = f"concurrent_batch_{thread_id}"
            thread_nonces = []
            
            for _ in range(batches_per_thread):
                batch = self.manager.get_batch_nonces(conn_id, batch_size)
                thread_nonces.extend(batch)
            
            with lock:
                all_nonces.extend(thread_nonces)
        
        # Run concurrent batch operations
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(generate_batches, i) for i in range(num_threads)]
            
            for future in as_completed(futures):
                future.result()  # Wait for completion
        
        # Each thread should have unique sequential nonces
        expected_total = num_threads * batches_per_thread * batch_size
        self.assertEqual(len(all_nonces), expected_total)
        
        # All nonces should be unique across all threads
        self.assertEqual(len(set(all_nonces)), expected_total)
    
    def test_time_jump_handling(self):
        """Test handling when system time jumps ahead"""
        conn_id = "time_jump_test"
        
        # Get initial nonce
        nonce1 = self.manager.get_nonce(conn_id)
        
        # Simulate time jump by setting nonce way behind current time
        with self.manager._lock:
            self.manager._connection_nonces[conn_id] = 1000
        
        # Next nonce should jump to current time
        nonce2 = self.manager.get_nonce(conn_id)
        current_microseconds = int(time.time() * 1000000)
        
        self.assertGreater(nonce2, current_microseconds)
        self.assertEqual(self.manager.get_statistics()['time_jumps'], 1)
    
    def test_global_instance(self):
        """Test global nonce manager instance"""
        # Get global instance
        global_manager1 = get_nonce_manager()
        global_manager2 = get_nonce_manager()
        
        # Should be same instance
        self.assertIs(global_manager1, global_manager2)
        
        # Should work correctly
        nonce = global_manager1.get_nonce("global_test")
        self.assertIsInstance(nonce, int)


class TestNonceManagerStress(unittest.TestCase):
    """Stress tests for the nonce manager"""
    
    def test_high_volume_generation(self):
        """Test high-volume nonce generation"""
        manager = KrakenNonceManager()
        conn_id = "stress_test"
        
        # Generate 10,000 nonces rapidly
        start_time = time.time()
        nonces = []
        
        for _ in range(10000):
            nonces.append(manager.get_nonce(conn_id))
        
        elapsed = time.time() - start_time
        
        # Should be fast (less than 1 second)
        self.assertLess(elapsed, 1.0)
        
        # All should be unique and sequential
        self.assertEqual(len(set(nonces)), 10000)
        for i in range(1, len(nonces)):
            self.assertEqual(nonces[i], nonces[i-1] + 1)
    
    def test_many_connections(self):
        """Test handling many simultaneous connections"""
        manager = KrakenNonceManager()
        num_connections = 100
        
        # Create many connections
        for i in range(num_connections):
            conn_id = f"many_conn_{i}"
            nonce = manager.get_nonce(conn_id)
            self.assertIsInstance(nonce, int)
        
        # Check statistics
        stats = manager.get_statistics()
        self.assertEqual(stats['active_connections'], num_connections)


if __name__ == "__main__":
    unittest.main()