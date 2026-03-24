"""
Simple in-memory cache for RADIUS authentication results
"""

from typing import Optional, Tuple
import time
import logging
from threading import Lock
from collections import OrderedDict

logger = logging.getLogger("roxx.radius_backends.cache")


class AuthCache:
    """
    Simple in-memory cache for authentication results.
    
    Caches successful authentications to reduce backend load.
    Cache entries expire after TTL seconds.
    """
    
    def __init__(self, ttl: int = 300, max_size: int = 1000):
        """
        Initialize cache.
        
        Args:
            ttl: Time to live in seconds (default: 5 minutes)
            max_size: Maximum cache entries (default: 1000)
        """
        self.ttl = ttl
        self.max_size = max_size
        self._cache = OrderedDict()  # LRU: {username: (password_hash, timestamp, attributes)}
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._lock = Lock()
        self._get_count = 0  # For batch cleanup trigger
    
    def get(self, username: str, password: str) -> Optional[Tuple[bool, dict]]:
        """
        Check if authentication result is cached.
        
        Returns:
            (success, attributes) if cached and not expired, None otherwise
        """
        with self._lock:
            self._get_count += 1
            
            # Batch TTL cleanup every 50 gets
            if self._get_count % 50 == 0:
                self._cleanup_expired()
            
            if username not in self._cache:
                self._misses += 1
                return None
            
            cached_password_hash, timestamp, attributes = self._cache[username]
            
            # Check if expired
            if time.time() - timestamp > self.ttl:
                del self._cache[username]
                logger.debug(f"Cache expired for {username}")
                self._misses += 1
                return None
            
            # Verify password hash matches
            import hashlib
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            if password_hash == cached_password_hash:
                logger.debug(f"Cache hit for {username}")
                self._hits += 1
                # Move to end for LRU
                self._cache.move_to_end(username)
                return True, attributes
            else:
                # Password changed, remove from cache
                del self._cache[username]
                logger.debug(f"Password mismatch for cached {username}")
                self._misses += 1
                return None
    
    def _cleanup_expired(self):
        """Remove all expired entries in batch"""
        now = time.time()
        expired = [k for k, (_, ts, _) in self._cache.items() if now - ts > self.ttl]
        for k in expired:
            del self._cache[k]
        if expired:
            logger.debug(f"Batch cleanup: removed {len(expired)} expired entries")
    
    def set(self, username: str, password: str, attributes: dict):
        """
        Cache successful authentication.
        
        Args:
            username: Username
            password: Password (will be hashed)
            attributes: RADIUS attributes
        """
        with self._lock:
            # LRU eviction if at capacity
            while len(self._cache) >= self.max_size:
                evicted_key, _ = self._cache.popitem(last=False)  # Remove oldest (LRU)
                self._evictions += 1
                logger.debug(f"LRU eviction: removed {evicted_key}")
            
            # Hash password for storage
            import hashlib
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            self._cache[username] = (password_hash, time.time(), attributes)
            logger.debug(f"Cached authentication for {username}")
    
    def clear(self):
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
            self._evictions = 0
            self._get_count = 0
            logger.info("Cache cleared")
    
    def stats(self) -> dict:
        """Get cache statistics (alias for get_stats)"""
        return self.get_stats()
    
    def get_stats(self) -> dict:
        """Get cache statistics"""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0.0
            
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'ttl': self.ttl,
                'hits': self._hits,
                'misses': self._misses,
                'hit_rate': round(hit_rate, 2),
                'evictions': self._evictions,
                'total_gets': self._get_count,
            }
