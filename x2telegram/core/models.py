"""
Data models for the x2telegram application.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any

@dataclass
class Tweet:
    """
    Model representing a tweet from Twitter/X.
    """
    tweet_id: str
    tweet_url: str
    tweet_content: str
    tweet_image: Optional[bytes] = None
    created_at: str = ""
    
    # Optional additional fields
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __str__(self) -> str:
        """String representation of a tweet."""
        return f"Tweet(id={self.tweet_id}, content={self.tweet_content[:30]}...)"
    
    @property
    def is_valid(self) -> bool:
        """Check if the tweet has all required fields."""
        return bool(self.tweet_id and self.tweet_url and self.tweet_content)

@dataclass
class Follower:
    """
    Model representing a Twitter/X user being followed.
    """
    id: int
    username: str
    enabled: bool = True
    
    # Optional additional fields
    last_checked: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __str__(self) -> str:
        """String representation of a follower."""
        status = "enabled" if self.enabled else "disabled"
        return f"Follower(id={self.id}, username={self.username}, {status})"