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

# --- Example: Flask-Caching integration placeholder ---
# from flask_caching import Cache
# cache_manager = Cache() # This would be initialized with the app

# def init_app_cache(app):
#     """Initialize a more robust cache with Flask app (e.g., Flask-Caching)."""
#     # Example config for simple cache (filesystem) - replace with Redis/Memcached for production
#     # app.config.setdefault("CACHE_TYPE", "FileSystemCache") # Or "SimpleCache" for in-memory like this one
#     # app.config.setdefault("CACHE_DIR", os.path.join(app.root_path, "cache"))
#     # os.makedirs(app.config["CACHE_DIR"], exist_ok=True)
#     # cache_manager.init_app(app)
#     if current_app:
#         current_app.logger.info("Simple in-memory caching is active. For production, consider Flask-Caching with Redis/Memcached.")


if __name__ == '__main__':
    # Basic test for the simple in-memory cache (simulating Flask app context for logger)
    class MockApp:
        class MockLogger:
            def debug(self, msg): print(f"DEBUG: {msg}")
            def info(self, msg): print(f"INFO: {msg}")
        logger = MockLogger()
        debug = True

    # Simulate current_app for testing the logger calls
    _original_current_app = current_app
    # current_app = MockApp() # This is tricky to mock globally, usually done with app_context

    print("--- Testing Simple In-Memory Cache ---")

    @cached(timeout=1, cache_key_prefix="test_func_")
    def my_test_function(param1, param2="default"):
        # This function won't have current_app in this __main__ block
        # unless explicitly pushed. For decorator tests, it's better to test within Flask context.
        print(f"Executing my_test_function({param1}, {param2})...")
        time.sleep(0.1) # Simulate work
        return f"Result for {param1}-{param2}"

    # To properly test with current_app logging, you'd need a Flask app context
    # For simplicity, we'll test the direct cache functions here primarily.
    
    print("Testing direct cache set/get:")
    set_in_cache("mykey1", "myvalue1", timeout=1)
    print(f"Get 'mykey1': {get_from_cache('mykey1')}") # HIT
    time.sleep(1.1)
    print(f"Get 'mykey1' after expiry: {get_from_cache('mykey1')}") # EXPIRED, then MISS

    set_in_cache("mykey2", "myvalue2_no_expire", timeout=0)
    print(f"Get 'mykey2': {get_from_cache('mykey2')}") # HIT
    time.sleep(0.1)
    print(f"Get 'mykey2' again: {get_from_cache('mykey2')}") # HIT (should not expire)


    print("\nTesting @cached decorator (logging might not appear if no app_context):")
    # Simulate some calls to the decorated function
    # Note: The logging inside the decorator relies on current_app.
    # If current_app is None, logging calls within the decorator might be skipped or error.
    # This is a limitation of testing Flask-dependent code outside a Flask context.
    
    # This test will work for functionality but not for logger output unless current_app is mocked.
    try:
        print(my_test_function("Arg1"))  # Executes, caches
        print(my_test_function("Arg1"))  # Hits cache
        print(my_test_function("Arg2"))  # Executes, caches
        print(my_test_function("Arg1", param2="override")) # Executes, caches
        print(my_test_function("Arg1", param2="override")) # Hits cache

        print("Waiting for cache to expire (1 sec for 'Arg1')...")
        time.sleep(1.1)
        print(my_test_function("Arg1")) # Executes again (cache expired)
        print(my_test_function("Arg2")) # Should still hit cache if its timeout hasn't passed
                                        # (it will, as it also had 1s timeout)

    except Exception as e:
        print(f"Error during decorated function test: {e}")


    clear_cache("mykey2")
    print(f"Get 'mykey2' after specific clear: {get_from_cache('mykey2')}") # MISS

    clear_cache()
    print("Entire cache cleared.")
    print(f"Get 'mykey1' after full clear: {get_from_cache('mykey1')}") # MISS

    # current_app = _original_current_app # Restore