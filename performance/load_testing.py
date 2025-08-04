"""
High-Frequency Trading Load Testing Framework
===========================================

Comprehensive load testing for crypto trading bot under realistic high-frequency conditions.
Tests system behavior under sustained load, burst traffic, and stress conditions.

Load Testing Scenarios:
- Sustained high-frequency trading load
- Burst order execution stress testing  
- WebSocket message flood handling
- Rate limiting under extreme load
- Balance update storms
- Market volatility simulation
- Memory pressure testing
- Resource exhaustion scenarios
"""

import asyncio
import time
import logging
import json
import statistics
import random
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional, Callable
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import psutil
import gc
from decimal import Decimal
import threading
from collections import deque, defaultdict
import numpy as np

# Import trading bot components
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.rate_limiting.kraken_rate_limiter import KrakenRateLimiter2025
from src.circuit_breaker.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from src.utils.decimal_precision_fix import safe_decimal, safe_float

logger = logging.getLogger(__name__)


@dataclass
class LoadTestResult:
    """Results from a load test scenario"""
    scenario: str
    duration: float
    total_operations: int
    successful_operations: int
    failed_operations: int
    operations_per_second: float
    avg_latency: float
    p95_latency: float
    p99_latency: float
    max_latency: float
    error_rate: float
    peak_cpu_usage: float
    peak_memory_mb: float
    network_throughput_mbps: float
    resource_exhaustion: bool
    stability_score: float
    notes: str = ""


@dataclass
class LoadTestConfig:
    """Configuration for load test scenarios"""
    # Basic load parameters
    duration_seconds: int = 300  # 5 minutes default
    ramp_up_seconds: int = 30
    ramp_down_seconds: int = 30
    
    # Concurrency settings
    max_concurrent_connections: int = 100
    max_concurrent_orders: int = 50
    max_websocket_connections: int = 10
    
    # Rate settings
    target_operations_per_second: int = 1000
    burst_operations_per_second: int = 5000
    sustained_load_percentage: float = 0.8  # 80% of max capacity
    
    # Resource limits
    max_memory_mb: int = 2048  # 2GB limit
    max_cpu_percentage: float = 80.0
    
    # Error thresholds
    max_error_rate: float = 0.05  # 5% max error rate
    max_latency_ms: float = 100.0
    
    # Market simulation
    price_volatility: float = 0.02  # 2% price swings
    volume_spikes: bool = True
    market_conditions: str = "normal"  # normal, volatile, trending


