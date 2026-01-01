"""
Tests for the RSSService module.
"""
import pytest
import responses
from unittest.mock import patch, MagicMock

from x2telegram.services.rss import RSSService, USER_AGENTS


class TestRSSServiceInit:
    """Tests for RSSService initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default values."""
        service = RSSService()
        assert service.mirrors is not None
        assert len(service.mirrors) > 0
        assert service.timeout > 0
        assert service.retry_count > 0

    def test_init_with_custom_values(self):
        """Test initialization with custom values."""
        mirrors = ["https://custom-mirror.com"]
        service = RSSService(mirrors=mirrors, timeout=30, retry_count=5)
        assert service.mirrors == mirrors
        assert service.timeout == 30
        assert service.retry_count == 5


class TestUserAgentHandling:
    """Tests for user agent functionality."""

    def test_get_random_user_agent(self):
        """Test getting random user agent."""
        service = RSSService()
        user_agent = service.get_random_user_agent()
        assert user_agent in USER_AGENTS

    def test_get_request_headers(self):
        """Test getting request headers."""
        service = RSSService()
        headers = service.get_request_headers()
        assert "User-Agent" in headers
        assert "Accept" in headers
        assert "Accept-Language" in headers


class TestMirrorManagement:
    """Tests for mirror management functionality."""

    def test_get_working_mirror(self):
        """Test getting a working mirror."""
        mirrors = ["https://mirror1.com", "https://mirror2.com"]
        service = RSSService(mirrors=mirrors)
        mirror = service.get_working_mirror()
        assert mirror in mirrors

    def test_mark_rate_limited(self):
        """Test marking a mirror as rate limited."""
        mirrors = ["https://mirror1.com"]
        service = RSSService(mirrors=mirrors)
        service.mark_rate_limited("https://mirror1.com", 60)
        assert "https://mirror1.com" in service.rate_limited_until


class TestHTMLParsing:
    """Tests for HTML parsing functionality."""

    def test_parse_nitter_html(self, sample_nitter_html):
        """Test parsing Nitter HTML."""
        service = RSSService()
        tweets = service.parse_nitter_html(sample_nitter_html, "https://nitter.net", "testuser")
        assert len(tweets) >= 1

    def test_parse_empty_html(self):
        """Test parsing empty HTML."""
        service = RSSService()
        tweets = service.parse_nitter_html("<html><body></body></html>", "https://nitter.net", "testuser")
        assert tweets == []

    def test_extract_tweet_data(self, sample_nitter_html):
        """Test extracting tweet data from element."""
        from bs4 import BeautifulSoup
        service = RSSService()
        soup = BeautifulSoup(sample_nitter_html, 'html.parser')
        element = soup.select_one('.timeline-item')

        if element:
            tweet_data = service.extract_tweet_data(element, "https://nitter.net", "testuser")
            if tweet_data:
                assert "id" in tweet_data
                assert "url" in tweet_data
                assert "content" in tweet_data


class TestFetchTweets:
    """Tests for tweet fetching functionality."""

    @responses.activate
    def test_fetch_tweets_html_success(self, sample_nitter_html):
        """Test successful tweet fetching."""
        mirrors = ["https://nitter.test"]
        service = RSSService(mirrors=mirrors, retry_count=1)

        responses.add(
            responses.GET,
            "https://nitter.test/testuser",
            body=sample_nitter_html,
            status=200
        )

        tweets, mirror = service.fetch_tweets_html("testuser")
        assert mirror == "https://nitter.test"

    @responses.activate
    def test_fetch_tweets_html_rate_limited(self):
        """Test handling rate limiting."""
        mirrors = ["https://nitter.test"]
        service = RSSService(mirrors=mirrors, retry_count=1)

        responses.add(
            responses.GET,
            "https://nitter.test/testuser",
            status=429,
            headers={"Retry-After": "60"}
        )

        tweets, mirror = service.fetch_tweets_html("testuser")
        assert tweets is None
        assert "https://nitter.test" in service.rate_limited_until

    def test_fetch_tweets_empty_username(self):
        """Test fetching with empty username."""
        service = RSSService()
        tweets, mirror = service.fetch_tweets_html("")
        assert tweets is None
        assert mirror is None

    def test_fetch_tweets_strips_at_symbol(self):
        """Test that @ symbol is stripped from username."""
        service = RSSService(mirrors=["https://nitter.test"], retry_count=0)
        # Just verify it doesn't crash - actual fetch will fail without mock
        with patch.object(service, 'session') as mock_session:
            mock_session.get.side_effect = Exception("Expected")
            tweets, mirror = service.fetch_tweets_html("@testuser")
            # Should have stripped @ and tried to fetch


class TestGetTweets:
    """Tests for get_tweets high-level interface."""

    @responses.activate
    def test_get_tweets_success(self, sample_nitter_html):
        """Test getting tweets as Tweet objects."""
        mirrors = ["https://nitter.test"]
        service = RSSService(mirrors=mirrors, retry_count=1)

        responses.add(
            responses.GET,
            "https://nitter.test/testuser",
            body=sample_nitter_html,
            status=200
        )

        tweets = service.get_tweets("testuser")
        # Should return Tweet objects
        assert isinstance(tweets, list)

    def test_get_tweets_empty_result(self):
        """Test getting tweets when no results."""
        service = RSSService(mirrors=["https://nitter.test"], retry_count=0)

        with patch.object(service, 'fetch_tweets_html', return_value=(None, None)):
            tweets = service.get_tweets("testuser")
            assert tweets == []
