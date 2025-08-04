"""
Authentication System Unit Tests
===============================

Comprehensive tests for Kraken authentication system including:
- KrakenAuth class functionality
- Nonce manager operations
- Signature generation
- Error handling and recovery
- Performance and timing
"""

import pytest
import asyncio
import time
import base64
import hmac
import hashlib
import urllib.parse
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, Any, Optional

from src.auth.kraken_auth import (
    KrakenAuth, KrakenAuthError, NonceError, SignatureError,
    AuthRequest, AuthStats
)
from src.auth.nonce_manager import NonceManager
from src.auth.signature_generator import SignatureGenerator


class TestKrakenAuth:
    """Test KrakenAuth main authentication class"""
    
    @pytest.fixture
    def valid_credentials(self):
        """Valid test credentials"""
        return {
            'api_key': 'test_api_key_12345678901234567890',
            'private_key': base64.b64encode(b'test_private_key_32_bytes_long_123').decode()
        }
    
    @pytest.fixture
    def kraken_auth(self, valid_credentials):
        """KrakenAuth instance with valid credentials"""
        return KrakenAuth(
            api_key=valid_credentials['api_key'],
            private_key=valid_credentials['private_key'],
            enable_debug=False
        )
    
    @pytest.fixture
    def mock_nonce_manager(self):
        """Mock nonce manager"""
        mock = Mock(spec=NonceManager)
        mock.get_next_nonce.return_value = "1234567890123456"
        mock.get_next_nonce_async = AsyncMock(return_value="1234567890123456")
        mock.handle_invalid_nonce_error.return_value = "1234567890123457"
        mock.validate_nonce.return_value = True
        mock.get_status.return_value = {'nonce_file': 'test', 'current_nonce': '123'}
        mock.cleanup.return_value = None
        return mock
    
    @pytest.fixture
    def mock_signature_generator(self):
        """Mock signature generator"""
        mock = Mock(spec=SignatureGenerator)
        mock.generate_signature.return_value = "test_signature_base64"
        mock.generate_signature_async = AsyncMock(return_value="test_signature_base64")
        mock.test_signature_algorithm.return_value = {'success': True}
        mock.generate_signature_with_debug.return_value = Mock(
            signature="test_signature_base64",
            nonce="1234567890123456",
            post_data="test_data"
        )
        mock.get_statistics.return_value = {'signatures_generated': 10}
        mock._signature_count = 10
        mock._private_key_bytes = b'test_key_32_bytes'
        return mock
    
    def test_init_valid_credentials(self, valid_credentials):
        """Test initialization with valid credentials"""
        auth = KrakenAuth(
            api_key=valid_credentials['api_key'],
            private_key=valid_credentials['private_key']
        )
        
        assert auth.api_key == valid_credentials['api_key']
        assert auth.private_key == valid_credentials['private_key']
        assert auth.enable_debug == False
        assert auth.max_retry_attempts == 3
        assert auth.retry_delay_ms == 100
        assert isinstance(auth.stats, AuthStats)
        assert auth.stats.requests_count == 0
    
    def test_init_invalid_api_key(self, valid_credentials):
        """Test initialization with invalid API key"""
        with pytest.raises(ValueError, match="Invalid API key"):
            KrakenAuth(
                api_key="short",
                private_key=valid_credentials['private_key']
            )
    
    def test_init_invalid_private_key(self, valid_credentials):
        """Test initialization with invalid private key"""
        with pytest.raises(ValueError, match="Invalid private key"):
            KrakenAuth(
                api_key=valid_credentials['api_key'],
                private_key="invalid_base64"
            )
    
    def test_validate_credentials_valid(self, kraken_auth):
        """Test credential validation with valid data"""
        # Should not raise any exceptions
        kraken_auth._validate_credentials()
    
    def test_validate_credentials_empty_api_key(self, valid_credentials):
        """Test credential validation with empty API key"""
        with pytest.raises(ValueError, match="Invalid API key"):
            KrakenAuth(api_key="", private_key=valid_credentials['private_key'])
    
    def test_validate_credentials_short_private_key(self, valid_credentials):
        """Test credential validation with short private key"""
        short_key = base64.b64encode(b'short').decode()
        with pytest.raises(ValueError, match="Decoded private key too short"):
            KrakenAuth(
                api_key=valid_credentials['api_key'],
                private_key=short_key
            )
    
    @patch('src.auth.kraken_auth.NonceManager')
    @patch('src.auth.kraken_auth.SignatureGenerator')
    def test_get_auth_headers_success(self, mock_sig_gen_class, mock_nonce_class, valid_credentials):
        """Test successful auth header generation"""
        # Setup mocks
        mock_nonce = Mock()
        mock_nonce.get_next_nonce.return_value = "1234567890123456"
        mock_nonce_class.return_value = mock_nonce
        
        mock_sig_gen = Mock()
        mock_sig_gen.generate_signature.return_value = "test_signature"
        mock_sig_gen_class.return_value = mock_sig_gen
        
        auth = KrakenAuth(
            api_key=valid_credentials['api_key'],
            private_key=valid_credentials['private_key']
        )
        
        # Test header generation
        headers = auth.get_auth_headers('/0/private/Balance', {'param': 'value'})
        
        # Verify headers
        assert 'API-Key' in headers
        assert 'API-Sign' in headers
        assert 'Content-Type' in headers
        assert headers['API-Key'] == valid_credentials['api_key']
        assert headers['API-Sign'] == "test_signature"
        assert headers['Content-Type'] == 'application/x-www-form-urlencoded'
        
        # Verify method calls
        mock_nonce.get_next_nonce.assert_called_once()
        mock_sig_gen.generate_signature.assert_called_once_with(
            '/0/private/Balance', "1234567890123456", {'param': 'value'}
        )
        
        # Verify stats update
        assert auth.stats.requests_count == 1
        assert auth.stats.successful_auths == 1
        assert auth.stats.failed_auths == 0
    
    @patch('src.auth.kraken_auth.NonceManager')
    @patch('src.auth.kraken_auth.SignatureGenerator')
    async def test_get_auth_headers_async_success(self, mock_sig_gen_class, mock_nonce_class, valid_credentials):
        """Test successful async auth header generation"""
        # Setup mocks
        mock_nonce = Mock()
        mock_nonce.get_next_nonce_async = AsyncMock(return_value="1234567890123456")
        mock_nonce_class.return_value = mock_nonce
        
        mock_sig_gen = Mock()
        mock_sig_gen.generate_signature_async = AsyncMock(return_value="test_signature")
        mock_sig_gen_class.return_value = mock_sig_gen
        
        auth = KrakenAuth(
            api_key=valid_credentials['api_key'],
            private_key=valid_credentials['private_key']
        )
        
        # Test async header generation
        headers = await auth.get_auth_headers_async('/0/private/Balance', {'param': 'value'})
        
        # Verify headers
        assert headers['API-Key'] == valid_credentials['api_key']
        assert headers['API-Sign'] == "test_signature"
        
        # Verify async method calls
        mock_nonce.get_next_nonce_async.assert_called_once()
        mock_sig_gen.generate_signature_async.assert_called_once()
    
    @patch('src.auth.kraken_auth.NonceManager')
    @patch('src.auth.kraken_auth.SignatureGenerator')
    def test_get_auth_headers_nonce_error(self, mock_sig_gen_class, mock_nonce_class, valid_credentials):
        """Test auth header generation with nonce error"""
        # Setup mocks
        mock_nonce = Mock()
        mock_nonce.get_next_nonce.side_effect = Exception("Nonce generation failed")
        mock_nonce_class.return_value = mock_nonce
        
        mock_sig_gen = Mock()
        mock_sig_gen_class.return_value = mock_sig_gen
        
        auth = KrakenAuth(
            api_key=valid_credentials['api_key'],
            private_key=valid_credentials['private_key']
        )
        
        # Test error handling
        with pytest.raises(KrakenAuthError, match="Failed to generate auth headers"):
            auth.get_auth_headers('/0/private/Balance')
        
        # Verify stats update
        assert auth.stats.requests_count == 1
        assert auth.stats.successful_auths == 0
        assert auth.stats.failed_auths == 1
    
    @patch('src.auth.kraken_auth.NonceManager')
    @patch('src.auth.kraken_auth.SignatureGenerator')
    def test_handle_nonce_error_recovery(self, mock_sig_gen_class, mock_nonce_class, valid_credentials):
        """Test nonce error recovery"""
        # Setup mocks
        mock_nonce = Mock()
        mock_nonce.handle_invalid_nonce_error.return_value = "1234567890123457"
        mock_nonce_class.return_value = mock_nonce
        
        mock_sig_gen = Mock()
        mock_sig_gen.generate_signature.return_value = "recovery_signature"
        mock_sig_gen_class.return_value = mock_sig_gen
        
        auth = KrakenAuth(
            api_key=valid_credentials['api_key'],
            private_key=valid_credentials['private_key']
        )
        
        # Test nonce error recovery
        headers = auth.handle_auth_error(
            "EGeneral:Invalid nonce",
            '/0/private/Balance',
            {'param': 'value'}
        )
        
        # Verify recovery headers
        assert headers['API-Key'] == valid_credentials['api_key']
        assert headers['API-Sign'] == "recovery_signature"
        
        # Verify recovery methods called
        mock_nonce.handle_invalid_nonce_error.assert_called_once()
        mock_sig_gen.generate_signature.assert_called_once_with(
            '/0/private/Balance', "1234567890123457", {'param': 'value'}
        )
        
        # Verify stats update
        assert auth.stats.nonce_errors == 1
        assert auth.stats.recovery_attempts == 1
    
    @patch('src.auth.kraken_auth.NonceManager')
    @patch('src.auth.kraken_auth.SignatureGenerator')
    def test_handle_signature_error_recovery(self, mock_sig_gen_class, mock_nonce_class, valid_credentials):
        """Test signature error recovery"""
        # Setup mocks
        mock_nonce = Mock()
        mock_nonce.get_next_nonce.return_value = "1234567890123458"
        mock_nonce_class.return_value = mock_nonce
        
        mock_sig_gen = Mock()
        mock_sig_gen.generate_signature.return_value = "recovery_signature"
        mock_sig_gen_class.return_value = mock_sig_gen
        
        auth = KrakenAuth(
            api_key=valid_credentials['api_key'],
            private_key=valid_credentials['private_key']
        )
        
        # Test signature error recovery
        headers = auth.handle_auth_error(
            "EGeneral:Invalid signature",
            '/0/private/Balance',
            {'param': 'value'}
        )
        
        # Verify recovery headers
        assert headers['API-Key'] == valid_credentials['api_key']
        assert headers['API-Sign'] == "recovery_signature"
        
        # Verify recovery methods called
        mock_nonce.get_next_nonce.assert_called_once()
        mock_sig_gen.generate_signature.assert_called_once()
        
        # Verify stats update
        assert auth.stats.signature_errors == 1
        assert auth.stats.recovery_attempts == 1
    
    def test_handle_unknown_auth_error(self, kraken_auth):
        """Test handling of unknown auth error"""
        with pytest.raises(KrakenAuthError, match="Unknown auth error"):
            kraken_auth.handle_auth_error(
                "Unknown error message",
                '/0/private/Balance'
            )
    
    @patch('src.auth.kraken_auth.NonceManager')
    @patch('src.auth.kraken_auth.SignatureGenerator')
    def test_stats_tracking(self, mock_sig_gen_class, mock_nonce_class, valid_credentials):
        """Test statistics tracking"""
        # Setup mocks
        mock_nonce = Mock()
        mock_nonce.get_next_nonce.return_value = "1234567890123456"
        mock_nonce_class.return_value = mock_nonce
        
        mock_sig_gen = Mock()
        mock_sig_gen.generate_signature.return_value = "test_signature"
        mock_sig_gen_class.return_value = mock_sig_gen
        
        auth = KrakenAuth(
            api_key=valid_credentials['api_key'],
            private_key=valid_credentials['private_key']
        )
        
        # Make multiple requests
        for i in range(5):
            auth.get_auth_headers(f'/0/private/Balance{i}')
        
        # Verify stats
        assert auth.stats.requests_count == 5
        assert auth.stats.successful_auths == 5
        assert auth.stats.failed_auths == 0
        assert auth.stats.avg_auth_time_ms > 0
        assert len(auth._last_auth_times) == 5
    
    @patch('src.auth.kraken_auth.NonceManager')
    @patch('src.auth.kraken_auth.SignatureGenerator')
    def test_comprehensive_status(self, mock_sig_gen_class, mock_nonce_class, valid_credentials):
        """Test comprehensive status reporting"""
        # Setup mocks
        mock_nonce = Mock()
        mock_nonce.get_status.return_value = {'current_nonce': '123', 'nonce_file': 'test'}
        mock_nonce_class.return_value = mock_nonce
        
        mock_sig_gen = Mock()
        mock_sig_gen.get_statistics.return_value = {'signatures_generated': 10}
        mock_sig_gen_class.return_value = mock_sig_gen
        
        auth = KrakenAuth(
            api_key=valid_credentials['api_key'],
            private_key=valid_credentials['private_key']
        )
        
        status = auth.get_comprehensive_status()
        
        # Verify status structure
        assert 'api_key' in status
        assert 'auth_stats' in status
        assert 'nonce_manager' in status
        assert 'signature_generator' in status
        assert 'configuration' in status
        
        # Verify auth stats
        auth_stats = status['auth_stats']
        assert 'total_requests' in auth_stats
        assert 'successful_auths' in auth_stats
        assert 'failed_auths' in auth_stats
        assert 'success_rate' in auth_stats
        assert 'avg_auth_time_ms' in auth_stats
        
        # Verify configuration
        config = status['configuration']
        assert config['debug_enabled'] == False
        assert config['max_retry_attempts'] == 3
        assert config['retry_delay_ms'] == 100
    
    @patch('src.auth.kraken_auth.NonceManager')
    @patch('src.auth.kraken_auth.SignatureGenerator')
    def test_comprehensive_test_execution(self, mock_sig_gen_class, mock_nonce_class, valid_credentials):
        """Test comprehensive test execution"""
        # Setup mocks
        mock_nonce = Mock()
        mock_nonce.get_next_nonce.side_effect = ["1234567890123456", "1234567890123457"]
        mock_nonce.handle_invalid_nonce_error.return_value = "1234567890123458"
        mock_nonce.validate_nonce.return_value = True
        mock_nonce_class.return_value = mock_nonce
        
        mock_sig_gen = Mock()
        mock_sig_gen.test_signature_algorithm.return_value = {'success': True}
        mock_sig_gen.generate_signature.return_value = "test_signature"
        mock_sig_gen_class.return_value = mock_sig_gen
        
        auth = KrakenAuth(
            api_key=valid_credentials['api_key'],
            private_key=valid_credentials['private_key']
        )
        
        results = auth.run_comprehensive_test()
        
        # Verify test results
        assert results['overall_success'] == True
        assert 'tests' in results
        assert 'nonce_generation' in results['tests']
        assert 'signature_generation' in results['tests']
        assert 'auth_headers' in results['tests']
        assert 'nonce_recovery' in results['tests']
        
        # Verify individual test results
        assert results['tests']['nonce_generation']['success'] == True
        assert results['tests']['signature_generation']['success'] == True
        assert results['tests']['auth_headers']['success'] == True
        assert results['tests']['nonce_recovery']['success'] == True
    
    def test_context_manager_sync(self, kraken_auth):
        """Test synchronous context manager"""
        with kraken_auth as auth:
            assert auth == kraken_auth
        # Should not raise exceptions
    
    async def test_context_manager_async(self, kraken_auth):
        """Test asynchronous context manager"""
        async with kraken_auth.auth_context() as auth:
            assert auth == kraken_auth
        # Should not raise exceptions
    
    def test_string_representation(self, kraken_auth):
        """Test string representation"""
        str_repr = str(kraken_auth)
        assert 'KrakenAuth' in str_repr
        assert kraken_auth.api_key[:8] in str_repr
        assert 'requests=' in str_repr
        assert 'success_rate=' in str_repr
    
    @patch('src.auth.kraken_auth.NonceManager')
    @patch('src.auth.kraken_auth.SignatureGenerator')
    def test_export_configuration(self, mock_sig_gen_class, mock_nonce_class, valid_credentials):
        """Test configuration export"""
        # Setup mocks
        mock_nonce = Mock()
        mock_nonce.nonce_file = "test_nonce_file"
        mock_nonce.api_key_hash = "test_hash_12345678"
        mock_nonce_class.return_value = mock_nonce
        
        mock_sig_gen = Mock()
        mock_sig_gen._private_key_bytes = b'test_key_bytes'
        mock_sig_gen._signature_count = 5
        mock_sig_gen_class.return_value = mock_sig_gen
        
        auth = KrakenAuth(
            api_key=valid_credentials['api_key'],
            private_key=valid_credentials['private_key']
        )
        
        config = auth.export_configuration()
        
        # Verify exported configuration
        assert 'api_key_hash' in config
        assert 'nonce_manager_config' in config
        assert 'signature_generator_config' in config
        assert 'auth_config' in config
        assert 'statistics' in config
        
        # Verify sensitive data is masked
        assert config['api_key_hash'].endswith('...')
        assert len(config['api_key_hash']) == 11  # 8 chars + '...'
    
    @patch('src.auth.kraken_auth.NonceManager')
    @patch('src.auth.kraken_auth.SignatureGenerator')
    def test_create_from_config(self, mock_sig_gen_class, mock_nonce_class):
        """Test creation from configuration"""
        config = {
            'api_key': 'test_api_key_12345678901234567890',
            'private_key': base64.b64encode(b'test_private_key_32_bytes_long_123').decode(),
            'storage_dir': '/tmp/test',
            'enable_debug': True
        }
        
        auth = KrakenAuth.create_from_config(config)
        
        assert auth.api_key == config['api_key']
        assert auth.private_key == config['private_key']
        assert auth.enable_debug == True


