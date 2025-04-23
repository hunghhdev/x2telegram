"""
Configuration package for the x2telegram application.
"""

from .settings import (
    ROOT_DIR,
    DATA_DIR,
    DATABASE_PATH,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    GROQ_API_KEY,
    OLLAMA_URL,
    OLLAMA_MODEL,
    AI_PROVIDER,
    AI_PROMPT,
    OLLAMA_PROMPT,
    GROQ_PROMPT,
    MAX_TWEETS_PER_USER,
    NITTER_MIRRORS
)

__all__ = [
    'ROOT_DIR',
    'DATA_DIR',
    'DATABASE_PATH',
    'TELEGRAM_BOT_TOKEN',
    'TELEGRAM_CHAT_ID',
    'GROQ_API_KEY',
    'OLLAMA_URL',
    'OLLAMA_MODEL',
    'AI_PROVIDER',
    'AI_PROMPT',
    'OLLAMA_PROMPT',
    'GROQ_PROMPT',
    'MAX_TWEETS_PER_USER',
    'NITTER_MIRRORS'
]