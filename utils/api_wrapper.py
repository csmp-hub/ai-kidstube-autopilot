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
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            
            for attempt in range(1, max_retries + 1):
                try:
                    # ✅ FIX: Use f-string instead of keyword arguments
                    logger.info(f"API call attempt {attempt}/{max_retries} - function: {func.__name__}")
                    return func(*args, **kwargs)
                    
                except retry_on_exceptions as e:
                    last_error = e
                    wait_time = backoff_factor ** (attempt - 1)
                    
                    # ✅ FIX: Use f-string instead of keyword arguments
                    logger.warning(
                        f"Attempt {attempt} failed: {type(e).__name__}: {str(e)[:100]} - function: {func.__name__} - retry_after: {wait_time}s"
                    )
                    
                    if attempt < max_retries:
                        time.sleep(wait_time)
                    continue
                    
                except Exception as e:
                    # Non-retryable exception
                    logger.error(f"Non-retryable error: {type(e).__name__}: {e} - function: {func.__name__}")
                    raise
            
            # All retries failed - try fallback
            if fallback_func and callable(fallback_func):
                logger.info(f"Switching to fallback method - primary: {func.__name__}, fallback: {fallback_func.__name__}")
                try:
                    return fallback_func(*args, **kwargs)
                except Exception as fallback_error:
                    logger.error(f"Fallback also failed: {str(fallback_error)[:100]}")
            
            # Everything failed
            error_msg = str(last_error)[:100] if last_error else "Unknown error"
            logger.error(f"All attempts exhausted - function: {func.__name__} - error: {error_msg}")
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
