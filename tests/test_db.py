#!/usr/bin/env python3
"""
Database test script for x2telegram project.
This script tests the database connection and operations to ensure they work correctly.
"""

import sys
import os
from datetime import datetime, timedelta

# Add project root to path to allow imports from other modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from x2telegram.db import Database
from x2telegram.core.models import Tweet
from x2telegram.config import DATABASE_PATH

def test_db():
    print("Starting database test...")
    
    # Initialize database with in-memory SQLite for testing
    db = Database(":memory:")
    if not db.connect():
        print("Failed to create database connection.")
        return False
    
    try:
        # Create database tables
        db.create_tables()
        
        # Test follower operations
        print("\nTesting follower operations...")
        follower = db.add_follower("testuser")
        if not follower:
            print("Error: Failed to add follower")
            return False
        print(f"Added test follower with ID: {follower.id}")
        
        followers = db.get_all_followers()
        if not followers or len(followers) == 0:
            print("Error: Failed to retrieve followers")
            return False
        print(f"Retrieved followers: {followers}")
        
        if not db.enable_follower("testuser", False):  # Disable
            print("Error: Failed to disable follower")
            return False
        disabled_followers = db.get_all_followers(enabled_only=True)
        if len(disabled_followers) > 0:
            print("Error: Follower still enabled after disabling")
            return False
        print("Successfully disabled follower")
        
        if not db.enable_follower("testuser", True):  # Re-enable
            print("Error: Failed to re-enable follower")
            return False
        enabled_followers = db.get_all_followers()
        if len(enabled_followers) == 0:
            print("Error: Failed to re-enable follower")
            return False
        print("Successfully re-enabled follower")
        
        # Test tweet operations
        print("\nTesting tweet operations...")
        test_tweet = Tweet(
            tweet_id="123456789",
            tweet_url="https://twitter.com/testuser/status/123456789",
            tweet_content="This is a test tweet",
            tweet_image=None,
            created_at=datetime.now().isoformat()
        )
        
        store_result = db.store_tweet(test_tweet, follower.id)
        print(f"Stored test tweet with result: {store_result}")
        
        exists = db.tweet_exists("123456789")
        if not exists:
            print("Error: Tweet should exist but doesn't")
            return False
        print("Successfully confirmed tweet exists")
        
        # Test tweet analysis operations
        print("\nTesting tweet analysis operations...")
        unanalyzed = db.get_unanalyzed_tweets()
        if len(unanalyzed) != 1:
            print(f"Error: Expected 1 unanalyzed tweet, got {len(unanalyzed)}")
            return False
        print(f"Found {len(unanalyzed)} unanalyzed tweets as expected")
        
        if not db.update_analysis_result("123456789", "relevant"):
            print("Error: Failed to update analysis result")
            return False
        unanalyzed_after = db.get_unanalyzed_tweets()
        if len(unanalyzed_after) != 0:
            print(f"Error: Expected 0 unanalyzed tweets after update, got {len(unanalyzed_after)}")
            return False
        print("Successfully updated analysis result")
        
        # Test telegram sending operations
        print("\nTesting telegram sending operations...")
        unsent = db.get_unsent_analyzed_tweets()
        if len(unsent) != 1:
            print(f"Error: Expected 1 unsent tweet, got {len(unsent)}")
            return False
        print(f"Found {len(unsent)} unsent tweets as expected")
        
        if not db.mark_as_sent("123456789"):
            print("Error: Failed to mark tweet as sent")
            return False
        unsent_after = db.get_unsent_analyzed_tweets()
        if len(unsent_after) != 0:
            print(f"Error: Expected 0 unsent tweets after marking as sent, got {len(unsent_after)}")
            return False
        print("Successfully marked tweet as sent")
        
        # Test tweet storage limit functionality
        print("\nTesting tweet storage limit functionality...")
        
        # First, create and mark special tweets (the ones we want to ensure are preserved)
        # Create tweet_12 and tweet_15 first and mark them as sent
        for special_id in [12, 15]:
            created_at = (datetime.now() - timedelta(minutes=special_id)).isoformat()
            tweet = Tweet(
                tweet_id=f"test_tweet_{special_id}",
                tweet_url=f"https://twitter.com/testuser/status/test_tweet_{special_id}",
                tweet_content=f"Test tweet {special_id}",
                tweet_image=None,
                created_at=created_at
            )
            db.store_tweet(tweet, follower.id)
            db.mark_as_sent(f"test_tweet_{special_id}")
            print(f"Created and marked special tweet {special_id} as sent")
            
        # Now create the rest of the tweets (1-11, 13-14)
        for i in range(1, 16):
            # Skip the special tweets we've already created
            if i in [12, 15]:
                continue
                
            created_at = (datetime.now() - timedelta(minutes=i)).isoformat()
            tweet = Tweet(
                tweet_id=f"test_tweet_{i}",
                tweet_url=f"https://twitter.com/testuser/status/test_tweet_{i}",
                tweet_content=f"Test tweet {i}",
                tweet_image=None,
                created_at=created_at
            )
            db.store_tweet(tweet, follower.id)
            
            # Mark every 3rd tweet as sent to Telegram
            if i % 3 == 0:
                db.mark_as_sent(f"test_tweet_{i}")
        
        # Ensure we have the correct number of tweets
        conn = db.conn  # Use the public conn attribute instead of _conn
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM tweets_cache WHERE follower_id = ?", (follower.id,))
        total_tweets = cursor.fetchone()[0]
        
        # Calculate expected tweets:
        # - 10 most recent tweets (test_tweet_1 through test_tweet_10)
        # - Plus 2 older sent tweets (test_tweet_12, test_tweet_15)
        expected_tweets = 12
        
        print(f"Total tweets after cleanup: {total_tweets} (expected: {expected_tweets})")
        
        # Debug: print all tweets to see what's there
        cursor.execute("""
            SELECT tweet_id, created_at, is_sent_to_telegram 
            FROM tweets_cache 
            WHERE follower_id = ? 
            ORDER BY created_at DESC
        """, (follower.id,))
        all_tweets = cursor.fetchall()
        print("Current tweets:")
        for t in all_tweets:
            print(f"- {t[0]}, created: {t[1]}, sent: {t[2]}")
        
        if total_tweets != expected_tweets:
            print(f"Error: Expected {expected_tweets} tweets after cleanup, got {total_tweets}")
            return False
            
        # Verify sent tweets are preserved
        cursor.execute("""
            SELECT tweet_id FROM tweets_cache
            WHERE follower_id = ? AND is_sent_to_telegram = 1
            ORDER BY created_at
        """, (follower.id,))
        sent_tweets = [row[0] for row in cursor.fetchall()]
        expected_sent = ["test_tweet_3", "test_tweet_6", "test_tweet_9", "test_tweet_12", "test_tweet_15", "123456789"]
        
        missing_tweets = [t for t in expected_sent if t not in sent_tweets]
        if missing_tweets:
            print(f"Error: The following sent tweets were missing: {missing_tweets}")
            return False
                
        print("Successfully verified tweet storage limit functionality")
        
        # Test removing followers
        print("\nTesting follower removal...")
        remove_result = db.remove_follower("testuser")
        if not remove_result:
            print("Error: Failed to remove follower")
            return False
        
        followers_after = db.get_all_followers(enabled_only=False)
        if len(followers_after) > 0:
            print(f"Error: Expected 0 followers after removal, got {len(followers_after)}")
            return False
        print("Successfully removed follower")
        
        print("\nAll database tests passed successfully!")
        return True
    
    except Exception as e:
        print(f"Error during database tests: {str(e)}")
        return False
    finally:
        if db:
            db.close()
            print("Database connection closed")

if __name__ == "__main__":
    success = test_db()
    sys.exit(0 if success else 1)