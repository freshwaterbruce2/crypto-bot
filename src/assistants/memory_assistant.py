"""
Memory Assistant
Provides persistent memory management and learning capabilities for the trading bot
"""

import asyncio
import json
import logging
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class MemoryAssistant:
    """
    Intelligent memory management system for trading bot learning and persistence
    Stores trading patterns, performance metrics, and decision outcomes
    """

    def __init__(self, bot=None):
        """Initialize memory assistant"""
        self.bot = bot
        self.logger = logger

        # Memory storage paths
        self.memory_dir = Path("D:/trading_data/memory")
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        # Memory components
        self.short_term_memory = {}  # Session-based memory
        self.long_term_memory = {}   # Persistent memory
        self.pattern_memory = {}     # Pattern recognition memory
        self.performance_memory = {} # Performance tracking memory

        # Memory management settings
        self.max_short_term_entries = 1000
        self.max_long_term_entries = 10000
        self.memory_retention_days = 30
        self.auto_save_interval = 300  # 5 minutes

        # Performance tracking
        self.memory_stats = {
            'total_stored': 0,
            'total_retrieved': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'last_cleanup': datetime.now()
        }

        self.logger.info("[MEMORY] Assistant initialized")

    async def initialize(self):
        """Initialize memory system and load persistent data"""
        try:
            # Load existing memory
            await self.load_persistent_memory()

            # Start auto-save task
            asyncio.create_task(self._auto_save_loop())

            # Start cleanup task
            asyncio.create_task(self._cleanup_loop())

            self.logger.info("[MEMORY] Memory system initialized and loaded")

        except Exception as e:
            self.logger.error(f"[MEMORY] Error initializing memory system: {e}")

    async def store_trading_decision(self, decision_type: str, symbol: str,
                                   decision_data: dict[str, Any], outcome: Optional[dict[str, Any]] = None):
        """Store a trading decision for learning purposes"""
        try:
            memory_entry = {
                'timestamp': datetime.now().isoformat(),
                'decision_type': decision_type,  # 'buy', 'sell', 'hold'
                'symbol': symbol,
                'decision_data': decision_data,
                'outcome': outcome,
                'session_id': self._get_session_id()
            }

            # Store in short-term memory
            entry_key = f"{decision_type}_{symbol}_{datetime.now().timestamp()}"
            self.short_term_memory[entry_key] = memory_entry

            # Store in long-term memory if significant
            if self._is_significant_decision(decision_data, outcome):
                self.long_term_memory[entry_key] = memory_entry

            # Extract patterns
            await self._extract_patterns(decision_type, symbol, decision_data, outcome)

            self.memory_stats['total_stored'] += 1

            self.logger.debug(f"[MEMORY] Stored {decision_type} decision for {symbol}")

        except Exception as e:
            self.logger.error(f"[MEMORY] Error storing trading decision: {e}")

    async def retrieve_similar_decisions(self, symbol: str, market_conditions: dict[str, Any],
                                       decision_type: str = None, limit: int = 10) -> list[dict[str, Any]]:
        """Retrieve similar trading decisions for pattern analysis"""
        try:
            similar_decisions = []

            # Search through long-term memory
            for _entry_key, memory_entry in self.long_term_memory.items():
                if symbol and memory_entry['symbol'] != symbol:
                    continue

                if decision_type and memory_entry['decision_type'] != decision_type:
                    continue

                # Calculate similarity score
                similarity = self._calculate_similarity(market_conditions, memory_entry['decision_data'])

                if similarity > 0.7:  # 70% similarity threshold
                    memory_entry['similarity_score'] = similarity
                    similar_decisions.append(memory_entry)

            # Sort by similarity and return top results
            similar_decisions.sort(key=lambda x: x['similarity_score'], reverse=True)

            self.memory_stats['total_retrieved'] += 1
            if similar_decisions:
                self.memory_stats['cache_hits'] += 1
            else:
                self.memory_stats['cache_misses'] += 1

            return similar_decisions[:limit]

        except Exception as e:
            self.logger.error(f"[MEMORY] Error retrieving similar decisions: {e}")
            return []

    async def get_symbol_performance_history(self, symbol: str, days: int = 30) -> dict[str, Any]:
        """Get performance history for a specific symbol"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)

            if symbol not in self.performance_memory:
                return {
                    'total_trades': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'avg_profit_pct': 0.0,
                    'avg_hold_time': 0.0,
                    'best_trade': None,
                    'worst_trade': None,
                    'recent_performance': []
                }

            symbol_data = self.performance_memory[symbol]
            recent_trades = [
                trade for trade in symbol_data.get('trades', [])
                if datetime.fromisoformat(trade['timestamp']) > cutoff_date
            ]

            if not recent_trades:
                return {
                    'total_trades': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'avg_profit_pct': 0.0,
                    'avg_hold_time': 0.0,
                    'best_trade': None,
                    'worst_trade': None,
                    'recent_performance': []
                }

            # Calculate performance metrics
            total_trades = len(recent_trades)
            winning_trades = len([t for t in recent_trades if t.get('profit_pct', 0) > 0])
            losing_trades = total_trades - winning_trades

            avg_profit = sum(t.get('profit_pct', 0) for t in recent_trades) / total_trades
            avg_hold_time = sum(t.get('hold_time_seconds', 0) for t in recent_trades) / total_trades

            best_trade = max(recent_trades, key=lambda x: x.get('profit_pct', 0))
            worst_trade = min(recent_trades, key=lambda x: x.get('profit_pct', 0))

            return {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'avg_profit_pct': avg_profit,
                'avg_hold_time': avg_hold_time,
                'win_rate': winning_trades / total_trades if total_trades > 0 else 0,
                'best_trade': best_trade,
                'worst_trade': worst_trade,
                'recent_performance': recent_trades[-10:]  # Last 10 trades
            }

        except Exception as e:
            self.logger.error(f"[MEMORY] Error getting symbol performance: {e}")
            return {}

    async def store_trade_outcome(self, symbol: str, entry_data: dict[str, Any],
                                exit_data: dict[str, Any], performance: dict[str, Any]):
        """Store complete trade outcome for learning"""
        try:
            trade_record = {
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol,
                'entry_data': entry_data,
                'exit_data': exit_data,
                'performance': performance,
                'profit_pct': performance.get('profit_pct', 0),
                'hold_time_seconds': performance.get('hold_time_seconds', 0),
                'session_id': self._get_session_id()
            }

            # Store in performance memory
            if symbol not in self.performance_memory:
                self.performance_memory[symbol] = {
                    'trades': [],
                    'total_profit': 0.0,
                    'total_trades': 0,
                    'win_rate': 0.0
                }

            self.performance_memory[symbol]['trades'].append(trade_record)
            self.performance_memory[symbol]['total_trades'] += 1
            self.performance_memory[symbol]['total_profit'] += performance.get('profit_pct', 0)

            # Update win rate
            winning_trades = len([
                t for t in self.performance_memory[symbol]['trades']
                if t.get('profit_pct', 0) > 0
            ])
            self.performance_memory[symbol]['win_rate'] = winning_trades / self.performance_memory[symbol]['total_trades']

            # Extract patterns from successful trades
            if performance.get('profit_pct', 0) > 0.01:  # Profitable trades > 1%
                await self._learn_from_successful_trade(symbol, entry_data, exit_data, performance)

            self.logger.info(f"[MEMORY] Stored trade outcome for {symbol}: {performance.get('profit_pct', 0):.3f}%")

        except Exception as e:
            self.logger.error(f"[MEMORY] Error storing trade outcome: {e}")

    async def get_learning_insights(self, symbol: str = None, decision_type: str = None) -> dict[str, Any]:
        """Get learning insights and patterns from memory"""
        try:
            insights = {
                'successful_patterns': [],
                'failed_patterns': [],
                'optimal_conditions': {},
                'risk_factors': [],
                'performance_trends': {}
            }

            # Analyze patterns
            for pattern_key, pattern_data in self.pattern_memory.items():
                if symbol and symbol not in pattern_key:
                    continue

                if decision_type and decision_type not in pattern_key:
                    continue

                pattern_success_rate = pattern_data.get('success_rate', 0)
                pattern_frequency = pattern_data.get('frequency', 0)

                if pattern_success_rate > 0.7 and pattern_frequency > 5:
                    insights['successful_patterns'].append({
                        'pattern': pattern_key,
                        'success_rate': pattern_success_rate,
                        'frequency': pattern_frequency,
                        'conditions': pattern_data.get('conditions', {})
                    })
                elif pattern_success_rate < 0.3 and pattern_frequency > 5:
                    insights['failed_patterns'].append({
                        'pattern': pattern_key,
                        'success_rate': pattern_success_rate,
                        'frequency': pattern_frequency,
                        'conditions': pattern_data.get('conditions', {})
                    })

            # Optimal conditions analysis
            if symbol:
                symbol_history = await self.get_symbol_performance_history(symbol)
                if symbol_history['total_trades'] > 10:
                    insights['optimal_conditions'] = self._analyze_optimal_conditions(symbol)

            return insights

        except Exception as e:
            self.logger.error(f"[MEMORY] Error getting learning insights: {e}")
            return {}

    async def clear_old_memory(self, days: int = None):
        """Clear old memory entries to free up space"""
        try:
            cutoff_days = days or self.memory_retention_days
            cutoff_date = datetime.now() - timedelta(days=cutoff_days)

            # Clear old short-term memory
            old_keys = [
                key for key, entry in self.short_term_memory.items()
                if datetime.fromisoformat(entry['timestamp']) < cutoff_date
            ]

            for key in old_keys:
                del self.short_term_memory[key]

            # Clear old performance memory trades
            for symbol in self.performance_memory:
                old_trades = [
                    trade for trade in self.performance_memory[symbol]['trades']
                    if datetime.fromisoformat(trade['timestamp']) < cutoff_date
                ]
                self.performance_memory[symbol]['trades'] = [
                    trade for trade in self.performance_memory[symbol]['trades']
                    if trade not in old_trades
                ]

            self.memory_stats['last_cleanup'] = datetime.now()
            self.logger.info(f"[MEMORY] Cleared {len(old_keys)} old memory entries")

        except Exception as e:
            self.logger.error(f"[MEMORY] Error clearing old memory: {e}")

    async def save_persistent_memory(self):
        """Save memory to persistent storage"""
        try:
            # Save long-term memory
            long_term_file = self.memory_dir / "long_term_memory.json"
            with open(long_term_file, 'w') as f:
                json.dump(self.long_term_memory, f, indent=2)

            # Save performance memory
            performance_file = self.memory_dir / "performance_memory.json"
            with open(performance_file, 'w') as f:
                json.dump(self.performance_memory, f, indent=2)

            # Save pattern memory
            pattern_file = self.memory_dir / "pattern_memory.pkl"
            with open(pattern_file, 'wb') as f:
                pickle.dump(self.pattern_memory, f)

            # Save memory stats
            stats_file = self.memory_dir / "memory_stats.json"
            stats_to_save = self.memory_stats.copy()
            stats_to_save['last_cleanup'] = stats_to_save['last_cleanup'].isoformat()
            with open(stats_file, 'w') as f:
                json.dump(stats_to_save, f, indent=2)

            self.logger.debug("[MEMORY] Persistent memory saved")

        except Exception as e:
            self.logger.error(f"[MEMORY] Error saving persistent memory: {e}")

    async def load_persistent_memory(self):
        """Load memory from persistent storage"""
        try:
            # Load long-term memory
            long_term_file = self.memory_dir / "long_term_memory.json"
            if long_term_file.exists():
                with open(long_term_file) as f:
                    self.long_term_memory = json.load(f)

            # Load performance memory
            performance_file = self.memory_dir / "performance_memory.json"
            if performance_file.exists():
                with open(performance_file) as f:
                    self.performance_memory = json.load(f)

            # Load pattern memory
            pattern_file = self.memory_dir / "pattern_memory.pkl"
            if pattern_file.exists():
                with open(pattern_file, 'rb') as f:
                    self.pattern_memory = pickle.load(f)

            # Load memory stats
            stats_file = self.memory_dir / "memory_stats.json"
            if stats_file.exists():
                with open(stats_file) as f:
                    loaded_stats = json.load(f)
                    loaded_stats['last_cleanup'] = datetime.fromisoformat(loaded_stats['last_cleanup'])
                    self.memory_stats.update(loaded_stats)

            self.logger.info(f"[MEMORY] Loaded {len(self.long_term_memory)} long-term entries, {len(self.performance_memory)} performance records")

        except Exception as e:
            self.logger.error(f"[MEMORY] Error loading persistent memory: {e}")

    def _get_session_id(self) -> str:
        """Get current session ID"""
        if self.bot and hasattr(self.bot, 'session_id'):
            return self.bot.session_id
        return f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def _is_significant_decision(self, decision_data: dict[str, Any], outcome: Optional[dict[str, Any]]) -> bool:
        """Determine if a decision is significant enough for long-term storage"""
        try:
            # High confidence decisions
            if decision_data.get('confidence', 0) > 0.8:
                return True

            # Decisions with outcomes
            if outcome:
                profit_pct = outcome.get('profit_pct', 0)
                # Significant profit or loss
                if abs(profit_pct) > 0.01:  # > 1%
                    return True

            # Large position sizes
            if decision_data.get('position_size', 0) > 10:  # > $10
                return True

            return False

        except Exception as e:
            self.logger.error(f"[MEMORY] Error determining decision significance: {e}")
            return False

    def _calculate_similarity(self, conditions1: dict[str, Any], conditions2: dict[str, Any]) -> float:
        """Calculate similarity between two sets of market conditions"""
        try:
            similarity_score = 0.0
            total_factors = 0

            # Compare numeric factors
            numeric_factors = ['price', 'volume_ratio', 'rsi', 'volatility', 'confidence']

            for factor in numeric_factors:
                if factor in conditions1 and factor in conditions2:
                    val1 = float(conditions1[factor])
                    val2 = float(conditions2[factor])

                    # Calculate percentage difference
                    if val1 != 0:
                        diff_pct = abs(val1 - val2) / abs(val1)
                        factor_similarity = max(0, 1 - diff_pct)
                        similarity_score += factor_similarity
                    total_factors += 1

            # Compare categorical factors
            categorical_factors = ['trend', 'signal_type', 'market_condition']

            for factor in categorical_factors:
                if factor in conditions1 and factor in conditions2:
                    if conditions1[factor] == conditions2[factor]:
                        similarity_score += 1.0
                    total_factors += 1

            return similarity_score / max(total_factors, 1)

        except Exception as e:
            self.logger.error(f"[MEMORY] Error calculating similarity: {e}")
            return 0.0

    async def _extract_patterns(self, decision_type: str, symbol: str,
                              decision_data: dict[str, Any], outcome: Optional[dict[str, Any]]):
        """Extract patterns from trading decisions"""
        try:
            # Create pattern key
            market_condition = decision_data.get('market_condition', 'unknown')
            confidence_range = self._get_confidence_range(decision_data.get('confidence', 0))
            pattern_key = f"{decision_type}_{symbol}_{market_condition}_{confidence_range}"

            if pattern_key not in self.pattern_memory:
                self.pattern_memory[pattern_key] = {
                    'frequency': 0,
                    'successful_outcomes': 0,
                    'total_outcomes': 0,
                    'success_rate': 0.0,
                    'conditions': {},
                    'avg_profit': 0.0
                }

            pattern = self.pattern_memory[pattern_key]
            pattern['frequency'] += 1

            # Update pattern conditions
            for key, value in decision_data.items():
                if key not in pattern['conditions']:
                    pattern['conditions'][key] = []
                pattern['conditions'][key].append(value)

            # Update outcomes if available
            if outcome:
                pattern['total_outcomes'] += 1
                profit_pct = outcome.get('profit_pct', 0)

                if profit_pct > 0:
                    pattern['successful_outcomes'] += 1

                # Update average profit
                pattern['avg_profit'] = (
                    (pattern['avg_profit'] * (pattern['total_outcomes'] - 1) + profit_pct) /
                    pattern['total_outcomes']
                )

                # Update success rate
                pattern['success_rate'] = pattern['successful_outcomes'] / pattern['total_outcomes']

        except Exception as e:
            self.logger.error(f"[MEMORY] Error extracting patterns: {e}")

    def _get_confidence_range(self, confidence: float) -> str:
        """Get confidence range category"""
        if confidence >= 0.8:
            return "high"
        elif confidence >= 0.6:
            return "medium"
        else:
            return "low"

    async def _learn_from_successful_trade(self, symbol: str, entry_data: dict[str, Any],
                                         exit_data: dict[str, Any], performance: dict[str, Any]):
        """Learn from successful trades to improve future decisions"""
        try:
            # Extract successful patterns
            success_pattern = {
                'symbol': symbol,
                'entry_conditions': entry_data,
                'exit_conditions': exit_data,
                'profit_pct': performance.get('profit_pct', 0),
                'hold_time': performance.get('hold_time_seconds', 0),
                'timestamp': datetime.now().isoformat()
            }

            # Store in pattern memory
            pattern_key = f"success_{symbol}_{entry_data.get('signal_type', 'unknown')}"
            if pattern_key not in self.pattern_memory:
                self.pattern_memory[pattern_key] = {
                    'successful_trades': [],
                    'avg_profit': 0.0,
                    'avg_hold_time': 0.0,
                    'optimal_entry_conditions': {},
                    'optimal_exit_conditions': {}
                }

            self.pattern_memory[pattern_key]['successful_trades'].append(success_pattern)

            # Update averages
            trades = self.pattern_memory[pattern_key]['successful_trades']
            self.pattern_memory[pattern_key]['avg_profit'] = sum(t['profit_pct'] for t in trades) / len(trades)
            self.pattern_memory[pattern_key]['avg_hold_time'] = sum(t['hold_time'] for t in trades) / len(trades)

        except Exception as e:
            self.logger.error(f"[MEMORY] Error learning from successful trade: {e}")

    def _analyze_optimal_conditions(self, symbol: str) -> dict[str, Any]:
        """Analyze optimal trading conditions for a symbol"""
        try:
            if symbol not in self.performance_memory:
                return {}

            trades = self.performance_memory[symbol]['trades']
            profitable_trades = [t for t in trades if t.get('profit_pct', 0) > 0]

            if len(profitable_trades) < 5:
                return {}

            # Analyze optimal entry conditions
            optimal_conditions = {
                'entry_rsi_range': self._analyze_range([t['entry_data'].get('rsi', 50) for t in profitable_trades]),
                'entry_volume_ratio_range': self._analyze_range([t['entry_data'].get('volume_ratio', 1) for t in profitable_trades]),
                'optimal_confidence_threshold': self._analyze_range([t['entry_data'].get('confidence', 0.5) for t in profitable_trades]),
                'optimal_hold_time_range': self._analyze_range([t.get('hold_time_seconds', 3600) for t in profitable_trades])
            }

            return optimal_conditions

        except Exception as e:
            self.logger.error(f"[MEMORY] Error analyzing optimal conditions: {e}")
            return {}

    def _analyze_range(self, values: list[float]) -> dict[str, float]:
        """Analyze optimal range for a set of values"""
        try:
            if not values:
                return {'min': 0, 'max': 0, 'avg': 0}

            return {
                'min': min(values),
                'max': max(values),
                'avg': sum(values) / len(values),
                'median': sorted(values)[len(values) // 2]
            }

        except Exception as e:
            self.logger.error(f"[MEMORY] Error analyzing range: {e}")
            return {'min': 0, 'max': 0, 'avg': 0}

    async def _auto_save_loop(self):
        """Auto-save memory periodically"""
        while True:
            try:
                await asyncio.sleep(self.auto_save_interval)
                await self.save_persistent_memory()
            except Exception as e:
                self.logger.error(f"[MEMORY] Error in auto-save loop: {e}")

    async def _cleanup_loop(self):
        """Cleanup old memory periodically"""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                await self.clear_old_memory()

                # Limit short-term memory size
                if len(self.short_term_memory) > self.max_short_term_entries:
                    # Remove oldest entries
                    sorted_entries = sorted(
                        self.short_term_memory.items(),
                        key=lambda x: x[1]['timestamp']
                    )
                    entries_to_remove = len(self.short_term_memory) - self.max_short_term_entries
                    for key, _ in sorted_entries[:entries_to_remove]:
                        del self.short_term_memory[key]

            except Exception as e:
                self.logger.error(f"[MEMORY] Error in cleanup loop: {e}")

    async def store_pattern(self, pattern_type: str, pattern_data: dict[str, Any]):
        """
        Store a pattern for recognition and learning
        Called by AssistantManager - provides pattern storage capability
        """
        try:
            # Create pattern entry
            pattern_entry = {
                'timestamp': datetime.now().isoformat(),
                'pattern_type': pattern_type,
                'pattern_data': pattern_data,
                'frequency': 1,
                'last_seen': datetime.now().isoformat()
            }

            # Generate pattern key
            pattern_key = f"{pattern_type}_{hash(str(sorted(pattern_data.items())))}"

            # Check if pattern already exists
            if pattern_key in self.pattern_memory:
                # Update existing pattern
                self.pattern_memory[pattern_key]['frequency'] += 1
                self.pattern_memory[pattern_key]['last_seen'] = datetime.now().isoformat()
                self.pattern_memory[pattern_key]['pattern_data'].update(pattern_data)
            else:
                # Store new pattern
                self.pattern_memory[pattern_key] = pattern_entry

            # Update stats
            self.memory_stats['total_stored'] += 1

            self.logger.debug(f"[MEMORY] Stored pattern: {pattern_type}")

        except Exception as e:
            self.logger.error(f"[MEMORY] Error storing pattern {pattern_type}: {e}")

    async def get_patterns(self, pattern_type: str, symbol: Optional[str] = None) -> list[dict[str, Any]]:
        """
        Retrieve patterns by type and optionally by symbol
        Called by AssistantManager - provides pattern retrieval capability
        """
        try:
            matching_patterns = []

            for pattern_key, pattern_entry in self.pattern_memory.items():
                # Filter by pattern type
                if pattern_entry['pattern_type'] != pattern_type:
                    continue

                # Filter by symbol if specified
                if symbol:
                    pattern_data = pattern_entry['pattern_data']
                    if pattern_data.get('symbol') != symbol:
                        continue

                # Add to results
                matching_patterns.append({
                    'pattern_key': pattern_key,
                    'pattern_type': pattern_entry['pattern_type'],
                    'pattern_data': pattern_entry['pattern_data'],
                    'frequency': pattern_entry['frequency'],
                    'last_seen': pattern_entry['last_seen'],
                    'timestamp': pattern_entry['timestamp']
                })

            # Sort by frequency (most common first)
            matching_patterns.sort(key=lambda x: x['frequency'], reverse=True)

            # Update retrieval stats
            self.memory_stats['total_retrieved'] += len(matching_patterns)
            if matching_patterns:
                self.memory_stats['cache_hits'] += 1
            else:
                self.memory_stats['cache_misses'] += 1

            self.logger.debug(f"[MEMORY] Retrieved {len(matching_patterns)} patterns for {pattern_type}")

            return matching_patterns

        except Exception as e:
            self.logger.error(f"[MEMORY] Error retrieving patterns for {pattern_type}: {e}")
            return []

    async def analyze_pattern_trends(self, pattern_type: str, days: int = 7) -> dict[str, Any]:
        """Analyze trends in stored patterns"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)

            recent_patterns = []
            for pattern_entry in self.pattern_memory.values():
                if pattern_entry['pattern_type'] == pattern_type:
                    last_seen = datetime.fromisoformat(pattern_entry['last_seen'])
                    if last_seen >= cutoff_date:
                        recent_patterns.append(pattern_entry)

            if not recent_patterns:
                return {
                    'total_patterns': 0,
                    'avg_frequency': 0,
                    'trending_patterns': []
                }

            # Calculate trends
            total_patterns = len(recent_patterns)
            avg_frequency = sum(p['frequency'] for p in recent_patterns) / total_patterns

            # Find trending patterns (high frequency, recently seen)
            trending_patterns = sorted(
                recent_patterns,
                key=lambda x: (x['frequency'], x['last_seen']),
                reverse=True
            )[:5]  # Top 5

            return {
                'total_patterns': total_patterns,
                'avg_frequency': avg_frequency,
                'trending_patterns': [
                    {
                        'pattern_data': p['pattern_data'],
                        'frequency': p['frequency'],
                        'last_seen': p['last_seen']
                    }
                    for p in trending_patterns
                ],
                'analysis_period_days': days
            }

        except Exception as e:
            self.logger.error(f"[MEMORY] Error analyzing pattern trends: {e}")
            return {'total_patterns': 0, 'avg_frequency': 0, 'trending_patterns': []}

    def get_memory_statistics(self) -> dict[str, Any]:
        """Get memory usage statistics"""
        return {
            'short_term_entries': len(self.short_term_memory),
            'long_term_entries': len(self.long_term_memory),
            'performance_symbols': len(self.performance_memory),
            'pattern_entries': len(self.pattern_memory),
            'total_stored': self.memory_stats['total_stored'],
            'total_retrieved': self.memory_stats['total_retrieved'],
            'cache_hit_rate': self.memory_stats['cache_hits'] / max(self.memory_stats['total_retrieved'], 1),
            'last_cleanup': self.memory_stats['last_cleanup'].isoformat()
        }
