"""
Constants for the x2telegram application.

This module centralizes all magic numbers and hardcoded values
to improve maintainability and configurability.
"""

# =============================================================================
# TIMEOUTS (seconds)
# =============================================================================
DEFAULT_HTTP_TIMEOUT = 10
IMAGE_DOWNLOAD_TIMEOUT = 10
TELEGRAM_TIMEOUT = 10

# AI Provider timeouts
OLLAMA_TIMEOUT = 30
CLAUDE_TIMEOUT = 15
OPENAI_TIMEOUT = 30
GEMINI_TIMEOUT = 30

# RSS/Scraping timeout
RSS_TIMEOUT = 60

# =============================================================================
# RETRY CONFIGURATION
# =============================================================================
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 2  # seconds
DEFAULT_BACKOFF_FACTOR = 1.5

RSS_MAX_RETRIES = 10

# Jitter range for retry delays (0.9 to 1.1)
RETRY_JITTER_MIN = 0.9
RETRY_JITTER_MAX = 0.2  # Added to min for range

# =============================================================================
# RATE LIMITING
# =============================================================================
TELEGRAM_RATE_LIMIT = 1.0  # seconds between messages
RSS_RATE_LIMIT_WAIT = 60  # seconds to wait when rate limited

# =============================================================================
# AI PARAMETERS
# =============================================================================
AI_MAX_TOKENS = 300
AI_TEMPERATURE = 0.3
AI_CONFIDENCE_THRESHOLD = 0.7

# =============================================================================
# PROCESSING
# =============================================================================
DEFAULT_MAX_WORKERS = 3
DEFAULT_PENDING_LIMIT = 10
SEQUENTIAL_PROCESSING_DELAY = 1  # seconds between followers

# =============================================================================
# HTML PARSING
# =============================================================================
DOM_TRAVERSAL_MAX_LEVELS = 5

# =============================================================================
# API VERSIONS
# =============================================================================
CLAUDE_API_VERSION = "2023-06-01"

# =============================================================================
# API ENDPOINTS
# =============================================================================
TELEGRAM_API_BASE = "https://api.telegram.org/bot"
CLAUDE_API_ENDPOINT = "https://api.anthropic.com/v1/messages"
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