class TestAuthPerformance:
    """Test authentication system performance"""
    
    @pytest.fixture
    def performance_auth(self):
        """KrakenAuth instance for performance testing"""
        return KrakenAuth(
            api_key='test_api_key_12345678901234567890',
            private_key=base64.b64encode(b'test_private_key_32_bytes_long_123').decode(),
            enable_debug=False
        )
    
    @patch('src.auth.kraken_auth.NonceManager')
    @patch('src.auth.kraken_auth.SignatureGenerator')
    def test_auth_header_generation_performance(self, mock_sig_gen_class, mock_nonce_class, performance_auth):
        """Test authentication header generation performance"""
        # Setup mocks
        mock_nonce = Mock()
        mock_nonce.get_next_nonce.return_value = "1234567890123456"
        mock_nonce_class.return_value = mock_nonce
        
        mock_sig_gen = Mock()
        mock_sig_gen.generate_signature.return_value = "test_signature"
        mock_sig_gen_class.return_value = mock_sig_gen
        
        performance_auth.nonce_manager = mock_nonce
        performance_auth.signature_generator = mock_sig_gen
        
        # Time multiple auth header generations
        iterations = 100
        start_time = time.time()
        
        for i in range(iterations):
            headers = performance_auth.get_auth_headers(f'/0/private/Balance{i}')
            assert 'API-Key' in headers
            assert 'API-Sign' in headers
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_time_per_request = (total_time / iterations) * 1000  # Convert to ms
        
        # Performance assertions
        assert avg_time_per_request < 10.0  # Should be less than 10ms per request
        assert performance_auth.stats.avg_auth_time_ms < 10.0
        assert performance_auth.stats.requests_count == iterations
        assert performance_auth.stats.successful_auths == iterations
        
        print(f"Average auth time: {avg_time_per_request:.2f}ms")
    
    @patch('src.auth.kraken_auth.NonceManager')
    @patch('src.auth.kraken_auth.SignatureGenerator')
    async def test_concurrent_auth_requests(self, mock_sig_gen_class, mock_nonce_class, performance_auth):
        """Test concurrent authentication requests"""
        # Setup mocks
        mock_nonce = Mock()
        mock_nonce.get_next_nonce_async = AsyncMock(
            side_effect=[f"123456789012345{i}" for i in range(50)]
        )
        mock_nonce_class.return_value = mock_nonce
        
        mock_sig_gen = Mock()
        mock_sig_gen.generate_signature_async = AsyncMock(return_value="test_signature")
        mock_sig_gen_class.return_value = mock_sig_gen
        
        performance_auth.nonce_manager = mock_nonce
        performance_auth.signature_generator = mock_sig_gen
        
        # Create concurrent auth requests
        async def make_auth_request(i):
            return await performance_auth.get_auth_headers_async(f'/0/private/Balance{i}')
        
        start_time = time.time()
        
        # Run 50 concurrent requests
        tasks = [make_auth_request(i) for i in range(50)]
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Verify all requests succeeded
        assert len(results) == 50
        for headers in results:
            assert 'API-Key' in headers
            assert 'API-Sign' in headers
        
        # Performance assertions
        assert total_time < 5.0  # Should complete in less than 5 seconds
        assert performance_auth.stats.requests_count == 50
        assert performance_auth.stats.successful_auths == 50
        
        print(f"Concurrent auth requests completed in: {total_time:.2f}s")


