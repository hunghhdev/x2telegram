"""
Pytest configuration and shared fixtures for x2telegram tests.
"""
import os
import sys
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from x2telegram.core.models import Tweet, Follower
from x2telegram.db.database import Database


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock environment variables for testing."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-bot-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "test-chat-id")
    monkeypatch.setenv("AI_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_URL", "http://localhost:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "test-model")


@pytest.fixture
def temp_db():
    """Create an in-memory SQLite database for testing."""
    db = Database(":memory:")
    db.connect()
    db.create_tables()
    yield db
    db.close()


@pytest.fixture
def sample_tweet():
    """Create a sample Tweet object for testing."""
    return Tweet(
        tweet_id="123456789",
        tweet_url="https://twitter.com/user/status/123456789",
        tweet_content="This is a test tweet content",
        tweet_image=None,
        created_at=datetime.now().isoformat()
    )


@pytest.fixture
def sample_tweet_with_image():
    """Create a sample Tweet object with image for testing."""
    return Tweet(
        tweet_id="987654321",
        tweet_url="https://twitter.com/user/status/987654321",
        tweet_content="This is a test tweet with image",
        tweet_image="https://example.com/image.jpg",
        created_at=datetime.now().isoformat()
    )


@pytest.fixture
def sample_follower():
    """Create a sample Follower object for testing."""
    return Follower(
        id=1,
        username="testuser",
        enabled=True
    )


@pytest.fixture
def mock_requests_session():
    """Mock requests.Session for HTTP testing."""
    with patch("requests.Session") as mock_session:
        mock_instance = MagicMock()
        mock_session.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_telegram_response():
    """Create a mock successful Telegram API response."""
    return {
        "ok": True,
        "result": {
            "message_id": 12345,
            "chat": {"id": "test-chat-id"},
            "text": "Test message"
        }
    }


@pytest.fixture
def mock_ollama_response():
    """Create a mock successful Ollama API response."""
    return {
        "message": {
            "content": "This is a test analysis of the tweet."
        }
    }


@pytest.fixture
def sample_nitter_html():
    """Create sample Nitter HTML for parsing tests."""
    return """
    <html>
    <body>
        <div class="timeline">
            <div class="timeline-item">
                <a class="tweet-link" href="/user/status/123456789">
                    <span class="tweet-date">
                        <a title="2024-01-01 12:00:00">Jan 1</a>
                    </span>
                </a>
                <div class="tweet-content">This is a test tweet</div>
                <div class="fullname">Test User</div>
            </div>
            <div class="timeline-item">
                <a class="tweet-link" href="/user/status/987654321">
                    <span class="tweet-date">
                        <a title="2024-01-02 12:00:00">Jan 2</a>
                    </span>
                </a>
                <div class="tweet-content">Another test tweet</div>
                <div class="fullname">Test User</div>
                <img class="still-image" src="/pic/image.jpg" />
            </div>
        </div>
    </body>
    </html>
    """
