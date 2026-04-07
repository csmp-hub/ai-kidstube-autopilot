# utils klasöründe yeni dosya: api_wrapper.py
# İçeriği yapıştır:

# utils/api_wrapper.py
# ====================
"""
Retry logic with fallback for unreliable free APIs
"""
import time
import requests
from functools import wraps
from typing import Optional, Callable
from utils.logger import logger

def retry_with_fallback(
    max_retries: int = 3,
    fallback_func: Optional[Callable] = None,
    backoff_factor: float = 2.0,
    timeout_seconds: int = 30,
    retry_on_exceptions: tuple = (requests.exceptions.RequestException, TimeoutError)
):
    """
    Decorator for retrying API calls with exponential backoff and fallback
    
    Args:
        max_retries: Number of retry attempts before giving up
        fallback_func: Function to call if all retries fail
        backoff_factor: Multiplier for wait time between retries (2.0 = 2s, 4s, 8s)
        timeout_seconds: Request timeout in seconds
        retry_on_exceptions: Tuple of exception types that trigger retry
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            
            for attempt in range(1, max_retries + 1):
                try:
                    logger.info(f"API call attempt {attempt}/{max_retries}", 
                               function=func.__name__)
                    return func(*args, **kwargs)
                    
                except retry_on_exceptions as e:
                    last_error = e
                    wait_time = backoff_factor ** (attempt - 1)
                    
                    logger.warning(
                        f"Attempt {attempt} failed: {type(e).__name__}: {str(e)[:100]}",
                        function=func.__name__,
                        retry_after=wait_time
                    )
                    
                    if attempt < max_retries:
                        time.sleep(wait_time)
                    continue
                    
                except Exception as e:
                    # Non-retryable exception
                    logger.error(f"Non-retryable error: {type(e).__name__}: {e}", 
                                function=func.__name__)
                    raise
            
            # All retries failed - try fallback
            if fallback_func and callable(fallback_func):
                logger.info("Switching to fallback method", 
                           primary=func.__name__,
                           fallback=fallback_func.__name__)
                try:
                    return fallback_func(*args, **kwargs)
                except Exception as fallback_error:
                    logger.error("Fallback also failed", 
                                error=str(fallback_error)[:100])
            
            # Everything failed
            logger.error("All attempts exhausted", 
                        function=func.__name__,
                        error=str(last_error)[:100] if last_error else "Unknown")
            raise last_error or RuntimeError("API call failed after all retries")
            
        return wrapper
    return decorator


def with_timeout(timeout_seconds: int = 30):
    """Decorator to add timeout to any function"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError(f"Function {func.__name__} timed out after {timeout_seconds}s")
            
            # Set timeout (Unix only - for Windows, use threading approach)
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(timeout_seconds)
            
            try:
                return func(*args, **kwargs)
            finally:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)
        return wrapper
    return decorator
# ====================
# Dosyayı kaydet ✅