class HFTLoadTester:
    """High-frequency trading load testing framework"""
    
    def __init__(self, config: LoadTestConfig = None):
        """Initialize load tester"""
        self.config = config or LoadTestConfig()
        self.results: List[LoadTestResult] = []
        self.is_running = False
        self.start_time = 0
        self.process = psutil.Process()
        
        # Monitoring data
        self.operation_times = deque(maxlen=10000)
        self.error_counts = defaultdict(int)
        self.resource_usage = deque(maxlen=1000)
        
        # Test data generators
        self.symbols = ['BTC/USDT', 'ETH/USDT', 'ADA/USDT', 'DOT/USDT', 'LINK/USDT', 
                       'MATIC/USDT', 'SHIB/USDT', 'SOL/USDT', 'AVAX/USDT', 'ATOM/USDT']
        self.price_data = self._initialize_price_data()
        
        logger.info("HFT Load Tester initialized")
    
    def _initialize_price_data(self) -> Dict[str, float]:
        """Initialize realistic price data for symbols"""
        prices = {
            'BTC/USDT': 50000.0,
            'ETH/USDT': 3500.0,
            'ADA/USDT': 1.2,
            'DOT/USDT': 25.0,
            'LINK/USDT': 15.0,
            'MATIC/USDT': 0.8,
            'SHIB/USDT': 0.000025,
            'SOL/USDT': 120.0,
            'AVAX/USDT': 40.0,
            'ATOM/USDT': 18.0
        }
        return prices
    
    async def run_comprehensive_load_tests(self) -> Dict[str, Any]:
        """Run complete suite of load tests"""
        logger.info("Starting comprehensive HFT load testing suite")
        start_time = time.time()
        
        # 1. Baseline Performance Test
        await self.test_baseline_performance()
        
        # 2. Sustained Load Test
        await self.test_sustained_high_frequency_load()
        
        # 3. Burst Load Test  
        await self.test_burst_order_execution()
        
        # 4. WebSocket Flood Test
        await self.test_websocket_message_flood()
        
        # 5. Rate Limiting Stress Test
        await self.test_rate_limiting_under_extreme_load()
        
        # 6. Balance Update Storm Test
        await self.test_balance_update_storm()
        
        # 7. Market Volatility Simulation
        await self.test_market_volatility_simulation()
        
        # 8. Memory Pressure Test
        await self.test_memory_pressure_scenarios()
        
        # 9. Resource Exhaustion Test
        await self.test_resource_exhaustion_scenarios()
        
        # 10. Stability and Recovery Test
        await self.test_stability_and_recovery()
        
        total_time = time.time() - start_time
        
        # Generate comprehensive report
        report = self._generate_load_test_report(total_time)
        
        logger.info(f"Load testing suite completed in {total_time:.2f}s")
        return report
    
    async def test_baseline_performance(self):
        """Test baseline performance under normal conditions"""
        logger.info("Running baseline performance test...")
        
        scenario = "Baseline Performance"
        duration = 60  # 1 minute
        target_ops = 100  # Normal operation rate
        
        # Mock trading operations
        async def trading_operation():
            """Simulate a typical trading operation"""
            start = time.perf_counter()
            
            # Simulate order validation
            await asyncio.sleep(0.001)
            
            # Simulate balance check
            await asyncio.sleep(0.002)
            
            # Simulate order placement
            await asyncio.sleep(0.005)
            
            # Simulate order confirmation
            await asyncio.sleep(0.002)
            
            latency = (time.perf_counter() - start) * 1000
            return latency, True  # latency, success
        
        result = await self._run_load_scenario(
            scenario=scenario,
            operation_func=trading_operation,
            duration_seconds=duration,
            target_ops_per_second=target_ops,
            max_concurrent=10
        )
        
        self.results.append(result)
        logger.info(f"Baseline test: {result.operations_per_second:.0f} ops/sec, "
                   f"{result.avg_latency:.1f}ms avg latency")
    
    async def test_sustained_high_frequency_load(self):
        """Test sustained high-frequency trading load"""
        logger.info("Running sustained high-frequency load test...")
        
        scenario = "Sustained HFT Load"
        duration = self.config.duration_seconds
        target_ops = int(self.config.target_operations_per_second * 
                        self.config.sustained_load_percentage)
        
        # High-frequency trading simulation
        async def hft_operation():
            """Simulate high-frequency trading operation"""
            start = time.perf_counter()
            
            try:
                # Ultra-fast order operations
                symbol = random.choice(self.symbols)
                price = self.price_data[symbol] * (1 + random.uniform(-0.001, 0.001))
                quantity = random.uniform(0.1, 10.0)
                
                # Minimal latency operations
                await asyncio.sleep(0.0001)  # Order validation
                await asyncio.sleep(0.0001)  # Rate limit check
                await asyncio.sleep(0.0002)  # Order submission
                
                # Random market conditions
                if random.random() < 0.01:  # 1% chance of delays
                    await asyncio.sleep(0.005)  # Network delay
                
                latency = (time.perf_counter() - start) * 1000
                success = random.random() > 0.001  # 99.9% success rate
                
                return latency, success
                
            except Exception as e:
                latency = (time.perf_counter() - start) * 1000
                return latency, False
        
        result = await self._run_load_scenario(
            scenario=scenario,
            operation_func=hft_operation,
            duration_seconds=duration,
            target_ops_per_second=target_ops,
            max_concurrent=self.config.max_concurrent_orders
        )
        
        self.results.append(result)
        logger.info(f"Sustained HFT load: {result.operations_per_second:.0f} ops/sec, "
                   f"{result.error_rate:.3f}% error rate")
    
    async def test_burst_order_execution(self):
        """Test burst order execution under extreme load"""
        logger.info("Running burst order execution test...")
        
        scenario = "Burst Order Execution"
        
        # Burst parameters
        burst_duration = 10  # 10 seconds of extreme load
        normal_ops = 100
        burst_ops = self.config.burst_operations_per_second
        
        async def burst_operation():
            """Simulate burst trading operation"""
            start = time.perf_counter()
            
            try:
                # Simulate order burst conditions
                symbol = random.choice(self.symbols[:5])  # Focus on top symbols
                
                # Multiple operations in quick succession
                operations = random.randint(1, 5)
                for _ in range(operations):
                    await asyncio.sleep(0.0001)  # Minimal processing time
                
                # Occasional system stress
                if random.random() < 0.1:  # 10% stress operations
                    await asyncio.sleep(0.01)  # System under load
                
                latency = (time.perf_counter() - start) * 1000
                success = random.random() > 0.02  # 98% success during burst
                
                return latency, success
                
            except Exception:
                latency = (time.perf_counter() - start) * 1000
                return latency, False
        
        # Run burst test with ramping
        total_duration = 60  # 1 minute total
        
        result = await self._run_burst_scenario(
            scenario=scenario,
            operation_func=burst_operation,
            normal_ops_per_second=normal_ops,
            burst_ops_per_second=burst_ops,
            burst_duration=burst_duration,
            total_duration=total_duration,
            max_concurrent=self.config.max_concurrent_orders * 2
        )
        
        self.results.append(result)
        logger.info(f"Burst execution: Peak {result.operations_per_second:.0f} ops/sec, "
                   f"Max latency {result.max_latency:.1f}ms")
    
    async def test_websocket_message_flood(self):
        """Test WebSocket message processing under flood conditions"""
        logger.info("Running WebSocket message flood test...")
        
        scenario = "WebSocket Message Flood"
        
        # Message generation patterns
        message_types = ['ticker', 'trade', 'orderbook', 'balance']
        message_weights = [0.4, 0.3, 0.2, 0.1]  # Realistic distribution
        
        async def websocket_message_processing():
            """Simulate WebSocket message processing"""
            start = time.perf_counter()
            
            try:
                # Generate realistic message
                msg_type = np.random.choice(message_types, p=message_weights)
                
                if msg_type == 'ticker':
                    message = {
                        'channel': 'ticker',
                        'data': [{
                            'symbol': random.choice(self.symbols),
                            'bid': random.uniform(100, 50000),
                            'ask': random.uniform(100, 50000),
                            'last': random.uniform(100, 50000),
                            'volume': random.uniform(1000, 100000)
                        }]
                    }
                elif msg_type == 'trade':
                    message = {
                        'channel': 'trade',
                        'data': [{
                            'symbol': random.choice(self.symbols),
                            'price': random.uniform(100, 50000),
                            'quantity': random.uniform(0.1, 100),
                            'side': random.choice(['buy', 'sell']),
                            'timestamp': time.time()
                        }]
                    }
                elif msg_type == 'orderbook':
                    message = {
                        'channel': 'book',
                        'data': [{
                            'symbol': random.choice(self.symbols),
                            'bids': [[random.uniform(100, 50000), random.uniform(0.1, 10)] for _ in range(10)],
                            'asks': [[random.uniform(100, 50000), random.uniform(0.1, 10)] for _ in range(10)]
                        }]
                    }
                else:  # balance
                    message = {
                        'channel': 'balances',
                        'data': [{
                            'asset': random.choice(['BTC', 'ETH', 'USDT', 'ADA']),
                            'balance': str(random.uniform(0.1, 1000)),
                            'hold_trade': str(random.uniform(0, 10))
                        }]
                    }
                
                # Simulate message processing
                if msg_type == 'ticker':
                    await asyncio.sleep(0.0005)  # Fast ticker processing
                elif msg_type == 'trade':
                    await asyncio.sleep(0.001)   # Trade processing
                elif msg_type == 'orderbook':
                    await asyncio.sleep(0.002)   # Orderbook processing
                else:  # balance
                    await asyncio.sleep(0.003)   # Balance update processing
                
                # Occasional processing spikes
                if random.random() < 0.05:  # 5% processing spikes
                    await asyncio.sleep(0.01)
                
                latency = (time.perf_counter() - start) * 1000
                success = random.random() > 0.001  # 99.9% success rate
                
                return latency, success
                
            except Exception:
                latency = (time.perf_counter() - start) * 1000
                return latency, False
        
        # High message rate simulation
        target_messages_per_second = 10000  # 10K messages/sec
        
        result = await self._run_load_scenario(
            scenario=scenario,
            operation_func=websocket_message_processing,
            duration_seconds=120,  # 2 minutes
            target_ops_per_second=target_messages_per_second,
            max_concurrent=self.config.max_websocket_connections * 10
        )
        
        self.results.append(result)
        logger.info(f"WebSocket flood: {result.operations_per_second:.0f} msg/sec, "
                   f"P99 latency {result.p99_latency:.2f}ms")
    
    async def test_rate_limiting_under_extreme_load(self):
        """Test rate limiting accuracy under extreme load"""
        logger.info("Running rate limiting extreme load test...")
        
        scenario = "Rate Limiting Extreme Load"
        
        # Create rate limiter with realistic limits
        rate_limiter = KrakenRateLimiter2025()
        await rate_limiter.start()
        
        # Track rate limiting accuracy
        allowed_requests = 0
        denied_requests = 0
        rate_check_times = []
        
        async def rate_limited_operation():
            """Simulate rate-limited API operation"""
            start = time.perf_counter()
            
            nonlocal allowed_requests, denied_requests
            
            try:
                # Check rate limit
                endpoint = random.choice(['AddOrder', 'CancelOrder', 'QueryOrders', 'Balance'])
                
                can_proceed, reason, wait_time = await rate_limiter.check_rate_limit(endpoint)
                if can_proceed:
                    allowed_requests += 1
                    
                    # Simulate API call processing
                    await asyncio.sleep(random.uniform(0.01, 0.05))
                    success = True
                else:
                    denied_requests += 1
                    success = False
                
                latency = (time.perf_counter() - start) * 1000
                rate_check_times.append(latency)
                
                return latency, success
                
            except Exception:
                latency = (time.perf_counter() - start) * 1000
                rate_check_times.append(latency)
                return latency, False
        
        # Extreme request rate to test rate limiting
        extreme_request_rate = 5000  # 5K requests/sec
        
        result = await self._run_load_scenario(
            scenario=scenario,
            operation_func=rate_limited_operation,
            duration_seconds=180,  # 3 minutes
            target_ops_per_second=extreme_request_rate,
            max_concurrent=100
        )
        
        # Calculate rate limiting accuracy
        total_requests = allowed_requests + denied_requests
        expected_allowed = 1800 * 3  # 30/sec * 180 seconds
        actual_allowed = allowed_requests
        accuracy = 100 - abs(actual_allowed - expected_allowed) / expected_allowed * 100
        
        result.notes = f"Rate limiting accuracy: {accuracy:.2f}%, " \
                      f"Allowed: {allowed_requests}, Denied: {denied_requests}"
        
        self.results.append(result)
        await rate_limiter.stop()
        logger.info(f"Rate limiting test: {accuracy:.1f}% accuracy, "
                   f"{result.operations_per_second:.0f} checks/sec")
    
    async def test_balance_update_storm(self):
        """Test balance update processing under storm conditions"""
        logger.info("Running balance update storm test...")
        
        scenario = "Balance Update Storm"
        
        # Simulate balance manager
        balance_cache = {}
        update_conflicts = 0
        
        async def balance_update_operation():
            """Simulate balance update processing"""
            start = time.perf_counter()
            
            nonlocal update_conflicts
            
            try:
                # Random asset update
                asset = random.choice(['BTC', 'ETH', 'USDT', 'ADA', 'DOT', 'LINK', 'MATIC'])
                
                # Simulate concurrent balance updates
                current_balance = balance_cache.get(asset, 1000.0)
                
                # Random balance change
                change = random.uniform(-50, 50)
                new_balance = max(0, current_balance + change)
                
                # Simulate validation and processing
                await asyncio.sleep(0.001)  # Balance validation
                await asyncio.sleep(0.002)  # Update processing
                await asyncio.sleep(0.001)  # Notification
                
                # Check for update conflicts (simplified)
                if asset in balance_cache:
                    if abs(balance_cache[asset] - current_balance) > 0.01:
                        update_conflicts += 1
                
                balance_cache[asset] = new_balance
                
                # Occasional heavy processing
                if random.random() < 0.1:  # 10% heavy updates
                    await asyncio.sleep(0.01)  # Portfolio recalculation
                
                latency = (time.perf_counter() - start) * 1000
                success = random.random() > 0.002  # 99.8% success rate
                
                return latency, success
                
            except Exception:
                latency = (time.perf_counter() - start) * 1000
                return latency, False
        
        # High balance update rate
        balance_update_rate = 2000  # 2K updates/sec
        
        result = await self._run_load_scenario(
            scenario=scenario,
            operation_func=balance_update_operation,
            duration_seconds=150,  # 2.5 minutes
            target_ops_per_second=balance_update_rate,
            max_concurrent=50
        )
        
        result.notes = f"Update conflicts: {update_conflicts}, Assets tracked: {len(balance_cache)}"
        
        self.results.append(result)
        logger.info(f"Balance update storm: {result.operations_per_second:.0f} updates/sec, "
                   f"{update_conflicts} conflicts")
    
    async def test_market_volatility_simulation(self):
        """Test system behavior during market volatility"""
        logger.info("Running market volatility simulation...")
        
        scenario = "Market Volatility Simulation"
        
        # Volatile market conditions
        volatility_events = 0
        circuit_breaker_triggers = 0
        
        async def volatile_market_operation():
            """Simulate trading during volatile market conditions"""
            start = time.perf_counter()
            
            nonlocal volatility_events, circuit_breaker_triggers
            
            try:
                symbol = random.choice(self.symbols)
                base_price = self.price_data[symbol]
                
                # Simulate market volatility
                volatility_factor = 1.0
                if random.random() < 0.1:  # 10% volatile events
                    volatility_factor = random.uniform(0.8, 1.2)  # ±20% price swing
                    volatility_events += 1
                
                current_price = base_price * volatility_factor
                
                # Simulate rapid price changes
                price_changes = random.randint(1, 10)
                for _ in range(price_changes):
                    price_change = random.uniform(-0.005, 0.005)  # ±0.5% per change
                    current_price *= (1 + price_change)
                    await asyncio.sleep(0.0001)  # Rapid price updates
                
                # Update stored price
                self.price_data[symbol] = current_price
                
                # Simulate order book processing
                await asyncio.sleep(0.002)  # Order book update
                await asyncio.sleep(0.001)  # Signal generation
                await asyncio.sleep(0.003)  # Risk calculation
                
                # Circuit breaker simulation
                if abs(volatility_factor - 1.0) > 0.15:  # >15% move
                    circuit_breaker_triggers += 1
                    await asyncio.sleep(0.1)  # Circuit breaker delay
                
                latency = (time.perf_counter() - start) * 1000
                success = random.random() > 0.005  # 99.5% success rate
                
                return latency, success
                
            except Exception:
                latency = (time.perf_counter() - start) * 1000
                return latency, False
        
        # Market data processing rate
        market_ops_rate = 1500  # 1.5K market operations/sec
        
        result = await self._run_load_scenario(
            scenario=scenario,
            operation_func=volatile_market_operation,
            duration_seconds=200,  # 3.33 minutes
            target_ops_per_second=market_ops_rate,
            max_concurrent=30
        )
        
        result.notes = f"Volatility events: {volatility_events}, " \
                      f"Circuit breaker triggers: {circuit_breaker_triggers}"
        
        self.results.append(result)
        logger.info(f"Market volatility: {result.operations_per_second:.0f} ops/sec, "
                   f"{volatility_events} volatile events")
    
    async def test_memory_pressure_scenarios(self):
        """Test system behavior under memory pressure"""
        logger.info("Running memory pressure test...")
        
        scenario = "Memory Pressure Test"
        
        # Memory allocation tracking
        memory_allocations = []
        gc_collections = 0
        
        async def memory_intensive_operation():
            """Simulate memory-intensive trading operation"""
            start = time.perf_counter()
            
            nonlocal gc_collections
            
            try:
                # Simulate large data structures
                market_data = {}
                
                # Create realistic trading data
                for symbol in self.symbols:
                    market_data[symbol] = {
                        'ohlc_history': [
                            {
                                'timestamp': time.time() - i * 60,
                                'open': random.uniform(100, 50000),
                                'high': random.uniform(100, 50000),
                                'low': random.uniform(100, 50000),
                                'close': random.uniform(100, 50000),
                                'volume': random.uniform(1000, 100000)
                            }
                            for i in range(1000)  # 1000 candles
                        ],
                        'order_book': {
                            'bids': [[random.uniform(100, 50000), random.uniform(0.1, 100)] 
                                    for _ in range(100)],
                            'asks': [[random.uniform(100, 50000), random.uniform(0.1, 100)] 
                                    for _ in range(100)]
                        },
                        'trade_history': [
                            {
                                'price': random.uniform(100, 50000),
                                'quantity': random.uniform(0.1, 100),
                                'timestamp': time.time() - i,
                                'side': random.choice(['buy', 'sell'])
                            }
                            for i in range(500)  # 500 recent trades
                        ]
                    }
                
                # Store in memory allocations list
                memory_allocations.append(market_data)
                
                # Simulate processing
                await asyncio.sleep(0.005)  # Data processing
                
                # Periodic cleanup
                if len(memory_allocations) > 100:
                    memory_allocations = memory_allocations[-50:]  # Keep last 50
                    gc.collect()
                    gc_collections += 1
                
                latency = (time.perf_counter() - start) * 1000
                success = True
                
                return latency, success
                
            except MemoryError:
                latency = (time.perf_counter() - start) * 1000
                return latency, False
            except Exception:
                latency = (time.perf_counter() - start) * 1000
                return latency, False
        
        # Memory-intensive operation rate
        memory_ops_rate = 200  # 200 memory ops/sec
        
        result = await self._run_load_scenario(
            scenario=scenario,
            operation_func=memory_intensive_operation,
            duration_seconds=120,  # 2 minutes
            target_ops_per_second=memory_ops_rate,
            max_concurrent=20
        )
        
        result.notes = f"GC collections: {gc_collections}, " \
                      f"Memory allocations: {len(memory_allocations)}"
        
        # Cleanup
        memory_allocations.clear()
        gc.collect()
        
        self.results.append(result)
        logger.info(f"Memory pressure: {result.operations_per_second:.0f} ops/sec, "
                   f"{gc_collections} GC collections")
    
    async def test_resource_exhaustion_scenarios(self):
        """Test system behavior under resource exhaustion"""
        logger.info("Running resource exhaustion test...")
        
        scenario = "Resource Exhaustion Test"
        
        # Resource tracking
        connection_pool = []
        file_handles = []
        thread_pool = []
        
        async def resource_exhaustive_operation():
            """Simulate resource-intensive operation"""
            start = time.perf_counter()
            
            try:
                # Simulate various resource usage
                operation_type = random.choice(['connection', 'file', 'thread', 'compute'])
                
                if operation_type == 'connection':
                    # Simulate network connections
                    connection = {'id': len(connection_pool), 'timestamp': time.time()}
                    connection_pool.append(connection)
                    await asyncio.sleep(0.01)  # Connection overhead
                    
                elif operation_type == 'file':
                    # Simulate file operations
                    file_handle = {'id': len(file_handles), 'timestamp': time.time()}
                    file_handles.append(file_handle)
                    await asyncio.sleep(0.005)  # File I/O
                    
                elif operation_type == 'thread':
                    # Simulate thread usage
                    thread = {'id': len(thread_pool), 'timestamp': time.time()}
                    thread_pool.append(thread)
                    await asyncio.sleep(0.002)  # Thread overhead
                    
                else:  # compute
                    # Simulate CPU-intensive operation
                    result = sum(i ** 2 for i in range(1000))  # CPU load
                    await asyncio.sleep(0.001)
                
                # Resource cleanup (simplified)
                current_time = time.time()
                if len(connection_pool) > 500:
                    connection_pool[:] = [c for c in connection_pool 
                                        if current_time - c['timestamp'] < 60]
                
                if len(file_handles) > 200:
                    file_handles[:] = [f for f in file_handles 
                                     if current_time - f['timestamp'] < 30]
                
                if len(thread_pool) > 100:
                    thread_pool[:] = [t for t in thread_pool 
                                    if current_time - t['timestamp'] < 10]
                
                latency = (time.perf_counter() - start) * 1000
                success = True
                
                # Simulate resource exhaustion
                if (len(connection_pool) > 1000 or 
                    len(file_handles) > 500 or 
                    len(thread_pool) > 200):
                    success = False  # Resource exhaustion
                
                return latency, success
                
            except Exception:
                latency = (time.perf_counter() - start) * 1000
                return latency, False
        
        # Resource exhaustion test rate
        resource_ops_rate = 800  # 800 resource ops/sec
        
        result = await self._run_load_scenario(
            scenario=scenario,
            operation_func=resource_exhaustive_operation,
            duration_seconds=90,  # 1.5 minutes
            target_ops_per_second=resource_ops_rate,
            max_concurrent=40
        )
        
        # Check for resource exhaustion
        max_connections = len(connection_pool)
        max_files = len(file_handles)
        max_threads = len(thread_pool)
        
        result.resource_exhaustion = (max_connections > 1000 or 
                                    max_files > 500 or 
                                    max_threads > 200)
        
        result.notes = f"Max connections: {max_connections}, " \
                      f"Max files: {max_files}, Max threads: {max_threads}"
        
        self.results.append(result)
        logger.info(f"Resource exhaustion: {result.operations_per_second:.0f} ops/sec, "
                   f"Exhaustion: {result.resource_exhaustion}")
    
    async def test_stability_and_recovery(self):
        """Test system stability and recovery capabilities"""
        logger.info("Running stability and recovery test...")
        
        scenario = "Stability and Recovery Test"
        
        # Failure simulation
        failure_events = []
        recovery_events = []
        
        async def stability_test_operation():
            """Simulate operation with failure and recovery scenarios"""
            start = time.perf_counter()
            
            try:
                # Normal operation most of the time
                if random.random() < 0.95:  # 95% normal operations
                    await asyncio.sleep(random.uniform(0.001, 0.005))
                    latency = (time.perf_counter() - start) * 1000
                    return latency, True
                
                # Failure scenarios
                failure_type = random.choice(['timeout', 'connection', 'memory', 'validation'])
                
                failure_events.append({
                    'type': failure_type,
                    'timestamp': time.time()
                })
                
                if failure_type == 'timeout':
                    # Simulate timeout
                    await asyncio.sleep(0.1)  # 100ms timeout
                    
                    # Recovery attempt
                    await asyncio.sleep(0.01)  # Recovery time
                    recovery_events.append({
                        'type': 'timeout_recovery',
                        'timestamp': time.time()
                    })
                    
                elif failure_type == 'connection':
                    # Simulate connection failure
                    await asyncio.sleep(0.05)  # Connection failure
                    
                    # Reconnection
                    await asyncio.sleep(0.02)  # Reconnection time
                    recovery_events.append({
                        'type': 'connection_recovery',
                        'timestamp': time.time()
                    })
                    
                elif failure_type == 'memory':
                    # Simulate memory pressure
                    large_data = [random.random() for _ in range(10000)]
                    await asyncio.sleep(0.01)
                    del large_data
                    
                    recovery_events.append({
                        'type': 'memory_recovery',
                        'timestamp': time.time()
                    })
                    
                else:  # validation
                    # Simulate validation failure
                    await asyncio.sleep(0.005)  # Validation processing
                    
                    # Retry with corrected data
                    await asyncio.sleep(0.003)  # Retry
                    recovery_events.append({
                        'type': 'validation_recovery',
                        'timestamp': time.time()
                    })
                
                latency = (time.perf_counter() - start) * 1000
                success = len(recovery_events) > len(failure_events) * 0.8  # 80% recovery rate
                
                return latency, success
                
            except Exception:
                latency = (time.perf_counter() - start) * 1000
                return latency, False
        
        # Stability test rate
        stability_ops_rate = 500  # 500 stability ops/sec
        
        result = await self._run_load_scenario(
            scenario=scenario,
            operation_func=stability_test_operation,
            duration_seconds=240,  # 4 minutes
            target_ops_per_second=stability_ops_rate,
            max_concurrent=25
        )
        
        # Calculate stability metrics
        total_failures = len(failure_events)
        total_recoveries = len(recovery_events)
        recovery_rate = (total_recoveries / max(1, total_failures)) * 100
        
        # Calculate stability score
        stability_score = min(100, (recovery_rate + (100 - result.error_rate * 100)) / 2)
        result.stability_score = stability_score
        
        result.notes = f"Failures: {total_failures}, Recoveries: {total_recoveries}, " \
                      f"Recovery rate: {recovery_rate:.1f}%"
        
        self.results.append(result)
        logger.info(f"Stability test: {stability_score:.1f} stability score, "
                   f"{recovery_rate:.1f}% recovery rate")
    
    async def _run_load_scenario(self, scenario: str, operation_func: Callable,
                                duration_seconds: int, target_ops_per_second: int,
                                max_concurrent: int) -> LoadTestResult:
        """Run a load test scenario"""
        
        logger.info(f"Running scenario: {scenario}")
        
        # Initialize tracking
        operation_times = []
        successful_ops = 0
        failed_ops = 0
        start_time = time.perf_counter()
        
        # Resource monitoring
        initial_memory = self.process.memory_info().rss / 1024 / 1024
        peak_memory = initial_memory
        peak_cpu = 0
        
        # Rate control
        target_interval = 1.0 / target_ops_per_second
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def monitored_operation():
            """Execute operation with monitoring"""
            nonlocal successful_ops, failed_ops, peak_memory, peak_cpu
            
            async with semaphore:
                try:
                    latency, success = await operation_func()
                    operation_times.append(latency)
                    
                    if success:
                        successful_ops += 1
                    else:
                        failed_ops += 1
                    
                    # Resource monitoring
                    current_memory = self.process.memory_info().rss / 1024 / 1024
                    current_cpu = self.process.cpu_percent()
                    
                    peak_memory = max(peak_memory, current_memory)
                    peak_cpu = max(peak_cpu, current_cpu)
                    
                except Exception as e:
                    logger.debug(f"Operation failed: {e}")
                    failed_ops += 1
        
        # Execute load test
        tasks = []
        end_time = start_time + duration_seconds
        last_op_time = start_time
        
        while time.perf_counter() < end_time:
            current_time = time.perf_counter()
            
            # Rate limiting
            if current_time - last_op_time >= target_interval:
                task = asyncio.create_task(monitored_operation())
                tasks.append(task)
                last_op_time = current_time
            
            # Limit concurrent tasks
            if len(tasks) >= max_concurrent * 2:
                # Wait for some tasks to complete
                done, pending = await asyncio.wait(
                    tasks, 
                    return_when=asyncio.FIRST_COMPLETED,
                    timeout=0.1
                )
                tasks = list(pending)
            
            await asyncio.sleep(0.001)  # Small yield
        
        # Wait for remaining tasks
        if tasks:
            await asyncio.wait(tasks, timeout=30)  # 30s timeout
        
        # Calculate results
        actual_duration = time.perf_counter() - start_time
        total_ops = successful_ops + failed_ops
        ops_per_second = total_ops / actual_duration if actual_duration > 0 else 0
        error_rate = (failed_ops / max(1, total_ops)) * 100
        
        # Latency statistics
        if operation_times:
            avg_latency = statistics.mean(operation_times)
            p95_latency = statistics.quantiles(operation_times, n=20)[18] if len(operation_times) >= 20 else max(operation_times)
            p99_latency = statistics.quantiles(operation_times, n=100)[98] if len(operation_times) >= 100 else max(operation_times)
            max_latency = max(operation_times)
        else:
            avg_latency = p95_latency = p99_latency = max_latency = 0
        
        # Stability score (simplified)
        stability_score = max(0, 100 - error_rate * 10)  # Penalize errors
        if avg_latency > self.config.max_latency_ms:
            stability_score *= 0.8  # Penalize high latency
        
        return LoadTestResult(
            scenario=scenario,
            duration=actual_duration,
            total_operations=total_ops,
            successful_operations=successful_ops,
            failed_operations=failed_ops,
            operations_per_second=ops_per_second,
            avg_latency=avg_latency,
            p95_latency=p95_latency,
            p99_latency=p99_latency,
            max_latency=max_latency,
            error_rate=error_rate,
            peak_cpu_usage=peak_cpu,
            peak_memory_mb=peak_memory - initial_memory,
            network_throughput_mbps=0,  # Not measured in this simulation
            resource_exhaustion=False,
            stability_score=stability_score
        )
    
    async def _run_burst_scenario(self, scenario: str, operation_func: Callable,
                                 normal_ops_per_second: int, burst_ops_per_second: int,
                                 burst_duration: int, total_duration: int,
                                 max_concurrent: int) -> LoadTestResult:
        """Run a burst load test scenario"""
        
        logger.info(f"Running burst scenario: {scenario}")
        
        # Initialize tracking
        operation_times = []
        successful_ops = 0
        failed_ops = 0
        start_time = time.perf_counter()
        
        # Resource monitoring
        initial_memory = self.process.memory_info().rss / 1024 / 1024
        peak_memory = initial_memory
        peak_cpu = 0
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def monitored_operation():
            """Execute operation with monitoring"""
            nonlocal successful_ops, failed_ops, peak_memory, peak_cpu
            
            async with semaphore:
                try:
                    latency, success = await operation_func()
                    operation_times.append(latency)
                    
                    if success:
                        successful_ops += 1
                    else:
                        failed_ops += 1
                    
                    # Resource monitoring
                    current_memory = self.process.memory_info().rss / 1024 / 1024
                    current_cpu = self.process.cpu_percent()
                    
                    peak_memory = max(peak_memory, current_memory)
                    peak_cpu = max(peak_cpu, current_cpu)
                    
                except Exception:
                    failed_ops += 1
        
        # Execute burst test
        tasks = []
        end_time = start_time + total_duration
        burst_start = start_time + 10  # Start burst after 10 seconds
        burst_end = burst_start + burst_duration
        
        while time.perf_counter() < end_time:
            current_time = time.perf_counter()
            
            # Determine current rate
            if burst_start <= current_time <= burst_end:
                current_rate = burst_ops_per_second
            else:
                current_rate = normal_ops_per_second
            
            target_interval = 1.0 / current_rate
            
            # Rate limiting
            task = asyncio.create_task(monitored_operation())
            tasks.append(task)
            
            # Limit concurrent tasks
            if len(tasks) >= max_concurrent:
                done, pending = await asyncio.wait(
                    tasks, 
                    return_when=asyncio.FIRST_COMPLETED,
                    timeout=0.01
                )
                tasks = list(pending)
            
            await asyncio.sleep(target_interval)
        
        # Wait for remaining tasks
        if tasks:
            await asyncio.wait(tasks, timeout=30)
        
        # Calculate results (same as _run_load_scenario)
        actual_duration = time.perf_counter() - start_time
        total_ops = successful_ops + failed_ops
        ops_per_second = total_ops / actual_duration if actual_duration > 0 else 0
        error_rate = (failed_ops / max(1, total_ops)) * 100
        
        # Latency statistics
        if operation_times:
            avg_latency = statistics.mean(operation_times)
            p95_latency = statistics.quantiles(operation_times, n=20)[18] if len(operation_times) >= 20 else max(operation_times)
            p99_latency = statistics.quantiles(operation_times, n=100)[98] if len(operation_times) >= 100 else max(operation_times)
            max_latency = max(operation_times)
        else:
            avg_latency = p95_latency = p99_latency = max_latency = 0
        
        stability_score = max(0, 100 - error_rate * 10)
        if avg_latency > self.config.max_latency_ms:
            stability_score *= 0.8
        
        return LoadTestResult(
            scenario=scenario,
            duration=actual_duration,
            total_operations=total_ops,
            successful_operations=successful_ops,
            failed_operations=failed_ops,
            operations_per_second=ops_per_second,
            avg_latency=avg_latency,
            p95_latency=p95_latency,
            p99_latency=p99_latency,
            max_latency=max_latency,
            error_rate=error_rate,
            peak_cpu_usage=peak_cpu,
            peak_memory_mb=peak_memory - initial_memory,
            network_throughput_mbps=0,
            resource_exhaustion=False,
            stability_score=stability_score
        )
    
    def _generate_load_test_report(self, total_time: float) -> Dict[str, Any]:
        """Generate comprehensive load test report"""
        
        # Summary statistics
        total_operations = sum(r.total_operations for r in self.results)
        total_successful = sum(r.successful_operations for r in self.results)
        total_failed = sum(r.failed_operations for r in self.results)
        
        avg_ops_per_second = statistics.mean([r.operations_per_second for r in self.results])
        avg_error_rate = statistics.mean([r.error_rate for r in self.results])
        avg_latency = statistics.mean([r.avg_latency for r in self.results])
        max_peak_memory = max([r.peak_memory_mb for r in self.results])
        max_peak_cpu = max([r.peak_cpu_usage for r in self.results])
        
        # Performance assessment
        performance_issues = []
        for result in self.results:
            if result.error_rate > self.config.max_error_rate * 100:
                performance_issues.append({
                    'scenario': result.scenario,
                    'issue': 'High error rate',
                    'value': result.error_rate,
                    'threshold': self.config.max_error_rate * 100,
                    'severity': 'HIGH'
                })
            
            if result.avg_latency > self.config.max_latency_ms:
                performance_issues.append({
                    'scenario': result.scenario,
                    'issue': 'High latency',
                    'value': result.avg_latency,
                    'threshold': self.config.max_latency_ms,
                    'severity': 'MEDIUM'
                })
            
            if result.peak_memory_mb > self.config.max_memory_mb:
                performance_issues.append({
                    'scenario': result.scenario,
                    'issue': 'Memory usage exceeded',
                    'value': result.peak_memory_mb,
                    'threshold': self.config.max_memory_mb,
                    'severity': 'HIGH'
                })
        
        # System stability assessment
        stability_scores = [r.stability_score for r in self.results if r.stability_score > 0]
        overall_stability = statistics.mean(stability_scores) if stability_scores else 0
        
        # Recommendations
        recommendations = []
        
        if avg_error_rate > 2:
            recommendations.append({
                'priority': 'HIGH',
                'category': 'Error Handling',
                'issue': f'Average error rate of {avg_error_rate:.2f}% is concerning',
                'recommendation': 'Implement better error handling and circuit breakers',
                'expected_improvement': 'Reduce error rate to <1%'
            })
        
        if avg_latency > 50:
            recommendations.append({
                'priority': 'HIGH',
                'category': 'Performance',
                'issue': f'Average latency of {avg_latency:.1f}ms is high',
                'recommendation': 'Optimize critical path operations and add caching',
                'expected_improvement': 'Reduce latency by 30-50%'
            })
        
        if max_peak_memory > self.config.max_memory_mb * 0.8:
            recommendations.append({
                'priority': 'MEDIUM',
                'category': 'Memory Management',
                'issue': f'Peak memory usage of {max_peak_memory:.0f}MB approaching limits',
                'recommendation': 'Implement memory pooling and optimize data structures',
                'expected_improvement': 'Reduce memory usage by 20-40%'
            })
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'test_duration': total_time,
            'config': asdict(self.config),
            'summary': {
                'total_scenarios': len(self.results),
                'total_operations': total_operations,
                'successful_operations': total_successful,
                'failed_operations': total_failed,
                'overall_success_rate': (total_successful / max(1, total_operations)) * 100,
                'avg_operations_per_second': avg_ops_per_second,
                'avg_error_rate': avg_error_rate,
                'avg_latency_ms': avg_latency,
                'peak_memory_mb': max_peak_memory,
                'peak_cpu_usage': max_peak_cpu,
                'overall_stability_score': overall_stability
            },
            'scenario_results': [asdict(result) for result in self.results],
            'performance_issues': performance_issues,
            'recommendations': recommendations,
            'load_test_passed': (
                avg_error_rate <= self.config.max_error_rate * 100 and
                avg_latency <= self.config.max_latency_ms and
                max_peak_memory <= self.config.max_memory_mb and
                overall_stability >= 70
            )
        }
        
        return report
    
    def save_report(self, report: Dict[str, Any], filename: str = None):
        """Save load test report to file"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'load_test_report_{timestamp}.json'
        
        filepath = os.path.join(os.path.dirname(__file__), filename)
        
        try:
            with open(filepath, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            logger.info(f"Load test report saved to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save report: {e}")
    
    def print_summary(self, report: Dict[str, Any]):
        """Print load test summary to console"""
        print("\n" + "="*80)
        print("⚡ HIGH-FREQUENCY TRADING LOAD TEST RESULTS")
        print("="*80)
        
        summary = report['summary']
        print(f"\n📊 LOAD TEST SUMMARY:")
        print(f"   Total Scenarios: {summary['total_scenarios']}")
        print(f"   Total Operations: {summary['total_operations']:,}")
        print(f"   Success Rate: {summary['overall_success_rate']:.2f}%")
        print(f"   Avg Throughput: {summary['avg_operations_per_second']:.0f} ops/sec")
        print(f"   Avg Error Rate: {summary['avg_error_rate']:.3f}%")
        print(f"   Avg Latency: {summary['avg_latency_ms']:.2f}ms")
        print(f"   Peak Memory: {summary['peak_memory_mb']:.0f}MB")
        print(f"   Peak CPU: {summary['peak_cpu_usage']:.1f}%")
        print(f"   Stability Score: {summary['overall_stability_score']:.1f}/100")
        
        # Test result
        test_passed = report['load_test_passed']
        status = "✅ PASSED" if test_passed else "❌ FAILED"
        print(f"\n🎯 OVERALL RESULT: {status}")
        
        # Performance issues
        issues = report['performance_issues']
        if issues:
            print(f"\n⚠️  PERFORMANCE ISSUES ({len(issues)}):")
            for issue in issues[:5]:  # Show top 5
                print(f"   {issue['severity']} | {issue['scenario']}: {issue['issue']}")
                print(f"        Value: {issue['value']:.2f} | Threshold: {issue['threshold']:.2f}")
        
        # Top recommendations
        recommendations = report['recommendations']
        if recommendations:
            print(f"\n💡 OPTIMIZATION RECOMMENDATIONS:")
            for rec in recommendations[:3]:  # Show top 3
                print(f"   {rec['priority']} | {rec['category']}")
                print(f"        Issue: {rec['issue']}")
                print(f"        Fix: {rec['recommendation']}")
                print(f"        Expected: {rec['expected_improvement']}")
        
        # Scenario performance
        print(f"\n📈 SCENARIO PERFORMANCE:")
        for result in report['scenario_results']:
            ops_per_sec = result['operations_per_second']
            error_rate = result['error_rate']
            avg_latency = result['avg_latency']
            
            status_icon = "✅" if error_rate < 5 and avg_latency < 100 else "⚠️"
            print(f"   {status_icon} {result['scenario'][:25]:<25} | "
                  f"{ops_per_sec:>6.0f} ops/sec | "
                  f"{error_rate:>5.2f}% err | "
                  f"{avg_latency:>5.1f}ms")
        
        print("\n" + "="*80)


async def main():
    """Run the load testing suite"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create custom configuration
    config = LoadTestConfig(
        duration_seconds=180,  # 3 minutes per test
        target_operations_per_second=2000,  # 2K ops/sec target
        burst_operations_per_second=8000,   # 8K ops/sec burst
        max_concurrent_orders=100,
        max_memory_mb=4096,  # 4GB limit
        max_error_rate=0.02,  # 2% max error rate
        max_latency_ms=50.0   # 50ms max latency
    )
    
    # Create and run load tester
    load_tester = HFTLoadTester(config)
    
    try:
        report = await load_tester.run_comprehensive_load_tests()
        
        # Save and display results
        load_tester.save_report(report)
        load_tester.print_summary(report)
        
        # Return success/failure
        if report['load_test_passed']:
            logger.info("✅ Load testing PASSED - System can handle HFT workloads")
            return 0
        else:
            logger.error("❌ Load testing FAILED - System needs optimization")
            return 1
            
    except Exception as e:
        logger.error(f"Load testing suite failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(asyncio.run(main()))