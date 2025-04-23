"""
Service for analyzing tweets to determine relevance.
"""
import re
import requests
import json
import os
import time
import random  # Added missing import for random module
from typing import Dict, Any, List, Optional, Union, Callable

from ..config import GROQ_API_KEY, OLLAMA_URL, OLLAMA_MODEL, AI_PROVIDER
from ..utils import log_info, log_error, log_debug

class AnalyzerService:
    """Service for analyzing tweets to determine relevance."""
    
    def __init__(self, api_key=None, threshold=0.7, provider=None, ollama_url=None, ollama_model=None):
        """
        Initialize the analyzer service.
        
        Args:
            api_key (str, optional): API key for cloud AI services. Defaults to config value.
            threshold (float, optional): Confidence threshold for AI analysis. Defaults to 0.7.
            provider (str, optional): AI provider to use ('groq', 'ollama'). Defaults to config value.
            ollama_url (str, optional): URL for Ollama API. Defaults to config value.
            ollama_model (str, optional): Model to use with Ollama. Defaults to config value.
        """
        self.api_key = api_key or GROQ_API_KEY
        self.threshold = threshold
        self.provider = provider or AI_PROVIDER
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
            prompt (str, optional): Custom prompt for the AI. Defaults to a generic relevance prompt.
            max_retries (int): Maximum number of retry attempts (default: 3)
            retry_delay (int): Delay between retries in seconds (default: 2)
            timeout (int): Request timeout in seconds (default: 30)
            
        Returns:
            dict: AI analysis results
        """
        # Default prompt if none provided
        if not prompt:
            prompt = (
                "Analyze the following tweet and determine if it contains important or interesting "
                "information. The tweet should be relevant if it contains news, announcements, "
                "or significant insights. Respond with a JSON object with two fields: "
                "'is_relevant' (boolean) and 'reason' (string explanation)."
            )
            
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
                    "stream": False,
                    "format": "json"
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
                    
                    # Parse the response 
                    try:
                        message_content = result.get("message", {}).get("content", "{}")
                        # Try to parse as JSON, but handle cases where the response might not be perfectly formatted JSON
                        try:
                            ai_result = json.loads(message_content)
                        except json.JSONDecodeError:
                            # If raw response isn't valid JSON, look for JSON pattern in the response
                            import re
                            json_match = re.search(r'\{.*\}', message_content, re.DOTALL)
                            if json_match:
                                try:
                                    ai_result = json.loads(json_match.group(0))
                                except json.JSONDecodeError:
                                    # Last resort: create our own analysis based on keywords
                                    is_relevant = any(kw in message_content.lower() for kw in 
                                                    ['relevant', 'important', 'interesting', 'news', 'announcement'])
                                    ai_result = {
                                        "is_relevant": is_relevant,
                                        "reason": message_content[:200] + "..."  # Truncated response
                                    }
                            else:
                                # Create a basic result if no JSON found
                                is_relevant = any(kw in message_content.lower() for kw in 
                                                ['relevant', 'important', 'interesting', 'news', 'announcement'])
                                ai_result = {
                                    "is_relevant": is_relevant,
                                    "reason": message_content[:200] + "..."  # Truncated response
                                }
                    except Exception as parse_error:
                        log_error(f"Error parsing Ollama response: {str(parse_error)}")
                        ai_result = {"is_relevant": False, "reason": "Error parsing response"}
                    
                    total_duration = time.time() - start_time
                    log_debug(f"Ollama analysis result: {ai_result}")
                    log_info(f"Total analysis time: {total_duration:.2f} seconds (including {retry_count} retries)")
                    
                    return {
                        "is_relevant": ai_result.get("is_relevant", False),
                        "reason": ai_result.get("reason", "No reason provided"),
                        "confidence": 1.0,  # Ollama doesn't provide confidence scores
                        "raw_response": ai_result,
                        "response_time": request_duration,
                        "total_analysis_time": total_duration
                    }
                elif response.status_code == 404:
                    # Model not found
                    log_error(f"Model {self.ollama_model} not found in Ollama. Try pulling it first.")
                    return {"error": f"Model {self.ollama_model} not found", "is_relevant": False, "confidence": 0.0}
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
                            "is_relevant": False, 
                            "confidence": 0.0,
                            "total_analysis_time": total_duration
                        }
                else:
                    # Other errors
                    log_error(f"Ollama request failed with status {response.status_code}: {response.text}")
                    return {"error": f"Request failed with status {response.status_code}", "is_relevant": False, "confidence": 0.0}
                
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
                        "is_relevant": False, 
                        "confidence": 0.0,
                        "total_analysis_time": total_duration
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
                        "is_relevant": False, 
                        "confidence": 0.0,
                        "total_analysis_time": total_duration
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
                        "is_relevant": False, 
                        "confidence": 0.0,
                        "total_analysis_time": total_duration
                    }
    
    def analyze_with_groq(self, text: str, prompt: str = None) -> Dict[str, Any]:
        """
        Analyze text using Groq AI.
        
        Args:
            text (str): Text to analyze
            prompt (str, optional): Custom prompt for the AI. Defaults to a generic relevance prompt.
            
        Returns:
            dict: AI analysis results
        """
        if not self.api_key:
            log_error("No GROQ API key provided for AI analysis")
            return {"error": "No API key", "is_relevant": False, "confidence": 0.0}
            
        # Default prompt if none provided
        if not prompt:
            prompt = (
                "Analyze the following tweet and determine if it contains important or interesting "
                "information. The tweet should be relevant if it contains news, announcements, "
                "or significant insights. Respond with a JSON object with two fields: "
                "'is_relevant' (boolean) and 'reason' (string explanation)."
            )
            
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "llama3-8b-8192",
                "messages": [
                    {"role": "system", "content": "You are an analyzer that evaluates content."},
                    {"role": "user", "content": f"{prompt}\n\nTweet: {text}"}
                ],
                "temperature": 0.3,
                "response_format": {"type": "json_object"}
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            response.raise_for_status()
            result = response.json()
            
            # Parse the JSON response
            ai_response = result.get("choices", [{}])[0].get("message", {}).get("content", "{}")
            ai_result = json.loads(ai_response)
            
            return {
                "is_relevant": ai_result.get("is_relevant", False),
                "reason": ai_result.get("reason", "No reason provided"),
                "confidence": 1.0,  # Groq doesn't provide confidence, so we use 1.0 for now
                "raw_response": ai_result
            }
            
        except Exception as e:
            log_error(f"Error in GROQ analysis: {str(e)}")
            return {"error": str(e), "is_relevant": False, "confidence": 0.0}
    
    def analyze_with_ai(self, text: str, prompt: str = None) -> Dict[str, Any]:
        """
        Analyze text using AI.
        
        Args:
            text (str): Text to analyze
            prompt (str, optional): Custom prompt for the AI. Defaults to a generic relevance prompt.
            
        Returns:
            dict: AI analysis results
        """
        if self.provider.lower() == 'ollama':
            log_info("Using Ollama for tweet analysis")
            return self.analyze_with_ollama(text, prompt)
        else:
            log_info("Using GROQ for tweet analysis")
            return self.analyze_with_groq(text, prompt)
    
    def analyze_tweet(self, tweet_content: str, use_ai: bool = False, custom_prompt: str = None) -> bool:
        """
        Analyze a tweet to determine if it's relevant.
        
        Args:
            tweet_content (str): Tweet content
            use_ai (bool, optional): Whether to use AI analysis. Defaults to False.
            custom_prompt (str, optional): Custom prompt for AI analysis. Defaults to None.
            
        Returns:
            bool: True if the tweet is relevant, False otherwise
        """
        # First, check keyword filters
        keyword_result = self.analyze_with_keywords(tweet_content)
        
        # If not using AI, return the keyword result
        if not use_ai:
            return keyword_result
            
        # If we're using AI, pass it to the AI service
        if keyword_result:
            # Only use AI if keyword filters say it's relevant
            ai_result = self.analyze_with_ai(tweet_content, custom_prompt)
            is_relevant = ai_result.get("is_relevant", False)
            confidence = ai_result.get("confidence", 0.0)
            reason = ai_result.get("reason", "No reason provided")
            
            log_info(f"AI analysis result: {is_relevant} (confidence: {confidence})")
            log_debug(f"AI reason: {reason}")
            
            # Return True if AI agrees with confidence above threshold
            return is_relevant and confidence >= self.threshold
        
        # If keyword filters determined it's not relevant, don't waste API calls
        return False

# For backward compatibility
def analyze_tweet(tweet_content):
    """Analyze a tweet (convenience function for backward compatibility)."""
    analyzer = AnalyzerService()
    analyzer.add_keyword_filter("crypto", True)  # Original implementation checked for "crypto"
    return analyzer.analyze_tweet(tweet_content)