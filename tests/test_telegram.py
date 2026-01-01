"""
Tests for the TelegramService module.
"""
import pytest
import responses
from unittest.mock import patch, MagicMock

from x2telegram.services.telegram import TelegramService
from x2telegram.config import TELEGRAM_API_BASE


class TestTelegramServiceInit:
    """Tests for TelegramService initialization."""

    @patch.dict('os.environ', {'TELEGRAM_BOT_TOKEN': 'test-token', 'TELEGRAM_CHAT_ID': 'test-chat'})
    def test_init_with_defaults(self):
        """Test initialization with default values from config."""
        with patch('x2telegram.services.telegram.TELEGRAM_BOT_TOKEN', 'test-token'):
            with patch('x2telegram.services.telegram.TELEGRAM_CHAT_ID', 'test-chat'):
                service = TelegramService()
                assert service.bot_token == 'test-token'
                assert service.default_chat_id == 'test-chat'

    def test_init_with_custom_values(self):
        """Test initialization with custom values."""
        service = TelegramService(bot_token="custom-token", default_chat_id="custom-chat")
        assert service.bot_token == "custom-token"
        assert service.default_chat_id == "custom-chat"


class TestSendMessage:
    """Tests for send_message functionality."""

    @responses.activate
    def test_send_message_success(self):
        """Test successful message sending."""
        service = TelegramService(bot_token="test-token", default_chat_id="test-chat")

        responses.add(
            responses.POST,
            f"{TELEGRAM_API_BASE}test-token/sendMessage",
            json={"ok": True, "result": {"message_id": 123}},
            status=200
        )

        result = service.send_message("Test message")
        assert result["ok"] is True

    @responses.activate
    def test_send_message_failure(self):
        """Test failed message sending."""
        service = TelegramService(bot_token="test-token", default_chat_id="test-chat")

        responses.add(
            responses.POST,
            f"{TELEGRAM_API_BASE}test-token/sendMessage",
            json={"ok": False, "description": "Bad Request"},
            status=400
        )

        result = service.send_message("Test message")
        assert result["ok"] is False

    def test_send_message_no_chat_id(self):
        """Test sending message without chat ID."""
        with patch('x2telegram.services.telegram.TELEGRAM_CHAT_ID', None):
            service = TelegramService(bot_token="test-token", default_chat_id=None)
            result = service.send_message("Test message")
            assert result["ok"] is False
            assert "No chat ID" in result["error"]

    @responses.activate
    def test_send_message_with_custom_chat_id(self):
        """Test sending message with custom chat ID."""
        service = TelegramService(bot_token="test-token", default_chat_id="default")

        responses.add(
            responses.POST,
            f"{TELEGRAM_API_BASE}test-token/sendMessage",
            json={"ok": True, "result": {"message_id": 123}},
            status=200
        )

        result = service.send_message("Test message", chat_id="custom-chat")
        assert result["ok"] is True


class TestSendPhoto:
    """Tests for send_photo functionality."""

    @responses.activate
    def test_send_photo_success(self):
        """Test successful photo sending."""
        service = TelegramService(bot_token="test-token", default_chat_id="test-chat")

        responses.add(
            responses.POST,
            f"{TELEGRAM_API_BASE}test-token/sendPhoto",
            json={"ok": True, "result": {"message_id": 123}},
            status=200
        )

        result = service.send_photo("https://example.com/photo.jpg", "Caption")
        assert result["ok"] is True


class TestGetBotInfo:
    """Tests for get_bot_info functionality."""

    @responses.activate
    def test_get_bot_info_success(self):
        """Test successful bot info retrieval."""
        service = TelegramService(bot_token="test-token", default_chat_id="test-chat")

        responses.add(
            responses.GET,
            f"{TELEGRAM_API_BASE}test-token/getMe",
            json={"ok": True, "result": {"id": 123, "username": "testbot"}},
            status=200
        )

        result = service.get_bot_info()
        assert result is not None
        assert result["username"] == "testbot"

    @responses.activate
    def test_get_bot_info_failure(self):
        """Test failed bot info retrieval."""
        service = TelegramService(bot_token="test-token", default_chat_id="test-chat")

        responses.add(
            responses.GET,
            f"{TELEGRAM_API_BASE}test-token/getMe",
            json={"ok": False, "description": "Unauthorized"},
            status=401
        )

        result = service.get_bot_info()
        assert result is None


class TestRateLimiting:
    """Tests for rate limiting functionality."""

    def test_rate_limit_initialization(self):
        """Test rate limit is properly initialized."""
        service = TelegramService(bot_token="test-token", default_chat_id="test-chat")
        assert service.rate_limit > 0
        assert service._last_send_time == 0
