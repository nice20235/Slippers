"""
Caching utilities for optimizing frequent database queries
"""
import asyncio
import time
from typing import Any, Dict, Optional, Callable
from functools import wraps

class SimpleAsyncCache:
    """Simple in-memory async cache with TTL support"""
    
    def __init__(self, default_ttl: int = 300):  # 5 minutes default
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._default_ttl = default_ttl
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        async with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if time.time() < entry['expires']:
                    return entry['value']
                else:
                    del self._cache[key]
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with TTL"""
        ttl = ttl or self._default_ttl
        expires = time.time() + ttl
        
        async with self._lock:
            self._cache[key] = {
                'value': value,
                'expires': expires
            }
    
    async def delete(self, key: str) -> None:
        """Delete key from cache"""
        async with self._lock:
            self._cache.pop(key, None)
    
    async def clear(self) -> None:
        """Clear all cache entries"""
        async with self._lock:
            self._cache.clear()
    
    async def cleanup_expired(self) -> None:
        """Remove expired entries"""
        current_time = time.time()
        async with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if current_time >= entry['expires']
            ]
            for key in expired_keys:
                del self._cache[key]
    
    async def clear_pattern(self, pattern: str) -> None:
        """Clear cache entries matching pattern"""
        async with self._lock:
            keys_to_delete = []
            for key in self._cache.keys():
                if pattern.replace('*', '') in key:
                    keys_to_delete.append(key)
            for key in keys_to_delete:
                del self._cache[key]

# Global cache instance
cache = SimpleAsyncCache(default_ttl=300)  # 5 minutes

def cached(ttl: int = 300, key_prefix: str = ""):
    """Decorator to cache function results"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}:{func.__name__}:"
            
            # Include args in key (skip self/db sessions)
            for i, arg in enumerate(args):
                if hasattr(arg, '__class__') and 'Session' in arg.__class__.__name__:
                    continue  # Skip database sessions
                cache_key += f"arg{i}:{str(arg)}:"
            
            # Include kwargs in key
            for k, v in kwargs.items():
                if hasattr(v, '__class__') and 'Session' in v.__class__.__name__:
                    continue  # Skip database sessions
                cache_key += f"{k}:{str(v)}:"
            
            # Try to get from cache
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, ttl)
            return result
        
        return wrapper
    return decorator

async def invalidate_cache_pattern(pattern: str) -> None:
    """Invalidate cache entries matching pattern"""
    await cache.cleanup_expired()
    # Simple pattern matching - in production, use Redis with pattern support
    keys_to_delete = []
    async with cache._lock:
        for key in cache._cache.keys():
            if pattern in key:
                keys_to_delete.append(key)
    
    for key in keys_to_delete:
        await cache.delete(key)
