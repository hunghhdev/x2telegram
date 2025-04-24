"""
Service for analyzing tweets to determine relevance.
"""
import re
import requests
import json
import os
import time
import random
from typing import Dict, Any, List, Optional, Union, Callable

from ..config import (
    CLAUDE_API_KEY, OLLAMA_URL, OLLAMA_MODEL, 
    AI_PROVIDER, CLAUDE_MODEL,
    AI_PROMPT, OLLAMA_PROMPT, CLAUDE_PROMPT
)
from ..utils import log_info, log_error, log_debug

class AnalyzerService:
    """Service for analyzing tweets to determine relevance."""
    
    def __init__(self, api_key=None, threshold=0.7, provider=None, ollama_url=None, ollama_model=None):
        """
        Initialize the analyzer service.
        
        Args:
            api_key (str, optional): API key for cloud AI services. Defaults to config value based on provider.
            threshold (float, optional): Confidence threshold for AI analysis. Defaults to 0.7.
            provider (str, optional): AI provider to use ('claude', 'ollama'). Defaults to config value.
            ollama_url (str, optional): URL for Ollama API. Defaults to config value.
            ollama_model (str, optional): Model to use with Ollama. Defaults to config value.
        """
        self.provider = provider or AI_PROVIDER
        
        # Set the API key based on the provider
        if self.provider.lower() == 'claude':
            self.api_key = api_key or CLAUDE_API_KEY
        else:
            # Default for Ollama (doesn't use API key, but keeping for consistency)
            self.api_key = api_key
            
        self.threshold = threshold
        self.ollama_url = ollama_url or OLLAMA_URL
        self.ollama_model = ollama_model or OLLAMA_MODEL
        self.keyword_filters = []
        self.regex_filters = []
        
    def add_keyword_filter(self, keyword: str, is_positive: bool = True):
        """
        Add a keyword filter.
        
        Args:
            keyword (str): Keyword to filter on
            is_positive (bool, optional): If True, include tweets with this keyword. 
                                         If False, exclude tweets with this keyword.
                                         Defaults to True.
        """
        self.keyword_filters.append((keyword.lower(), is_positive))
        
    def add_regex_filter(self, pattern: str, is_positive: bool = True):
        """
        Add a regex filter.
        
        Args:
            pattern (str): Regex pattern to filter on
            is_positive (bool, optional): If True, include tweets matching this pattern. 
                                         If False, exclude tweets matching this pattern.
                                         Defaults to True.
        """
        try:
            regex = re.compile(pattern, re.IGNORECASE)
            self.regex_filters.append((regex, is_positive))
        except re.error as e:
            log_error(f"Invalid regex pattern '{pattern}': {str(e)}")
    
    def analyze_with_keywords(self, text: str) -> bool:
        """
        Analyze text using keyword filters.
        
        Args:
            text (str): Text to analyze
            
        Returns:
            bool: True if text passes all filters, False otherwise
        """
        text_lower = text.lower()
        
        # First, check exclusion filters (negative filters)
        for keyword, is_positive in self.keyword_filters:
            if not is_positive and keyword in text_lower:
                log_debug(f"Text excluded by negative keyword filter: '{keyword}'")
                return False
                
        for regex, is_positive in self.regex_filters:
            if not is_positive and regex.search(text):
                log_debug(f"Text excluded by negative regex filter: '{regex.pattern}'")
                return False
        
        # If no exclusion filters matched, check inclusion filters
        # If we have no inclusion filters, return True by default
        has_inclusion_filters = any(is_positive for _, is_positive in self.keyword_filters + self.regex_filters)
        
        if not has_inclusion_filters:
            return True
            
        # Check if any inclusion filter matches
        for keyword, is_positive in self.keyword_filters:
            if is_positive and keyword in text_lower:
                log_debug(f"Text included by positive keyword filter: '{keyword}'")
                return True
                
        for regex, is_positive in self.regex_filters:
            if is_positive and regex.search(text):
                log_debug(f"Text included by positive regex filter: '{regex.pattern}'")
                return True
                
        # If we have inclusion filters but none matched, return False
        return False
    
    def analyze_with_ollama(self, text: str, prompt: str = None, max_retries=3, retry_delay=2, timeout=30) -> Dict[str, Any]:
        """
        Analyze text using Ollama with retry mechanism.
        
        Args:
            text (str): Text to analyze
            prompt (str, optional): Custom prompt for the AI. Defaults to the value from environment settings.
            max_retries (int): Maximum number of retry attempts (default: 3)
            retry_delay (int): Delay between retries in seconds (default: 2)
            timeout (int): Request timeout in seconds (default: 30)
            
        Returns:
            dict: AI analysis results
        """
        # Use the environment-based prompt if none provided
        if not prompt:
            prompt = OLLAMA_PROMPT
            
        retry_count = 0
        start_time = time.time()
        while retry_count <= max_retries:
            try:
                url = f"{self.ollama_url}/api/chat"
                headers = {
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": self.ollama_model,
                    "messages": [
                        {"role": "system", "content": "You are an analyzer that evaluates content."},
                        {"role": "user", "content": f"{prompt}\n\nTweet: {text}"}
                    ],
                    "stream": False
                }
                
                log_info(f"Analyzing tweet with Ollama using model {self.ollama_model}")
                log_debug(f"Attempt {retry_count + 1} of {max_retries + 1}")
                
                # Log timing information for monitoring
                request_start = time.time()
                response = requests.post(url, headers=headers, json=payload, timeout=timeout)
                request_duration = time.time() - request_start
                log_debug(f"Ollama API call took {request_duration:.2f} seconds")
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Get the plain text response
                    message_content = result.get("message", {}).get("content", "")
                    
                    # Remove any thinking sections from the response
                    analysis = self._remove_thinking_section(message_content)
                    
                    total_duration = time.time() - start_time
                    log_debug(f"Ollama analysis: {analysis}")
                    log_info(f"Total analysis time: {total_duration:.2f} seconds (including {retry_count} retries)")
                    
                    return {
                        "analysis": analysis,
                        "response_time": request_duration,
                        "total_analysis_time": total_duration
                    }
                elif response.status_code == 404:
                    # Model not found
                    log_error(f"Model {self.ollama_model} not found in Ollama. Try pulling it first.")
                    return {"error": f"Model {self.ollama_model} not found", "analysis": "Error: Model not found"}
                elif response.status_code >= 500:
                    # Server error, retry
                    log_error(f"Ollama server error (status: {response.status_code}). Retrying in {retry_delay} seconds...")
                    retry_count += 1
                    if retry_count <= max_retries:
                        # Adding jitter to prevent thundering herd
                        actual_delay = retry_delay * (0.9 + 0.2 * random.random())
                        log_debug(f"Waiting {actual_delay:.2f} seconds before retry #{retry_count}")
                        time.sleep(actual_delay)
                        # Increase delay for next retry (exponential backoff)
                        retry_delay *= 1.5
                    else:
                        total_duration = time.time() - start_time
                        log_error(f"Ollama failed after {total_duration:.2f} seconds with {max_retries} retries")
                        return {
                            "error": f"Ollama server error after {max_retries} retries", 
                            "analysis": "Error: Server error"
                        }
                else:
                    # Other errors
                    log_error(f"Ollama request failed with status {response.status_code}: {response.text}")
                    return {"error": f"Request failed with status {response.status_code}", "analysis": "Error: Request failed"}
                
            except requests.Timeout:
                log_error(f"Ollama request timed out after {timeout} seconds. Retrying...")
                retry_count += 1
                if retry_count <= max_retries:
                    time.sleep(retry_delay)
                    # Increase timeout for next retry
                    timeout *= 1.5
                    log_debug(f"Increased timeout to {timeout} seconds for next attempt")
                else:
                    total_duration = time.time() - start_time
                    log_error(f"Ollama timed out after {total_duration:.2f} seconds with {max_retries} retries")
                    return {
                        "error": f"Timeout after {max_retries} retries", 
                        "analysis": "Error: Request timed out"
                    }
            
            except requests.ConnectionError:
                log_error(f"Connection error to Ollama server at {self.ollama_url}. Retrying...")
                retry_count += 1
                if retry_count <= max_retries:
                    # Adding jitter to prevent thundering herd
                    actual_delay = retry_delay * (0.9 + 0.2 * random.random())
                    log_debug(f"Waiting {actual_delay:.2f} seconds before retry #{retry_count}")
                    time.sleep(actual_delay)
                    retry_delay *= 1.5
                else:
                    total_duration = time.time() - start_time
                    log_error(f"Connection errors persisted for {total_duration:.2f} seconds with {max_retries} retries")
                    return {
                        "error": f"Connection error after {max_retries} retries", 
                        "analysis": "Error: Connection failed"
                    }
                
            except Exception as e:
                log_error(f"Error in Ollama analysis: {str(e)}")
                retry_count += 1
                if retry_count <= max_retries:
                    time.sleep(retry_delay)
                    retry_delay *= 1.5
                else:
                    total_duration = time.time() - start_time
                    return {
                        "error": str(e), 
                        "analysis": f"Error: {str(e)}"
                    }
    
    def analyze_with_claude(self, text: str, prompt: str = None, image_url: str = None) -> Dict[str, Any]:
        """
        Analyze text using Claude AI (Anthropic), optionally including an image.
        
        Args:
            text (str): Text to analyze
            prompt (str, optional): Custom prompt for the AI. Defaults to the value from environment settings.
            image_url (str, optional): URL of an image to include in the analysis. Defaults to None.
            
        Returns:
            dict: AI analysis results
        """
        if not self.api_key:
            log_error("No Anthropic/Claude API key provided for AI analysis")
            return {"error": "No API key", "analysis": "Error: No API key configured"}
            
        # Use the environment-based prompt if none provided
        if not prompt:
            prompt = CLAUDE_PROMPT
            
        try:
            url = "https://api.anthropic.com/v1/messages"
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            
            # Prepare the content section based on whether we have an image
            content = []
            
            # First part is always the text prompt
            content.append({
                "type": "text",
                "text": f"{prompt}\n\nTweet: {text}"
            })
            
            # If an image URL is provided, download and include it
            if image_url:
                try:
                    log_info(f"Downloading tweet image from: {image_url}")
                    image_response = requests.get(image_url, timeout=10)
                    image_response.raise_for_status()
                    
                    # Get image mime type from response headers or infer from URL
                    content_type = image_response.headers.get('Content-Type')
                    if not content_type or not content_type.startswith('image/'):
                        if image_url.lower().endswith('.jpg') or image_url.lower().endswith('.jpeg'):
                            content_type = 'image/jpeg'
                        elif image_url.lower().endswith('.png'):
                            content_type = 'image/png'
                        elif image_url.lower().endswith('.gif'):
                            content_type = 'image/gif'
                        elif image_url.lower().endswith('.webp'):
                            content_type = 'image/webp'
                        else:
                            content_type = 'image/jpeg'  # Default to jpeg
                    
                    # Encode the image as base64
                    import base64
                    image_data = base64.b64encode(image_response.content).decode('utf-8')
                    
                    # Add the image to the content
                    content.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": content_type,
                            "data": image_data
                        }
                    })
                    
                    log_info("Successfully added image to Claude API request")
                    
                except Exception as e:
                    log_error(f"Error downloading or processing image: {str(e)}")
                    # Continue with text-only analysis if image processing fails
                    log_info("Continuing with text-only analysis")
            
            payload = {
                "model": CLAUDE_MODEL,
                "messages": [
                    {"role": "user", "content": content}
                ],
                "max_tokens": 300,
                "temperature": 0.3
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            response.raise_for_status()
            result = response.json()
            
            # Get the plain text response from Claude's response format
            message_content = result.get("content", [{}])[0].get("text", "")
            
            # Remove any thinking sections from the response
            analysis = self._remove_thinking_section(message_content)
            
            log_debug(f"Claude analysis: {analysis}")
            
            return {
                "analysis": analysis,
                "response_time": 0.0,  # Claude doesn't provide timing info
                "includes_image": image_url is not None
            }
            
        except Exception as e:
            log_error(f"Error in Claude analysis: {str(e)}")
            return {"error": str(e), "analysis": f"Error: {str(e)}"}
            
    def analyze_with_ai(self, text: str, prompt: str = None, image_url: str = None) -> Dict[str, Any]:
        """
        Analyze text using AI, optionally with an image for Claude provider.
        
        Args:
            text (str): Text to analyze
            prompt (str, optional): Custom prompt for the AI.
            image_url (str, optional): URL of an image to include in the analysis (Claude only).
            
        Returns:
            dict: AI analysis results with plain text analysis
        """
        if self.provider.lower() == 'ollama':
            log_info("Using Ollama for tweet analysis")
            # Ollama doesn't support image analysis, so we ignore the image_url
            if image_url:
                log_info("Image analysis not supported by Ollama, analyzing text only")
            return self.analyze_with_ollama(text, prompt)
        elif self.provider.lower() == 'claude':
            log_info("Using Claude for tweet analysis")
            if image_url:
                log_info(f"Including image in Claude analysis: {image_url}")
            return self.analyze_with_claude(text, prompt, image_url)
        else:
            # Default to Ollama if provider is not recognized
            log_info(f"Unknown provider '{self.provider}', defaulting to Ollama for tweet analysis")
            return self.analyze_with_ollama(text, prompt)
    
    def analyze_tweet(self, tweet_content: str, use_ai: bool = True, custom_prompt: str = None, image_url: str = None) -> Dict[str, Any]:
        """
        Analyze a tweet and return the analysis.
        
        Args:
            tweet_content (str): Tweet content
            use_ai (bool, optional): Whether to use AI analysis. Defaults to True.
            custom_prompt (str, optional): Custom prompt for AI analysis. Defaults to None.
            image_url (str, optional): URL of an image to include in the analysis (Claude only). Defaults to None.
            
        Returns:
            dict: Analysis results containing the analysis text
        """
        # If not using AI, return a simple message
        if not use_ai:
            return {"analysis": "No AI analysis performed"}
        
        # Check if we have an image and log it
        if image_url:
            log_info(f"Tweet has image for analysis: {image_url}")
            
        # Use AI to analyze the tweet
        ai_result = self.analyze_with_ai(tweet_content, custom_prompt, image_url)
        
        # Log the analysis
        analysis = ai_result.get("analysis", "No analysis provided")
        log_info(f"AI analysis completed")
        log_debug(f"AI analysis: {analysis}")
        
        return ai_result

    def _remove_thinking_section(self, text):
        """
        Remove any thinking sections from the AI response.
        
        Args:
            text (str): The AI response text
            
        Returns:
            str: The response with thinking sections removed
        """
        # Check if the text contains a thinking section
        thinking_pattern = r'<think>.*?</think>'
        text = re.sub(thinking_pattern, '', text, flags=re.DOTALL)
        
        # Remove any remaining tags that might be present
        text = re.sub(r'<[^>]+>', '', text)
        
        # Clean up any extra whitespace that might be left
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text

# For backward compatibility
def analyze_tweet(tweet_content):
    """Analyze a tweet (co  nvenience function for backward compatibility)."""
    analyzer = AnalyzerService()
    return analyzer.analyze_tweet(tweet_content).get("analysis", "No analysis available")