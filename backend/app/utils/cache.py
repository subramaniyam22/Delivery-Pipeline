"""
Redis caching utilities and decorators.
"""
import json
import logging
from functools import wraps
from typing import Optional, Any, Callable
import redis
from app.config import settings

logger = logging.getLogger(__name__)

# Initialize Redis client
try:
    redis_client = redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5
    )
    # Test connection
    redis_client.ping()
    logger.info("Redis cache client initialized successfully")
except Exception as e:
    logger.error(f"Failed to connect to Redis: {e}")
    redis_client = None


class CacheManager:
    """Redis cache manager with TTL support."""
    
    def __init__(self, client: Optional[redis.Redis] = None):
        self.client = client or redis_client
        
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self.client:
            return None
            
        try:
            value = self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """
        Set value in cache with TTL.
        
        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time to live in seconds (default: 5 minutes)
        """
        if not self.client:
            return False
            
        try:
            serialized = json.dumps(value, default=str)
            self.client.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not self.client:
            return False
            
        try:
            self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern.
        
        Args:
            pattern: Redis pattern (e.g., "projects:*")
            
        Returns:
            Number of keys deleted
        """
        if not self.client:
            return 0
            
        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache delete pattern error for {pattern}: {e}")
            return 0
    
    def clear_all(self) -> bool:
        """Clear all cache (use with caution!)."""
        if not self.client:
            return False
            
        try:
            self.client.flushdb()
            logger.warning("All cache cleared!")
            return True
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return False


# Global cache manager instance
cache = CacheManager()


def cached(key_prefix: str, ttl: int = 300):
    """
    Decorator to cache function results.
    
    Args:
        key_prefix: Prefix for cache key
        ttl: Time to live in seconds
        
    Usage:
        @cached("user", ttl=900)
        def get_user(user_id: str):
            return db.query(User).filter(User.id == user_id).first()
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Build cache key from function arguments
            key_parts = [key_prefix]
            
            # Add positional args
            for arg in args:
                if hasattr(arg, 'id'):  # Skip DB session objects
                    continue
                key_parts.append(str(arg))
            
            # Add keyword args
            for k, v in sorted(kwargs.items()):
                if k in ['db', 'session']:  # Skip DB session
                    continue
                key_parts.append(f"{k}:{v}")
            
            cache_key = ":".join(key_parts)
            
            # Try to get from cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached_value
            
            # Cache miss - call function
            logger.debug(f"Cache miss: {cache_key}")
            result = func(*args, **kwargs)
            
            # Store in cache
            if result is not None:
                cache.set(cache_key, result, ttl=ttl)
            
            return result
        
        return wrapper
    return decorator


def invalidate_cache(pattern: str):
    """
    Invalidate cache by pattern.
    
    Usage:
        invalidate_cache("projects:*")
        invalidate_cache("user:123")
    """
    deleted = cache.delete_pattern(pattern)
    logger.info(f"Invalidated {deleted} cache keys matching: {pattern}")
    return deleted


# Cache key builders
def project_cache_key(project_id: str) -> str:
    """Build cache key for single project."""
    return f"project:{project_id}"


def projects_list_cache_key(page: int = 1, page_size: int = 50, user_id: str = None) -> str:
    """Build cache key for projects list."""
    parts = [f"projects:list:page{page}:size{page_size}"]
    if user_id:
        parts.append(f"user{user_id}")
    return ":".join(parts)


def user_cache_key(user_id: str) -> str:
    """Build cache key for user."""
    return f"user:{user_id}"


def config_cache_key(config_type: str) -> str:
    """Build cache key for configuration."""
    return f"config:{config_type}"
