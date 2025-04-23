"""
Core processor for the x2telegram application.

This module handles the main processing logic for fetching, analyzing,
and forwarding tweets to Telegram.
"""
import sys
import time
from datetime import datetime

from ..config import MAX_TWEETS_PER_USER
# Import services
from ..services.rss import RSSService
from ..services.analyzer import AnalyzerService
from ..services.telegram import TelegramService
from ..utils import log_info, log_error, log_debug, format_tweet_message, safe_sleep

# Database will be imported inside methods to avoid circular imports

class TweetProcessor:
    """Main processor for handling tweet fetching, analysis, and forwarding."""
    
    def __init__(self, db_path=None):
        """Initialize the tweet processor with database and service instances."""
        # Import Database here to avoid circular imports
        from ..db import Database
        self.db = Database(db_path)
        self.rss_service = RSSService()
        self.analyzer = AnalyzerService()
        self.telegram = TelegramService()
    
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
                    
                    # Analyze the tweet content with AI
                    ai_result = self.analyzer.analyze_with_ai(tweet.tweet_content)
                    
                    # Get the analysis text
                    analysis_text = ai_result.get("analysis", "No analysis provided")
                    
                    # Update with analysis results
                    self.db.update_analysis_result(tweet.tweet_id, analysis_text)
                    
                    # Send to Telegram with the analysis included
                    message = format_tweet_message(username, tweet, analysis_text)
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
            
            for tweet_data in unsent_tweets:
                # Unpack the tuple (tweet, follower_id, analysis_result)
                tweet, follower_id, analysis_result = tweet_data
                
                # Get follower username
                followers = self.db.get_all_followers(enabled_only=False)
                username = next((f.username for f in followers if f.id == follower_id), "unknown")
                
                log_info(f"Sending pending tweet to Telegram: {tweet.tweet_url}")
                message = format_tweet_message(username, tweet, analysis_result)
                result = self.telegram.send_message(message, parse_mode="HTML")
                
                # Only mark as sent if successfully delivered to Telegram
                if result.get("ok", False):
                    self.db.mark_as_sent(tweet.tweet_id)
                    log_info(f"Pending tweet {tweet.tweet_id} sent to Telegram successfully")
                else:
                    log_error(f"Failed to send pending tweet {tweet.tweet_id} to Telegram: {result.get('error', 'Unknown error')}")
                    
        except Exception as e:
            log_error(f"Error processing pending tweets: {str(e)}")
    
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
            
            # Process tweets for each follower
            for follower in followers:
                self.process_follower_tweets(follower)
                # Small pause between processing different accounts to avoid rate limits
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