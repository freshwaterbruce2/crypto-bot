"""
Kraken Rate Limit Manager

Handles Kraken-specific rate limits per trading pair based on official documentation.
"""

import logging
import time
from typing import Dict, Any

logger = logging.getLogger(__name__)


class KrakenRateLimitManager:
    """
    Manages Kraken-specific rate limits per trading pair.
    
    Based on Kraken documentation (document 28):
    - Rate counter starts at 0, increments on transactions
    - Decay rates vary by tier (Starter: -1/sec, Intermediate: -2.34/sec, Pro: -3.75/sec)
    - Thresholds: Starter: 60, Intermediate: 125, Pro: 180
    """
    
    def __init__(self, tier: str = "intermediate"):
        self.tier = tier.lower()
        self.rate_counters = {}  # symbol -> counter value
        self.last_decay_time = {}  # symbol -> last decay timestamp
        
        # Kraken rate limit parameters by tier - HFT ULTRA OPTIMIZED
        self.tier_params = {
            "starter": {"threshold": 60, "decay_rate": -1.0, "fee_free": False},
            "intermediate": {"threshold": 125, "decay_rate": -2.34, "fee_free": False},
            "pro": {
                "threshold": 180, 
                "decay_rate": -3.75,          # 3.75x faster recovery than starter
                "burst_threshold": 270,       # 50% burst capacity for HFT
                "fee_free": True,             # CRITICAL: Fee-free trading
                "priority_access": True,      # Priority API access
                "burst_allowance": 1.5,       # 50% higher burst capacity for HFT
                "micro_scalping_mode": True,  # Optimized for micro-profits
                "ioc_optimized": True,        # IOC order optimization
                "ultra_high_frequency": True, # Ultra-fast execution mode
                "adaptive_scaling": True,     # Dynamic threshold scaling
                "predictive_throttling": True, # Predictive rate management
                "burst_window": 60,           # 1-minute burst windows
                "recovery_boost": 1.25        # 25% faster recovery during bursts
            }
        }
        
        # HFT Performance tracking
        self.burst_mode = False
        self.burst_start_time = 0
        self.adaptive_multipliers = {}  # symbol -> dynamic multiplier
        self.performance_history = {}   # symbol -> performance metrics
        self.prediction_cache = {}      # symbol -> predicted availability
        
        self.params = self.tier_params.get(self.tier, self.tier_params["intermediate"])
        logger.info(f"[RATE_LIMIT] Initialized for {self.tier} tier - Threshold: {self.params['threshold']}")
    
    def can_trade(self, symbol: str, high_priority: bool = False) -> bool:
        """HFT optimized trade availability check with predictive throttling."""
        self._decay_counter(symbol)
        current_counter = self.rate_counters.get(symbol, 0)
        
        # Apply adaptive threshold with HFT optimizations
        threshold = self._get_adaptive_threshold(symbol)
        
        # High priority trades get preferential treatment
        if high_priority and self.tier == "pro":
            threshold = int(threshold * 1.2)  # 20% higher threshold for priority trades
        
        # Predictive availability for HFT
        if self._use_predictive_throttling(symbol):
            predicted_counter = self._predict_counter_in_seconds(symbol, 1.0)  # 1 second ahead
            if predicted_counter > threshold * 0.9:  # 90% threshold for prediction
                logger.debug(f"[HFT_RATE_LIMIT] {symbol}: Predictive throttling engaged")
                return False
        
        can_trade = current_counter < threshold
        
        # Update performance tracking
        self._update_performance_metrics(symbol, can_trade, current_counter, threshold)
        
        if not can_trade:
            logger.warning(f"[HFT_RATE_LIMIT] {symbol}: Rate limit reached ({current_counter}/{threshold})")
            # Enable burst mode recovery if needed
            self._consider_burst_mode_activation(symbol)
        
        return can_trade
    
    def increment_counter(self, symbol: str, increment: int = 1, trade_type: str = "market"):
        """HFT optimized counter increment with adaptive scaling."""
        self._decay_counter(symbol)
        
        # Apply adaptive increment based on current performance
        adaptive_increment = self._calculate_adaptive_increment(symbol, increment, trade_type)
        
        # Pro tier: Fee-free trading optimizations
        if self.tier == "pro" and self.params.get("fee_free"):
            # HFT optimization: Even lower penalty for successful patterns
            if symbol in self.performance_history:
                success_rate = self.performance_history[symbol].get('success_rate', 0.5)
                if success_rate > 0.8:  # High success rate
                    adaptive_increment = max(1, int(adaptive_increment * 0.6))  # 40% reduction
                elif success_rate > 0.6:  # Medium success rate
                    adaptive_increment = max(1, int(adaptive_increment * 0.7))  # 30% reduction
                else:
                    adaptive_increment = max(1, int(adaptive_increment * 0.8))  # 20% reduction
            
        self.rate_counters[symbol] = self.rate_counters.get(symbol, 0) + adaptive_increment
        
        # Update adaptive multiplier for future predictions
        self._update_adaptive_multiplier(symbol, adaptive_increment)
        
        logger.debug(f"[HFT_RATE_LIMIT] {symbol}: Counter incremented by {adaptive_increment} to {self.rate_counters[symbol]}")
        
        # HFT: Track micro-scalping efficiency and patterns
        if self.tier == "pro" and self.params.get("micro_scalping_mode"):
            self._track_hft_efficiency(symbol, trade_type)
    
    def _decay_counter(self, symbol: str):
        """Apply decay to rate counter based on time elapsed."""
        now = time.time()
        last_decay = self.last_decay_time.get(symbol, now)
        elapsed = now - last_decay
        
        if elapsed > 0:
            decay_amount = elapsed * abs(self.params["decay_rate"])
            self.rate_counters[symbol] = max(0, self.rate_counters.get(symbol, 0) - decay_amount)
            self.last_decay_time[symbol] = now
    
    def _track_micro_scalping_efficiency(self, symbol: str):
        """Track micro-scalping efficiency for Pro accounts."""
        if not hasattr(self, 'micro_scalping_stats'):
            self.micro_scalping_stats = {}
        
        if symbol not in self.micro_scalping_stats:
            self.micro_scalping_stats[symbol] = {
                'total_trades': 0,
                'rate_efficiency': 0.0,
                'last_update': time.time()
            }
        
        stats = self.micro_scalping_stats[symbol]
        stats['total_trades'] += 1
        
        # Calculate rate efficiency (lower counter = higher efficiency)
        current_counter = self.rate_counters.get(symbol, 0)
        threshold = self.params["threshold"]
        efficiency = max(0, 100 - (current_counter / threshold * 100))
        stats['rate_efficiency'] = ((stats['rate_efficiency'] * (stats['total_trades'] - 1)) + efficiency) / stats['total_trades']
        stats['last_update'] = time.time()
    
    def get_pro_optimization_stats(self) -> Dict[str, Any]:
        """Get Pro account optimization statistics."""
        if self.tier != "pro":
            return {"error": "Pro tier required for optimization stats"}
        
        stats = {
            "tier": "pro",
            "fee_free_trading": True,
            "rate_limit_threshold": self.params["threshold"],
            "decay_rate": abs(self.params["decay_rate"]),
            "burst_allowance": self.params.get("burst_allowance", 1.0),
            "current_utilization": {},
            "micro_scalping_efficiency": {}
        }
        
        # Current utilization per symbol
        for symbol, counter in self.rate_counters.items():
            utilization = (counter / self.params["threshold"]) * 100
            stats["current_utilization"][symbol] = round(utilization, 2)
        
        # Micro-scalping efficiency
        if hasattr(self, 'micro_scalping_stats'):
            for symbol, efficiency_stats in self.micro_scalping_stats.items():
                stats["micro_scalping_efficiency"][symbol] = {
                    "trades": efficiency_stats['total_trades'],
                    "avg_efficiency": round(efficiency_stats['rate_efficiency'], 2)
                }
        
        return stats
    
    def is_approaching_limit(self, symbol: str, threshold_pct: float = 0.9) -> bool:
        """Check if approaching rate limit for Pro account optimization."""
        self._decay_counter(symbol)
        current_counter = self.rate_counters.get(symbol, 0)
        
        # Apply Pro tier burst allowance
        threshold = self.params["threshold"]
        if self.tier == "pro" and self.params.get("burst_allowance"):
            threshold = int(threshold * self.params["burst_allowance"])
        
        return current_counter >= (threshold * threshold_pct)
    
    def get_optimal_trade_timing(self, symbol: str) -> Dict[str, Any]:
        """Calculate optimal trade timing for Pro accounts with HFT predictions."""
        if self.tier != "pro":
            return {"error": "Pro tier required for optimal timing calculations"}
        
        self._decay_counter(symbol)
        current_counter = self.rate_counters.get(symbol, 0)
        threshold = self._get_adaptive_threshold(symbol)
        decay_rate = abs(self.params["decay_rate"])
        
        # Apply recovery boost if in burst mode
        if self.burst_mode and self.params.get("recovery_boost"):
            decay_rate *= self.params["recovery_boost"]
        
        # Calculate time to specific utilization levels
        time_to_50_pct = max(0, (current_counter - threshold * 0.5) / decay_rate)
        time_to_25_pct = max(0, (current_counter - threshold * 0.25) / decay_rate)
        time_to_zero = max(0, current_counter / decay_rate)
        
        # Predictive analysis for HFT
        burst_window_remaining = 0
        if self.burst_mode:
            burst_window_remaining = max(0, self.params["burst_window"] - (time.time() - self.burst_start_time))
        
        return {
            "current_counter": current_counter,
            "threshold": threshold,
            "adaptive_threshold": self._get_adaptive_threshold(symbol),
            "current_utilization_pct": round((current_counter / threshold) * 100, 2),
            "time_to_50_pct_utilization": round(time_to_50_pct, 2),
            "time_to_25_pct_utilization": round(time_to_25_pct, 2),
            "time_to_zero_utilization": round(time_to_zero, 2),
            "optimal_for_micro_scalping": current_counter < threshold * 0.7,
            "burst_mode_active": self.burst_mode,
            "burst_window_remaining": round(burst_window_remaining, 1),
            "predicted_1s": self._predict_counter_in_seconds(symbol, 1.0),
            "predicted_5s": self._predict_counter_in_seconds(symbol, 5.0),
            "hft_recommendation": self._get_hft_recommendation(symbol)
        }
    
    def _get_adaptive_threshold(self, symbol: str) -> int:
        """Get adaptive threshold based on current performance and burst mode."""
        base_threshold = self.params["threshold"]
        
        # Apply burst allowance
        if self.burst_mode or self.params.get("burst_allowance", 1.0) > 1.0:
            base_threshold = int(base_threshold * self.params.get("burst_allowance", 1.0))
        
        # Apply adaptive scaling based on performance
        if symbol in self.adaptive_multipliers:
            multiplier = self.adaptive_multipliers[symbol]
            base_threshold = int(base_threshold * multiplier)
        
        return base_threshold
    
    def _calculate_adaptive_increment(self, symbol: str, base_increment: int, trade_type: str) -> int:
        """Calculate adaptive increment based on trading patterns."""
        increment = base_increment
        
        # Reduce increment for high-frequency successful patterns
        if symbol in self.performance_history:
            history = self.performance_history[symbol]
            success_rate = history.get('success_rate', 0.5)
            frequency = history.get('trade_frequency', 1.0)
            
            # HFT patterns get reduced increments
            if frequency > 10 and success_rate > 0.7:  # High frequency, high success
                increment = max(1, int(increment * 0.5))
            elif frequency > 5 and success_rate > 0.6:  # Medium frequency, good success
                increment = max(1, int(increment * 0.7))
        
        # Different increments for different trade types
        if trade_type == "limit":
            increment = max(1, int(increment * 0.8))  # Limit orders are lighter
        elif trade_type == "market":
            increment = max(1, int(increment * 1.0))  # Market orders standard
        
        return increment
    
    def _update_adaptive_multiplier(self, symbol: str, actual_increment: int):
        """Update adaptive multiplier based on actual usage patterns."""
        if symbol not in self.adaptive_multipliers:
            self.adaptive_multipliers[symbol] = 1.0
        
        # Track efficiency and adjust multiplier
        current_utilization = self.rate_counters.get(symbol, 0) / self.params["threshold"]
        
        if current_utilization > 0.9:  # High utilization
            self.adaptive_multipliers[symbol] = max(0.8, self.adaptive_multipliers[symbol] - 0.05)
        elif current_utilization < 0.3:  # Low utilization
            self.adaptive_multipliers[symbol] = min(1.5, self.adaptive_multipliers[symbol] + 0.05)
    
    def _update_performance_metrics(self, symbol: str, can_trade: bool, counter: float, threshold: int):
        """Update performance metrics for predictive analysis."""
        if symbol not in self.performance_history:
            self.performance_history[symbol] = {
                'total_checks': 0,
                'successful_checks': 0,
                'success_rate': 0.5,
                'trade_frequency': 1.0,
                'last_update': time.time(),
                'utilization_history': deque(maxlen=50)
            }
        
        history = self.performance_history[symbol]
        history['total_checks'] += 1
        if can_trade:
            history['successful_checks'] += 1
        
        history['success_rate'] = history['successful_checks'] / history['total_checks']
        history['utilization_history'].append(counter / threshold)
        
        # Calculate trade frequency (checks per minute)
        time_diff = time.time() - history['last_update']
        if time_diff > 0:
            history['trade_frequency'] = 60.0 / max(1.0, time_diff)
        history['last_update'] = time.time()
    
    def _use_predictive_throttling(self, symbol: str) -> bool:
        """Check if predictive throttling should be used."""
        return (self.tier == "pro" and 
                self.params.get("predictive_throttling", False) and
                symbol in self.performance_history)
    
    def _predict_counter_in_seconds(self, symbol: str, seconds: float) -> float:
        """Predict counter value in N seconds."""
        if symbol in self.prediction_cache:
            cache_entry = self.prediction_cache[symbol]
            if time.time() - cache_entry['timestamp'] < 1.0:  # Use cache for 1 second
                return cache_entry['prediction']
        
        current_counter = self.rate_counters.get(symbol, 0)
        decay_rate = abs(self.params["decay_rate"])
        
        # Apply recovery boost if in burst mode
        if self.burst_mode and self.params.get("recovery_boost"):
            decay_rate *= self.params["recovery_boost"]
        
        # Predict decay
        predicted_counter = max(0, current_counter - (decay_rate * seconds))
        
        # Cache prediction
        self.prediction_cache[symbol] = {
            'prediction': predicted_counter,
            'timestamp': time.time()
        }
        
        return predicted_counter
    
    def _consider_burst_mode_activation(self, symbol: str):
        """Consider activating burst mode for recovery."""
        if self.tier == "pro" and not self.burst_mode:
            # Check if multiple symbols are hitting limits
            limited_symbols = sum(1 for s, counter in self.rate_counters.items() 
                                if counter >= self.params["threshold"] * 0.9)
            
            if limited_symbols >= 2:  # Multiple symbols limited
                self.activate_burst_mode()
    
    def activate_burst_mode(self):
        """Activate burst mode for faster recovery."""
        if self.tier != "pro":
            return
            
        self.burst_mode = True
        self.burst_start_time = time.time()
        logger.info("[HFT_RATE_LIMIT] Burst mode activated for faster recovery")
        
        # Schedule deactivation
        import asyncio
        async def deactivate_later():
            await asyncio.sleep(self.params.get("burst_window", 60))
            self.burst_mode = False
            logger.info("[HFT_RATE_LIMIT] Burst mode deactivated")
        
        asyncio.create_task(deactivate_later())
    
    def _track_hft_efficiency(self, symbol: str, trade_type: str):
        """Enhanced efficiency tracking for HFT."""
        if not hasattr(self, 'hft_stats'):
            self.hft_stats = {}
        
        if symbol not in self.hft_stats:
            self.hft_stats[symbol] = {
                'total_trades': 0,
                'trade_types': {},
                'efficiency_score': 1.0,
                'last_update': time.time()
            }
        
        stats = self.hft_stats[symbol]
        stats['total_trades'] += 1
        stats['trade_types'][trade_type] = stats['trade_types'].get(trade_type, 0) + 1
        
        # Calculate efficiency score
        current_utilization = self.rate_counters.get(symbol, 0) / self._get_adaptive_threshold(symbol)
        efficiency = max(0, 1.0 - current_utilization)
        stats['efficiency_score'] = (stats['efficiency_score'] * 0.9) + (efficiency * 0.1)
        stats['last_update'] = time.time()
    
    def _get_hft_recommendation(self, symbol: str) -> str:
        """Get HFT trading recommendation."""
        current_counter = self.rate_counters.get(symbol, 0)
        threshold = self._get_adaptive_threshold(symbol)
        utilization = current_counter / threshold
        
        if utilization < 0.3:
            return "OPTIMAL_HFT"  # Perfect for high-frequency trading
        elif utilization < 0.6:
            return "GOOD_HFT"     # Good for trading
        elif utilization < 0.8:
            return "MODERATE_HFT" # Moderate frequency recommended
        elif utilization < 0.95:
            return "LOW_HFT"      # Low frequency only
        else:
            return "WAIT_HFT"     # Wait for recovery
