"""
Settings module for the x2telegram application.
"""
import json
import os
import re
import sys
from pathlib import Path
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
CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY", "your-key")

# Ollama settings
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "deepseek-r1")
# Set to "ollama" to use locally hosted Ollama models or "claude" for Claude API
AI_PROVIDER = os.environ.get("AI_PROVIDER", "ollama")

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

# Claude model configuration
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-3-sonnet-20240229")

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
def parse_mirrors_from_env_file():
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

def _log_stderr(msg):
    """Simple stderr logging for config initialization (before logging is set up)."""
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