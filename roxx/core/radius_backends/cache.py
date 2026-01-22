"""
Simple in-memory cache for RADIUS authentication results
"""

from typing import Optional, Tuple
import time
import logging
from threading import Lock

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
        self._cache = {}  # {username: (password_hash, timestamp, attributes)}
        self._hits = 0
        self._misses = 0
        self._lock = Lock()
    
    def get(self, username: str, password: str) -> Optional[Tuple[bool, dict]]:
        """
        Check if authentication result is cached.
        
        Returns:
            (success, attributes) if cached and not expired, None otherwise
        """
        with self._lock:
            if username not in self._cache:
                self._misses += 1
                return None
            
            cached_password_hash, timestamp, attributes = self._cache[username]
            
            # Check if expired
            if time.time() - timestamp > self.ttl:
                del self._cache[username]
                logger.debug(f"Cache expired for {username}")
                return None
            
            # Verify password hash matches
            import hashlib
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            if password_hash == cached_password_hash:
                logger.debug(f"Cache hit for {username}")
                self._hits += 1
                return True, attributes
            else:
                # Password changed, remove from cache
                del self._cache[username]
                logger.debug(f"Password mismatch for cached {username}")
                self._misses += 1
                return None
    
    def set(self, username: str, password: str, attributes: dict):
        """
        Cache successful authentication.
        
        Args:
            username: Username
            password: Password (will be hashed)
            attributes: RADIUS attributes
        """
        with self._lock:
            # Check cache size
            if len(self._cache) >= self.max_size:
                # Remove oldest entry
                oldest_user = min(self._cache.keys(), 
                                key=lambda k: self._cache[k][1])
                del self._cache[oldest_user]
                logger.debug(f"Cache full, removed {oldest_user}")
            
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
            logger.info("Cache cleared")
    
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
                'hit_rate': hit_rate
            }
