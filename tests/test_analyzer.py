"""
Tests for the AnalyzerService module.
"""
import pytest
import responses
from unittest.mock import patch, MagicMock

from x2telegram.services.analyzer import AnalyzerService
from x2telegram.config import CLAUDE_API_ENDPOINT, GEMINI_API_BASE


class TestAnalyzerServiceInit:
    """Tests for AnalyzerService initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default values."""
        with patch('x2telegram.services.analyzer.AI_PROVIDER', 'ollama'):
            service = AnalyzerService()
            assert service.provider == 'ollama'
            assert service.threshold > 0

    def test_init_with_custom_provider(self):
        """Test initialization with custom provider."""
        service = AnalyzerService(provider='claude', api_key='test-key')
        assert service.provider == 'claude'
        assert service.api_key == 'test-key'


class TestAnalyzeWithOllama:
    """Tests for Ollama analysis."""

    @responses.activate
    def test_analyze_with_ollama_success(self):
        """Test successful Ollama analysis."""
        service = AnalyzerService(provider='ollama')

        responses.add(
            responses.POST,
            "http://localhost:11434/api/chat",
            json={"message": {"content": "This is a test analysis."}},
            status=200
        )

        result = service.analyze_with_ollama("Test tweet content")
        assert "analysis" in result
        assert result["analysis"] == "This is a test analysis."

    @responses.activate
    def test_analyze_with_ollama_model_not_found(self):
        """Test Ollama model not found error."""
        service = AnalyzerService(provider='ollama')

        responses.add(
            responses.POST,
            "http://localhost:11434/api/chat",
            json={"error": "model not found"},
            status=404
        )

        result = service.analyze_with_ollama("Test tweet", max_retries=0)
        assert "error" in result


class TestAnalyzeWithClaude:
    """Tests for Claude analysis."""

    @responses.activate
    def test_analyze_with_claude_success(self):
        """Test successful Claude analysis."""
        service = AnalyzerService(provider='claude', api_key='test-key')

        responses.add(
            responses.POST,
            CLAUDE_API_ENDPOINT,
            json={"content": [{"text": "Claude analysis result."}]},
            status=200
        )

        result = service.analyze_with_claude("Test tweet content")
        assert "analysis" in result
        assert result["analysis"] == "Claude analysis result."

    def test_analyze_with_claude_no_api_key(self):
        """Test Claude analysis without API key."""
        service = AnalyzerService(provider='claude', api_key=None)
        result = service.analyze_with_claude("Test tweet")
        assert "error" in result
        assert "No API key" in result["error"]

    @responses.activate
    def test_analyze_with_claude_image(self):
        """Test Claude analysis with image."""
        service = AnalyzerService(provider='claude', api_key='test-key')

        # Mock image download
        responses.add(
            responses.GET,
            "https://example.com/image.jpg",
            body=b"fake image data",
            status=200,
            headers={"Content-Type": "image/jpeg"}
        )

        responses.add(
            responses.POST,
            CLAUDE_API_ENDPOINT,
            json={"content": [{"text": "Image analysis result."}]},
            status=200
        )

        result = service.analyze_with_claude("Test tweet", image_url="https://example.com/image.jpg")
        assert "analysis" in result
        assert result.get("includes_image") is True


class TestAnalyzeWithOpenAI:
    """Tests for OpenAI analysis."""

    @responses.activate
    def test_analyze_with_openai_success(self):
        """Test successful OpenAI analysis."""
        service = AnalyzerService(provider='openai')

        responses.add(
            responses.POST,
            "https://api.openai.com/v1/chat/completions",
            json={"choices": [{"message": {"content": "OpenAI analysis."}}]},
            status=200
        )

        result = service.analyze_with_openai("Test tweet", api_key="test-key")
        assert "analysis" in result

    def test_analyze_with_openai_no_api_key(self):
        """Test OpenAI analysis without API key."""
        service = AnalyzerService(provider='openai')
        result = service.analyze_with_openai("Test tweet", api_key=None)
        assert "error" in result


class TestAnalyzeWithGemini:
    """Tests for Gemini analysis."""

    @responses.activate
    def test_analyze_with_gemini_success(self):
        """Test successful Gemini analysis."""
        with patch('x2telegram.services.analyzer.GEMINI_API_KEY', 'test-key'):
            with patch('x2telegram.services.analyzer.GEMINI_MODEL', 'gemini-pro'):
                service = AnalyzerService(provider='gemini')

                responses.add(
                    responses.POST,
                    f"{GEMINI_API_BASE}/gemini-pro:generateContent",
                    json={"candidates": [{"content": {"parts": [{"text": "Gemini analysis."}]}}]},
                    status=200,
                    match_querystring=False
                )

                result = service.analyze_with_gemini("Test tweet")
                assert "analysis" in result


class TestAnalyzeWithAI:
    """Tests for the unified analyze_with_ai interface."""

    def test_analyze_with_ai_ollama(self):
        """Test analyze_with_ai dispatches to Ollama."""
        service = AnalyzerService(provider='ollama')

        with patch.object(service, 'analyze_with_ollama', return_value={"analysis": "test"}) as mock:
            result = service.analyze_with_ai("Test tweet")
            mock.assert_called_once()

    def test_analyze_with_ai_claude(self):
        """Test analyze_with_ai dispatches to Claude."""
        service = AnalyzerService(provider='claude', api_key='test')

        with patch.object(service, 'analyze_with_claude', return_value={"analysis": "test"}) as mock:
            result = service.analyze_with_ai("Test tweet")
            mock.assert_called_once()

    def test_analyze_with_ai_unknown_provider(self):
        """Test analyze_with_ai falls back to Ollama for unknown provider."""
        service = AnalyzerService(provider='unknown')

        with patch.object(service, 'analyze_with_ollama', return_value={"analysis": "test"}) as mock:
            result = service.analyze_with_ai("Test tweet")
            mock.assert_called_once()


class TestAnalyzeTweet:
    """Tests for the high-level analyze_tweet interface."""

    def test_analyze_tweet_with_ai(self):
        """Test analyze_tweet with AI enabled."""
        service = AnalyzerService(provider='ollama')

        with patch.object(service, 'analyze_with_ai', return_value={"analysis": "test"}) as mock:
            result = service.analyze_tweet("Test content", use_ai=True)
            mock.assert_called_once()

    def test_analyze_tweet_without_ai(self):
        """Test analyze_tweet with AI disabled."""
        service = AnalyzerService(provider='ollama')
        result = service.analyze_tweet("Test content", use_ai=False)
        assert result["analysis"] == "No AI analysis performed"


class TestRemoveThinkingSection:
    """Tests for thinking section removal."""

    def test_remove_thinking_section(self):
        """Test removing thinking tags from response."""
        service = AnalyzerService()
        text = "<think>Internal thoughts</think>Actual response"
        result = service._remove_thinking_section(text)
        assert "<think>" not in result
        assert "Actual response" in result

    def test_remove_multiple_tags(self):
        """Test removing multiple tags."""
        service = AnalyzerService()
        text = "<think>thoughts</think><other>content</other>Final"
        result = service._remove_thinking_section(text)
        assert "Final" in result
        assert "<think>" not in result

    def test_clean_whitespace(self):
        """Test cleaning extra whitespace."""
        service = AnalyzerService()
        text = "  Multiple   spaces   here  "
        result = service._remove_thinking_section(text)
        assert "  " not in result
