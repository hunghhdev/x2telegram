"""
Configuration package for the x2telegram application.
"""

from .settings import (
    # Paths
    ROOT_DIR,
    DATA_DIR,
    DATABASE_PATH,
    # Telegram
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    # AI Provider
    AI_PROVIDER,
    AI_PROMPT,
    # Ollama
    OLLAMA_URL,
    OLLAMA_MODEL,
    OLLAMA_PROMPT,
    # Claude
    CLAUDE_API_KEY,
    CLAUDE_MODEL,
    CLAUDE_PROMPT,
    # OpenAI
    OPENAI_API_KEY,
    OPENAI_MODEL,
    OPENAI_BASE_URL,
    OPENAI_PROMPT,
    # DeepSeek
    DEEPSEEK_API_KEY,
    DEEPSEEK_MODEL,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_PROMPT,
    # Gemini
    GEMINI_API_KEY,
    GEMINI_MODEL,
    GEMINI_PROMPT,
    # Processing
    MAX_TWEETS_PER_USER,
    NITTER_MIRRORS,
    # Filtering
    FILTER_KEYWORDS_INCLUDE,
    FILTER_KEYWORDS_EXCLUDE,
    FILTER_REGEX_INCLUDE,
    FILTER_REGEX_EXCLUDE,
)