# -*- coding: utf-8 -*-
"""
Ollama API Communication
Handles connection checking, model listing, and chat requests
"""
from typing import List, Dict
from .dependencies import REQUESTS_AVAILABLE, ollama_available, available_models

# Update global state
_ollama_available = ollama_available
_available_models = available_models


def check_ollama_connection(api_url: str) -> bool:
    """Check if Ollama is running and accessible"""
    global _ollama_available
    if not REQUESTS_AVAILABLE:
        return False
    
    try:
        import requests
        response = requests.get(f"{api_url}/api/tags", timeout=2)
        if response.status_code == 200:
            _ollama_available = True
            return True
    except Exception:
        pass
    
    _ollama_available = False
    return False


def get_available_models(api_url: str) -> List[str]:
    """Get list of available Ollama models"""
    global _available_models
    if not REQUESTS_AVAILABLE:
        return []
    
    try:
        import requests
        response = requests.get(f"{api_url}/api/tags", timeout=5)
        if response.status_code == 200:
            data = response.json()
            models = []
            if "models" in data:
                for model in data["models"]:
                    model_name = model.get("name", "")
                    if model_name:
                        models.append(model_name)
            _available_models = models
            return models
    except Exception as e:
        pass
    
    return []


def chat_with_ollama(api_url: str, model: str, messages: List[Dict], settings: Dict, callback):
    """Send chat request to Ollama API"""
    if not REQUESTS_AVAILABLE:
        callback(False, "requests library not installed")
        return
    
    try:
        import requests
        import json
        
        # Prepare the request - use STREAMING for no timeout
        # Add system message if not present to guide the model
        has_system = any(msg.get("role") == "system" for msg in messages)
        if not has_system:
            # Add system message to guide the model
            system_msg = {
                "role": "system",
                "content": "You are a helpful assistant that extracts and displays employee information from documents. When asked to list employee info, extract ALL employee data from the provided document content and display it in a clear, organized format. Include names, license numbers, states, DOBs, positions, status (FT/PT), and personal use (Y/N)."
            }
            messages = [system_msg] + messages
        
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,  # Stream response chunks
            "options": {
                "temperature": 0.3,
                "num_predict": 512,  # Balanced - enough for responses but not too slow
                "num_ctx": 4096,  # Balanced context window - enough for data but faster
            }
        }
        
        # Use streaming to avoid timeout - increased timeout for larger contexts
        response = requests.post(
            f"{api_url}/api/chat",
            json=payload,
            stream=True,
            timeout=120  # Increased to 120 seconds for larger contexts
        )
        
        if response.status_code == 200:
            full_response = ""
            for line in response.iter_lines():
                if line:
                    try:
                        chunk = json.loads(line)
                        if "message" in chunk and "content" in chunk["message"]:
                            full_response += chunk["message"]["content"]
                        if chunk.get("done", False):
                            break
                    except:
                        continue
            
            if full_response:
                callback(True, full_response)
            else:
                callback(False, "No response from model")
        else:
            callback(False, f"API error: {response.status_code}")
    
    except requests.exceptions.ConnectionError:
        callback(False, "Cannot connect to Ollama. Make sure Ollama is running.")
    except requests.exceptions.Timeout:
        callback(False, "Request timed out starting. Try a smaller/faster model like phi3:mini")
    except Exception as e:
        callback(False, f"Error: {str(e)}")

