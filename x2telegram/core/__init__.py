"""
Core package for the x2telegram application.
"""

from .models import Tweet, Follower

__all__ = ['Tweet', 'Follower', 'TweetProcessor']

# Import TweetProcessor after defining core models to avoid circular imports
from .processor import TweetProcessor