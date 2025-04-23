#!/usr/bin/env python
"""
Test script to verify Ollama connection and deepseek-r1 model availability.
"""
import requests
import json
import sys

def test_ollama_models():
    """Check available Ollama models."""
    print("Testing Ollama connection...")
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=10)
        print(f"Status code: {response.status_code}")
        if response.status_code == 200:
            models = response.json().get("models", [])
            print(f"Available models: {len(models)}")
            for model in models:
                print(f" - {model.get('name')}")
            
            # Check if deepseek-r1 is available (case insensitive check)
            has_deepseek = any(model.get('name').lower().startswith('deepseek-r1') for model in models)
            if has_deepseek:
                print("\nDeepSeek-R1 model is available! ✓")
            else:
                print("\nDeepSeek-R1 model is NOT available! ✗")
                print("You might need to pull it first with: 'ollama pull deepseek-r1'")
        else:
            print(f"Error: Received status code {response.status_code}")
    except Exception as e:
        print(f"Error connecting to Ollama: {str(e)}")
        return False
    
    return True

def test_ollama_chat():
    """Try a simple chat request with the deepseek-r1 model."""
    try:
        payload = {
            "model": "DeepSeek-R1",
            "messages": [
                {"role": "user", "content": "What is the capital of France?"}
            ],
            "stream": False
        }
        
        print("\nTesting chat with DeepSeek-R1 model...")
        response = requests.post(
            "http://localhost:11434/api/chat", 
            json=payload,
            timeout=15
        )
        
        print(f"Status code: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print("\nResponse received! ✓")
            content = result.get("message", {}).get("content", "")
            print(f"Response: {content[:100]}...")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Error using Ollama chat: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    if test_ollama_models():
        test_ollama_chat()
    else:
        print("Skipping chat test due to model check failure")
        sys.exit(1)