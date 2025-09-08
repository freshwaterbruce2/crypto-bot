#!/usr/bin/env python3
"""
Performance and Load Testing Framework
Tests system performance under various load conditions and stress scenarios
"""

import asyncio
import pytest
import time
import statistics
import psutil
import os
from decimal import Decimal
from typing import Dict, Any, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, patch
from concurrent.futures import ThreadPoolExecutor
import threading

from engine.trading.trading_config import TradingConfig
from engine.market_data.market_data_processor import MarketDataProcessor
from engine.risk_manager_enhanced import EnhancedRiskManager
from engine.order_execution.order_executor import OrderExecutor
from engine.state.state_manager import StateManager
from engine.config.config_manager import ConfigManager
from engine.risk.circuit_breaker import CircuitBreaker


class PerformanceMetrics:
    """Performance metrics collector"""

    def __init__(self):
        self.metrics = {
            "execution_times": [],
            "memory_usage": [],
            "cpu_usage": [],
            "error_count": 0,
            "success_count": 0,
        }
        self.start_time = time.time()
        self.memory_monitor_active = False

    def record_execution_time(self, operation: str, duration: float):
        """Record execution time for an operation"""
        self.metrics["execution_times"].append(
            {"operation": operation, "duration": duration, "timestamp": time.time()}
        )

    def record_memory_usage(self):
        """Record current memory usage"""
        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / 1024 / 1024
        self.metrics["memory_usage"].append(
            {"memory_mb": memory_mb, "timestamp": time.time()}
        )

    def record_cpu_usage(self):
        """Record current CPU usage"""
        cpu_percent = psutil.cpu_percent(interval=0.1)
        self.metrics["cpu_usage"].append(
            {"cpu_percent": cpu_percent, "timestamp": time.time()}
        )

    def record_result(self, success: bool):
        """Record operation result"""
        if success:
            self.metrics["success_count"] += 1
        else:
            self.metrics["error_count"] += 1

    def start_memory_monitoring(self):
        """Start background memory monitoring"""
        self.memory_monitor_active = True

        def monitor_memory():
            while self.memory_monitor_active:
                self.record_memory_usage()
                time.sleep(0.5)  # Monitor every 500ms

        monitor_thread = threading.Thread(target=monitor_memory, daemon=True)
        monitor_thread.start()

    def stop_memory_monitoring(self):
        """Stop background memory monitoring"""
        self.memory_monitor_active = False

    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        total_time = time.time() - self.start_time
        execution_times = [m["duration"] for m in self.metrics["execution_times"]]

        summary = {
            "total_test_time": total_time,
            "total_operations": len(self.metrics["execution_times"]),
            "operations_per_second": len(self.metrics["execution_times"]) / total_time
            if total_time > 0
            else 0,
            "success_rate": self.metrics["success_count"]
            / (self.metrics["success_count"] + self.metrics["error_count"])
            if (self.metrics["success_count"] + self.metrics["error_count"]) > 0
            else 0,
            "error_count": self.metrics["error_count"],
        }

        if execution_times:
            summary.update(
                {
                    "avg_execution_time": statistics.mean(execution_times),
                    "median_execution_time": statistics.median(execution_times),
                    "min_execution_time": min(execution_times),
                    "max_execution_time": max(execution_times),
                    "execution_time_stddev": statistics.stdev(execution_times)
                    if len(execution_times) > 1
                    else 0,
                }
            )

        if self.metrics["memory_usage"]:
            memory_values = [m["memory_mb"] for m in self.metrics["memory_usage"]]
            summary.update(
                {
                    "avg_memory_mb": statistics.mean(memory_values),
                    "max_memory_mb": max(memory_values),
                    "memory_growth_mb": memory_values[-1] - memory_values[0]
                    if len(memory_values) > 1
                    else 0,
                }
            )

        if self.metrics["cpu_usage"]:
            cpu_values = [m["cpu_percent"] for m in self.metrics["cpu_usage"]]
            summary.update(
                {
                    "avg_cpu_percent": statistics.mean(cpu_values),
                    "max_cpu_percent": max(cpu_values),
                }
            )

        return summary


