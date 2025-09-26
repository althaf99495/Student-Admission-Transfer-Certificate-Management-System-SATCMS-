# utils/caching.py
"""
Simple in-memory caching utilities for the application.
WARNING: This is process-specific and not suitable for multi-process or multi-server setups (e.g., Gunicorn with multiple workers).
For production environments, consider using a distributed cache like Redis or Memcached with Flask-Caching.
"""

from functools import wraps
import time
from flask import current_app # Used for logging and app context awareness
import hashlib # For more robust cache key generation
from flask_caching import Cache

# Create a cache manager instance.
# This instance will be configured and initialized with the Flask app
# in the application factory (create_app).
cache_manager = Cache()

# Simple in-memory cache (dictionary-based)
_cache = {} # Stores cached data: {'cache_key': data}
_cache_expiry = {} # Stores expiry timestamps: {'cache_key': timestamp}

DEFAULT_TIMEOUT = 300  # Default cache timeout in seconds (5 minutes)

def get_from_cache(key: str):
    """
    Retrieves an item from the cache if it exists and hasn't expired.
    If the item is expired, it's removed from the cache.
    """
    if key in _cache_expiry and _cache_expiry[key] < time.time():
        # Item has expired
        _cache.pop(key, None)
        _cache_expiry.pop(key, None)
        if current_app and current_app.debug:
             current_app.logger.debug(f"Cache EXPIRED for key: {key}")
        return None
    
    cached_value = _cache.get(key)
    if cached_value is not None:
        if current_app and current_app.debug:
            current_app.logger.debug(f"Cache HIT for key: {key}")
    elif current_app and current_app.debug:
        current_app.logger.debug(f"Cache MISS for key: {key}")
        
    return cached_value

def set_in_cache(key: str, value, timeout: int = DEFAULT_TIMEOUT):
    """
    Sets an item in the cache with an expiry time.
    A timeout of 0 or negative means cache indefinitely (or until cleared).
    """
    if timeout <= 0: # Treat 0 or negative as "no expiry" for this simple cache
        expiry_time = float('inf') 
    else:
        expiry_time = time.time() + timeout

    _cache[key] = value
    _cache_expiry[key] = expiry_time
    if current_app and current_app.debug:
        log_timeout = f"{timeout}s" if timeout > 0 else "indefinitely"
        current_app.logger.debug(f"Cache SET for key: {key} with timeout: {log_timeout}")


def clear_cache(key: str = None):
    """
    Clears a specific key from the cache, or the entire cache if no key is provided.
    """
    global _cache, _cache_expiry # Needed as we are reassigning global _cache and _cache_expiry
    if key:
        _cache.pop(key, None)
        _cache_expiry.pop(key, None)
        if current_app and current_app.debug:
            current_app.logger.info(f"Cache CLEARED for key: {key}")
    else:
        _cache = {}
        _cache_expiry = {}
        if current_app and current_app.debug:
            current_app.logger.info("Entire in-memory cache CLEARED.")

def _generate_cache_key(prefix: str, func_name: str, args, kwargs) -> str:
    """Helper to generate a cache key."""
    key_parts = [prefix, func_name]
    # Serialize args and kwargs to a string representation for the key.
    # Using repr() and sorting kwargs ensures consistency.
    # For complex objects, a more sophisticated serialization might be needed.
    if args:
        key_parts.extend(repr(arg) for arg in args)
    if kwargs:
        key_parts.extend(f"{k}={repr(v)}" for k, v in sorted(kwargs.items()))
    
    # Use hashlib for a more robust and potentially shorter key if parts are long
    # For simple cases, joining is fine.
    # return ":".join(key_parts)
    
    # Using hash to keep keys more manageable
    serialized_parts = ":".join(key_parts)
    return prefix + hashlib.md5(serialized_parts.encode('utf-8')).hexdigest()


def cached(timeout: int = DEFAULT_TIMEOUT, cache_key_prefix: str = "view_cache_"):
    """
    Decorator to cache the result of a function using the simple in-memory cache.
    
    Args:
        timeout (int): Cache timeout in seconds. Use 0 or negative for indefinite.
        cache_key_prefix (str): Prefix for the cache key.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_app: # Cannot cache if not in an app context (e.g. during tests without app setup)
                return func(*args, **kwargs)

            cache_key = _generate_cache_key(cache_key_prefix, func.__name__, args, kwargs)
            
            cached_value = get_from_cache(cache_key)
            if cached_value is not None:
                return cached_value
            
            result = func(*args, **kwargs)
            set_in_cache(cache_key, result, timeout)
            return result
        return wrapper
    return decorator

def init_app_cache(app):
    """Initialize the cache manager with the Flask app."""
    # Default to Redis if not explicitly set
    app.config.setdefault("CACHE_TYPE", "RedisCache")
    app.config.setdefault("CACHE_REDIS_HOST", "localhost")
    app.config.setdefault("CACHE_REDIS_PORT", 6379)
    app.config.setdefault("CACHE_REDIS_DB", 0)
    app.config.setdefault("CACHE_REDIS_PASSWORD", None)

    cache_manager.init_app(app)

    app.logger.info(f"Flask-Caching initialized with type: {app.config.get('CACHE_TYPE')}")
    if app.config["CACHE_TYPE"].lower() == "simplecache":
        app.logger.warning("Using SimpleCache (in-memory). NOT suitable for production!")
    elif app.config["CACHE_TYPE"].lower() == "rediscache":
        app.logger.info("Redis cache enabled ✅")