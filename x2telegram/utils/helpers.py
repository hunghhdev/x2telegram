"""
Helper utilities for the x2telegram application.
"""
import sys
import time
from datetime import datetime
from typing import List, Any, Optional, Dict, Union

def log_info(message: str) -> None:
    """
    Log an informational message to stderr.
    
    Args:
        message (str): The message to log
    """
    print(f"[INFO] {message}", file=sys.stderr)

def log_error(message: str) -> None:
    """
    Log an error message to stderr.
    
    Args:
        message (str): The error message to log
    """
    print(f"[ERROR] {message}", file=sys.stderr)

def log_debug(message: str) -> None:
    """
    Log a debug message to stderr.
    
    Args:
        message (str): The debug message to log
    """
    print(f"[DEBUG] {message}", file=sys.stderr)

def format_tweet_message(username: str, tweet, analysis_result: str = None) -> str:
    """
    Format a tweet for sending to Telegram.
    
    Args:
        username (str): The Twitter/X username
        tweet: A Tweet object with tweet_content and tweet_url
        analysis_result (str, optional): AI analysis result to include
        
    Returns:
        str: Formatted message for Telegram
    """
    message = f"New tweet from @{username}:\n\n{tweet.tweet_content}\n\n{tweet.tweet_url}"
    
    # Add AI analysis if provided
    if analysis_result:
        message += f"\n\n<b>AI Analysis:</b> {analysis_result}"
    
    return message

def format_timestamp(dt: datetime) -> str:
    """
    Format a datetime object to ISO format string.
    
    Args:
        dt (datetime): The datetime object to format
        
    Returns:
        str: Formatted timestamp string
    """
    return dt.isoformat()

def retry_with_backoff(func, max_retries=3, initial_delay=1, backoff_factor=2):
    """
    Execute a function with exponential backoff retry logic.
    
    Args:
        func: The function to execute
        max_retries (int): Maximum number of retry attempts
        initial_delay (int): Initial delay between retries in seconds
        backoff_factor (int): Multiplicative factor for backoff
        
    Returns:
        The result of the function call, or raises the last exception
    """
    retries = 0
    last_exception = None
    
    while retries <= max_retries:
        try:
            return func()
        except Exception as e:
            last_exception = e
            if retries == max_retries:
                break
                
            delay = initial_delay * (backoff_factor ** retries)
            log_info(f"Retry {retries+1}/{max_retries} after {delay}s delay due to: {str(e)}")
            time.sleep(delay)
            retries += 1
            
    raise last_exception


def retry_decorator(max_retries=3, initial_delay=1, backoff_factor=2, exceptions=(Exception,)):
    """
    Decorator for retrying a function with exponential backoff.
    
    Args:
        max_retries (int): Maximum number of retry attempts
        initial_delay (float): Initial delay between retries in seconds
        backoff_factor (float): Multiplicative factor for backoff
        exceptions (tuple): Tuple of exception types to catch and retry
        
    Returns:
        Decorated function with retry logic
        
    Example:
        @retry_decorator(max_retries=3, exceptions=(requests.RequestException,))
        def fetch_data():
            return requests.get(url)
    """
    import functools
    import random
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            delay = initial_delay
            last_exception = None
            
            while retries <= max_retries:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if retries == max_retries:
                        break
                    
                    # Add jitter to prevent thundering herd
                    jittered_delay = delay * (0.9 + 0.2 * random.random())
                    log_info(f"Retry {retries+1}/{max_retries} for {func.__name__} "
                             f"after {jittered_delay:.2f}s due to: {str(e)}")
                    time.sleep(jittered_delay)
                    delay *= backoff_factor
                    retries += 1
            
            raise last_exception
        return wrapper
    return decorator

def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """
    Split a list into chunks of specified size.
    
    Args:
        lst (List): The list to split
        chunk_size (int): Size of each chunk
        
    Returns:
        List[List]: List of chunks
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]

def safe_get(data: Dict[str, Any], key_path: str, default: Any = None) -> Any:
    """
    Safely get a nested value from a dictionary using dot notation.
    
    Args:
        data (Dict): The dictionary to access
        key_path (str): Path to the value using dot notation (e.g., "user.profile.name")
        default: Value to return if the path doesn't exist
        
    Returns:
        The value at the specified path or the default value
    """
    keys = key_path.split('.')
    current = data
    
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
            
    return current

def safe_sleep(seconds: float) -> None:
    """
    Sleep for the specified number of seconds safely.
    
    Args:
        seconds (float): Number of seconds to sleep
    """
    try:
        time.sleep(seconds)
    except KeyboardInterrupt:
        raise
    except Exception as e:
        log_error(f"Error during sleep: {str(e)}")

def generate_timestamp() -> str:
    """
    Generate a current timestamp string in ISO format.
    
    Returns:
        str: Current timestamp in ISO format
    """
    return datetime.now().isoformat()


def filter_tweet_content(content: str, 
                         include_keywords: List[str] = None,
                         exclude_keywords: List[str] = None,
                         include_regex: List[str] = None,
                         exclude_regex: List[str] = None) -> bool:
    """
    Check if a tweet should be forwarded based on filter rules.
    
    Args:
        content: Tweet content to check
        include_keywords: Only forward if content contains any of these (case-insensitive)
        exclude_keywords: Skip if content contains any of these (case-insensitive)
        include_regex: Only forward if content matches any of these patterns
        exclude_regex: Skip if content matches any of these patterns
        
    Returns:
        bool: True if tweet should be forwarded, False if it should be skipped
    """
    import re
    
    content_lower = content.lower()
    
    # Check exclude keywords first (highest priority)
    if exclude_keywords:
        for keyword in exclude_keywords:
            if keyword in content_lower:
                log_debug(f"Tweet excluded by keyword: '{keyword}'")
                return False
    
    # Check exclude regex
    if exclude_regex:
        for pattern in exclude_regex:
            try:
                if re.search(pattern, content, re.IGNORECASE):
                    log_debug(f"Tweet excluded by regex: '{pattern}'")
                    return False
            except re.error:
                log_error(f"Invalid exclude regex pattern: '{pattern}'")
    
    # If no include filters, accept all (that weren't excluded)
    has_include_filters = bool(include_keywords or include_regex)
    if not has_include_filters:
        return True
    
    # Check include keywords
    if include_keywords:
        for keyword in include_keywords:
            if keyword in content_lower:
                log_debug(f"Tweet included by keyword: '{keyword}'")
                return True
    
    # Check include regex
    if include_regex:
        for pattern in include_regex:
            try:
                if re.search(pattern, content, re.IGNORECASE):
                    log_debug(f"Tweet included by regex: '{pattern}'")
                    return True
            except re.error:
                log_error(f"Invalid include regex pattern: '{pattern}'")
    
    # Has include filters but none matched
    log_debug("Tweet skipped: no include filters matched")
    return False


def compute_content_hash(content: str) -> str:
    """
    Compute a hash of tweet content for duplicate detection.
    
    Args:
        content: Tweet content to hash
        
    Returns:
        str: MD5 hash of normalized content
    """
    import hashlib
    
    # Normalize: lowercase, remove extra whitespace, remove URLs
    import re
    normalized = content.lower()
    normalized = re.sub(r'https?://\S+', '', normalized)  # Remove URLs
    normalized = re.sub(r'\s+', ' ', normalized).strip()  # Normalize whitespace
    
    return hashlib.md5(normalized.encode('utf-8')).hexdigest()