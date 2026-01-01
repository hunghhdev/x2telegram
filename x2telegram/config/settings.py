"""
Settings module for the x2telegram application.
"""
import json
import os
import re
import sys
from pathlib import Path
from typing import Optional, List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

# Base paths
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = os.path.join(ROOT_DIR, "data")

# Database settings
DATABASE_PATH = os.path.join(DATA_DIR, "tweets.db")

# API tokens (override these from environment variables)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "your-token")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "your-chat-id")

# =============================================================================
# AI CONFIGURATION (User-friendly)
# =============================================================================
# Option 1: Just set your API key - provider auto-detected
#   AI_API_KEY=sk-xxx        -> OpenAI
#   AI_API_KEY=sk-ant-xxx    -> Claude  
#   AI_API_KEY=sk-xxx (with DEEPSEEK_API_KEY) -> DeepSeek
#
# Option 2: Explicitly set provider
#   AI_PROVIDER=openai|claude|deepseek|gemini|ollama
# =============================================================================

# Universal API key (auto-detects provider)
AI_API_KEY = os.environ.get("AI_API_KEY", "")

# Provider-specific API keys (override AI_API_KEY)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY", "")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# Auto-detect provider from API key format
def _detect_ai_provider() -> str:
    """Auto-detect AI provider from API key format."""
    explicit = os.environ.get("AI_PROVIDER", "").lower()
    if explicit:
        # Normalize common aliases
        aliases = {
            "gpt": "openai", "gpt4": "openai", "gpt-4": "openai", "chatgpt": "openai",
            "anthropic": "claude", "sonnet": "claude", "opus": "claude",
            "deep-seek": "deepseek", "ds": "deepseek",
            "google": "gemini", "bard": "gemini",
            "local": "ollama", "llama": "ollama"
        }
        return aliases.get(explicit, explicit)
    
    # Auto-detect from specific API keys first
    if DEEPSEEK_API_KEY:
        return "deepseek"
    if GEMINI_API_KEY:
        return "gemini"
    if CLAUDE_API_KEY or (AI_API_KEY and AI_API_KEY.startswith("sk-ant-")):
        return "claude"
    if OPENAI_API_KEY or (AI_API_KEY and AI_API_KEY.startswith("sk-")):
        return "openai"
    
    # Default to ollama (local, no API key needed)
    return "ollama"

AI_PROVIDER = _detect_ai_provider()

# Apply AI_API_KEY to the detected provider if specific key not set
if AI_API_KEY:
    if AI_PROVIDER == "openai" and not OPENAI_API_KEY:
        OPENAI_API_KEY = AI_API_KEY
    elif AI_PROVIDER == "claude" and not CLAUDE_API_KEY:
        CLAUDE_API_KEY = AI_API_KEY
    elif AI_PROVIDER == "deepseek" and not DEEPSEEK_API_KEY:
        DEEPSEEK_API_KEY = AI_API_KEY
    elif AI_PROVIDER == "gemini" and not GEMINI_API_KEY:
        GEMINI_API_KEY = AI_API_KEY

# Ollama settings (local, no API key needed)
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "deepseek-r1")

# Model settings (with sensible defaults)
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")

# AI analysis prompts
DEFAULT_AI_PROMPT = (
    "Analyze the following tweet and provide a brief, thoughtful comment about it. "
    "Keep your response short and to the point - no more than 1-2 sentences. "
    "Do not include any thinking process or explanations of your reasoning. "
    "Simply provide your final analysis directly."
)
AI_PROMPT = os.environ.get("AI_PROMPT", DEFAULT_AI_PROMPT)
# Provider-specific prompts (optional - if not set, AI_PROMPT will be used)
OLLAMA_PROMPT = os.environ.get("OLLAMA_PROMPT", AI_PROMPT)
CLAUDE_PROMPT = os.environ.get("CLAUDE_PROMPT", AI_PROMPT)
OPENAI_PROMPT = os.environ.get("OPENAI_PROMPT", AI_PROMPT)
DEEPSEEK_PROMPT = os.environ.get("DEEPSEEK_PROMPT", AI_PROMPT)
GEMINI_PROMPT = os.environ.get("GEMINI_PROMPT", AI_PROMPT)

# Processing settings
MAX_TWEETS_PER_USER = int(os.environ.get("MAX_TWEETS_PER_USER", "10"))

# Tweet filtering settings
# FILTER_KEYWORDS: Only forward tweets containing these keywords (comma-separated, case-insensitive)
# If empty, all tweets are forwarded
FILTER_KEYWORDS_INCLUDE = [k.strip().lower() for k in os.environ.get("FILTER_KEYWORDS_INCLUDE", "").split(",") if k.strip()]
# FILTER_KEYWORDS_EXCLUDE: Skip tweets containing these keywords (comma-separated, case-insensitive)
FILTER_KEYWORDS_EXCLUDE = [k.strip().lower() for k in os.environ.get("FILTER_KEYWORDS_EXCLUDE", "").split(",") if k.strip()]
# FILTER_REGEX_INCLUDE: Only forward tweets matching these regex patterns (comma-separated)
FILTER_REGEX_INCLUDE = [p.strip() for p in os.environ.get("FILTER_REGEX_INCLUDE", "").split(",") if p.strip()]
# FILTER_REGEX_EXCLUDE: Skip tweets matching these regex patterns (comma-separated)
FILTER_REGEX_EXCLUDE = [p.strip() for p in os.environ.get("FILTER_REGEX_EXCLUDE", "").split(",") if p.strip()]

# Default Nitter mirrors - preferably override these from environment
NITTER_MIRRORS = [
    "https://nitter.net"
]

# Custom parser for NITTER_MIRRORS (dot-env doesn't handle multi-line arrays well)
def parse_mirrors_from_env_file() -> Optional[List[str]]:
    """Parse Nitter mirrors from .env file."""
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if not env_path.exists():
        return None
    
    # Read the .env file directly
    with open(env_path, 'r') as f:
        env_content = f.read()
    
    # Look for NITTER_MIRRORS section
    mirrors_match = re.search(r'NITTER_MIRRORS\s*=\s*\[(.*?)\]', env_content, re.DOTALL)
    if not mirrors_match:
        return None
    
    # Extract all URLs from the section
    mirrors_content = mirrors_match.group(1)
    url_matches = re.findall(r'"(https?://[^"]+)"', mirrors_content)
    
    return url_matches if url_matches else None

# Try to get mirrors from direct .env file parsing first
custom_mirrors = parse_mirrors_from_env_file()

def _log_stderr(msg: str) -> None:
    """Simple stderr logging for config initialization."""
    print(f"[CONFIG] {msg}", file=sys.stderr)

if custom_mirrors:
    NITTER_MIRRORS = custom_mirrors
    _log_stderr(f"Using {len(NITTER_MIRRORS)} custom Nitter mirrors from .env file")
# Fallback to environment variable if direct parsing failed
elif os.environ.get("NITTER_MIRRORS"):
    try:
        # Try to parse as JSON (for simpler formats)
        mirrors_raw = os.environ.get("NITTER_MIRRORS", "[]")
        custom_mirrors = json.loads(mirrors_raw)
        if isinstance(custom_mirrors, list) and custom_mirrors:
            NITTER_MIRRORS = custom_mirrors
            _log_stderr(f"Using {len(NITTER_MIRRORS)} custom Nitter mirrors from environment variable")
    except Exception as e:
        _log_stderr(f"Error parsing NITTER_MIRRORS environment variable: {e}")
        _log_stderr("Using default mirror: https://nitter.net")

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)