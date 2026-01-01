"""
Core processor for the x2telegram application.

This module handles the main processing logic for fetching, analyzing,
and forwarding tweets to Telegram.
"""
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from ..config import MAX_TWEETS_PER_USER
# Import services
from ..services.rss import RSSService
from ..services.analyzer import AnalyzerService
from ..services.telegram import TelegramService
from ..utils import log_info, log_error, log_debug, format_tweet_message, safe_sleep

# Database will be imported inside methods to avoid circular imports

# Default number of concurrent workers for processing followers
DEFAULT_MAX_WORKERS = int(os.environ.get('MAX_WORKERS', '3'))


class TweetProcessor:
    """Main processor for handling tweet fetching, analysis, and forwarding."""
    
    def __init__(self, db_path=None, max_workers=None):
        """Initialize the tweet processor with database and service instances.
        
        Args:
            db_path: Path to the SQLite database file
            max_workers: Maximum number of concurrent workers for processing followers
        """
        # Import Database here to avoid circular imports
        from ..db import Database
        self.db_path = db_path
        self.db = Database(db_path)
        self.rss_service = RSSService()
        self.analyzer = AnalyzerService()
        self.telegram = TelegramService()
        self.max_workers = max_workers or DEFAULT_MAX_WORKERS
    
    def process_follower_tweets(self, follower):
        """
        Process tweets for a specific follower.
        
        Args:
            follower: A Follower object with id, username, and enabled properties
        """
        follower_id = follower.id
        username = follower.username
        log_info(f"Processing tweets for @{username}...")
        
        try:
            # Fetch recent tweets via RSS
            tweets = self.rss_service.get_tweets(username)
            log_info(f"Fetched {len(tweets)} tweets for @{username}")
            
            # Limit the number of tweets processed per user
            tweets = tweets[:MAX_TWEETS_PER_USER]
            
            for tweet in tweets:
                # Check if tweet already exists in our database
                if not self.db.tweet_exists(tweet.tweet_id):
                    log_info(f"New tweet found: {tweet.tweet_url}")
                    
                    # Store the tweet first
                    self.db.store_tweet(tweet, follower_id)
                    
                    # Check if the tweet has an image (just for logging)
                    image_url = tweet.tweet_image
                    if image_url:
                        log_info(f"Tweet has image: {image_url}")
                    
                    # Analyze the tweet using the analyzer service (using Claude for analysis)
                    analysis_result = self.analyzer.analyze_tweet(tweet.tweet_content, image_url=image_url)
                    analysis_text = analysis_result.get("analysis", "No analysis available")
                    log_info(f"Tweet analyzed: {analysis_text}")
                    
                    # Store the analysis result in the database
                    self.db.update_analysis_result(tweet.tweet_id, analysis_text)
                    
                    # Format the message including both tweet content and analysis
                    message = format_tweet_message(username, tweet, analysis_text)
                    
                    # Send to Telegram
                    result = self.telegram.send_message(message, parse_mode="HTML")
                    
                    # Mark as sent if successfully delivered to Telegram
                    if result.get("ok", False):
                        self.db.mark_as_sent(tweet.tweet_id)
                        log_info(f"Tweet {tweet.tweet_id} sent to Telegram successfully")
                    else:
                        log_error(f"Failed to send tweet {tweet.tweet_id} to Telegram: {result.get('error', 'Unknown error')}")
                    
        except Exception as e:
            log_error(f"Error processing tweets for @{username}: {str(e)}")
    
    def process_pending_tweets(self, limit=10):
        """
        Process tweets that have been analyzed but not sent yet.
        
        Args:
            limit (int): Maximum number of pending tweets to process
        """
        try:
            log_info("Checking for pending tweets to send...")
            unsent_tweets = self.db.get_unsent_analyzed_tweets(limit)
            
            log_info(f"Found {len(unsent_tweets)} unsent analyzed tweets")
            
            # Pre-fetch all followers once to avoid N+1 query
            followers = self.db.get_all_followers(enabled_only=False)
            follower_map = {f.id: f.username for f in followers}
            
            for tweet_data in unsent_tweets:
                # Unpack the tuple (tweet, follower_id, analysis_result)
                tweet, follower_id, analysis_result = tweet_data
                
                # Get follower username from pre-fetched map
                username = follower_map.get(follower_id, "unknown")
                
                log_info(f"Sending pending tweet to Telegram: {tweet.tweet_url}")
                
                # Format the message without analysis
                message = format_tweet_message(username, tweet)
                
                result = self.telegram.send_message(message, parse_mode="HTML")
                
                # Only mark as sent if successfully delivered to Telegram
                if result.get("ok", False):
                    self.db.mark_as_sent(tweet.tweet_id)
                    log_info(f"Pending tweet {tweet.tweet_id} sent to Telegram successfully")
                else:
                    log_error(f"Failed to send pending tweet {tweet.tweet_id} to Telegram: {result.get('error', 'Unknown error')}")
                    
        except Exception as e:
            log_error(f"Error processing pending tweets: {str(e)}")
    
    def _process_followers_concurrent(self, followers):
        """
        Process multiple followers concurrently using ThreadPoolExecutor.
        
        Args:
            followers: List of Follower objects to process
        """
        log_info(f"Processing {len(followers)} followers concurrently with {self.max_workers} workers")
        
        # Create a thread-safe wrapper that creates its own database connection
        def process_follower_thread_safe(follower):
            """Process a single follower with its own database connection."""
            from ..db import Database
            
            # Create a new processor instance for this thread with its own DB connection
            thread_db = Database(self.db_path)
            if not thread_db.connect():
                log_error(f"Failed to connect to database for @{follower.username}")
                return follower.username, False
            
            try:
                thread_db.create_tables()
                
                # Create thread-local services
                rss_service = RSSService()
                analyzer = AnalyzerService()
                telegram = TelegramService()
                
                follower_id = follower.id
                username = follower.username
                log_info(f"[Thread] Processing tweets for @{username}...")
                
                # Fetch recent tweets
                tweets = rss_service.get_tweets(username)
                log_info(f"[Thread] Fetched {len(tweets)} tweets for @{username}")
                
                # Limit the number of tweets processed per user
                tweets = tweets[:MAX_TWEETS_PER_USER]
                
                for tweet in tweets:
                    if not thread_db.tweet_exists(tweet.tweet_id):
                        log_info(f"[Thread] New tweet found: {tweet.tweet_url}")
                        
                        thread_db.store_tweet(tweet, follower_id)
                        
                        image_url = tweet.tweet_image
                        if image_url:
                            log_info(f"[Thread] Tweet has image: {image_url}")
                        
                        analysis_result = analyzer.analyze_tweet(tweet.tweet_content, image_url=image_url)
                        analysis_text = analysis_result.get("analysis", "No analysis available")
                        log_info(f"[Thread] Tweet analyzed: {analysis_text}")
                        
                        thread_db.update_analysis_result(tweet.tweet_id, analysis_text)
                        
                        message = format_tweet_message(username, tweet, analysis_text)
                        result = telegram.send_message(message, parse_mode="HTML")
                        
                        if result.get("ok", False):
                            thread_db.mark_as_sent(tweet.tweet_id)
                            log_info(f"[Thread] Tweet {tweet.tweet_id} sent to Telegram successfully")
                        else:
                            log_error(f"[Thread] Failed to send tweet {tweet.tweet_id}: {result.get('error', 'Unknown error')}")
                
                return username, True
                
            except Exception as e:
                log_error(f"[Thread] Error processing @{follower.username}: {str(e)}")
                return follower.username, False
            finally:
                thread_db.close()
        
        # Process followers concurrently
        results = {}
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_follower = {
                executor.submit(process_follower_thread_safe, follower): follower 
                for follower in followers
            }
            
            for future in as_completed(future_to_follower):
                follower = future_to_follower[future]
                try:
                    username, success = future.result()
                    results[username] = success
                except Exception as e:
                    log_error(f"[Thread] Exception for @{follower.username}: {str(e)}")
                    results[follower.username] = False
        
        # Log summary
        successful = sum(1 for v in results.values() if v)
        log_info(f"Concurrent processing complete: {successful}/{len(followers)} followers processed successfully")
    
    def run(self):
        """Run the main processing job."""
        log_info(f"Starting tweet processing job at {datetime.now().isoformat()}")
        
        # Connect to the database
        if not self.db.connect():
            log_error("Failed to connect to database. Exiting.")
            return False
        
        try:
            # Initialize database tables if needed
            self.db.create_tables()
            
            # Get all enabled followers
            followers = self.db.get_all_followers(enabled_only=True)
            log_info(f"Found {len(followers)} enabled followers to process")
            
            # Process tweets for each follower concurrently
            if len(followers) > 1 and self.max_workers > 1:
                self._process_followers_concurrent(followers)
            else:
                # Sequential processing for single follower or when concurrency is disabled
                for follower in followers:
                    self.process_follower_tweets(follower)
                    safe_sleep(1)
            
            # Process any pending tweets that need to be sent
            self.process_pending_tweets()
            
            # Run database maintenance
            self.db.run_maintenance()
            
            log_info(f"Tweet processing job completed at {datetime.now().isoformat()}")
            return True
            
        except Exception as e:
            log_error(f"Error in processing job: {str(e)}")
            return False
            
        finally:
            # Make sure to close the database connection
            self.db.close()
            log_info("Database connection closed")