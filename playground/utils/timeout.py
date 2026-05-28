import time
import random
from functools import wraps
from loguru import logger

def deco_retry_on_ratelimit(max_retries: int = 10, wait_seconds: int = 60):
    """
    A decorator that retries a function when a rate-limit (HTTP 429) error is
    encountered, waiting a fixed number of seconds between attempts.

    Non-rate-limit exceptions are re-raised immediately without retrying.

    Args:
        max_retries (int):   Maximum number of retry attempts after the first failure.
        wait_seconds (int):  Fixed wait time in seconds between retries (default 60).
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for i in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    exc_str = str(e)
                    is_rate_limit = (
                        "429" in exc_str
                        or "rate limit" in exc_str.lower()
                        or "RateLimitError" in type(e).__name__
                        or "每分钟请求次数超过限制" in exc_str
                    )
                    if not is_rate_limit or i >= max_retries:
                        raise
                    logger.warning(
                        f"Attempt {i + 1}/{max_retries} failed for '{func.__name__}' "
                        f"(rate limit): {e}. Waiting {wait_seconds}s before retry..."
                    )
                    time.sleep(wait_seconds)
        return wrapper
    return decorator


def deco_retry_exponential(max_retries: int = 3, initial_sleep_seconds: int = 2):
    """
    A decorator for retrying a function with exponential backoff and jitter.

    Args:
        max_retries (int): The maximum number of retries.
        initial_sleep_seconds (int): The initial sleep time in seconds, which doubles on each retry.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for i in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if i == max_retries - 1:
                        logger.error(f"Function '{func.__name__}' failed after {max_retries} retries.")
                        raise  # Re-raise the last exception

                    sleep_time = (initial_sleep_seconds * (2 ** i)) + random.uniform(0, 1)
                    logger.warning(f"Attempt {i + 1}/{max_retries} failed for '{func.__name__}': {e}. Retrying in {sleep_time:.2f} seconds...")
                    time.sleep(sleep_time)
            # This part should not be reachable if max_retries > 0, but is here for completeness.
            raise Exception(f"Function '{func.__name__}' failed after {max_retries} retries.")
        return wrapper
    return decorator
