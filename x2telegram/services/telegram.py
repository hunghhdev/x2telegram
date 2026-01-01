"""
Telegram service for sending messages to Telegram chats.
"""
import os
import requests
import threading
import time
from collections import deque
from typing import Dict, Any, Optional

from ..config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from ..utils import log_info, log_error, log_debug

# Rate limit: Telegram allows ~30 messages per second to different chats
# For same chat, limit is ~1 message per second
DEFAULT_RATE_LIMIT = float(os.environ.get('TELEGRAM_RATE_LIMIT', '1.0'))  # seconds between messages

class TelegramService:
    """Service for sending messages to Telegram."""
    
    def __init__(self, bot_token=None, default_chat_id=None):
        """
        Initialize the Telegram service.
        
        Args:
            bot_token (str, optional): Telegram bot token. Defaults to config value.
            default_chat_id (str, optional): Default chat ID. Defaults to config value.
        """
        self.bot_token = bot_token or TELEGRAM_BOT_TOKEN
        self.default_chat_id = default_chat_id or TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.retry_count = 3
        self.retry_delay = 2  # seconds
        
        # Connection pooling with requests.Session for better performance
        self.session = requests.Session()
        
        # Rate limiting
        self.rate_limit = DEFAULT_RATE_LIMIT
        self._last_send_time = 0
        self._rate_lock = threading.Lock()
    
    def _wait_for_rate_limit(self):
        """Wait if necessary to respect rate limits."""
        with self._rate_lock:
            now = time.time()
            elapsed = now - self._last_send_time
            if elapsed < self.rate_limit:
                wait_time = self.rate_limit - elapsed
                log_debug(f"Rate limiting: waiting {wait_time:.2f}s before sending")
                time.sleep(wait_time)
            self._last_send_time = time.time()
        
    def send_message(self, text: str, chat_id=None, parse_mode="HTML", 
                     disable_web_page_preview=False) -> Dict[str, Any]:
        """
        Send a message to a Telegram chat.
        
        Args:
            text (str): Message text
            chat_id (str, optional): Chat ID. Defaults to the default chat ID.
            parse_mode (str, optional): Message parse mode. Defaults to "HTML".
            disable_web_page_preview (bool, optional): Disable link previews. Defaults to False.
            
        Returns:
            dict: Response from Telegram API
        """
        chat_id = chat_id or self.default_chat_id
        if not chat_id:
            log_error("No chat ID provided and no default chat ID set")
            return {"ok": False, "error": "No chat ID provided"}
            
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_web_page_preview
        }
        
        # Apply rate limiting before sending
        self._wait_for_rate_limit()
        
        # Try to send message with retries
        for attempt in range(self.retry_count):
            try:
                log_info(f"Sending message to Telegram chat {chat_id} (attempt {attempt+1}/{self.retry_count})")
                response = self.session.post(url, data=payload, timeout=10)
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("ok"):
                        log_info("Message sent successfully")
                        return result
                        
                log_error(f"Failed to send message: {response.text}")
                
            except Exception as e:
                log_error(f"Error sending message to Telegram: {str(e)}")
                
            # Wait before retrying
            if attempt < self.retry_count - 1:
                time.sleep(self.retry_delay)
                
        return {"ok": False, "error": "Failed to send message after retries"}
        
    def send_photo(self, photo_url: str, caption: str = "", chat_id=None) -> Dict[str, Any]:
        """
        Send a photo to a Telegram chat.
        
        Args:
            photo_url (str): URL of the photo
            caption (str, optional): Photo caption. Defaults to "".
            chat_id (str, optional): Chat ID. Defaults to the default chat ID.
            
        Returns:
            dict: Response from Telegram API
        """
        chat_id = chat_id or self.default_chat_id
        url = f"{self.base_url}/sendPhoto"
        payload = {
            "chat_id": chat_id,
            "photo": photo_url,
            "caption": caption,
            "parse_mode": "HTML"
        }
        
        # Apply rate limiting before sending
        self._wait_for_rate_limit()
        
        try:
            log_info(f"Sending photo to Telegram chat {chat_id}")
            response = self.session.post(url, data=payload, timeout=10)
            return response.json()
        except Exception as e:
            log_error(f"Error sending photo to Telegram: {str(e)}")
            return {"ok": False, "error": str(e)}
    
    def get_bot_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the bot.
        
        Returns:
            dict: Bot information from Telegram API
        """
        url = f"{self.base_url}/getMe"
        
        try:
            response = self.session.get(url, timeout=10)
            result = response.json()
            if result.get("ok"):
                return result.get("result")
            else:
                log_error(f"Failed to get bot info: {result.get('description')}")
                return None
        except Exception as e:
            log_error(f"Error getting bot info: {str(e)}")
            return None

# Convenience function for backward compatibility
def send_telegram_message(text, chat_id=TELEGRAM_CHAT_ID):
    """Send a message to Telegram (convenience function for backward compatibility)."""
    service = TelegramService()
    result = service.send_message(text, chat_id)
    return result