class LoadGenerator:
    """Load generator for stress testing"""

    def __init__(self, num_concurrent_users: int = 10):
        self.num_concurrent_users = num_concurrent_users
        self.tasks = []

    async def generate_market_data_load(
        self, market_processor: MarketDataProcessor, duration_seconds: int = 30
    ) -> List[Dict[str, Any]]:
        """Generate high-frequency market data load"""
        messages = []
        start_time = time.time()
        message_count = 0

        while time.time() - start_time < duration_seconds:
            # Generate realistic market data updates
            for symbol in ["XXLMZUSD", "XXBTZUSD", "XETHZUSD"]:
                message = {
                    "channel": "ticker",
                    "type": "update",
                    "data": [
                        {
                            "symbol": symbol,
                            "last_price": f"0.{350 + message_count % 100}",  # Varying prices
                            "bid": f"0.{349 + message_count % 100}",
                            "ask": f"0.{351 + message_count % 100}",
                            "volume": "10000.0",
                        }
                    ],
                }
                messages.append(message)
                message_count += 1

            await asyncio.sleep(0.01)  # 100 messages per second

        return messages

    async def generate_risk_evaluation_load(
        self, risk_manager: EnhancedRiskManager, num_evaluations: int = 1000
    ) -> List[Tuple[float, bool]]:
        """Generate high-volume risk evaluation load"""
        results = []

        # Pre-generate test data
        test_cases = []
        for i in range(num_evaluations):
            market_data = {
                "last_price": Decimal(f"0.{350 + i % 50}"),
                "bid": Decimal(f"0.{349 + i % 50}"),
                "ask": Decimal(f"0.{351 + i % 50}"),
                "volatility": Decimal("0.02"),
                "market_condition": "normal",
            }
            test_cases.append(
                (
                    Decimal("10.0"),  # position_size
                    market_data["last_price"],  # entry_price
                    Decimal("500.0"),  # account_balance
                    market_data,
                )
            )

        # Execute evaluations concurrently
        semaphore = asyncio.Semaphore(50)  # Limit concurrent evaluations

        async def evaluate_with_timing(
            position_size, entry_price, account_balance, market_data
        ):
            async with semaphore:
                start_time = time.time()
                try:
                    approved, _, _ = await risk_manager.evaluate_trade_risk_enhanced(
                        position_size, entry_price, account_balance, market_data
                    )
                    duration = time.time() - start_time
                    return duration, approved
                except Exception as e:
                    duration = time.time() - start_time
                    return duration, False

        tasks = [evaluate_with_timing(*test_case) for test_case in test_cases]
        results = await asyncio.gather(*tasks)

        return results

    async def generate_order_execution_load(
        self, order_executor: OrderExecutor, num_orders: int = 500
    ) -> List[Tuple[float, bool]]:
        """Generate high-volume order execution load"""
        results = []

        async def execute_with_timing(order_id: int):
            start_time = time.time()
            try:
                result = await order_executor.execute_order(
                    order_type="buy" if order_id % 2 == 0 else "sell",
                    volume="10.0",
                    price="0.35",
                )
                duration = time.time() - start_time
                success = "order_id" in result
                return duration, success
            except Exception as e:
                duration = time.time() - start_time
                return duration, False

        tasks = [execute_with_timing(i) for i in range(num_orders)]
        results = await asyncio.gather(*tasks)

        return results


