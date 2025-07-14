"""
Advanced Memory Manager
=======================

Enhanced memory management system with compression, indexing, and intelligent retrieval.
Integrates with the unified learning system for optimal trading intelligence.
"""

import asyncio
import logging
import json
import pickle
import hashlib
import zlib
import time
import numpy as np
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    """Enhanced memory entry with metadata"""
    entry_id: str
    data: Dict[str, Any]
    entry_type: str
    timestamp: datetime
    importance_score: float
    access_count: int
    last_accessed: datetime
    tags: List[str]
    compression_level: int
    checksum: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'entry_id': self.entry_id,
            'data': self.data,
            'entry_type': self.entry_type,
            'timestamp': self.timestamp.isoformat(),
            'importance_score': self.importance_score,
            'access_count': self.access_count,
            'last_accessed': self.last_accessed.isoformat(),
            'tags': self.tags,
            'compression_level': self.compression_level,
            'checksum': self.checksum
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryEntry':
        return cls(
            entry_id=data['entry_id'],
            data=data['data'],
            entry_type=data['entry_type'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            importance_score=data['importance_score'],
            access_count=data['access_count'],
            last_accessed=datetime.fromisoformat(data['last_accessed']),
            tags=data['tags'],
            compression_level=data['compression_level'],
            checksum=data['checksum']
        )


class MemoryIndex:
    """Advanced indexing system for fast memory retrieval"""
    
    def __init__(self):
        """Initialize memory index"""
        self.type_index = defaultdict(list)
        self.tag_index = defaultdict(list)
        self.time_index = defaultdict(list)
        self.importance_index = defaultdict(list)
        self.similarity_index = {}
        
    def add_entry(self, entry: MemoryEntry):
        """Add entry to all relevant indexes"""
        entry_id = entry.entry_id
        
        # Type index
        self.type_index[entry.entry_type].append(entry_id)
        
        # Tag index
        for tag in entry.tags:
            self.tag_index[tag].append(entry_id)
        
        # Time index (by day)
        day_key = entry.timestamp.strftime('%Y-%m-%d')
        self.time_index[day_key].append(entry_id)
        
        # Importance index (by score range)
        importance_range = int(entry.importance_score * 10)  # 0-10 buckets
        self.importance_index[importance_range].append(entry_id)
        
        # Similarity index (for future similarity searches)
        self.similarity_index[entry_id] = self._extract_similarity_features(entry)
    
    def remove_entry(self, entry: MemoryEntry):
        """Remove entry from all indexes"""
        entry_id = entry.entry_id
        
        # Remove from type index
        if entry_id in self.type_index[entry.entry_type]:
            self.type_index[entry.entry_type].remove(entry_id)
        
        # Remove from tag index
        for tag in entry.tags:
            if entry_id in self.tag_index[tag]:
                self.tag_index[tag].remove(entry_id)
        
        # Remove from time index
        day_key = entry.timestamp.strftime('%Y-%m-%d')
        if entry_id in self.time_index[day_key]:
            self.time_index[day_key].remove(entry_id)
        
        # Remove from importance index
        importance_range = int(entry.importance_score * 10)
        if entry_id in self.importance_index[importance_range]:
            self.importance_index[importance_range].remove(entry_id)
        
        # Remove from similarity index
        if entry_id in self.similarity_index:
            del self.similarity_index[entry_id]
    
    def search_by_type(self, entry_type: str) -> List[str]:
        """Search entries by type"""
        return self.type_index.get(entry_type, [])
    
    def search_by_tags(self, tags: List[str], match_all: bool = False) -> List[str]:
        """Search entries by tags"""
        if not tags:
            return []
        
        if match_all:
            # Find entries that have ALL tags
            result_sets = [set(self.tag_index.get(tag, [])) for tag in tags]
            if result_sets:
                return list(set.intersection(*result_sets))
            return []
        else:
            # Find entries that have ANY tag
            result_set = set()
            for tag in tags:
                result_set.update(self.tag_index.get(tag, []))
            return list(result_set)
    
    def search_by_time_range(self, start_date: datetime, end_date: datetime) -> List[str]:
        """Search entries by time range"""
        results = []
        current_date = start_date
        
        while current_date <= end_date:
            day_key = current_date.strftime('%Y-%m-%d')
            results.extend(self.time_index.get(day_key, []))
            current_date += timedelta(days=1)
        
        return results
    
    def search_by_importance(self, min_importance: float, max_importance: float = 1.0) -> List[str]:
        """Search entries by importance score range"""
        results = []
        min_range = int(min_importance * 10)
        max_range = int(max_importance * 10)
        
        for importance_range in range(min_range, max_range + 1):
            results.extend(self.importance_index.get(importance_range, []))
        
        return results
    
    def find_similar(self, entry_id: str, similarity_threshold: float = 0.7) -> List[str]:
        """Find similar entries based on feature similarity"""
        if entry_id not in self.similarity_index:
            return []
        
        target_features = self.similarity_index[entry_id]
        similar_entries = []
        
        for other_id, other_features in self.similarity_index.items():
            if other_id != entry_id:
                similarity = self._calculate_similarity(target_features, other_features)
                if similarity >= similarity_threshold:
                    similar_entries.append((other_id, similarity))
        
        # Sort by similarity score
        similar_entries.sort(key=lambda x: x[1], reverse=True)
        return [entry_id for entry_id, _ in similar_entries]
    
    def _extract_similarity_features(self, entry: MemoryEntry) -> Dict[str, Any]:
        """Extract features for similarity comparison"""
        features = {
            'entry_type': entry.entry_type,
            'importance_score': entry.importance_score,
            'tag_count': len(entry.tags),
            'data_keys': sorted(entry.data.keys()) if isinstance(entry.data, dict) else []
        }
        
        # Extract numerical features from data
        if isinstance(entry.data, dict):
            numerical_features = {}
            for key, value in entry.data.items():
                if isinstance(value, (int, float)):
                    numerical_features[key] = value
            features['numerical_features'] = numerical_features
        
        return features
    
    def _calculate_similarity(self, features1: Dict[str, Any], features2: Dict[str, Any]) -> float:
        """Calculate similarity between two feature sets"""
        similarity_score = 0.0
        total_weight = 0.0
        
        # Type similarity
        if features1.get('entry_type') == features2.get('entry_type'):
            similarity_score += 0.3
        total_weight += 0.3
        
        # Importance similarity
        imp1 = features1.get('importance_score', 0)
        imp2 = features2.get('importance_score', 0)
        imp_similarity = 1.0 - abs(imp1 - imp2)
        similarity_score += imp_similarity * 0.2
        total_weight += 0.2
        
        # Tag similarity
        tags1 = set(features1.get('data_keys', []))
        tags2 = set(features2.get('data_keys', []))
        if tags1 or tags2:
            tag_similarity = len(tags1.intersection(tags2)) / len(tags1.union(tags2))
            similarity_score += tag_similarity * 0.3
        total_weight += 0.3
        
        # Numerical feature similarity
        num1 = features1.get('numerical_features', {})
        num2 = features2.get('numerical_features', {})
        if num1 and num2:
            common_keys = set(num1.keys()).intersection(set(num2.keys()))
            if common_keys:
                num_similarities = []
                for key in common_keys:
                    val1, val2 = num1[key], num2[key]
                    if val1 != 0 or val2 != 0:
                        diff = abs(val1 - val2) / (max(abs(val1), abs(val2)) + 1e-8)
                        num_similarities.append(1.0 - diff)
                
                if num_similarities:
                    num_similarity = sum(num_similarities) / len(num_similarities)
                    similarity_score += num_similarity * 0.2
        total_weight += 0.2
        
        return similarity_score / max(total_weight, 1.0)


class CompressionManager:
    """Manages data compression for memory efficiency"""
    
    def __init__(self):
        """Initialize compression manager"""
        self.compression_stats = {
            'total_compressed': 0,
            'total_uncompressed': 0,
            'compression_ratio': 0.0,
            'compression_time': 0.0
        }
    
    def compress_data(self, data: Any, compression_level: int = 6) -> Tuple[bytes, str]:
        """Compress data with specified compression level"""
        start_time = time.time()
        
        try:
            # Serialize data
            serialized = pickle.dumps(data)
            
            # Compress
            compressed = zlib.compress(serialized, level=compression_level)
            
            # Calculate checksum
            checksum = hashlib.md5(compressed).hexdigest()
            
            # Update stats
            self.compression_stats['total_uncompressed'] += len(serialized)
            self.compression_stats['total_compressed'] += len(compressed)
            self.compression_stats['compression_time'] += time.time() - start_time
            
            if self.compression_stats['total_uncompressed'] > 0:
                self.compression_stats['compression_ratio'] = (
                    self.compression_stats['total_compressed'] / 
                    self.compression_stats['total_uncompressed']
                )
            
            return compressed, checksum
            
        except Exception as e:
            logger.error(f"[MEMORY_MANAGER] Error compressing data: {e}")
            return b'', ''
    
    def decompress_data(self, compressed_data: bytes, checksum: str) -> Any:
        """Decompress data and verify integrity"""
        try:
            # Verify checksum
            if hashlib.md5(compressed_data).hexdigest() != checksum:
                raise ValueError("Data integrity check failed")
            
            # Decompress
            decompressed = zlib.decompress(compressed_data)
            
            # Deserialize
            data = pickle.loads(decompressed)
            
            return data
            
        except Exception as e:
            logger.error(f"[MEMORY_MANAGER] Error decompressing data: {e}")
            return None
    
    def get_compression_stats(self) -> Dict[str, Any]:
        """Get compression statistics"""
        return self.compression_stats.copy()


class AdvancedMemoryManager:
    """Enhanced memory management system with advanced features"""
    
    def __init__(self, memory_dir: str = "D:/trading_data/advanced_memory"):
        """Initialize advanced memory manager"""
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        # Core components
        self.index = MemoryIndex()
        self.compression_manager = CompressionManager()
        
        # Memory storage
        self.active_memory = {}  # Hot memory (frequently accessed)
        self.cold_storage_path = self.memory_dir / "cold_storage"
        self.cold_storage_path.mkdir(exist_ok=True)
        
        # Configuration
        self.max_active_entries = 1000
        self.compression_threshold_size = 1024  # 1KB
        self.auto_archive_days = 7
        self.similarity_cache_size = 10000
        
        # Statistics
        self.stats = {
            'total_entries': 0,
            'active_entries': 0,
            'cold_entries': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'compression_savings': 0
        }
        
        # Background tasks
        self.cleanup_interval = 3600  # 1 hour
        self.archive_interval = 86400  # 24 hours
        
        # Thread pool for compression/decompression
        self.thread_pool = ThreadPoolExecutor(max_workers=2)
        
        logger.info("[ADVANCED_MEMORY] Manager initialized")
    
    async def initialize(self):
        """Initialize the advanced memory manager"""
        try:
            # Load existing memory index
            await self._load_memory_index()
            
            # Start background tasks
            asyncio.create_task(self._cleanup_loop())
            asyncio.create_task(self._archive_loop())
            
            logger.info("[ADVANCED_MEMORY] Manager started successfully")
            
        except Exception as e:
            logger.error(f"[ADVANCED_MEMORY] Error initializing manager: {e}")
    
    async def store_entry(self, data: Dict[str, Any], entry_type: str, 
                         tags: List[str] = None, importance_score: float = 0.5) -> str:
        """Store a new memory entry with advanced features"""
        try:
            # Generate unique entry ID
            entry_id = self._generate_entry_id(data, entry_type)
            
            # Create memory entry
            entry = MemoryEntry(
                entry_id=entry_id,
                data=data,
                entry_type=entry_type,
                timestamp=datetime.now(),
                importance_score=importance_score,
                access_count=0,
                last_accessed=datetime.now(),
                tags=tags or [],
                compression_level=0,
                checksum=''
            )
            
            # Determine storage method
            data_size = len(json.dumps(data).encode('utf-8'))
            if data_size > self.compression_threshold_size:
                # Compress large data
                compressed_data, checksum = self.compression_manager.compress_data(data)
                entry.data = {'compressed': True, 'size': data_size}
                entry.compression_level = 6
                entry.checksum = checksum
                
                # Store compressed data separately
                await self._store_compressed_data(entry_id, compressed_data)
            
            # Add to active memory if space available
            if len(self.active_memory) < self.max_active_entries:
                self.active_memory[entry_id] = entry
                self.stats['active_entries'] += 1
            else:
                # Move to cold storage
                await self._move_to_cold_storage(entry)
                self.stats['cold_entries'] += 1
            
            # Update index
            self.index.add_entry(entry)
            
            # Update statistics
            self.stats['total_entries'] += 1
            
            logger.debug(f"[ADVANCED_MEMORY] Stored entry {entry_id} ({entry_type})")
            return entry_id
            
        except Exception as e:
            logger.error(f"[ADVANCED_MEMORY] Error storing entry: {e}")
            return ""
    
    async def retrieve_entry(self, entry_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve memory entry with intelligent caching"""
        try:
            # Check active memory first
            if entry_id in self.active_memory:
                entry = self.active_memory[entry_id]
                await self._update_access_stats(entry)
                self.stats['cache_hits'] += 1
                
                # Return decompressed data if needed
                if entry.data.get('compressed'):
                    compressed_data = await self._load_compressed_data(entry_id)
                    if compressed_data:
                        decompressed_data = self.compression_manager.decompress_data(
                            compressed_data, entry.checksum
                        )
                        return decompressed_data
                
                return entry.data
            
            # Check cold storage
            entry = await self._load_from_cold_storage(entry_id)
            if entry:
                # Move to active memory if important
                if entry.importance_score > 0.7 or entry.access_count > 5:
                    await self._promote_to_active_memory(entry)
                
                await self._update_access_stats(entry)
                self.stats['cache_misses'] += 1
                
                # Return decompressed data if needed
                if entry.data.get('compressed'):
                    compressed_data = await self._load_compressed_data(entry_id)
                    if compressed_data:
                        decompressed_data = self.compression_manager.decompress_data(
                            compressed_data, entry.checksum
                        )
                        return decompressed_data
                
                return entry.data
            
            logger.warning(f"[ADVANCED_MEMORY] Entry {entry_id} not found")
            return None
            
        except Exception as e:
            logger.error(f"[ADVANCED_MEMORY] Error retrieving entry {entry_id}: {e}")
            return None
    
    async def search_entries(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Advanced search with multiple criteria"""
        try:
            result_sets = []
            
            # Search by type
            if 'type' in query:
                type_results = self.index.search_by_type(query['type'])
                result_sets.append(set(type_results))
            
            # Search by tags
            if 'tags' in query:
                tag_results = self.index.search_by_tags(
                    query['tags'], 
                    query.get('match_all_tags', False)
                )
                result_sets.append(set(tag_results))
            
            # Search by time range
            if 'start_date' in query and 'end_date' in query:
                time_results = self.index.search_by_time_range(
                    query['start_date'], 
                    query['end_date']
                )
                result_sets.append(set(time_results))
            
            # Search by importance
            if 'min_importance' in query:
                importance_results = self.index.search_by_importance(
                    query['min_importance'],
                    query.get('max_importance', 1.0)
                )
                result_sets.append(set(importance_results))
            
            # Find similarity
            if 'similar_to' in query:
                similar_results = self.index.find_similar(
                    query['similar_to'],
                    query.get('similarity_threshold', 0.7)
                )
                result_sets.append(set(similar_results))
            
            # Combine results
            if result_sets:
                if query.get('match_all_criteria', False):
                    # Intersection of all result sets
                    final_results = set.intersection(*result_sets)
                else:
                    # Union of all result sets
                    final_results = set.union(*result_sets)
            else:
                final_results = set()
            
            # Retrieve and return entry data
            entries = []
            for entry_id in final_results:
                entry_data = await self.retrieve_entry(entry_id)
                if entry_data:
                    entries.append({
                        'entry_id': entry_id,
                        'data': entry_data
                    })
            
            # Sort by relevance (importance score and access count)
            entries.sort(
                key=lambda x: self._calculate_relevance_score(x['entry_id']),
                reverse=True
            )
            
            # Apply limit if specified
            limit = query.get('limit', len(entries))
            return entries[:limit]
            
        except Exception as e:
            logger.error(f"[ADVANCED_MEMORY] Error searching entries: {e}")
            return []
    
    async def update_entry(self, entry_id: str, updates: Dict[str, Any]) -> bool:
        """Update existing memory entry"""
        try:
            # Find entry
            entry = await self._find_entry(entry_id)
            if not entry:
                return False
            
            # Update entry data
            if 'data' in updates:
                # Handle compression if data is large
                new_data = updates['data']
                data_size = len(json.dumps(new_data).encode('utf-8'))
                
                if data_size > self.compression_threshold_size:
                    compressed_data, checksum = self.compression_manager.compress_data(new_data)
                    entry.data = {'compressed': True, 'size': data_size}
                    entry.checksum = checksum
                    await self._store_compressed_data(entry_id, compressed_data)
                else:
                    entry.data = new_data
            
            # Update metadata
            if 'importance_score' in updates:
                entry.importance_score = updates['importance_score']
            
            if 'tags' in updates:
                # Remove from old tag indexes
                self.index.remove_entry(entry)
                entry.tags = updates['tags']
                # Re-add to indexes
                self.index.add_entry(entry)
            
            entry.last_accessed = datetime.now()
            
            logger.debug(f"[ADVANCED_MEMORY] Updated entry {entry_id}")
            return True
            
        except Exception as e:
            logger.error(f"[ADVANCED_MEMORY] Error updating entry {entry_id}: {e}")
            return False
    
    async def delete_entry(self, entry_id: str) -> bool:
        """Delete memory entry"""
        try:
            # Find and remove entry
            if entry_id in self.active_memory:
                entry = self.active_memory[entry_id]
                del self.active_memory[entry_id]
                self.stats['active_entries'] -= 1
            else:
                entry = await self._load_from_cold_storage(entry_id)
                if entry:
                    await self._delete_from_cold_storage(entry_id)
                    self.stats['cold_entries'] -= 1
            
            if entry:
                # Remove from index
                self.index.remove_entry(entry)
                
                # Remove compressed data if exists
                if entry.data.get('compressed'):
                    await self._delete_compressed_data(entry_id)
                
                self.stats['total_entries'] -= 1
                logger.debug(f"[ADVANCED_MEMORY] Deleted entry {entry_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"[ADVANCED_MEMORY] Error deleting entry {entry_id}: {e}")
            return False
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics"""
        compression_stats = self.compression_manager.get_compression_stats()
        
        return {
            'total_entries': self.stats['total_entries'],
            'active_entries': self.stats['active_entries'],
            'cold_entries': self.stats['cold_entries'],
            'cache_hit_rate': (
                self.stats['cache_hits'] / 
                max(self.stats['cache_hits'] + self.stats['cache_misses'], 1)
            ),
            'memory_efficiency': {
                'compression_ratio': compression_stats['compression_ratio'],
                'compression_savings': compression_stats.get('compression_savings', 0),
                'total_compressed_entries': compression_stats.get('total_compressed', 0)
            },
            'storage_distribution': {
                'active_memory_usage': len(self.active_memory),
                'cold_storage_files': len(list(self.cold_storage_path.glob('*.pkl')))
            }
        }
    
    # Helper methods
    
    def _generate_entry_id(self, data: Dict[str, Any], entry_type: str) -> str:
        """Generate unique entry ID"""
        content_hash = hashlib.md5(
            json.dumps(data, sort_keys=True).encode('utf-8')
        ).hexdigest()[:8]
        timestamp = int(time.time() * 1000)
        return f"{entry_type}_{timestamp}_{content_hash}"
    
    async def _update_access_stats(self, entry: MemoryEntry):
        """Update entry access statistics"""
        entry.access_count += 1
        entry.last_accessed = datetime.now()
    
    def _calculate_relevance_score(self, entry_id: str) -> float:
        """Calculate relevance score for search ranking"""
        entry = self.active_memory.get(entry_id)
        if not entry:
            return 0.0
        
        # Combine importance, recency, and access frequency
        time_factor = 1.0 - min((datetime.now() - entry.last_accessed).total_seconds() / 86400, 1.0)
        access_factor = min(entry.access_count / 10.0, 1.0)
        
        return (entry.importance_score * 0.5 + time_factor * 0.3 + access_factor * 0.2)
    
    async def _find_entry(self, entry_id: str) -> Optional[MemoryEntry]:
        """Find entry in active memory or cold storage"""
        if entry_id in self.active_memory:
            return self.active_memory[entry_id]
        
        return await self._load_from_cold_storage(entry_id)
    
    async def _store_compressed_data(self, entry_id: str, compressed_data: bytes):
        """Store compressed data to disk"""
        compressed_file = self.memory_dir / f"{entry_id}_compressed.bin"
        with open(compressed_file, 'wb') as f:
            f.write(compressed_data)
    
    async def _load_compressed_data(self, entry_id: str) -> Optional[bytes]:
        """Load compressed data from disk"""
        compressed_file = self.memory_dir / f"{entry_id}_compressed.bin"
        if compressed_file.exists():
            with open(compressed_file, 'rb') as f:
                return f.read()
        return None
    
    async def _delete_compressed_data(self, entry_id: str):
        """Delete compressed data file"""
        compressed_file = self.memory_dir / f"{entry_id}_compressed.bin"
        if compressed_file.exists():
            compressed_file.unlink()
    
    async def _move_to_cold_storage(self, entry: MemoryEntry):
        """Move entry to cold storage"""
        cold_file = self.cold_storage_path / f"{entry.entry_id}.pkl"
        with open(cold_file, 'wb') as f:
            pickle.dump(entry, f)
    
    async def _load_from_cold_storage(self, entry_id: str) -> Optional[MemoryEntry]:
        """Load entry from cold storage"""
        cold_file = self.cold_storage_path / f"{entry_id}.pkl"
        if cold_file.exists():
            with open(cold_file, 'rb') as f:
                return pickle.load(f)
        return None
    
    async def _delete_from_cold_storage(self, entry_id: str):
        """Delete entry from cold storage"""
        cold_file = self.cold_storage_path / f"{entry_id}.pkl"
        if cold_file.exists():
            cold_file.unlink()
    
    async def _promote_to_active_memory(self, entry: MemoryEntry):
        """Promote entry from cold storage to active memory"""
        if len(self.active_memory) >= self.max_active_entries:
            # Remove least recently used entry
            lru_entry_id = min(
                self.active_memory.keys(),
                key=lambda x: self.active_memory[x].last_accessed
            )
            lru_entry = self.active_memory[lru_entry_id]
            del self.active_memory[lru_entry_id]
            await self._move_to_cold_storage(lru_entry)
            self.stats['active_entries'] -= 1
            self.stats['cold_entries'] += 1
        
        self.active_memory[entry.entry_id] = entry
        await self._delete_from_cold_storage(entry.entry_id)
        self.stats['active_entries'] += 1
        self.stats['cold_entries'] -= 1
    
    async def _load_memory_index(self):
        """Load memory index from disk"""
        index_file = self.memory_dir / "memory_index.pkl"
        if index_file.exists():
            try:
                with open(index_file, 'rb') as f:
                    index_data = pickle.load(f)
                    self.index = index_data
                logger.info("[ADVANCED_MEMORY] Memory index loaded")
            except Exception as e:
                logger.error(f"[ADVANCED_MEMORY] Error loading memory index: {e}")
    
    async def _save_memory_index(self):
        """Save memory index to disk"""
        try:
            index_file = self.memory_dir / "memory_index.pkl"
            with open(index_file, 'wb') as f:
                pickle.dump(self.index, f)
        except Exception as e:
            logger.error(f"[ADVANCED_MEMORY] Error saving memory index: {e}")
    
    async def _cleanup_loop(self):
        """Background cleanup loop"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_old_entries()
                await self._save_memory_index()
            except Exception as e:
                logger.error(f"[ADVANCED_MEMORY] Error in cleanup loop: {e}")
    
    async def _archive_loop(self):
        """Background archival loop"""
        while True:
            try:
                await asyncio.sleep(self.archive_interval)
                await self._archive_old_entries()
            except Exception as e:
                logger.error(f"[ADVANCED_MEMORY] Error in archive loop: {e}")
    
    async def _cleanup_old_entries(self):
        """Clean up old, low-importance entries"""
        cutoff_date = datetime.now() - timedelta(days=self.auto_archive_days)
        
        # Clean up active memory
        entries_to_remove = []
        for entry_id, entry in self.active_memory.items():
            if (entry.last_accessed < cutoff_date and 
                entry.importance_score < 0.3 and 
                entry.access_count < 2):
                entries_to_remove.append(entry_id)
        
        for entry_id in entries_to_remove:
            await self.delete_entry(entry_id)
        
        if entries_to_remove:
            logger.info(f"[ADVANCED_MEMORY] Cleaned up {len(entries_to_remove)} old entries")
    
    async def _archive_old_entries(self):
        """Archive very old entries to compressed storage"""
        # This could implement long-term archival to compressed formats
        # For now, we'll just ensure old cold storage files are cleaned up
        archive_cutoff = datetime.now() - timedelta(days=30)
        
        archived_count = 0
        for cold_file in self.cold_storage_path.glob('*.pkl'):
            if cold_file.stat().st_mtime < archive_cutoff.timestamp():
                # Could move to compressed archive instead of deleting
                cold_file.unlink()
                archived_count += 1
        
        if archived_count > 0:
            logger.info(f"[ADVANCED_MEMORY] Archived {archived_count} old cold storage files")
    
    async def stop(self):
        """Stop the advanced memory manager"""
        try:
            await self._save_memory_index()
            self.thread_pool.shutdown(wait=True)
            logger.info("[ADVANCED_MEMORY] Manager stopped")
        except Exception as e:
            logger.error(f"[ADVANCED_MEMORY] Error stopping manager: {e}")