# x2telegram

A service to forward relevant tweets from Twitter/X to Telegram.

## Overview

x2telegram monitors Twitter/X profiles through RSS feeds provided by Nitter instances, analyzes the tweets for relevance, and forwards the relevant ones to a Telegram chat.

## Features

- Follow multiple Twitter/X accounts
- Filter tweets based on relevance (keyword matching or AI analysis)
- Forward relevant tweets to Telegram
- Command-line interface for easy management
- SQLite database for persistent storage
- Resilient RSS fetching with multiple Nitter mirrors
- Customizable AI analysis prompts for tailored relevance detection

## Project Structure

```
x2telegram/
├── data/                     # Data storage directory
│   └── tweets.db             # SQLite database
├── main.py                   # Command-line interface
├── x2telegram/               # Main package
│   ├── __init__.py           # Package initialization
│   ├── config/               # Configuration settings
│   │   ├── __init__.py
│   │   └── settings.py       # Configuration constants and environment vars
│   ├── core/                 # Core functionality
│   │   ├── __init__.py
│   │   ├── models.py         # Data models (Tweet, Follower)
│   │   └── processor.py      # Main tweet processing logic
│   ├── db/                   # Database operations
│   │   ├── __init__.py
│   │   └── database.py       # Database connection and operations
│   ├── services/             # External services integration
│   │   ├── __init__.py
│   │   ├── analyzer.py       # Tweet relevance analysis
│   │   ├── rss.py            # RSS feed fetching from Nitter
│   │   └── telegram.py       # Telegram messaging
│   └── utils/                # Utility functions
│       ├── __init__.py
│       └── helpers.py        # Helper utilities and logging
├── tests/                    # Tests
│   ├── __init__.py
│   └── test_db.py            # Database tests
└── requirements.txt          # Dependencies
```

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/hunghhdev/x2telegram.git
   cd x2telegram
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure your environment:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

## Configuration

Create a `.env` file based on `.env.example` with the following parameters:

- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token (get it from [@BotFather](https://t.me/BotFather))
- `TELEGRAM_CHAT_ID`: The ID of the chat where messages will be sent
- `ANTHROPIC_API_KEY`: (Optional) API key for AI-based analysis with Claude
- `MAX_TWEETS_PER_USER`: Maximum number of tweets to process per user
- `NITTER_MIRRORS`: (Optional) JSON array of custom Nitter instance URLs

### AI Configuration

The app supports two AI providers for tweet analysis:

1. **Ollama** (default, locally-hosted): 
   - `OLLAMA_URL`: URL for the Ollama API server (default: http://localhost:11434)
   - `OLLAMA_MODEL`: Model to use with Ollama (default: deepseek-r1)

2. **Claude** (cloud-based):
   - `ANTHROPIC_API_KEY`: Your Anthropic/Claude API key
   - `CLAUDE_MODEL`: Claude model to use (default: claude-3-sonnet-20240229)
   - Set `AI_PROVIDER=claude` to use Claude

### AI Prompt Customization

You can customize the prompts used for AI analysis:

- `AI_PROMPT`: General prompt for all AI providers
- `OLLAMA_PROMPT`: Specific prompt for Ollama (overrides AI_PROMPT)
- `CLAUDE_PROMPT`: Specific prompt for Claude (overrides AI_PROMPT)

Example:
```
AI_PROMPT="Analyze this tweet and provide a brief, thoughtful comment about it. Keep your response short and to the point."
```

## Usage

### Command-line Interface

The application has several commands:

```bash
# Run the tweet processing job
python main.py run

# Add a Twitter/X user to follow
python main.py add-follower elonmusk

# List all followed users
python main.py list-followers

# Remove a user
python main.py remove-follower elonmusk

# Enable a user
python main.py enable-follower elonmusk

# Disable a user
python main.py disable-follower elonmusk

# Run database maintenance
python main.py maintenance
```

### Deployment Options

You can deploy x2telegram in several ways depending on your needs:

#### 1. Using Cron

Set up a cron job to run the script periodically:

```bash
# Edit your crontab
crontab -e

# Add a line to run every 15 minutes
*/15 * * * * cd /path/to/x2telegram && python main.py run >> /path/to/x2telegram/logs/cron.log 2>&1
```

#### 2. Using Systemd (Linux)

For a more robust solution on Linux systems, use systemd:

```bash
# Create a systemd service file
sudo nano /etc/systemd/system/x2telegram.service
```

With content:
```ini
[Unit]
Description=X2Telegram Service
After=network.target

[Service]
Type=oneshot
User=youruser
WorkingDirectory=/path/to/x2telegram
ExecStart=/path/to/x2telegram/venv/bin/python main.py run
Environment="PATH=/path/to/x2telegram/venv/bin"

[Install]
WantedBy=multi-user.target
```

And a timer file for scheduling:
```bash
sudo nano /etc/systemd/system/x2telegram.timer
```

With content:
```ini
[Unit]
Description=Run X2Telegram every 15 minutes

[Timer]
OnBootSec=1min
OnUnitActiveSec=15min
AccuracySec=1s

[Install]
WantedBy=timers.target
```

Enable and start the timer:
```bash
sudo systemctl enable x2telegram.timer
sudo systemctl start x2telegram.timer
```

## Development

### Running Tests

```bash
# Run all tests
python -m unittest discover tests

# Run a specific test
python -m unittest tests.test_db
```

### Creating a Virtual Environment

For development, it's recommended to use a virtual environment:

```bash
# Create a virtual environment
python -m venv venv

# Activate it (Linux/macOS)
source venv/bin/activate

# Activate it (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.