"""
Tests for the Database module.
"""
import pytest
from datetime import datetime

from x2telegram.db.database import Database
from x2telegram.core.models import Tweet, Follower


class TestDatabaseConnection:
    """Tests for database connection handling."""

    def test_connect_in_memory(self):
        """Test connecting to in-memory database."""
        db = Database(":memory:")
        conn = db.connect()
        assert conn is not None
        db.close()

    def test_create_tables(self, temp_db):
        """Test table creation."""
        result = temp_db.create_tables()
        assert result is True

    def test_context_manager(self):
        """Test database context manager."""
        with Database(":memory:") as db:
            assert db.conn is not None
            db.create_tables()


class TestFollowerManagement:
    """Tests for follower CRUD operations."""

    def test_add_follower(self, temp_db):
        """Test adding a new follower."""
        follower = temp_db.add_follower("testuser")
        assert follower is not None
        assert follower.username == "testuser"
        assert follower.enabled is True

    def test_add_duplicate_follower(self, temp_db):
        """Test adding a duplicate follower returns None."""
        temp_db.add_follower("testuser")
        result = temp_db.add_follower("testuser")
        assert result is None

    def test_remove_follower(self, temp_db):
        """Test removing a follower."""
        temp_db.add_follower("testuser")
        result = temp_db.remove_follower("testuser")
        assert result is True

    def test_remove_nonexistent_follower(self, temp_db):
        """Test removing a non-existent follower."""
        result = temp_db.remove_follower("nonexistent")
        assert result is False

    def test_enable_follower(self, temp_db):
        """Test enabling a follower."""
        temp_db.add_follower("testuser")
        temp_db.enable_follower("testuser", False)
        result = temp_db.enable_follower("testuser", True)
        assert result is True

    def test_disable_follower(self, temp_db):
        """Test disabling a follower."""
        temp_db.add_follower("testuser")
        result = temp_db.enable_follower("testuser", False)
        assert result is True

    def test_get_all_followers(self, temp_db):
        """Test getting all followers."""
        temp_db.add_follower("user1")
        temp_db.add_follower("user2")
        followers = temp_db.get_all_followers()
        assert len(followers) == 2

    def test_get_enabled_followers_only(self, temp_db):
        """Test getting only enabled followers."""
        temp_db.add_follower("user1")
        temp_db.add_follower("user2")
        temp_db.enable_follower("user2", False)
        followers = temp_db.get_all_followers(enabled_only=True)
        assert len(followers) == 1
        assert followers[0].username == "user1"


class TestTweetManagement:
    """Tests for tweet CRUD operations."""

    def test_store_tweet(self, temp_db, sample_tweet):
        """Test storing a tweet."""
        follower = temp_db.add_follower("testuser")
        result = temp_db.store_tweet(sample_tweet, follower.id)
        assert result is not None

    def test_tweet_exists(self, temp_db, sample_tweet):
        """Test checking if tweet exists."""
        follower = temp_db.add_follower("testuser")
        temp_db.store_tweet(sample_tweet, follower.id)
        assert temp_db.tweet_exists(sample_tweet.tweet_id) is True
        assert temp_db.tweet_exists("nonexistent") is False

    def test_content_hash_exists(self, temp_db, sample_tweet):
        """Test content hash duplicate detection."""
        follower = temp_db.add_follower("testuser")
        content_hash = "abc123hash"
        temp_db.store_tweet(sample_tweet, follower.id, content_hash=content_hash)
        assert temp_db.content_hash_exists(content_hash) is True
        assert temp_db.content_hash_exists("differenthash") is False

    def test_content_hash_exists_none(self, temp_db):
        """Test content hash check with None value."""
        assert temp_db.content_hash_exists(None) is False

    def test_update_analysis_result(self, temp_db, sample_tweet):
        """Test updating analysis result."""
        follower = temp_db.add_follower("testuser")
        temp_db.store_tweet(sample_tweet, follower.id)
        result = temp_db.update_analysis_result(sample_tweet.tweet_id, "Test analysis")
        assert result is True

    def test_mark_as_sent(self, temp_db, sample_tweet):
        """Test marking tweet as sent."""
        follower = temp_db.add_follower("testuser")
        temp_db.store_tweet(sample_tweet, follower.id)
        result = temp_db.mark_as_sent(sample_tweet.tweet_id)
        assert result is True

    def test_get_unsent_analyzed_tweets(self, temp_db, sample_tweet):
        """Test getting unsent analyzed tweets."""
        follower = temp_db.add_follower("testuser")
        temp_db.store_tweet(sample_tweet, follower.id)
        temp_db.update_analysis_result(sample_tweet.tweet_id, "Analysis")

        tweets = temp_db.get_unsent_analyzed_tweets()
        assert len(tweets) == 1
        assert tweets[0][0].tweet_id == sample_tweet.tweet_id

    def test_get_unanalyzed_tweets(self, temp_db, sample_tweet):
        """Test getting unanalyzed tweets."""
        follower = temp_db.add_follower("testuser")
        temp_db.store_tweet(sample_tweet, follower.id)

        tweets = temp_db.get_unanalyzed_tweets()
        assert len(tweets) == 1


class TestMaintenance:
    """Tests for database maintenance operations."""

    def test_cleanup_old_tweets(self, temp_db):
        """Test cleaning up old tweets."""
        follower = temp_db.add_follower("testuser")

        # store_tweet already calls cleanup_old_tweets after each insert,
        # so we test with a smaller keep_count to see if manual cleanup works
        for i in range(5):
            tweet = Tweet(
                tweet_id=f"tweet_{i}",
                tweet_url=f"https://twitter.com/user/status/{i}",
                tweet_content=f"Tweet content {i}",
                created_at=datetime.now().isoformat()
            )
            temp_db.store_tweet(tweet, follower.id)

        # Cleanup with keep_count=2 should delete 3 tweets
        deleted = temp_db.cleanup_old_tweets(follower.id, keep_count=2)
        assert deleted == 3

    def test_run_maintenance(self, temp_db):
        """Test running maintenance for all followers."""
        follower = temp_db.add_follower("testuser")

        # store_tweet already calls cleanup, so after inserting we'll have max 10
        # run_maintenance uses default keep_count=10, so no additional cleanup
        for i in range(5):
            tweet = Tweet(
                tweet_id=f"tweet_{i}",
                tweet_url=f"https://twitter.com/user/status/{i}",
                tweet_content=f"Tweet content {i}",
                created_at=datetime.now().isoformat()
            )
            temp_db.store_tweet(tweet, follower.id)

        # With 5 tweets and default keep_count=10, no cleanup needed
        deleted = temp_db.run_maintenance()
        assert deleted == 0
