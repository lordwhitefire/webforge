#!/usr/bin/env python3
"""
AI Client — calls OpenCode CLI for AI reasoning.

PRINCIPLE: The script is the body. OpenCode is the brain.
The script does deterministic work (create task, route, notify).
When AI reasoning is needed, the script calls `opencode run` which
uses whatever model is configured in OpenCode (free models work).

This replaces direct API calls (DeepSeek/Z.ai). No API key needed.
OpenCode handles the model, the key, the reasoning.

Usage from agent scripts:
    from ai_client import ask_opencode
    response = ask_opencode("Analyze this message and tell me if it's a bug or feature")
"""

import subprocess
import os
import json
from pathlib import Path


def _find_opencode() -> str:
    """Find the opencode binary."""
    # Check common locations
    candidates = [
        os.path.expanduser("~/.opencode/bin/opencode"),
        "/usr/local/bin/opencode",
        "/usr/bin/opencode",
    ]
    for c in candidates:
        if os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    
    # Try PATH
    result = subprocess.run(["which", "opencode"], capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout.strip()
    
    return ""


def _get_default_model() -> str:
    """Get the default free model."""
    # These are free models available in OpenCode
    # Try them in order of preference
    free_models = [
        "opencode/deepseek-v4-flash-free",
        "opencode/north-mini-code-free",
        "opencode/mimo-v2.5-free",
        "opencode/nemotron-3-ultra-free",
        "opencode/big-pickle",
    ]
    
    # Check if user has a preferred model in config
    config_path = Path.home() / ".config" / "opencode" / "config.json"
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text())
            model = config.get("model", "")
            if model:
                return model
        except:
            pass
    
    # Default to first free model
    return free_models[0]


def ask_opencode(prompt: str, model: str = "", timeout: int = 120) -> dict:
    """
    Call OpenCode CLI to get AI reasoning.
    
    Args:
        prompt: The prompt to send to the AI
        model: Model to use (default: free model)
        timeout: Max seconds to wait (default: 120)
    
    Returns:
        {
            "status": "ok" | "error",
            "response": str,  # AI's response text
            "model": str,     # Model used
        }
    """
    opencode_bin = _find_opencode()
    
    if not opencode_bin:
        return {
            "status": "error",
            "response": "",
            "error": "OpenCode not found. Install it: curl -fsSL https://opencode.ai/install | bash",
        }
    
    if not model:
        model = _get_default_model()
    
    # Build the command
    # opencode run "prompt" --auto -m model
    cmd = [
        opencode_bin,
        "run",
        prompt,
        "--auto",
        "-m", model,
    ]
    
    # Set up environment
    env = os.environ.copy()
    env["PATH"] = f"{os.path.expanduser('~/.opencode/bin')}:{env.get('PATH', '')}"
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        
        if result.returncode == 0:
            # OpenCode returns the AI response in stdout
            response = result.stdout.strip()
            
            # Try to parse as JSON if it looks like JSON
            if response.startswith("{") and response.endswith("}"):
                try:
                    parsed = json.loads(response)
                    if "response" in parsed:
                        response = parsed["response"]
                except:
                    pass
            
            return {
                "status": "ok",
                "response": response,
                "model": model,
            }
        else:
            return {
                "status": "error",
                "response": "",
                "error": result.stderr.strip() or f"OpenCode exited with code {result.returncode}",
                "model": model,
            }
    
    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "response": "",
            "error": f"OpenCode timed out after {timeout}s. Try a simpler prompt or increase timeout.",
            "model": model,
        }
    except Exception as e:
        return {
            "status": "error",
            "response": "",
            "error": str(e),
            "model": model,
        }


def ask_opencode_simple(prompt: str, timeout: int = 60) -> str:
    """
    Simple wrapper — returns just the response text.
    Returns empty string on error.
    """
    result = ask_opencode(prompt, timeout=timeout)
    if result["status"] == "ok":
        return result["response"]
    return ""


# ── CLI for testing ──
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("AI Client — OpenCode CLI wrapper")
        print("Usage: python ai_client.py <prompt>")
        print()
        print("This calls `opencode run` with the prompt and returns the AI's response.")
        print("No API key needed — uses OpenCode's configured model (free models work).")
        sys.exit(1)
    
    prompt = " ".join(sys.argv[1:])
    print(f"Calling OpenCode with prompt: {prompt[:80]}...")
    print(f"Model: {_get_default_model()}")
    print()
    
    result = ask_opencode(prompt)
    if result["status"] == "ok":
        print("=== AI RESPONSE ===")
        print(result["response"])
    else:
        print(f"ERROR: {result.get('error', 'unknown')}")