class TestAuthErrorScenarios:
    """Test authentication system error scenarios"""
    
    @pytest.fixture
    def error_auth(self):
        """KrakenAuth instance for error testing"""
        return KrakenAuth(
            api_key='test_api_key_12345678901234567890',
            private_key=base64.b64encode(b'test_private_key_32_bytes_long_123').decode(),
            enable_debug=False
        )
    
    @patch('src.auth.kraken_auth.NonceManager')
    @patch('src.auth.kraken_auth.SignatureGenerator')
    def test_nonce_error_cascade(self, mock_sig_gen_class, mock_nonce_class, error_auth):
        """Test cascade of nonce errors"""
        # Setup mocks for cascading failures
        mock_nonce = Mock()
        mock_nonce.get_next_nonce.side_effect = [
            Exception("Nonce error 1"),
            Exception("Nonce error 2"),
            "1234567890123456"  # Finally succeeds
        ]
        mock_nonce_class.return_value = mock_nonce
        
        mock_sig_gen = Mock()
        mock_sig_gen_class.return_value = mock_sig_gen
        
        error_auth.nonce_manager = mock_nonce
        error_auth.signature_generator = mock_sig_gen
        
        # First two requests should fail
        with pytest.raises(KrakenAuthError):
            error_auth.get_auth_headers('/0/private/Balance')
        
        with pytest.raises(KrakenAuthError):
            error_auth.get_auth_headers('/0/private/Balance')
        
        # Verify error statistics
        assert error_auth.stats.requests_count == 2
        assert error_auth.stats.failed_auths == 2
        assert error_auth.stats.successful_auths == 0
    
    @patch('src.auth.kraken_auth.NonceManager')
    @patch('src.auth.kraken_auth.SignatureGenerator')
    def test_signature_error_recovery_failure(self, mock_sig_gen_class, mock_nonce_class, error_auth):
        """Test signature error recovery failure"""
        # Setup mocks
        mock_nonce = Mock()
        mock_nonce.get_next_nonce.return_value = "1234567890123456"
        mock_nonce_class.return_value = mock_nonce
        
        mock_sig_gen = Mock()
        mock_sig_gen.generate_signature.side_effect = Exception("Signature generation failed")
        mock_sig_gen_class.return_value = mock_sig_gen
        
        error_auth.nonce_manager = mock_nonce
        error_auth.signature_generator = mock_sig_gen
        
        # Test signature error recovery failure
        with pytest.raises(SignatureError):
            error_auth.handle_auth_error(
                "EGeneral:Invalid signature",
                '/0/private/Balance'
            )
        
        # Verify error tracking
        assert error_auth.stats.signature_errors == 1
        assert error_auth.stats.recovery_attempts == 1
    
    @patch('src.auth.kraken_auth.NonceManager')
    @patch('src.auth.kraken_auth.SignatureGenerator')
    def test_nonce_recovery_failure(self, mock_sig_gen_class, mock_nonce_class, error_auth):
        """Test nonce recovery failure"""
        # Setup mocks
        mock_nonce = Mock()
        mock_nonce.handle_invalid_nonce_error.side_effect = Exception("Nonce recovery failed")
        mock_nonce_class.return_value = mock_nonce
        
        mock_sig_gen = Mock()
        mock_sig_gen_class.return_value = mock_sig_gen
        
        error_auth.nonce_manager = mock_nonce
        error_auth.signature_generator = mock_sig_gen
        
        # Test nonce recovery failure
        with pytest.raises(NonceError):
            error_auth.handle_auth_error(
                "EGeneral:Invalid nonce",
                '/0/private/Balance'
            )
        
        # Verify error tracking
        assert error_auth.stats.nonce_errors == 1
        assert error_auth.stats.recovery_attempts == 1
    
    def test_memory_usage_under_load(self, error_auth):
        """Test memory usage under high load"""
        import gc
        import sys
        
        # Force garbage collection and get initial memory
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        # Create many auth instances to test memory management
        auth_instances = []
        for i in range(100):
            try:
                auth = KrakenAuth(
                    api_key=f'test_api_key_1234567890123456789{i:02d}',
                    private_key=base64.b64encode(f'test_private_key_32_bytes_long_1{i:02d}'.encode()).decode(),
                    enable_debug=False
                )
                auth_instances.append(auth)
            except Exception:
                pass  # Expected to fail for some invalid keys
        
        # Clean up instances
        for auth in auth_instances:
            auth.cleanup()
        
        del auth_instances
        gc.collect()
        
        # Check memory usage hasn't grown excessively
        final_objects = len(gc.get_objects())
        memory_growth = final_objects - initial_objects
        
        # Memory growth should be reasonable (less than 1000 new objects)
        assert memory_growth < 1000, f"Memory growth too high: {memory_growth} objects"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])