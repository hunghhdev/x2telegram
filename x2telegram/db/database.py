"""
Database module for the x2telegram application.
"""
import sqlite3
from sqlite3 import Error
import logging
from datetime import datetime
import os
import sys

from ..config import DATABASE_PATH
from ..core.models import Tweet, Follower

class Database:
    """Database manager for the x2telegram application."""
    
    def __init__(self, db_path=DATABASE_PATH):
        """Initialize database connection."""
        self.db_path = db_path
        self.conn = None
    
    def connect(self):
        """Create a database connection to the SQLite database."""
        try:
            # For in-memory database, no need to create directories
            if self.db_path != ":memory:":
                # Ensure the directory exists
                os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
                
                # For SQLite, just connecting to the database will create it if it doesn't exist
                # Log whether we're creating a new file or connecting to existing one
                file_exists = os.path.exists(self.db_path)
                if not file_exists:
                    print(f"Database file does not exist, will be created: {self.db_path}", file=sys.stderr)
            
            self.conn = sqlite3.connect(self.db_path)
            print(f"Connected to database: {self.db_path}", file=sys.stderr)
            return self.conn
        except Error as e:
            print(f"Error connecting to database: {e}", file=sys.stderr)
            return None
    
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            print("Database connection closed", file=sys.stderr)
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def create_tables(self):
        """Create necessary tables if they don't exist."""
        if not self.conn:
            self.connect()
        
        try:
            cursor = self.conn.cursor()
            
            # Create followers table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS followers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    enabled BOOLEAN DEFAULT 1
                );
            ''')
            
            # Create tweets_cache table with columns for analysis and sent status
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tweets_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    follower_id INTEGER,
                    tweet_id TEXT,
                    tweet_url TEXT,
                    tweet_content TEXT,
                    tweet_image BLOB,
                    created_at DATETIME,
                    inserted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    is_analyzed BOOLEAN DEFAULT 0,
                    analysis_result TEXT,
                    is_sent_to_telegram BOOLEAN DEFAULT 0,
                    sent_at DATETIME,
                    FOREIGN KEY(follower_id) REFERENCES followers(id)
                );
            ''')
            
            # Create indexes for performance optimization
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_tweet_id ON tweets_cache(tweet_id);
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_follower_id ON tweets_cache(follower_id);
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_is_analyzed ON tweets_cache(is_analyzed);
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_is_sent ON tweets_cache(is_sent_to_telegram);
            ''')
            
            self.conn.commit()
            print("Database tables and indexes created successfully", file=sys.stderr)
            return True
        except Error as e:
            print(f"Error creating tables: {e}", file=sys.stderr)
            return False
    
    # Follower Management Methods
    
    def add_follower(self, username):
        """Add a new follower to follow their tweets."""
        if not self.conn:
            self.connect()
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("INSERT INTO followers (username) VALUES (?)", (username,))
            self.conn.commit()
            print(f"Added follower: {username}", file=sys.stderr)
            
            # Return a Follower object
            follower_id = cursor.lastrowid
            return Follower(id=follower_id, username=username, enabled=True)
        except sqlite3.IntegrityError:
            print(f"Follower {username} already exists", file=sys.stderr)
            return None
        except Error as e:
            print(f"Error adding follower: {e}", file=sys.stderr)
            return None
    
    def remove_follower(self, username):
        """Remove a follower."""
        if not self.conn:
            self.connect()
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM followers WHERE username = ?", (username,))
            self.conn.commit()
            if cursor.rowcount > 0:
                print(f"Removed follower: {username}", file=sys.stderr)
                return True
            else:
                print(f"Follower {username} not found", file=sys.stderr)
                return False
        except Error as e:
            print(f"Error removing follower: {e}", file=sys.stderr)
            return False
    
    def enable_follower(self, username, enabled=True):
        """Enable or disable a follower."""
        if not self.conn:
            self.connect()
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("UPDATE followers SET enabled = ? WHERE username = ?", 
                          (1 if enabled else 0, username))
            self.conn.commit()
            if cursor.rowcount > 0:
                status = "enabled" if enabled else "disabled"
                print(f"{status.capitalize()} follower: {username}", file=sys.stderr)
                return True
            else:
                print(f"Follower {username} not found", file=sys.stderr)
                return False
        except Error as e:
            print(f"Error updating follower status: {e}", file=sys.stderr)
            return False
    
    def get_all_followers(self, enabled_only=True):
        """Get all followers, optionally filtered by enabled status."""
        if not self.conn:
            self.connect()
        
        try:
            cursor = self.conn.cursor()
            if enabled_only:
                cursor.execute("SELECT id, username, enabled FROM followers WHERE enabled = 1")
            else:
                cursor.execute("SELECT id, username, enabled FROM followers")
            
            # Convert to Follower objects
            followers = []
            for row in cursor.fetchall():
                followers.append(Follower(id=row[0], username=row[1], enabled=row[2]))
            return followers
        except Error as e:
            print(f"Error getting followers: {e}", file=sys.stderr)
            return []
    
    # Tweet Management Methods
    
    def store_tweet(self, tweet, follower_id):
        """Store a tweet in the database and clean up old tweets."""
        if not self.conn:
            self.connect()
        
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO tweets_cache (
                    follower_id, tweet_id, tweet_url, 
                    tweet_content, tweet_image, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                follower_id, 
                tweet.tweet_id, 
                tweet.tweet_url, 
                tweet.tweet_content, 
                tweet.tweet_image, 
                tweet.created_at
            ))
            self.conn.commit()
            tweet_id = cursor.lastrowid
            print(f"Stored tweet: {tweet.tweet_id}", file=sys.stderr)
            
            # Clean up old tweets to keep only the most recent ones
            self.cleanup_old_tweets(follower_id)
            
            return tweet_id
        except sqlite3.IntegrityError:
            print(f"Tweet {tweet.tweet_id} already exists", file=sys.stderr)
            return None
        except Error as e:
            print(f"Error storing tweet: {e}", file=sys.stderr)
            return None
    
    def tweet_exists(self, tweet_id):
        """Check if a tweet already exists in the database."""
        if not self.conn:
            self.connect()
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT 1 FROM tweets_cache WHERE tweet_id = ?", (tweet_id,))
            return cursor.fetchone() is not None
        except Error as e:
            print(f"Error checking tweet existence: {e}", file=sys.stderr)
            return False
    
    def update_analysis_result(self, tweet_id, analysis_result):
        """Update the analysis result for a tweet."""
        if not self.conn:
            self.connect()
        
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                UPDATE tweets_cache 
                SET is_analyzed = 1, analysis_result = ? 
                WHERE tweet_id = ?
            ''', (analysis_result, tweet_id))
            self.conn.commit()
            if cursor.rowcount > 0:
                print(f"Updated analysis for tweet: {tweet_id}", file=sys.stderr)
                return True
            else:
                print(f"Tweet {tweet_id} not found", file=sys.stderr)
                return False
        except Error as e:
            print(f"Error updating analysis: {e}", file=sys.stderr)
            return False
    
    def mark_as_sent(self, tweet_id):
        """Mark a tweet as sent to Telegram."""
        if not self.conn:
            self.connect()
        
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                UPDATE tweets_cache 
                SET is_sent_to_telegram = 1, sent_at = ? 
                WHERE tweet_id = ?
            ''', (datetime.now().isoformat(), tweet_id))
            self.conn.commit()
            if cursor.rowcount > 0:
                print(f"Marked tweet {tweet_id} as sent to Telegram", file=sys.stderr)
                return True
            else:
                print(f"Tweet {tweet_id} not found", file=sys.stderr)
                return False
        except Error as e:
            print(f"Error marking tweet as sent: {e}", file=sys.stderr)
            return False
    
    def get_unsent_analyzed_tweets(self, limit=10):
        """Get tweets that have been analyzed but not sent to Telegram."""
        if not self.conn:
            self.connect()
        
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT follower_id, tweet_id, tweet_url, tweet_content, 
                       tweet_image, created_at, analysis_result
                FROM tweets_cache 
                WHERE is_analyzed = 1 
                AND is_sent_to_telegram = 0 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (limit,))
            
            # Convert to Tweet objects
            tweets = []
            for row in cursor.fetchall():
                tweet = Tweet(
                    tweet_id=row[1],
                    tweet_url=row[2],
                    tweet_content=row[3],
                    tweet_image=row[4],
                    created_at=row[5]
                )
                tweets.append((tweet, row[0], row[6]))  # tweet, follower_id, analysis_result
            return tweets
        except Error as e:
            print(f"Error getting unsent tweets: {e}", file=sys.stderr)
            return []
    
    def get_unanalyzed_tweets(self, limit=50):
        """Get tweets that have not been analyzed yet."""
        if not self.conn:
            self.connect()
        
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT follower_id, tweet_id, tweet_url, tweet_content, 
                       tweet_image, created_at
                FROM tweets_cache 
                WHERE is_analyzed = 0 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (limit,))
            
            # Convert to Tweet objects
            tweets = []
            for row in cursor.fetchall():
                tweet = Tweet(
                    tweet_id=row[1],
                    tweet_url=row[2],
                    tweet_content=row[3],
                    tweet_image=row[4],
                    created_at=row[5]
                )
                tweets.append((tweet, row[0]))  # tweet, follower_id
            return tweets
        except Error as e:
            print(f"Error getting unanalyzed tweets: {e}", file=sys.stderr)
            return []
    
    # Maintenance Methods
    
    def cleanup_old_tweets(self, follower_id, keep_count=10):
        """
        Remove old tweets for a follower, keeping only the 'keep_count' most recent ones 
        and any tweets that have been sent to Telegram regardless of age.
        """
        if not self.conn:
            self.connect()
        
        try:
            cursor = self.conn.cursor()
            
            # Count total tweets for this follower
            cursor.execute(
                "SELECT COUNT(*) FROM tweets_cache WHERE follower_id = ?", 
                (follower_id,)
            )
            total_tweets = cursor.fetchone()[0]
            
            # If we have more tweets than the limit, cleanup is needed
            if total_tweets > keep_count:
                print(f"Cleaning up old tweets for follower_id {follower_id}. "
                      f"Total: {total_tweets}, keeping {keep_count} + sent tweets", 
                      file=sys.stderr)
                
                # First, get IDs of tweets that have been sent to Telegram
                cursor.execute('''
                    SELECT id FROM tweets_cache 
                    WHERE follower_id = ? AND is_sent_to_telegram = 1
                ''', (follower_id,))
                sent_tweet_ids = [row[0] for row in cursor.fetchall()]
                
                # Then, get IDs of most recent tweets
                cursor.execute('''
                    SELECT id FROM tweets_cache 
                    WHERE follower_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                ''', (follower_id, keep_count))
                recent_tweet_ids = [row[0] for row in cursor.fetchall()]
                
                # Combine the two lists and remove duplicates
                keep_ids = list(set(sent_tweet_ids + recent_tweet_ids))
                
                if keep_ids:
                    # Convert list to comma-separated string for the SQL query
                    keep_ids_str = ','.join(map(str, keep_ids))
                    
                    # Delete tweets that are not in the keep list
                    cursor.execute(f'''
                        DELETE FROM tweets_cache 
                        WHERE follower_id = ? 
                        AND id NOT IN ({keep_ids_str})
                    ''', (follower_id,))
                    
                    deleted_count = cursor.rowcount
                    self.conn.commit()
                    print(f"Deleted {deleted_count} old tweets for follower_id {follower_id}", 
                          file=sys.stderr)
                    return deleted_count
                
            return 0  # No cleanup needed
        except Error as e:
            print(f"Error cleaning up old tweets: {e}", file=sys.stderr)
            return 0
    
    def run_maintenance(self):
        """Run maintenance tasks like cleaning up old tweets for all followers."""
        if not self.conn:
            self.connect()
        
        try:
            print("Running database maintenance...", file=sys.stderr)
            cursor = self.conn.cursor()
            cursor.execute("SELECT id FROM followers")
            follower_ids = [row[0] for row in cursor.fetchall()]
            
            total_deleted = 0
            for follower_id in follower_ids:
                deleted = self.cleanup_old_tweets(follower_id)
                total_deleted += deleted
            
            print(f"Maintenance complete. Deleted {total_deleted} old tweets", file=sys.stderr)
            return total_deleted
        except Error as e:
            print(f"Error during maintenance: {e}", file=sys.stderr)
            return 0

def init_database(db_path=DATABASE_PATH):
    """Initialize the database with tables and indexes."""
    db = Database(db_path)
    if db.connect():
        db.create_tables()
        return db
    else:
        print("Error! Cannot create the database connection.", file=sys.stderr)
        return None