class TestPerformanceLoad:
    """Performance and load testing suite"""

    @pytest.fixture
    def performance_setup(self):
        """Setup performance testing environment (synchronous fixture for tests)"""
        # Initialize components
        config = TradingConfig()
        config_manager = ConfigManager()
        market_processor = MarketDataProcessor(config, config_manager)

        with (
            patch("src.exchange.kraken_ws_client_unified.KrakenWebSocketUnified"),
            patch("src.exchange.kraken_rest_client.KrakenRESTClient"),
        ):
            risk_manager = EnhancedRiskManager(config, config_manager)
            order_executor = OrderExecutor(config, config_manager, CircuitBreaker())

        # Run any async initializers synchronously using the running loop
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(
                market_processor.initialize()
                if hasattr(market_processor, "initialize")
                else asyncio.sleep(0)
            )
        except RuntimeError:
            # If loop already running (rare in pytest), skip direct execution
            pass

        return {
            "config": config,
            "market_processor": market_processor,
            "risk_manager": risk_manager,
            "order_executor": order_executor,
            "metrics": PerformanceMetrics(),
            "load_generator": LoadGenerator(),
        }

    @pytest.mark.asyncio
    async def test_market_data_processing_performance(self, performance_setup):
        """Test market data processing performance under load"""
        setup = performance_setup
        market_processor = setup["market_processor"]
        load_generator = setup["load_generator"]
        metrics = setup["metrics"]

        # Generate high-frequency market data
        messages = await load_generator.generate_market_data_load(
            market_processor, duration_seconds=5
        )

        # Process messages and measure performance
        start_time = time.time()

        for message in messages:
            msg_start = time.time()
            success = market_processor.process_message(message)
            msg_duration = time.time() - msg_start

            metrics.record_execution_time("market_data_processing", msg_duration)
            metrics.record_result(success)

        total_time = time.time() - start_time

        # Performance assertions
        summary = metrics.get_summary()
        assert summary["avg_execution_time"] < 0.001  # < 1ms per message
        assert summary["success_rate"] > 0.99  # > 99% success rate
        assert summary["operations_per_second"] > 1000  # > 1000 messages/second

        print(
            f"Market Data Performance: {summary['operations_per_second']:.0f} msg/sec, "
            f"{summary['avg_execution_time'] * 1000:.2f}ms avg"
        )

    @pytest.mark.asyncio
    async def test_risk_evaluation_performance(self, performance_setup):
        """Test risk evaluation performance under high load"""
        setup = performance_setup
        risk_manager = setup["risk_manager"]
        load_generator = setup["load_generator"]
        metrics = setup["metrics"]

        # Generate high-volume risk evaluation load
        results = await load_generator.generate_risk_evaluation_load(
            risk_manager, num_evaluations=1000
        )

        # Record performance metrics
        for duration, success in results:
            metrics.record_execution_time("risk_evaluation", duration)
            metrics.record_result(success)

        # Performance assertions
        summary = metrics.get_summary()
        assert summary["avg_execution_time"] < 0.01  # < 10ms per evaluation
        assert summary["success_rate"] > 0.99  # > 99% success rate
        assert summary["operations_per_second"] > 50  # > 50 evaluations/second

        print(
            f"Risk Evaluation Performance: {summary['operations_per_second']:.0f} eval/sec, "
            f"{summary['avg_execution_time'] * 1000:.2f}ms avg"
        )

    @pytest.mark.asyncio
    async def test_order_execution_performance(self, performance_setup):
        """Test order execution performance under load"""
        setup = performance_setup
        order_executor = setup["order_executor"]
        load_generator = setup["load_generator"]
        metrics = setup["metrics"]

        # Generate high-volume order execution load
        results = await load_generator.generate_order_execution_load(
            order_executor, num_orders=200
        )

        # Record performance metrics
        for duration, success in results:
            metrics.record_execution_time("order_execution", duration)
            metrics.record_result(success)

        # Performance assertions
        summary = metrics.get_summary()
        assert summary["avg_execution_time"] < 0.1  # < 100ms per order
        assert (
            summary["success_rate"] > 0.95
        )  # > 95% success rate (some may fail due to rate limits)
        assert summary["operations_per_second"] > 5  # > 5 orders/second

        print(
            f"Order Execution Performance: {summary['operations_per_second']:.1f} orders/sec, "
            f"{summary['avg_execution_time'] * 1000:.2f}ms avg"
        )

    @pytest.mark.asyncio
    async def test_concurrent_load_performance(self, performance_setup):
        """Test system performance under concurrent load"""
        setup = performance_setup
        market_processor = setup["market_processor"]
        risk_manager = setup["risk_manager"]
        metrics = setup["metrics"]

        metrics.start_memory_monitoring()

        # Run multiple load generators concurrently
        async def market_data_load():
            messages = await setup["load_generator"].generate_market_data_load(
                market_processor, duration_seconds=10
            )
            for message in messages:
                start_time = time.time()
                success = market_processor.process_message(message)
                duration = time.time() - start_time
                metrics.record_execution_time("concurrent_market_data", duration)
                metrics.record_result(success)

        async def risk_evaluation_load():
            results = await setup["load_generator"].generate_risk_evaluation_load(
                risk_manager, num_evaluations=500
            )
            for duration, success in results:
                metrics.record_execution_time("concurrent_risk_eval", duration)
                metrics.record_result(success)

        # Execute concurrent loads
        start_time = time.time()
        await asyncio.gather(market_data_load(), risk_evaluation_load())
        total_time = time.time() - start_time

        metrics.stop_memory_monitoring()

        # Performance assertions
        summary = metrics.get_summary()
        assert summary["operations_per_second"] > 100  # > 100 operations/second total
        assert summary["success_rate"] > 0.98  # > 98% success rate
        assert summary["avg_memory_mb"] < 200  # < 200MB memory usage
        assert summary["max_cpu_percent"] < 80  # < 80% CPU usage

        print(
            f"Concurrent Load Performance: {summary['operations_per_second']:.0f} ops/sec, "
            f"{summary['avg_memory_mb']:.1f}MB memory, {summary['max_cpu_percent']:.1f}% CPU"
        )

    @pytest.mark.asyncio
    async def test_memory_leak_detection(self, performance_setup):
        """Test for memory leaks under sustained load"""
        setup = performance_setup
        market_processor = setup["market_processor"]
        metrics = setup["metrics"]

        metrics.start_memory_monitoring()

        # Sustained load test
        start_time = time.time()
        message_count = 0

        while time.time() - start_time < 30:  # 30 second test
            # Generate and process market data
            message = {
                "channel": "ticker",
                "type": "update",
                "data": [
                    {
                        "symbol": "XXLMZUSD",
                        "last_price": f"0.{350 + message_count % 100}",
                        "bid": f"0.{349 + message_count % 100}",
                        "ask": f"0.{351 + message_count % 100}",
                        "volume": "10000.0",
                    }
                ],
            }

            msg_start = time.time()
            success = market_processor.process_message(message)
            duration = time.time() - msg_start

            metrics.record_execution_time("memory_test", duration)
            metrics.record_result(success)
            message_count += 1

            await asyncio.sleep(0.01)  # Small delay to prevent overwhelming

        metrics.stop_memory_monitoring()

        # Memory leak detection
        summary = metrics.get_summary()

        # Check for significant memory growth (potential leak)
        if summary["memory_growth_mb"] > 50:  # More than 50MB growth
            pytest.fail(
                f"Potential memory leak detected: {summary['memory_growth_mb']:.1f}MB growth"
            )

        # Performance should remain consistent
        assert summary["avg_execution_time"] < 0.005  # < 5ms per message
        assert summary["success_rate"] > 0.99  # > 99% success rate

        print(
            f"Memory Leak Test: {summary['memory_growth_mb']:.1f}MB growth, "
            f"{message_count} messages processed"
        )

    @pytest.mark.asyncio
    async def test_scalability_under_increasing_load(self, performance_setup):
        """Test system scalability as load increases"""
        setup = performance_setup
        market_processor = setup["market_processor"]
        risk_manager = setup["risk_manager"]
        metrics = setup["metrics"]

        load_levels = [10, 50, 100, 200]  # Messages per second
        performance_results = []

        for load_level in load_levels:
            level_start = time.time()
            message_count = 0

            # Test for 5 seconds at each load level
            while time.time() - level_start < 5:
                # Generate load
                for i in range(load_level // 10):  # Distribute load
                    message = {
                        "channel": "ticker",
                        "type": "update",
                        "data": [
                            {
                                "symbol": "XXLMZUSD",
                                "last_price": f"0.{350 + message_count % 100}",
                                "bid": f"0.{349 + message_count % 100}",
                                "ask": f"0.{351 + message_count % 100}",
                                "volume": "10000.0",
                            }
                        ],
                    }

                    start_time = time.time()
                    success = market_processor.process_message(message)
                    duration = time.time() - start_time

                    metrics.record_execution_time(f"load_{load_level}", duration)
                    metrics.record_result(success)
                    message_count += 1

                await asyncio.sleep(0.1)  # 10 batches per second

            # Calculate performance for this load level
            level_messages = [
                m
                for m in metrics.metrics["execution_times"]
                if m["operation"] == f"load_{load_level}"
            ]

            if level_messages:
                avg_time = statistics.mean([m["duration"] for m in level_messages])
                success_rate = sum(
                    1 for m in level_messages if m["duration"] < 0.01
                ) / len(level_messages)

                performance_results.append(
                    {
                        "load_level": load_level,
                        "avg_response_time": avg_time,
                        "success_rate": success_rate,
                        "messages_processed": len(level_messages),
                    }
                )

        # Scalability assertions
        for result in performance_results:
            # Response time should degrade gracefully
            assert result["avg_response_time"] < 0.02  # < 20ms even at high load
            assert result["success_rate"] > 0.95  # > 95% success rate

            print(
                f"Load {result['load_level']}: {result['avg_response_time'] * 1000:.1f}ms avg, "
                f"{result['success_rate'] * 100:.1f}% success"
            )

    @pytest.mark.asyncio
    async def test_resource_utilization_bounds(self, performance_setup):
        """Test that resource utilization stays within acceptable bounds"""
        setup = performance_setup
        metrics = setup["metrics"]

        metrics.start_memory_monitoring()

        # High-intensity test
        start_time = time.time()

        while time.time() - start_time < 15:  # 15 second stress test
            # Simulate intensive operations
            market_data = setup["market_processor"].get_current_market_data()

            if market_data.get("last_price"):
                await setup["risk_manager"].evaluate_trade_risk_enhanced(
                    Decimal("10.0"),
                    market_data["last_price"],
                    Decimal("500.0"),
                    market_data,
                )

            await asyncio.sleep(0.001)  # High frequency

        metrics.stop_memory_monitoring()

        # Resource utilization checks
        summary = metrics.get_summary()

        # Memory bounds (should not exceed reasonable limits)
        assert summary["max_memory_mb"] < 300  # < 300MB peak
        assert summary["avg_memory_mb"] < 150  # < 150MB average

        # CPU bounds (should not peg CPU)
        assert summary["max_cpu_percent"] < 90  # < 90% peak CPU
        assert summary["avg_cpu_percent"] < 50  # < 50% average CPU

        print(
            f"Resource Utilization: {summary['max_memory_mb']:.1f}MB peak memory, "
            f"{summary['max_cpu_percent']:.1f}% peak CPU"
        )

    @pytest.mark.asyncio
    async def test_performance_regression_detection(self, performance_setup):
        """Test for performance regressions compared to baseline"""
        setup = performance_setup
        market_processor = setup["market_processor"]
        metrics = setup["metrics"]

        # Establish baseline performance
        baseline_messages = []
        for i in range(100):
            message = {
                "channel": "ticker",
                "type": "update",
                "data": [
                    {
                        "symbol": "XXLMZUSD",
                        "last_price": "0.35",
                        "bid": "0.349",
                        "ask": "0.351",
                        "volume": "10000.0",
                    }
                ],
            }
            baseline_messages.append(message)

        # Measure baseline
        baseline_times = []
        for message in baseline_messages:
            start_time = time.time()
            market_processor.process_message(message)
            baseline_times.append(time.time() - start_time)

        baseline_avg = statistics.mean(baseline_times)

        # Test current performance
        current_messages = []
        for i in range(100):
            message = {
                "channel": "ticker",
                "type": "update",
                "data": [
                    {
                        "symbol": "XXLMZUSD",
                        "last_price": f"0.{350 + i}",
                        "bid": f"0.{349 + i}",
                        "ask": f"0.{351 + i}",
                        "volume": "10000.0",
                    }
                ],
            }
            current_messages.append(message)

        current_times = []
        for message in current_messages:
            start_time = time.time()
            market_processor.process_message(message)
            current_times.append(time.time() - start_time)

        current_avg = statistics.mean(current_times)

        # Performance regression check (current should not be > 50% slower than baseline)
        regression_ratio = current_avg / baseline_avg
        assert regression_ratio < 1.5, (
            f"Performance regression detected: {regression_ratio:.2f}x slower"
        )

        print(
            f"Performance Regression Check: Baseline {baseline_avg * 1000:.2f}ms, "
            f"Current {current_avg * 1000:.2f}ms ({regression_ratio:.2f}x)"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
