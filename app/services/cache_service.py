"""
Caching service for RAG - Auto-summary caching
"""
import os
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '.env')
load_dotenv(dotenv_path=env_path)

@dataclass
class CacheEntry:
    key: str
    value: Any
    created_at: datetime
    expires_at: datetime
    hits: int = 0

class CacheService:
    """In-memory caching service for RAG (use Redis for production)"""
    
    def __init__(self, default_ttl: int = 3600):  # 1 hour default
        self.cache: Dict[str, CacheEntry] = {}
        self.default_ttl = default_ttl
        self.max_size = 1000  # Max cache entries
    
    def _generate_key(
        self,
        query: str,
        document_id: Optional[str] = None,
        filters: Optional[Dict] = None
    ) -> str:
        """Generate a cache key from query parameters"""
        key_data = {
            "query": query,
            "document_id": document_id,
            "filters": filters
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def get(
        self,
        query: str,
        document_id: Optional[str] = None,
        filters: Optional[Dict] = None
    ) -> Optional[Dict[str, Any]]:
        """Get cached result"""
        key = self._generate_key(query, document_id, filters)
        
        if key not in self.cache:
            return None
        
        entry = self.cache[key]
        
        # Check if expired
        if datetime.now() > entry.expires_at:
            del self.cache[key]
            return None
        
        # Increment hits
        entry.hits += 1
        
        return {
            "data": entry.value,
            "cached_at": entry.created_at.isoformat(),
            "hits": entry.hits
        }
    
    def set(
        self,
        query: str,
        value: Dict[str, Any],
        document_id: Optional[str] = None,
        filters: Optional[Dict] = None,
        ttl: Optional[int] = None
    ) -> str:
        """Cache a result"""
        key = self._generate_key(query, document_id, filters)
        
        # Evict old entries if cache is full
        if len(self.cache) >= self.max_size:
            self._evict_oldest()
        
        expires_at = datetime.now() + timedelta(seconds=ttl or self.default_ttl)
        
        self.cache[key] = CacheEntry(
            key=key,
            value=value,
            created_at=datetime.now(),
            expires_at=expires_at
        )
        
        return key
    
    def invalidate(
        self,
        query: Optional[str] = None,
        document_id: Optional[str] = None
    ) -> int:
        """Invalidate cached entries"""
        keys_to_delete = []
        
        for key, entry in self.cache.items():
            should_delete = False
            
            if query and query in key:
                should_delete = True
            
            if document_id and document_id in key:
                should_delete = True
            
            if should_delete:
                keys_to_delete.append(key)
        
        for key in keys_to_delete:
            del self.cache[key]
        
        return len(keys_to_delete)
    
    def invalidate_document(self, document_id: str) -> int:
        """Invalidate all cached results for a document"""
        return self.invalidate(document_id=document_id)
    
    def _evict_oldest(self):
        """Evict the oldest cache entry"""
        if not self.cache:
            return
        
        oldest_key = min(
            self.cache.keys(),
            key=lambda k: self.cache[k].created_at
        )
        del self.cache[oldest_key]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        now = datetime.now()
        active_entries = [
            entry for entry in self.cache.values()
            if now < entry.expires_at
        ]
        
        total_hits = sum(entry.hits for entry in self.cache.values())
        
        return {
            "total_entries": len(self.cache),
            "active_entries": len(active_entries),
            "expired_entries": len(self.cache) - len(active_entries),
            "total_hits": total_hits,
            "hit_rate": total_hits / max(len(self.cache) + total_hits, 1)
        }
    
    def clear(self):
        """Clear all cache entries"""
        self.cache.clear()
    
    def cleanup(self):
        """Remove expired entries"""
        now = datetime.now()
        expired_keys = [
            key for key, entry in self.cache.items()
            if now > entry.expires_at
        ]
        
        for key in expired_keys:
            del self.cache[key]
        
        return len(expired_keys)

# Summary-specific cache
class SummaryCacheService:
    """Cache for document summaries"""
    
    def __init__(self):
        self.summary_cache = CacheService(default_ttl=7200)  # 2 hours
        self.key_points_cache = CacheService(default_ttl=7200)
    
    def get_summary(
        self,
        document_id: str,
        max_length: int = 200
    ) -> Optional[Dict[str, Any]]:
        """Get cached summary"""
        return self.summary_cache.get(
            query=f"summary_{document_id}",
            filters={"max_length": max_length}
        )
    
    def cache_summary(
        self,
        document_id: str,
        summary: str,
        max_length: int = 200
    ) -> str:
        """Cache a summary"""
        return self.summary_cache.set(
            query=f"summary_{document_id}",
            value={"summary": summary, "document_id": document_id},
            filters={"max_length": max_length}
        )
    
    def get_key_points(
        self,
        document_id: str,
        num_points: int = 5
    ) -> Optional[Dict[str, Any]]:
        """Get cached key points"""
        return self.key_points_cache.get(
            query=f"key_points_{document_id}",
            filters={"num_points": num_points}
        )
    
    def cache_key_points(
        self,
        document_id: str,
        key_points: list,
        num_points: int = 5
    ) -> str:
        """Cache key points"""
        return self.key_points_cache.set(
            query=f"key_points_{document_id}",
            value={"key_points": key_points, "document_id": document_id},
            filters={"num_points": num_points}
        )
    
    def invalidate_document(self, document_id: str) -> int:
        """Invalidate all cached data for a document"""
        count = self.summary_cache.invalidate_document(document_id)
        count += self.key_points_cache.invalidate_document(document_id)
        return count

# Singleton instances
cache_service = CacheService()
summary_cache_service = SummaryCacheService()