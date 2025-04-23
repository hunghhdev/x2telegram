"""
Settings module for the x2telegram application.
"""
import os
import sys
import re
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
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "your-key")

# Ollama settings
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "deepseek-r1")
# Set to "ollama" to use locally hosted Ollama models instead of GROQ
AI_PROVIDER = os.environ.get("AI_PROVIDER", "ollama")

# AI analysis prompts
DEFAULT_AI_PROMPT = (
    "Analyze the following tweet and determine if it contains important or interesting "
    "information. The tweet should be relevant if it contains news, announcements, "
    "or significant insights. Respond with a JSON object with two fields: "
    "'is_relevant' (boolean) and 'reason' (string explanation)."
)
AI_PROMPT = os.environ.get("AI_PROMPT", DEFAULT_AI_PROMPT)
# Provider-specific prompts (optional - if not set, AI_PROMPT will be used)
OLLAMA_PROMPT = os.environ.get("OLLAMA_PROMPT", AI_PROMPT)
GROQ_PROMPT = os.environ.get("GROQ_PROMPT", AI_PROMPT)

# Processing settings
MAX_TWEETS_PER_USER = int(os.environ.get("MAX_TWEETS_PER_USER", "10"))

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

if custom_mirrors:
    NITTER_MIRRORS = custom_mirrors
    print(f"Using {len(NITTER_MIRRORS)} custom Nitter mirrors from .env file", file=sys.stderr)
    # Print the first few mirrors to confirm correct parsing
    for i, mirror in enumerate(NITTER_MIRRORS[:3]):
        print(f"  Mirror {i+1}: {mirror}", file=sys.stderr)
    if len(NITTER_MIRRORS) > 3:
        print(f"  ...and {len(NITTER_MIRRORS) - 3} more", file=sys.stderr)
# Fallback to environment variable if direct parsing failed
elif os.environ.get("NITTER_MIRRORS"):
    try:
        import json
        # Try to parse as JSON (for simpler formats)
        mirrors_raw = os.environ.get("NITTER_MIRRORS", "[]")
        custom_mirrors = json.loads(mirrors_raw)
        if isinstance(custom_mirrors, list) and custom_mirrors:
            NITTER_MIRRORS = custom_mirrors
            print(f"Using {len(NITTER_MIRRORS)} custom Nitter mirrors from environment variable", 
                  file=sys.stderr)
    except Exception as e:
        print(f"Error parsing NITTER_MIRRORS environment variable: {e}", file=sys.stderr)
        print(f"Using default mirror: https://nitter.net", file=sys.stderr)

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)