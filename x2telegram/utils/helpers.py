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

def format_tweet_message(username: str, tweet) -> str:
    """
    Format a tweet for sending to Telegram.
    
    Args:
        username (str): The Twitter/X username
        tweet: A Tweet object with tweet_content and tweet_url
        
    Returns:
        str: Formatted message for Telegram
    """
    return f"New tweet from @{username}:\n\n{tweet.tweet_content}\n\n{tweet.tweet_url}"

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