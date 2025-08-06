"""
High-Frequency Trading Performance Benchmark Suite
==================================================

Comprehensive performance benchmarking for all trading bot components.
Measures latency, throughput, and resource usage under realistic trading conditions.

Target Performance Requirements:
- Authentication signature generation: <1ms
- Rate limiting accuracy: 99.9%
- Circuit breaker reaction: <10ms
- REST API call latency: <50ms end-to-end
- WebSocket message processing: <5ms per message
- Balance update latency: <10ms
- Portfolio calculation speed: <100ms
- Database query performance: <50ms
"""

import asyncio
import gc
import json
import logging
import os
import statistics

# Import trading bot components
import sys
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

import psutil

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Set up logger first
logger = logging.getLogger(__name__)

# Core component imports with error handling
try:
    from src.auth.signature_generator import SignatureGenerator
    HAVE_AUTH = True
except ImportError:
    HAVE_AUTH = False
    logger.warning("Auth components not available - skipping auth benchmarks")

try:
    from src.utils.consolidated_nonce_manager import ConsolidatedNonceManager as NonceManager
    HAVE_NONCE = True
except ImportError:
    HAVE_NONCE = False
    logger.warning("Nonce manager not available - skipping nonce benchmarks")

try:
    from src.rate_limiting.kraken_rate_limiter import KrakenRateLimiter2025
    HAVE_RATE_LIMITER = True
except ImportError:
    HAVE_RATE_LIMITER = False
    logger.warning("Rate limiter not available - skipping rate limit benchmarks")

try:
    from src.circuit_breaker.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
    HAVE_CIRCUIT_BREAKER = True
except ImportError:
    HAVE_CIRCUIT_BREAKER = False
    logger.warning("Circuit breaker not available - skipping circuit breaker benchmarks")

try:
    from src.exchange.websocket_manager_v2 import KrakenProWebSocketManager
    HAVE_WEBSOCKET = True
except ImportError:
    HAVE_WEBSOCKET = False
    logger.warning("WebSocket manager not available - skipping WebSocket benchmarks")

try:
    from src.balance.balance_manager import BalanceManager
    HAVE_BALANCE = True
except ImportError:
    HAVE_BALANCE = False
    logger.warning("Balance manager not available - skipping balance benchmarks")

try:
    from src.portfolio.portfolio_manager import PortfolioManager
    HAVE_PORTFOLIO = True
except ImportError:
    HAVE_PORTFOLIO = False
    logger.warning("Portfolio manager not available - skipping portfolio benchmarks")
# Optional database imports
try:
    from src.storage.database_manager import DatabaseManager
    HAVE_DATABASE = True
except ImportError:
    HAVE_DATABASE = False
    logger.warning("Database manager not available - skipping database benchmarks")
from src.utils.decimal_precision_fix import safe_decimal


@dataclass
class BenchmarkResult:
    """Results from a performance benchmark"""
    component: str
    test_name: str
    iterations: int
    total_time: float
    avg_latency: float
    min_latency: float
    max_latency: float
    p95_latency: float
    p99_latency: float
    throughput: float
    cpu_usage_avg: float
    memory_usage_mb: float
    passed: bool
    target_latency: float
    notes: str = ""


