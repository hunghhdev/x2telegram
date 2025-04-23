"""
HTML scraping service for fetching tweets from Nitter pages.
Despite the filename (kept for backward compatibility), this module 
now uses direct HTML scraping instead of RSS feeds.
"""
import sys
import random
import time
import requests
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any
from bs4 import BeautifulSoup
import re

from ..config import NITTER_MIRRORS
from ..core.models import Tweet
from ..utils import log_info, log_error, log_debug

# List of possible user agents to rotate
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
]

class RSSService:
    """
    Service for fetching and processing tweets from Nitter instances.
    Despite the class name (kept for backward compatibility), this class
    now uses direct HTML scraping instead of RSS feeds.
    """
    
    def __init__(self, mirrors=None, timeout=60, retry_count=10):
        """
        Initialize the scraping service.
        
        Args:
            mirrors (list, optional): List of Nitter mirror URLs. Defaults to configured mirrors.
            timeout (int, optional): Timeout for web requests in seconds. Defaults to 60.
            retry_count (int, optional): Maximum number of retry attempts. Defaults to 10.
        """
        # Use configured mirrors from settings
        self.mirrors = mirrors or NITTER_MIRRORS
        
        self.timeout = timeout
        self.retry_count = retry_count
        
        # Initialize working mirrors list with all mirrors
        self.working_mirrors = self.mirrors.copy()
        
        # Track rate limiting for each mirror
        self.rate_limited_until = {}
        
        # Track which selectors work for which mirrors
        self.mirror_selectors = {}
    
    def get_random_user_agent(self) -> str:
        """Get a random user agent from the list."""
        return random.choice(USER_AGENTS)
    
    def get_request_headers(self) -> Dict[str, str]:
        """
        Get headers for the HTTP request with a random user agent.
        
        Returns:
            dict: HTTP headers
        """
        return {
            'User-Agent': self.get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://google.com/',  # Add a generic referer
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
        }
    
    def get_working_mirror(self) -> str:
        """
        Get a working Nitter mirror that's not rate limited.
        
        Returns:
            str: URL of a working Nitter mirror
        """
        # Filter out rate-limited mirrors
        current_time = time.time()
        available_mirrors = [
            mirror for mirror in self.working_mirrors 
            if mirror not in self.rate_limited_until or current_time > self.rate_limited_until[mirror]
        ]
        
        if not available_mirrors:
            log_info("No immediately available mirrors, waiting for rate limits to expire")
            # Find the mirror with the soonest expiry of rate limiting
            next_available_time = min(self.rate_limited_until.values())
            sleep_time = max(0, next_available_time - current_time) + 1
            
            if sleep_time > 60:  # If we need to wait more than a minute
                log_info(f"All mirrors rate limited, resetting list")
                self.working_mirrors = self.mirrors.copy()
                self.rate_limited_until = {}
                return random.choice(self.working_mirrors)
            
            log_info(f"Waiting {sleep_time:.1f} seconds for rate limits to expire")
            time.sleep(sleep_time)
            return self.get_working_mirror()
        
        return random.choice(available_mirrors)
    
    def mark_rate_limited(self, mirror: str, retry_after: int = 60) -> None:
        """
        Mark a mirror as rate limited.
        
        Args:
            mirror (str): The mirror URL
            retry_after (int): Seconds to wait before retrying
        """
        self.rate_limited_until[mirror] = time.time() + retry_after
        log_info(f"Mirror {mirror} rate limited, will retry after {retry_after} seconds")
    
    def fetch_tweets_html(self, username: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
        """
        Fetch tweets for a Twitter/X user by scraping Nitter HTML.
        
        Args:
            username (str): Twitter/X username without @ symbol
            
        Returns:
            tuple: (tweets_data, mirror_url) if successful, (None, None) otherwise
        """
        if not username:
            log_error("No username provided to fetch_tweets_html")
            return None, None
            
        # Remove @ if present
        username = username.lstrip('@')
        
        # Try up to retry_count times with different mirrors
        for attempt in range(self.retry_count):
            if not self.working_mirrors:
                log_error("No working Nitter mirrors available, resetting list")
                self.working_mirrors = self.mirrors.copy()
                if attempt == self.retry_count - 1:
                    return None, None
            
            mirror = self.get_working_mirror()
            url = f"{mirror}/{username}"
            
            try:
                log_info(f"Fetching tweets from {url} (attempt {attempt+1}/{self.retry_count})")
                
                # Get random headers for each request to avoid detection
                headers = self.get_request_headers()
                
                # Fetch the HTML page
                response = requests.get(url, timeout=self.timeout, headers=headers)
                
                # Handle rate limiting
                if response.status_code == 429:
                    log_error(f"Rate limited by {mirror} (HTTP 429)")
                    retry_after = int(response.headers.get('Retry-After', 60))
                    self.mark_rate_limited(mirror, retry_after)
                    if mirror in self.working_mirrors:
                        self.working_mirrors.remove(mirror)
                    continue
                
                # Handle other error status codes
                if response.status_code != 200:
                    log_error(f"Failed to fetch HTML from {mirror}: HTTP {response.status_code}")
                    if mirror in self.working_mirrors:
                        self.working_mirrors.remove(mirror)
                    continue
                
                # Parse the HTML and extract tweets with multiple selector strategies
                tweets_data = self.parse_nitter_html(response.text, mirror, username)
                
                if tweets_data:
                    log_info(f"Successfully scraped {len(tweets_data)} tweets from {mirror}")
                    return tweets_data, mirror
                else:
                    log_error(f"No tweets found on {mirror} for @{username}")
                    # Don't remove the mirror as it might just be that the user has no tweets
                    
            except requests.exceptions.Timeout:
                log_error(f"Timeout connecting to {mirror}")
                if mirror in self.working_mirrors:
                    self.working_mirrors.remove(mirror)
            except requests.exceptions.ConnectionError:
                log_error(f"Connection error with {mirror}")
                if mirror in self.working_mirrors:
                    self.working_mirrors.remove(mirror)
            except Exception as e:
                log_error(f"Error fetching from {mirror}: {str(e)}")
                if mirror in self.working_mirrors:
                    self.working_mirrors.remove(mirror)
            
            # Wait before retrying with a different mirror, with increasing backoff
            if attempt < self.retry_count - 1:
                backoff_time = 1 * (2 ** attempt)  # Exponential backoff: 1, 2, 4, 8...
                time.sleep(backoff_time)
        
        log_error(f"Failed to fetch tweets for @{username} after {self.retry_count} attempts")
        return None, None
    
    def parse_nitter_html(self, html: str, mirror: str, username: str) -> List[Dict[str, Any]]:
        """
        Parse Nitter HTML page to extract tweets using multiple strategies.
        
        Args:
            html (str): HTML content of the Nitter page
            mirror (str): Nitter mirror URL
            username (str): Twitter/X username
            
        Returns:
            list: List of tweet dictionaries
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Try multiple selectors used by different Nitter instances
            selectors = [
                # Classic Nitter selectors
                '.timeline-item', 
                '.tweet',
                '.timeline .item',
                # Alternative selectors
                '.tweet-container',
                'article.tweet',
                '.timeline article',
                'div[data-tweet-id]',
                # Broader selectors if needed
                '#timeline > div',
                '.feed > div'
            ]
            
            tweets = []
            
            # Try each selector until we find tweets
            for selector in selectors:
                elements = soup.select(selector)
                if elements:
                    log_info(f"Found {len(elements)} potential tweet elements with selector: {selector}")
                    
                    # Remember which selector worked for this mirror
                    self.mirror_selectors[mirror] = selector
                    
                    # Process each potential tweet element
                    for element in elements:
                        tweet_data = self.extract_tweet_data(element, mirror, username)
                        if tweet_data:
                            tweets.append(tweet_data)
                    
                    # If we found tweets, we can stop trying other selectors
                    if tweets:
                        break
            
            # If we still don't have tweets, try a more generic approach
            if not tweets:
                log_info("No tweets found with standard selectors, trying generic extraction")
                
                # Look for any elements that might be tweets
                potential_tweets = self.find_potential_tweets(soup, mirror, username)
                tweets.extend(potential_tweets)
            
            # Sort tweets by published date (newest first)
            try:
                tweets = sorted(tweets, key=lambda x: x['published'], reverse=True)
            except Exception:
                log_error("Could not sort tweets by date, using default order")
            
            return tweets
            
        except Exception as e:
            log_error(f"Error parsing HTML: {str(e)}")
            return []
    
    def extract_tweet_data(self, element, mirror: str, username: str) -> Optional[Dict[str, Any]]:
        """
        Extract tweet data from a single HTML element.
        
        Args:
            element: BeautifulSoup element
            mirror: Nitter mirror URL
            username: Twitter/X username
            
        Returns:
            Optional[Dict]: Tweet data or None if not a valid tweet
        """
        try:
            # Skip non-tweet elements
            if 'timeline-header' in str(element.get('class', [])):
                return None
                
            # Try multiple strategies to get tweet ID and URL
            tweet_id = None
            tweet_url = None
            
            # Check data attributes first
            if element.has_attr('data-tweet-id'):
                tweet_id = element['data-tweet-id']
            
            # Try to find permalink
            permalink_selectors = [
                'a.tweet-link', 'a[href*="status"]', '.tweet-date a', 
                'a[href*="/status/"]', 'a.Permalink', 'a.timestamp'
            ]
            
            for selector in permalink_selectors:
                permalink = element.select_one(selector)
                if permalink and permalink.has_attr('href'):
                    tweet_url = permalink['href']
                    # Extract ID from URL if not found yet
                    if not tweet_id:
                        # Look for status/DIGITS pattern
                        match = re.search(r'status[es]?/(\d+)', tweet_url)
                        if match:
                            tweet_id = match.group(1)
                    break
            
            # If we can't find either ID or URL, this isn't a tweet
            if not tweet_id and not tweet_url:
                return None
            
            # Make URL absolute if it's relative
            if tweet_url and tweet_url.startswith('/'):
                tweet_url = f"{mirror}{tweet_url}"
            
            # Extract tweet content
            content = ""
            content_selectors = [
                '.tweet-content', '.content', '.tweet-text', 
                '.tweet-body', '.tweet p', '.tweet > div > p'
            ]
            
            for selector in content_selectors:
                content_element = element.select_one(selector)
                if content_element:
                    content = content_element.get_text(strip=True)
                    break
            
            # Extract timestamp
            published = datetime.now().isoformat()
            time_selectors = [
                '.tweet-date a', 'time', '.timestamp', '.time'
            ]
            
            for selector in time_selectors:
                timestamp = element.select_one(selector)
                if timestamp:
                    if timestamp.has_attr('title'):
                        published = timestamp.get('title', '')
                    elif timestamp.has_attr('datetime'):
                        published = timestamp.get('datetime', '')
                    break
            
            # Extract author info
            author = username
            author_selectors = [
                '.fullname', '.username', '.name', '.user'
            ]
            
            for selector in author_selectors:
                fullname = element.select_one(selector)
                if fullname:
                    author = fullname.get_text(strip=True)
                    break
            
            # Extract media (images)
            tweet_image = None
            image_selectors = [
                '.still-image', 'img.media-img', '.media img', 
                '.attachment img', '.tweet-img'
            ]
            
            for selector in image_selectors:
                image_element = element.select_one(selector)
                if image_element and image_element.has_attr('src'):
                    image_url = image_element['src']
                    # Make URL absolute if it's relative
                    if image_url.startswith('/'):
                        image_url = f"{mirror}{image_url}"
                    tweet_image = image_url
                    break
            
            return {
                'id': tweet_id or f"unknown_{int(time.time())}",
                'url': tweet_url or f"{mirror}/{username}/status/{tweet_id}",
                'content': content,
                'published': published,
                'author': author,
                'image': tweet_image
            }
            
        except Exception as e:
            log_error(f"Error extracting tweet data: {str(e)}")
            return None
    
    def find_potential_tweets(self, soup, mirror: str, username: str) -> List[Dict[str, Any]]:
        """
        Try to find tweets using pattern matching when standard selectors fail.
        
        Args:
            soup: BeautifulSoup object
            mirror: Nitter mirror URL
            username: Twitter/X username
            
        Returns:
            List[Dict]: List of found tweets
        """
        tweets = []
        
        try:
            # Look for any elements with status in the URL
            status_links = soup.select('a[href*="status"]')
            processed_urls = set()
            
            for link in status_links:
                try:
                    href = link.get('href', '')
                    
                    # Skip if already processed this URL
                    if href in processed_urls:
                        continue
                    processed_urls.add(href)
                    
                    # Check if this looks like a tweet URL
                    if '/status/' in href:
                        # Try to extract tweet ID
                        match = re.search(r'status[es]?/(\d+)', href)
                        if match:
                            tweet_id = match.group(1)
                            
                            # Find the closest container element
                            container = link
                            for _ in range(5):  # Look up to 5 levels up
                                if container.parent:
                                    container = container.parent
                                    # Stop if we reach a good container element
                                    if container.name in ['div', 'article', 'li'] and container.get('class'):
                                        break
                            
                            # Extract tweet content - look for nearby text
                            content = ""
                            # Option 1: Look for specific paragraphs
                            p_elements = container.find_all('p')
                            if p_elements:
                                content = p_elements[0].get_text(strip=True)
                            
                            # Option 2: Just get all text from the container
                            if not content:
                                content = container.get_text(strip=True)
                                # Try to clean up the content by removing usernames and timestamps
                                content = re.sub(r'@[\w]+|^\s*[\w\s]+\s*·\s*[\w\s]+\s*$', '', content)
                            
                            # Make URL absolute if needed
                            tweet_url = href
                            if tweet_url.startswith('/'):
                                tweet_url = f"{mirror}{tweet_url}"
                            
                            # Add the tweet if we have an ID and content
                            if tweet_id and content:
                                tweets.append({
                                    'id': tweet_id,
                                    'url': tweet_url,
                                    'content': content,
                                    'published': datetime.now().isoformat(),
                                    'author': username,
                                    'image': None  # Not trying to find images in this fallback
                                })
                
                except Exception as e:
                    log_error(f"Error finding potential tweet: {str(e)}")
                    continue
            
        except Exception as e:
            log_error(f"Error in find_potential_tweets: {str(e)}")
        
        return tweets
    
    def get_tweets(self, username: str) -> List[Tweet]:
        """
        Get tweets for a Twitter/X user.
        
        Args:
            username (str): Twitter/X username
            
        Returns:
            list: List of Tweet objects
        """
        tweets_data, mirror = self.fetch_tweets_html(username)
        if not tweets_data:
            return []
            
        tweets = []
        for tweet_data in tweets_data:
            try:
                # Create Tweet object
                tweet = Tweet(
                    tweet_id=tweet_data['id'],
                    tweet_url=tweet_data['url'],
                    tweet_content=tweet_data['content'],
                    tweet_image=tweet_data.get('image'),
                    created_at=tweet_data['published']
                )
                
                # Store additional data in metadata
                tweet.metadata = {
                    'author': tweet_data['author'],
                    'mirror': mirror
                }
                
                tweets.append(tweet)
                
            except Exception as e:
                log_error(f"Error creating Tweet object: {str(e)}")
                continue
                
        return tweets

# Legacy function for backward compatibility
def fetch_rss(username):
    """
    Fetch tweets for a Twitter/X user (legacy function kept for backward compatibility).
    Now uses HTML scraping instead of RSS.
    """
    service = RSSService()
    tweets_data, _ = service.fetch_tweets_html(username)
    return tweets_data or []