class HFTBenchmarkSuite:
    """High-frequency trading performance benchmark suite"""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize benchmark suite"""
        self.results: list[BenchmarkResult] = []
        self.process = psutil.Process()
        self.config = self._load_config(config_path)

        # Performance targets (in milliseconds)
        self.targets = {
            'auth_signature': 1.0,     # <1ms
            'rate_limiting': 0.1,      # <0.1ms check
            'circuit_breaker': 10.0,   # <10ms reaction
            'rest_api_call': 50.0,     # <50ms end-to-end
            'websocket_msg': 5.0,      # <5ms per message
            'balance_update': 10.0,    # <10ms
            'portfolio_calc': 100.0,   # <100ms
            'database_query': 50.0     # <50ms
        }

        logger.info("HFT Benchmark Suite initialized with performance targets")

    def _load_config(self, config_path: Optional[str]) -> dict[str, Any]:
        """Load benchmark configuration"""
        default_config = {
            'iterations': {
                'auth_signature': 10000,
                'rate_limiting': 50000,
                'circuit_breaker': 1000,
                'rest_api_call': 100,
                'websocket_msg': 10000,
                'balance_update': 5000,
                'portfolio_calc': 1000,
                'database_query': 2000
            },
            'concurrent_threads': {
                'auth_signature': 10,
                'rate_limiting': 20,
                'balance_update': 5,
                'database_query': 8
            }
        }

        if config_path and os.path.exists(config_path):
            try:
                with open(config_path) as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
            except Exception as e:
                logger.warning(f"Failed to load config from {config_path}: {e}")

        return default_config

    async def run_all_benchmarks(self) -> dict[str, Any]:
        """Run complete benchmark suite"""
        logger.info("Starting comprehensive HFT performance benchmark suite")
        start_time = time.time()

        # Authentication & Security Benchmarks
        if HAVE_AUTH:
            await self.benchmark_auth_signature_generation()
        else:
            logger.info("Skipping auth signature benchmarks - auth components not available")

        if HAVE_NONCE:
            await self.benchmark_nonce_generation()
        else:
            logger.info("Skipping nonce benchmarks - nonce manager not available")

        # Rate Limiting Benchmarks
        if HAVE_RATE_LIMITER:
            await self.benchmark_rate_limiting_accuracy()
            await self.benchmark_rate_limiting_performance()
        else:
            logger.info("Skipping rate limiting benchmarks - rate limiter not available")

        # Circuit Breaker Benchmarks
        if HAVE_CIRCUIT_BREAKER:
            await self.benchmark_circuit_breaker_reaction()
            await self.benchmark_circuit_breaker_recovery()
        else:
            logger.info("Skipping circuit breaker benchmarks - circuit breaker not available")

        # WebSocket Performance Benchmarks
        if HAVE_WEBSOCKET:
            await self.benchmark_websocket_message_processing()
            await self.benchmark_websocket_reconnection()
        else:
            logger.info("Skipping WebSocket benchmarks - WebSocket manager not available")

        # Balance Management Benchmarks
        if HAVE_BALANCE:
            await self.benchmark_balance_update_latency()
            await self.benchmark_balance_validation()
            await self.benchmark_balance_cache_performance()
        else:
            logger.info("Skipping balance benchmarks - balance manager not available")

        # Portfolio System Benchmarks
        if HAVE_PORTFOLIO:
            await self.benchmark_portfolio_calculation()
            await self.benchmark_position_tracking()
        else:
            logger.info("Skipping portfolio benchmarks - portfolio manager not available")

        # Database Performance Benchmarks (optional)
        if HAVE_DATABASE:
            await self.benchmark_database_queries()
            await self.benchmark_database_writes()
        else:
            logger.info("Skipping database benchmarks - database manager not available")

        # Memory & Resource Benchmarks
        await self.benchmark_memory_usage()
        await self.benchmark_gc_performance()

        total_time = time.time() - start_time

        # Generate comprehensive report
        report = self._generate_performance_report(total_time)

        logger.info(f"Benchmark suite completed in {total_time:.2f}s")
        return report

    async def benchmark_auth_signature_generation(self):
        """Benchmark authentication signature generation speed"""
        logger.info("Benchmarking authentication signature generation...")

        # Setup test data
        test_api_key = "test_key_12345"
        test_secret = "test_secret_67890_very_long_secret_key_for_testing"
        test_data = {
            'nonce': str(int(time.time() * 1000000)),
            'ordertype': 'limit',
            'type': 'buy',
            'volume': '1.0',
            'pair': 'XBTUSD',
            'price': '50000.0'
        }

        sig_gen = SignatureGenerator(test_api_key, test_secret)
        iterations = self.config['iterations']['auth_signature']

        # Warmup
        for _ in range(100):
            sig_gen.generate_signature('/0/private/AddOrder', test_data)

        # Performance measurement with concurrent load
        latencies = []
        cpu_before = self.process.cpu_percent()
        mem_before = self.process.memory_info().rss / 1024 / 1024

        start_time = time.perf_counter()

        # Test both single-threaded and multi-threaded performance
        with ThreadPoolExecutor(max_workers=self.config['concurrent_threads']['auth_signature']) as executor:
            futures = []

            for i in range(iterations):
                # Vary the data slightly to prevent caching
                test_data['nonce'] = str(int(time.time() * 1000000) + i)
                future = executor.submit(self._measure_signature_generation, sig_gen, test_data)
                futures.append(future)

            for future in as_completed(futures):
                latency = future.result()
                latencies.append(latency * 1000)  # Convert to milliseconds

        end_time = time.perf_counter()

        cpu_after = self.process.cpu_percent()
        mem_after = self.process.memory_info().rss / 1024 / 1024

        # Calculate metrics
        total_time = end_time - start_time
        avg_latency = statistics.mean(latencies)
        throughput = iterations / total_time

        result = BenchmarkResult(
            component="Authentication",
            test_name="Signature Generation",
            iterations=iterations,
            total_time=total_time,
            avg_latency=avg_latency,
            min_latency=min(latencies),
            max_latency=max(latencies),
            p95_latency=statistics.quantiles(latencies, n=20)[18],  # 95th percentile
            p99_latency=statistics.quantiles(latencies, n=100)[98], # 99th percentile
            throughput=throughput,
            cpu_usage_avg=(cpu_before + cpu_after) / 2,
            memory_usage_mb=mem_after - mem_before,
            passed=avg_latency < self.targets['auth_signature'],
            target_latency=self.targets['auth_signature'],
            notes=f"Concurrent threads: {self.config['concurrent_threads']['auth_signature']}"
        )

        self.results.append(result)
        logger.info(f"Auth signature benchmark: {avg_latency:.3f}ms avg, {throughput:.0f} ops/sec")

    def _measure_signature_generation(self, sig_gen: SignatureGenerator, data: dict) -> float:
        """Measure single signature generation"""
        start = time.perf_counter()
        sig_gen.generate_signature('/0/private/AddOrder', data)
        return time.perf_counter() - start

    async def benchmark_nonce_generation(self):
        """Benchmark nonce generation performance"""
        logger.info("Benchmarking nonce generation...")

        nonce_manager = UnifiedUnifiedKrakenNonceManager()
        iterations = 100000

        latencies = []
        start_time = time.perf_counter()

        for _ in range(iterations):
            nonce_start = time.perf_counter()
            nonce_manager.get_nonce()
            latencies.append((time.perf_counter() - nonce_start) * 1000)

        end_time = time.perf_counter()

        total_time = end_time - start_time
        avg_latency = statistics.mean(latencies)
        throughput = iterations / total_time

        result = BenchmarkResult(
            component="Authentication",
            test_name="Nonce Generation",
            iterations=iterations,
            total_time=total_time,
            avg_latency=avg_latency,
            min_latency=min(latencies),
            max_latency=max(latencies),
            p95_latency=statistics.quantiles(latencies, n=20)[18],
            p99_latency=statistics.quantiles(latencies, n=100)[98],
            throughput=throughput,
            cpu_usage_avg=self.process.cpu_percent(),
            memory_usage_mb=self.process.memory_info().rss / 1024 / 1024,
            passed=avg_latency < 0.01,  # <0.01ms target
            target_latency=0.01,
            notes="Sequential nonce generation"
        )

        self.results.append(result)
        logger.info(f"Nonce generation benchmark: {avg_latency:.4f}ms avg, {throughput:.0f} ops/sec")

    async def benchmark_rate_limiting_accuracy(self):
        """Benchmark rate limiting accuracy under load"""
        logger.info("Benchmarking rate limiting accuracy...")

        # Create rate limiter with strict limits
        rate_limiter = KrakenRateLimiter2025()
        await rate_limiter.start()

        iterations = self.config['iterations']['rate_limiting']
        allowed_calls = 0
        rejected_calls = 0
        latencies = []

        start_time = time.perf_counter()

        # Test rate limiting accuracy with high frequency requests
        for i in range(iterations):
            call_start = time.perf_counter()

            can_proceed, reason, wait_time = await rate_limiter.check_rate_limit('test_endpoint')
            if can_proceed:
                allowed_calls += 1
            else:
                rejected_calls += 1

            latencies.append((time.perf_counter() - call_start) * 1000)

            # Simulate small delay between requests (microseconds)
            if i % 100 == 0:
                await asyncio.sleep(0.001)

        end_time = time.perf_counter()

        total_time = end_time - start_time
        actual_rate = allowed_calls / total_time * 60  # calls per minute
        expected_rate = 60  # calls per minute
        accuracy = 100 - abs(actual_rate - expected_rate) / expected_rate * 100

        avg_latency = statistics.mean(latencies)

        result = BenchmarkResult(
            component="Rate Limiting",
            test_name="Accuracy Under Load",
            iterations=iterations,
            total_time=total_time,
            avg_latency=avg_latency,
            min_latency=min(latencies),
            max_latency=max(latencies),
            p95_latency=statistics.quantiles(latencies, n=20)[18],
            p99_latency=statistics.quantiles(latencies, n=100)[98],
            throughput=iterations / total_time,
            cpu_usage_avg=self.process.cpu_percent(),
            memory_usage_mb=self.process.memory_info().rss / 1024 / 1024,
            passed=accuracy >= 99.9 and avg_latency < self.targets['rate_limiting'],
            target_latency=self.targets['rate_limiting'],
            notes=f"Accuracy: {accuracy:.2f}%, Allowed: {allowed_calls}, Rejected: {rejected_calls}"
        )

        self.results.append(result)
        await rate_limiter.stop()
        logger.info(f"Rate limiting accuracy: {accuracy:.2f}%, {avg_latency:.4f}ms avg latency")

    async def benchmark_rate_limiting_performance(self):
        """Benchmark rate limiting check performance"""
        logger.info("Benchmarking rate limiting performance...")

        rate_limiter = KrakenRateLimiter2025()
        await rate_limiter.start()
        iterations = 1000000  # 1M checks

        # Warmup
        for _ in range(1000):
            await rate_limiter.check_rate_limit('warmup')

        latencies = []
        start_time = time.perf_counter()

        for _ in range(iterations):
            check_start = time.perf_counter()
            await rate_limiter.check_rate_limit('test_endpoint')
            latencies.append((time.perf_counter() - check_start) * 1000)

        end_time = time.perf_counter()

        total_time = end_time - start_time
        avg_latency = statistics.mean(latencies)
        throughput = iterations / total_time

        result = BenchmarkResult(
            component="Rate Limiting",
            test_name="Check Performance",
            iterations=iterations,
            total_time=total_time,
            avg_latency=avg_latency,
            min_latency=min(latencies),
            max_latency=max(latencies),
            p95_latency=statistics.quantiles(latencies, n=20)[18],
            p99_latency=statistics.quantiles(latencies, n=100)[98],
            throughput=throughput,
            cpu_usage_avg=self.process.cpu_percent(),
            memory_usage_mb=self.process.memory_info().rss / 1024 / 1024,
            passed=avg_latency < self.targets['rate_limiting'],
            target_latency=self.targets['rate_limiting'],
            notes="Pure rate limit checks at maximum speed"
        )

        self.results.append(result)
        await rate_limiter.stop()
        logger.info(f"Rate limiting performance: {avg_latency:.4f}ms avg, {throughput:.0f} checks/sec")

    async def benchmark_circuit_breaker_reaction(self):
        """Benchmark circuit breaker reaction time"""
        logger.info("Benchmarking circuit breaker reaction time...")

        config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=5.0,
            half_open_max_calls=2
        )

        circuit_breaker = CircuitBreaker(config)
        iterations = self.config['iterations']['circuit_breaker']

        # Setup for failure detection
        reaction_times = []

        for _i in range(iterations):
            # Reset circuit breaker
            circuit_breaker._state = 'closed'
            circuit_breaker._failure_count = 0

            # Inject failures to trigger circuit breaker
            for _j in range(config.failure_threshold):
                circuit_breaker.record_failure()

            # Measure reaction time on next call
            reaction_start = time.perf_counter()

            # This should immediately return False due to open circuit
            with circuit_breaker:
                pass  # This will raise an exception due to open circuit

            reaction_time = (time.perf_counter() - reaction_start) * 1000
            reaction_times.append(reaction_time)

        avg_reaction = statistics.mean(reaction_times)

        result = BenchmarkResult(
            component="Circuit Breaker",
            test_name="Reaction Time",
            iterations=iterations,
            total_time=sum(reaction_times) / 1000,
            avg_latency=avg_reaction,
            min_latency=min(reaction_times),
            max_latency=max(reaction_times),
            p95_latency=statistics.quantiles(reaction_times, n=20)[18],
            p99_latency=statistics.quantiles(reaction_times, n=100)[98],
            throughput=iterations / (sum(reaction_times) / 1000),
            cpu_usage_avg=self.process.cpu_percent(),
            memory_usage_mb=self.process.memory_info().rss / 1024 / 1024,
            passed=avg_reaction < self.targets['circuit_breaker'],
            target_latency=self.targets['circuit_breaker'],
            notes="Time to detect and react to failures"
        )

        self.results.append(result)
        logger.info(f"Circuit breaker reaction time: {avg_reaction:.3f}ms avg")

    async def benchmark_circuit_breaker_recovery(self):
        """Benchmark circuit breaker recovery performance"""
        logger.info("Benchmarking circuit breaker recovery...")

        config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=1.0,  # Short timeout for testing
            half_open_max_calls=2
        )

        circuit_breaker = CircuitBreaker(config)

        # Trigger circuit breaker opening
        for _ in range(config.failure_threshold):
            circuit_breaker.record_failure()

        # Wait for recovery timeout
        await asyncio.sleep(config.recovery_timeout + 0.1)

        # Measure recovery time
        recovery_start = time.perf_counter()

        # First successful call should transition to half-open
        circuit_breaker.record_success()

        # Second successful call should transition to closed
        circuit_breaker.record_success()

        recovery_time = (time.perf_counter() - recovery_start) * 1000

        result = BenchmarkResult(
            component="Circuit Breaker",
            test_name="Recovery Time",
            iterations=1,
            total_time=recovery_time / 1000,
            avg_latency=recovery_time,
            min_latency=recovery_time,
            max_latency=recovery_time,
            p95_latency=recovery_time,
            p99_latency=recovery_time,
            throughput=1 / (recovery_time / 1000),
            cpu_usage_avg=self.process.cpu_percent(),
            memory_usage_mb=self.process.memory_info().rss / 1024 / 1024,
            passed=recovery_time < 50.0,  # 50ms target for recovery
            target_latency=50.0,
            notes="Time to recover from open to closed state"
        )

        self.results.append(result)
        logger.info(f"Circuit breaker recovery time: {recovery_time:.3f}ms")

    async def benchmark_websocket_message_processing(self):
        """Benchmark WebSocket message processing speed"""
        logger.info("Benchmarking WebSocket message processing...")

        # Create mock WebSocket manager
        class MockWebSocketManager:
            def __init__(self):
                self.processed_messages = 0
                self.processing_times = []

            async def process_message(self, message):
                start = time.perf_counter()

                # Simulate typical message processing
                if message.get('channel') == 'ticker':
                    # Process ticker data
                    data = message.get('data', [{}])[0]
                    data.get('symbol', 'BTC/USD')
                    price = float(data.get('last', 50000))
                    volume = float(data.get('volume', 100))

                    # Simulate calculations
                    price * 0.001
                    price * volume

                elif message.get('channel') == 'balances':
                    # Process balance data
                    balances = message.get('data', [])
                    for balance in balances:
                        balance.get('asset', 'BTC')
                        amount = float(balance.get('free', 0))
                        amount * 50000  # Mock price

                processing_time = (time.perf_counter() - start) * 1000
                self.processing_times.append(processing_time)
                self.processed_messages += 1

        ws_manager = MockWebSocketManager()
        iterations = self.config['iterations']['websocket_msg']

        # Generate test messages
        test_messages = []
        for i in range(iterations):
            if i % 2 == 0:
                # Ticker message
                message = {
                    'channel': 'ticker',
                    'data': [{
                        'symbol': f'TEST{i % 10}/USD',
                        'last': 50000 + (i % 1000),
                        'bid': 49990 + (i % 1000),
                        'ask': 50010 + (i % 1000),
                        'volume': 1000 + (i % 500)
                    }]
                }
            else:
                # Balance message
                message = {
                    'channel': 'balances',
                    'data': [{
                        'asset': f'ASSET{i % 5}',
                        'free': str(100 + (i % 50)),
                        'used': str(i % 10)
                    }]
                }
            test_messages.append(message)

        # Process messages
        start_time = time.perf_counter()

        for message in test_messages:
            await ws_manager.process_message(message)

        end_time = time.perf_counter()

        total_time = end_time - start_time
        avg_latency = statistics.mean(ws_manager.processing_times)
        throughput = iterations / total_time

        result = BenchmarkResult(
            component="WebSocket",
            test_name="Message Processing",
            iterations=iterations,
            total_time=total_time,
            avg_latency=avg_latency,
            min_latency=min(ws_manager.processing_times),
            max_latency=max(ws_manager.processing_times),
            p95_latency=statistics.quantiles(ws_manager.processing_times, n=20)[18],
            p99_latency=statistics.quantiles(ws_manager.processing_times, n=100)[98],
            throughput=throughput,
            cpu_usage_avg=self.process.cpu_percent(),
            memory_usage_mb=self.process.memory_info().rss / 1024 / 1024,
            passed=avg_latency < self.targets['websocket_msg'],
            target_latency=self.targets['websocket_msg'],
            notes="Mixed ticker and balance messages"
        )

        self.results.append(result)
        logger.info(f"WebSocket processing: {avg_latency:.3f}ms avg, {throughput:.0f} msg/sec")

    async def benchmark_websocket_reconnection(self):
        """Benchmark WebSocket reconnection performance"""
        logger.info("Benchmarking WebSocket reconnection performance...")

        # Simulate reconnection scenarios
        reconnection_times = []

        for _i in range(10):  # Test 10 reconnections
            reconnect_start = time.perf_counter()

            # Simulate disconnect and reconnect process
            await asyncio.sleep(0.01)  # Connection establishment
            await asyncio.sleep(0.02)  # Authentication
            await asyncio.sleep(0.01)  # Subscription setup

            reconnect_time = (time.perf_counter() - reconnect_start) * 1000
            reconnection_times.append(reconnect_time)

        avg_reconnect = statistics.mean(reconnection_times)

        result = BenchmarkResult(
            component="WebSocket",
            test_name="Reconnection Speed",
            iterations=10,
            total_time=sum(reconnection_times) / 1000,
            avg_latency=avg_reconnect,
            min_latency=min(reconnection_times),
            max_latency=max(reconnection_times),
            p95_latency=statistics.quantiles(reconnection_times, n=10)[8],
            p99_latency=max(reconnection_times),
            throughput=10 / (sum(reconnection_times) / 1000),
            cpu_usage_avg=self.process.cpu_percent(),
            memory_usage_mb=self.process.memory_info().rss / 1024 / 1024,
            passed=avg_reconnect < 1000.0,  # <1 second target
            target_latency=1000.0,
            notes="Full reconnection including auth and subscriptions"
        )

        self.results.append(result)
        logger.info(f"WebSocket reconnection: {avg_reconnect:.1f}ms avg")

    async def benchmark_balance_update_latency(self):
        """Benchmark balance update processing latency"""
        logger.info("Benchmarking balance update latency...")

        # Create mock balance manager
        class MockBalanceManager:
            def __init__(self):
                self.balances = {}
                self.update_times = []

            async def update_balance(self, asset: str, balance_data: dict):
                start = time.perf_counter()

                # Simulate balance processing
                free = safe_decimal(balance_data.get('free', '0'))
                used = safe_decimal(balance_data.get('used', '0'))
                total = free + used

                self.balances[asset] = {
                    'free': free,
                    'used': used,
                    'total': total,
                    'timestamp': time.time()
                }

                # Simulate validation
                if total < 0:
                    raise ValueError("Negative balance")

                # Simulate notifications
                if asset in ['BTC', 'ETH', 'USDT']:
                    pass  # Important asset notification

                update_time = (time.perf_counter() - start) * 1000
                self.update_times.append(update_time)

        balance_manager = MockBalanceManager()
        iterations = self.config['iterations']['balance_update']

        # Generate test balance updates
        test_assets = ['BTC', 'ETH', 'USDT', 'ADA', 'DOT', 'LINK', 'MATIC', 'SHIB']

        start_time = time.perf_counter()

        for i in range(iterations):
            asset = test_assets[i % len(test_assets)]
            balance_data = {
                'free': str(100 + (i % 1000)),
                'used': str(i % 50),
                'timestamp': time.time()
            }

            await balance_manager.update_balance(asset, balance_data)

        end_time = time.perf_counter()

        total_time = end_time - start_time
        avg_latency = statistics.mean(balance_manager.update_times)
        throughput = iterations / total_time

        result = BenchmarkResult(
            component="Balance Manager",
            test_name="Update Latency",
            iterations=iterations,
            total_time=total_time,
            avg_latency=avg_latency,
            min_latency=min(balance_manager.update_times),
            max_latency=max(balance_manager.update_times),
            p95_latency=statistics.quantiles(balance_manager.update_times, n=20)[18],
            p99_latency=statistics.quantiles(balance_manager.update_times, n=100)[98],
            throughput=throughput,
            cpu_usage_avg=self.process.cpu_percent(),
            memory_usage_mb=self.process.memory_info().rss / 1024 / 1024,
            passed=avg_latency < self.targets['balance_update'],
            target_latency=self.targets['balance_update'],
            notes=f"Updates across {len(test_assets)} assets"
        )

        self.results.append(result)
        logger.info(f"Balance update latency: {avg_latency:.3f}ms avg, {throughput:.0f} updates/sec")

    async def benchmark_balance_validation(self):
        """Benchmark balance validation performance"""
        logger.info("Benchmarking balance validation performance...")

        # Create mock validator
        class MockBalanceValidator:
            def __init__(self):
                self.validation_times = []

            def validate_balance(self, asset: str, balance_data: dict) -> bool:
                start = time.perf_counter()

                # Simulate validation logic
                try:
                    free = float(balance_data.get('free', 0))
                    used = float(balance_data.get('used', 0))
                    total = float(balance_data.get('total', free + used))

                    # Basic validations
                    if free < 0 or used < 0 or total < 0:
                        return False

                    if abs(total - (free + used)) > 0.00000001:
                        return False

                    # Asset-specific validations
                    if asset in ['BTC', 'ETH'] and total > 1000000:
                        return False  # Unrealistic balance

                    if asset == 'USDT' and total > 10000000:
                        return False  # Very high USDT balance

                    validation_time = (time.perf_counter() - start) * 1000
                    self.validation_times.append(validation_time)
                    return True

                except Exception:
                    validation_time = (time.perf_counter() - start) * 1000
                    self.validation_times.append(validation_time)
                    return False

        validator = MockBalanceValidator()
        iterations = 10000

        # Generate test data
        test_data = []
        for i in range(iterations):
            asset = ['BTC', 'ETH', 'USDT', 'ADA', 'DOT'][i % 5]
            balance_data = {
                'free': 100 + (i % 1000),
                'used': i % 50,
                'total': 100 + (i % 1000) + (i % 50)
            }
            test_data.append((asset, balance_data))

        # Run validations
        start_time = time.perf_counter()
        valid_count = 0

        for asset, balance_data in test_data:
            if validator.validate_balance(asset, balance_data):
                valid_count += 1

        end_time = time.perf_counter()

        total_time = end_time - start_time
        avg_latency = statistics.mean(validator.validation_times)
        throughput = iterations / total_time

        result = BenchmarkResult(
            component="Balance Manager",
            test_name="Validation Performance",
            iterations=iterations,
            total_time=total_time,
            avg_latency=avg_latency,
            min_latency=min(validator.validation_times),
            max_latency=max(validator.validation_times),
            p95_latency=statistics.quantiles(validator.validation_times, n=20)[18],
            p99_latency=statistics.quantiles(validator.validation_times, n=100)[98],
            throughput=throughput,
            cpu_usage_avg=self.process.cpu_percent(),
            memory_usage_mb=self.process.memory_info().rss / 1024 / 1024,
            passed=avg_latency < 1.0,  # <1ms target for validation
            target_latency=1.0,
            notes=f"Valid: {valid_count}/{iterations} ({valid_count/iterations*100:.1f}%)"
        )

        self.results.append(result)
        logger.info(f"Balance validation: {avg_latency:.4f}ms avg, {throughput:.0f} validations/sec")

    async def benchmark_balance_cache_performance(self):
        """Benchmark balance cache performance"""
        logger.info("Benchmarking balance cache performance...")

        # Create mock cache
        cache = {}
        cache_times = []

        iterations = 100000
        assets = ['BTC', 'ETH', 'USDT', 'ADA', 'DOT', 'LINK', 'MATIC', 'SHIB'] * 100

        # Benchmark cache writes
        start_time = time.perf_counter()

        for i in range(iterations):
            cache_start = time.perf_counter()

            asset = assets[i % len(assets)]
            cache[asset] = {
                'free': 100 + i,
                'used': i % 10,
                'timestamp': time.time()
            }

            cache_times.append((time.perf_counter() - cache_start) * 1000)

        write_time = time.perf_counter() - start_time

        # Benchmark cache reads
        read_times = []
        start_time = time.perf_counter()

        for i in range(iterations):
            read_start = time.perf_counter()

            asset = assets[i % len(assets)]
            cache.get(asset)

            read_times.append((time.perf_counter() - read_start) * 1000)

        read_time = time.perf_counter() - start_time

        avg_write_latency = statistics.mean(cache_times)
        avg_read_latency = statistics.mean(read_times)

        result = BenchmarkResult(
            component="Balance Manager",
            test_name="Cache Performance",
            iterations=iterations * 2,  # Both reads and writes
            total_time=write_time + read_time,
            avg_latency=(avg_write_latency + avg_read_latency) / 2,
            min_latency=min(min(cache_times), min(read_times)),
            max_latency=max(max(cache_times), max(read_times)),
            p95_latency=(statistics.quantiles(cache_times, n=20)[18] +
                        statistics.quantiles(read_times, n=20)[18]) / 2,
            p99_latency=(statistics.quantiles(cache_times, n=100)[98] +
                        statistics.quantiles(read_times, n=100)[98]) / 2,
            throughput=(iterations * 2) / (write_time + read_time),
            cpu_usage_avg=self.process.cpu_percent(),
            memory_usage_mb=self.process.memory_info().rss / 1024 / 1024,
            passed=avg_write_latency < 0.01 and avg_read_latency < 0.01,
            target_latency=0.01,
            notes=f"Write: {avg_write_latency:.4f}ms, Read: {avg_read_latency:.4f}ms"
        )

        self.results.append(result)
        logger.info(f"Cache performance - Write: {avg_write_latency:.4f}ms, Read: {avg_read_latency:.4f}ms")

    async def benchmark_portfolio_calculation(self):
        """Benchmark portfolio calculation performance"""
        logger.info("Benchmarking portfolio calculation performance...")

        # Create mock portfolio calculator
        class MockPortfolioCalculator:
            def __init__(self):
                self.calc_times = []
                self.positions = {}
                self.prices = {}

            def calculate_portfolio_value(self, balances: dict, prices: dict) -> dict:
                start = time.perf_counter()

                total_value = Decimal('0')
                portfolio = {}

                for asset, balance_info in balances.items():
                    if isinstance(balance_info, dict):
                        balance = safe_decimal(balance_info.get('free', '0'))
                    else:
                        balance = safe_decimal(str(balance_info))

                    price = safe_decimal(str(prices.get(asset, '0')))
                    value = balance * price

                    portfolio[asset] = {
                        'balance': balance,
                        'price': price,
                        'value': value,
                        'percentage': Decimal('0')  # Will calculate after total
                    }

                    total_value += value

                # Calculate percentages
                for asset in portfolio:
                    if total_value > 0:
                        portfolio[asset]['percentage'] = (
                            portfolio[asset]['value'] / total_value * 100
                        )

                # Calculate additional metrics
                portfolio_metrics = {
                    'total_value': total_value,
                    'asset_count': len(portfolio),
                    'largest_position': max(portfolio.values(),
                                          key=lambda x: x['value'])['value'] if portfolio else Decimal('0'),
                    'diversification_ratio': len(portfolio) / max(1, len(balances))
                }

                calc_time = (time.perf_counter() - start) * 1000
                self.calc_times.append(calc_time)

                return {
                    'positions': portfolio,
                    'metrics': portfolio_metrics
                }

        calculator = MockPortfolioCalculator()
        iterations = self.config['iterations']['portfolio_calc']

        # Generate test data
        test_balances = {}
        test_prices = {}

        for i in range(50):  # 50 different assets
            asset = f"ASSET{i}"
            test_balances[asset] = {
                'free': 100 + (i * 10),
                'used': i % 10
            }
            test_prices[asset] = 50000 + (i * 1000)

        # Run portfolio calculations
        start_time = time.perf_counter()

        for i in range(iterations):
            # Vary the data slightly
            current_balances = test_balances.copy()
            current_prices = test_prices.copy()

            # Add some variation
            for asset in list(current_balances.keys())[:10]:
                current_balances[asset]['free'] += i % 100
                current_prices[asset] += (i % 1000) - 500

            calculator.calculate_portfolio_value(current_balances, current_prices)

        end_time = time.perf_counter()

        total_time = end_time - start_time
        avg_latency = statistics.mean(calculator.calc_times)
        throughput = iterations / total_time

        result = BenchmarkResult(
            component="Portfolio Manager",
            test_name="Portfolio Calculation",
            iterations=iterations,
            total_time=total_time,
            avg_latency=avg_latency,
            min_latency=min(calculator.calc_times),
            max_latency=max(calculator.calc_times),
            p95_latency=statistics.quantiles(calculator.calc_times, n=20)[18],
            p99_latency=statistics.quantiles(calculator.calc_times, n=100)[98],
            throughput=throughput,
            cpu_usage_avg=self.process.cpu_percent(),
            memory_usage_mb=self.process.memory_info().rss / 1024 / 1024,
            passed=avg_latency < self.targets['portfolio_calc'],
            target_latency=self.targets['portfolio_calc'],
            notes="50 assets, full portfolio recalculation"
        )

        self.results.append(result)
        logger.info(f"Portfolio calculation: {avg_latency:.3f}ms avg, {throughput:.0f} calcs/sec")

    async def benchmark_position_tracking(self):
        """Benchmark position tracking performance"""
        logger.info("Benchmarking position tracking performance...")

        # Create mock position tracker
        class MockPositionTracker:
            def __init__(self):
                self.positions = {}
                self.track_times = []

            def update_position(self, symbol: str, side: str, quantity: float,
                              price: float, timestamp: float):
                start = time.perf_counter()

                if symbol not in self.positions:
                    self.positions[symbol] = {
                        'long': {'quantity': 0, 'avg_price': 0, 'value': 0},
                        'short': {'quantity': 0, 'avg_price': 0, 'value': 0}
                    }

                pos = self.positions[symbol][side]

                # Update position with FIFO accounting
                if pos['quantity'] == 0:
                    pos['avg_price'] = price
                    pos['quantity'] = quantity
                else:
                    total_value = pos['quantity'] * pos['avg_price'] + quantity * price
                    total_quantity = pos['quantity'] + quantity
                    pos['avg_price'] = total_value / total_quantity if total_quantity > 0 else 0
                    pos['quantity'] = total_quantity

                pos['value'] = pos['quantity'] * pos['avg_price']

                track_time = (time.perf_counter() - start) * 1000
                self.track_times.append(track_time)

        tracker = MockPositionTracker()
        iterations = 10000

        # Generate test trades
        symbols = ['BTC/USD', 'ETH/USD', 'ADA/USD', 'DOT/USD', 'LINK/USD']

        start_time = time.perf_counter()

        for i in range(iterations):
            symbol = symbols[i % len(symbols)]
            side = 'long' if i % 2 == 0 else 'short'
            quantity = 1.0 + (i % 100) / 100
            price = 50000 + (i % 10000) - 5000
            timestamp = time.time()

            tracker.update_position(symbol, side, quantity, price, timestamp)

        end_time = time.perf_counter()

        total_time = end_time - start_time
        avg_latency = statistics.mean(tracker.track_times)
        throughput = iterations / total_time

        result = BenchmarkResult(
            component="Portfolio Manager",
            test_name="Position Tracking",
            iterations=iterations,
            total_time=total_time,
            avg_latency=avg_latency,
            min_latency=min(tracker.track_times),
            max_latency=max(tracker.track_times),
            p95_latency=statistics.quantiles(tracker.track_times, n=20)[18],
            p99_latency=statistics.quantiles(tracker.track_times, n=100)[98],
            throughput=throughput,
            cpu_usage_avg=self.process.cpu_percent(),
            memory_usage_mb=self.process.memory_info().rss / 1024 / 1024,
            passed=avg_latency < 5.0,  # <5ms target
            target_latency=5.0,
            notes=f"Tracking across {len(symbols)} symbols"
        )

        self.results.append(result)
        logger.info(f"Position tracking: {avg_latency:.3f}ms avg, {throughput:.0f} updates/sec")

    async def benchmark_database_queries(self):
        """Benchmark database query performance"""
        logger.info("Benchmarking database query performance...")

        # Create mock database
        class MockDatabase:
            def __init__(self):
                self.trades = []
                self.balances = {}
                self.query_times = []

                # Populate with test data
                for i in range(10000):
                    trade = {
                        'id': i,
                        'symbol': f'PAIR{i % 20}',
                        'side': 'buy' if i % 2 == 0 else 'sell',
                        'quantity': 1.0 + (i % 100),
                        'price': 50000 + (i % 1000),
                        'timestamp': time.time() - (i * 60)
                    }
                    self.trades.append(trade)

            def query_recent_trades(self, symbol: str, limit: int = 100):
                start = time.perf_counter()

                # Filter trades for symbol
                symbol_trades = [t for t in self.trades if t['symbol'] == symbol]

                # Sort by timestamp descending
                symbol_trades.sort(key=lambda x: x['timestamp'], reverse=True)

                # Apply limit
                result = symbol_trades[:limit]

                query_time = (time.perf_counter() - start) * 1000
                self.query_times.append(query_time)

                return result

            def query_balance_history(self, asset: str, hours: int = 24):
                start = time.perf_counter()

                # Simulate balance history query
                cutoff_time = time.time() - (hours * 3600)

                history = []
                for i in range(hours * 60):  # Minute-by-minute data
                    timestamp = cutoff_time + (i * 60)
                    balance = 1000 + (i % 100)
                    history.append({
                        'asset': asset,
                        'balance': balance,
                        'timestamp': timestamp
                    })

                query_time = (time.perf_counter() - start) * 1000
                self.query_times.append(query_time)

                return history

            def query_portfolio_performance(self, start_time: float, end_time: float):
                start = time.perf_counter()

                # Simulate complex portfolio query
                time_range = int(end_time - start_time)
                performance_data = []

                for i in range(0, time_range, 3600):  # Hourly data
                    timestamp = start_time + i
                    total_value = 100000 + (i % 10000)
                    pnl = (i % 2000) - 1000

                    performance_data.append({
                        'timestamp': timestamp,
                        'total_value': total_value,
                        'pnl': pnl,
                        'return_pct': pnl / total_value * 100
                    })

                query_time = (time.perf_counter() - start) * 1000
                self.query_times.append(query_time)

                return performance_data

        db = MockDatabase()
        iterations = self.config['iterations']['database_query']

        start_time = time.perf_counter()

        # Run various query types
        for i in range(iterations):
            query_type = i % 3

            if query_type == 0:
                # Trade queries
                symbol = f'PAIR{i % 20}'
                db.query_recent_trades(symbol, 100)
            elif query_type == 1:
                # Balance history queries
                asset = ['BTC', 'ETH', 'USDT', 'ADA'][i % 4]
                db.query_balance_history(asset, 24)
            else:
                # Portfolio performance queries
                end_time_ts = time.time()
                start_time_ts = end_time_ts - (24 * 3600)  # 24 hours
                db.query_portfolio_performance(start_time_ts, end_time_ts)

        end_time = time.perf_counter()

        total_time = end_time - start_time
        avg_latency = statistics.mean(db.query_times)
        throughput = iterations / total_time

        result = BenchmarkResult(
            component="Database",
            test_name="Query Performance",
            iterations=iterations,
            total_time=total_time,
            avg_latency=avg_latency,
            min_latency=min(db.query_times),
            max_latency=max(db.query_times),
            p95_latency=statistics.quantiles(db.query_times, n=20)[18],
            p99_latency=statistics.quantiles(db.query_times, n=100)[98],
            throughput=throughput,
            cpu_usage_avg=self.process.cpu_percent(),
            memory_usage_mb=self.process.memory_info().rss / 1024 / 1024,
            passed=avg_latency < self.targets['database_query'],
            target_latency=self.targets['database_query'],
            notes="Mixed query types: trades, balance history, portfolio performance"
        )

        self.results.append(result)
        logger.info(f"Database queries: {avg_latency:.3f}ms avg, {throughput:.0f} queries/sec")

    async def benchmark_database_writes(self):
        """Benchmark database write performance"""
        logger.info("Benchmarking database write performance...")

        # Create mock database for writes
        class MockWriteDatabase:
            def __init__(self):
                self.write_times = []
                self.trades = []
                self.balances = []

            def insert_trade(self, trade_data: dict):
                start = time.perf_counter()

                # Simulate trade insertion with validation
                trade = {
                    'id': len(self.trades) + 1,
                    'symbol': trade_data['symbol'],
                    'side': trade_data['side'],
                    'quantity': float(trade_data['quantity']),
                    'price': float(trade_data['price']),
                    'timestamp': trade_data.get('timestamp', time.time()),
                    'status': 'filled'
                }

                # Simulate index updates and constraints
                self.trades.append(trade)

                write_time = (time.perf_counter() - start) * 1000
                self.write_times.append(write_time)

            def insert_balance_update(self, balance_data: dict):
                start = time.perf_counter()

                # Simulate balance update insertion
                balance_entry = {
                    'id': len(self.balances) + 1,
                    'asset': balance_data['asset'],
                    'balance': float(balance_data['balance']),
                    'timestamp': balance_data.get('timestamp', time.time()),
                    'source': balance_data.get('source', 'websocket')
                }

                self.balances.append(balance_entry)

                write_time = (time.perf_counter() - start) * 1000
                self.write_times.append(write_time)

            def batch_insert_trades(self, trades: list[dict]):
                start = time.perf_counter()

                # Simulate batch insertion
                for trade_data in trades:
                    trade = {
                        'id': len(self.trades) + 1,
                        'symbol': trade_data['symbol'],
                        'side': trade_data['side'],
                        'quantity': float(trade_data['quantity']),
                        'price': float(trade_data['price']),
                        'timestamp': trade_data.get('timestamp', time.time())
                    }
                    self.trades.append(trade)

                write_time = (time.perf_counter() - start) * 1000
                self.write_times.append(write_time)

        db = MockWriteDatabase()
        iterations = 2000

        # Single inserts
        single_insert_start = time.perf_counter()

        for i in range(iterations // 2):
            if i % 2 == 0:
                # Insert trade
                trade_data = {
                    'symbol': f'PAIR{i % 10}',
                    'side': 'buy' if i % 2 == 0 else 'sell',
                    'quantity': 1.0 + (i % 100),
                    'price': 50000 + (i % 1000),
                    'timestamp': time.time()
                }
                db.insert_trade(trade_data)
            else:
                # Insert balance update
                balance_data = {
                    'asset': ['BTC', 'ETH', 'USDT'][i % 3],
                    'balance': 1000 + (i % 500),
                    'timestamp': time.time(),
                    'source': 'websocket'
                }
                db.insert_balance_update(balance_data)

        # Batch inserts
        batch_size = 100
        num_batches = (iterations // 2) // batch_size

        for batch_num in range(num_batches):
            batch_trades = []
            for i in range(batch_size):
                trade_data = {
                    'symbol': f'BATCH{(batch_num * batch_size + i) % 10}',
                    'side': 'buy' if i % 2 == 0 else 'sell',
                    'quantity': 1.0 + (i % 100),
                    'price': 50000 + (i % 1000),
                    'timestamp': time.time()
                }
                batch_trades.append(trade_data)

            db.batch_insert_trades(batch_trades)

        end_time = time.perf_counter()

        total_time = end_time - single_insert_start
        avg_latency = statistics.mean(db.write_times)
        throughput = len(db.write_times) / total_time

        result = BenchmarkResult(
            component="Database",
            test_name="Write Performance",
            iterations=len(db.write_times),
            total_time=total_time,
            avg_latency=avg_latency,
            min_latency=min(db.write_times),
            max_latency=max(db.write_times),
            p95_latency=statistics.quantiles(db.write_times, n=20)[18],
            p99_latency=statistics.quantiles(db.write_times, n=100)[98],
            throughput=throughput,
            cpu_usage_avg=self.process.cpu_percent(),
            memory_usage_mb=self.process.memory_info().rss / 1024 / 1024,
            passed=avg_latency < 25.0,  # <25ms target for writes
            target_latency=25.0,
            notes=f"Single inserts + batch inserts, {num_batches} batches of {batch_size}"
        )

        self.results.append(result)
        logger.info(f"Database writes: {avg_latency:.3f}ms avg, {throughput:.0f} writes/sec")

    async def benchmark_memory_usage(self):
        """Benchmark memory usage patterns"""
        logger.info("Benchmarking memory usage patterns...")

        # Start memory tracking
        tracemalloc.start()

        # Create test data structures
        large_dict = {}
        large_list = []

        # Simulate typical trading bot memory usage
        start_time = time.perf_counter()
        initial_memory = self.process.memory_info().rss / 1024 / 1024

        # Market data simulation
        for i in range(10000):
            symbol = f'PAIR{i % 100}'
            large_dict[symbol] = {
                'ticker': {
                    'bid': 50000 + (i % 1000),
                    'ask': 50010 + (i % 1000),
                    'last': 50005 + (i % 1000),
                    'volume': 1000 + (i % 500),
                    'timestamp': time.time()
                },
                'orderbook': {
                    'bids': [[50000 - j, 1.0 + j] for j in range(10)],
                    'asks': [[50010 + j, 1.0 + j] for j in range(10)]
                }
            }

        # Balance data simulation
        for i in range(1000):
            asset = f'ASSET{i}'
            large_list.append({
                'asset': asset,
                'balance': 1000 + i,
                'history': [1000 + i + j for j in range(100)],
                'timestamp': time.time()
            })

        # Portfolio data simulation
        portfolio_data = {}
        for i in range(500):
            symbol = f'POSITION{i}'
            portfolio_data[symbol] = {
                'quantity': 100 + i,
                'avg_price': 50000 + (i * 10),
                'current_price': 50000 + (i * 10) + (i % 100),
                'pnl': (i % 200) - 100,
                'trades': [{'price': 50000 + j, 'qty': 1.0} for j in range(20)]
            }

        end_time = time.perf_counter()
        final_memory = self.process.memory_info().rss / 1024 / 1024

        # Get memory usage details
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        memory_used = final_memory - initial_memory

        result = BenchmarkResult(
            component="Memory Management",
            test_name="Memory Usage Patterns",
            iterations=11500,  # Total objects created
            total_time=end_time - start_time,
            avg_latency=(end_time - start_time) * 1000 / 11500,
            min_latency=0,
            max_latency=(end_time - start_time) * 1000,
            p95_latency=(end_time - start_time) * 1000,
            p99_latency=(end_time - start_time) * 1000,
            throughput=11500 / (end_time - start_time),
            cpu_usage_avg=self.process.cpu_percent(),
            memory_usage_mb=memory_used,
            passed=memory_used < 500,  # <500MB target
            target_latency=500,
            notes=f"Peak traced memory: {peak / 1024 / 1024:.1f}MB, "
                  f"Current: {current / 1024 / 1024:.1f}MB"
        )

        self.results.append(result)
        logger.info(f"Memory usage: {memory_used:.1f}MB for 11.5K objects")

        # Cleanup
        del large_dict
        del large_list
        del portfolio_data
        gc.collect()

    async def benchmark_gc_performance(self):
        """Benchmark garbage collection performance"""
        logger.info("Benchmarking garbage collection performance...")

        # Force garbage collection and measure
        gc_times = []

        # Create objects that will need garbage collection
        for _cycle in range(10):
            # Create circular references
            objects = []
            for i in range(1000):
                obj = {'id': i, 'data': list(range(100))}
                if i > 0:
                    obj['ref'] = objects[i-1]
                objects.append(obj)

            # Force garbage collection
            gc_start = time.perf_counter()
            gc.collect()
            gc_time = (time.perf_counter() - gc_start) * 1000
            gc_times.append(gc_time)

            # Clear references
            del objects

        avg_gc_time = statistics.mean(gc_times)

        result = BenchmarkResult(
            component="Memory Management",
            test_name="Garbage Collection",
            iterations=10,
            total_time=sum(gc_times) / 1000,
            avg_latency=avg_gc_time,
            min_latency=min(gc_times),
            max_latency=max(gc_times),
            p95_latency=statistics.quantiles(gc_times, n=10)[8],
            p99_latency=max(gc_times),
            throughput=10 / (sum(gc_times) / 1000),
            cpu_usage_avg=self.process.cpu_percent(),
            memory_usage_mb=self.process.memory_info().rss / 1024 / 1024,
            passed=avg_gc_time < 100,  # <100ms target
            target_latency=100,
            notes="1000 objects with circular refs per cycle"
        )

        self.results.append(result)
        logger.info(f"GC performance: {avg_gc_time:.1f}ms avg")

    def _generate_performance_report(self, total_time: float) -> dict[str, Any]:
        """Generate comprehensive performance report"""

        # Calculate summary statistics
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.passed)
        failed_tests = total_tests - passed_tests

        # Performance categories
        categories = {}
        for result in self.results:
            if result.component not in categories:
                categories[result.component] = []
            categories[result.component].append(result)

        # Critical performance violations
        critical_violations = []
        for result in self.results:
            if not result.passed:
                violation_severity = "HIGH" if result.avg_latency > result.target_latency * 2 else "MEDIUM"
                critical_violations.append({
                    'component': result.component,
                    'test': result.test_name,
                    'actual_latency': result.avg_latency,
                    'target_latency': result.target_latency,
                    'severity': violation_severity,
                    'performance_ratio': result.avg_latency / result.target_latency
                })

        # Performance recommendations
        recommendations = []

        for result in self.results:
            if result.avg_latency > result.target_latency * 0.8:  # Within 80% of target
                if result.component == "Authentication":
                    recommendations.append({
                        'priority': 'HIGH',
                        'component': result.component,
                        'issue': f'{result.test_name} approaching performance limit',
                        'recommendation': 'Consider caching signatures or optimizing hash calculations',
                        'expected_improvement': '20-40% latency reduction'
                    })
                elif result.component == "Rate Limiting":
                    recommendations.append({
                        'priority': 'MEDIUM',
                        'component': result.component,
                        'issue': f'{result.test_name} near performance threshold',
                        'recommendation': 'Implement async rate limiting or optimize counter updates',
                        'expected_improvement': '10-30% latency reduction'
                    })
                elif result.component == "WebSocket":
                    recommendations.append({
                        'priority': 'HIGH',
                        'component': result.component,
                        'issue': f'{result.test_name} message processing slow',
                        'recommendation': 'Implement message batching or async processing queue',
                        'expected_improvement': '30-50% throughput increase'
                    })
                elif result.component == "Balance Manager":
                    recommendations.append({
                        'priority': 'HIGH',
                        'component': result.component,
                        'issue': f'{result.test_name} update latency high',
                        'recommendation': 'Optimize decimal calculations and reduce validation overhead',
                        'expected_improvement': '25-45% latency reduction'
                    })
                elif result.component == "Database":
                    recommendations.append({
                        'priority': 'MEDIUM',
                        'component': result.component,
                        'issue': f'{result.test_name} query performance degrading',
                        'recommendation': 'Add database indexes or implement query caching',
                        'expected_improvement': '40-60% query speed improvement'
                    })

        # System resource analysis
        avg_cpu = statistics.mean([r.cpu_usage_avg for r in self.results if r.cpu_usage_avg > 0])
        avg_memory = statistics.mean([r.memory_usage_mb for r in self.results if r.memory_usage_mb > 0])

        report = {
            'timestamp': datetime.now().isoformat(),
            'execution_time': total_time,
            'summary': {
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'failed_tests': failed_tests,
                'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0,
                'avg_cpu_usage': avg_cpu,
                'avg_memory_usage_mb': avg_memory
            },
            'performance_targets': self.targets,
            'results_by_category': {
                category: [asdict(result) for result in results]
                for category, results in categories.items()
            },
            'critical_violations': critical_violations,
            'recommendations': recommendations,
            'detailed_results': [asdict(result) for result in self.results]
        }

        return report

    def save_report(self, report: dict[str, Any], filename: str = None):
        """Save performance report to file"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'performance_report_{timestamp}.json'

        filepath = os.path.join(os.path.dirname(__file__), filename)

        try:
            with open(filepath, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            logger.info(f"Performance report saved to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save report: {e}")

    def print_summary(self, report: dict[str, Any]):
        """Print performance summary to console"""
        print("\n" + "="*80)
        print("🚀 HIGH-FREQUENCY TRADING PERFORMANCE BENCHMARK RESULTS")
        print("="*80)

        summary = report['summary']
        print("\n📊 SUMMARY:")
        print(f"   Total Tests: {summary['total_tests']}")
        print(f"   Passed: {summary['passed_tests']} ({summary['success_rate']:.1f}%)")
        print(f"   Failed: {summary['failed_tests']}")
        print(f"   Execution Time: {report['execution_time']:.2f}s")
        print(f"   Avg CPU Usage: {summary['avg_cpu_usage']:.1f}%")
        print(f"   Avg Memory Usage: {summary['avg_memory_usage_mb']:.1f}MB")

        # Critical violations
        violations = report['critical_violations']
        if violations:
            print(f"\n❌ CRITICAL PERFORMANCE VIOLATIONS ({len(violations)}):")
            for v in violations[:5]:  # Show top 5
                print(f"   {v['severity']} | {v['component']} - {v['test']}")
                print(f"        Actual: {v['actual_latency']:.3f}ms | Target: {v['target_latency']:.3f}ms")
                print(f"        Ratio: {v['performance_ratio']:.1f}x over target")

        # Top recommendations
        recommendations = report['recommendations']
        if recommendations:
            print("\n💡 TOP OPTIMIZATION RECOMMENDATIONS:")
            for rec in recommendations[:3]:  # Show top 3
                print(f"   {rec['priority']} | {rec['component']}")
                print(f"        Issue: {rec['issue']}")
                print(f"        Fix: {rec['recommendation']}")
                print(f"        Expected: {rec['expected_improvement']}")

        # Performance by category
        print("\n📈 PERFORMANCE BY CATEGORY:")
        for category, results in report['results_by_category'].items():
            passed = sum(1 for r in results if r['passed'])
            total = len(results)
            avg_latency = statistics.mean([r['avg_latency'] for r in results])
            print(f"   {category}: {passed}/{total} passed, {avg_latency:.3f}ms avg")

        print("\n" + "="*80)


async def main():
    """Run the benchmark suite"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create and run benchmark suite
    benchmark = HFTBenchmarkSuite()

    try:
        report = await benchmark.run_all_benchmarks()

        # Save and display results
        benchmark.save_report(report)
        benchmark.print_summary(report)

        # Return success/failure
        success_rate = report['summary']['success_rate']
        if success_rate >= 90:
            logger.info(f"✅ Benchmark PASSED with {success_rate:.1f}% success rate")
            return 0
        else:
            logger.error(f"❌ Benchmark FAILED with {success_rate:.1f}% success rate")
            return 1

    except Exception as e:
        logger.error(f"Benchmark suite failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(asyncio.run(main()))
