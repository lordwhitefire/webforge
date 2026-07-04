#!/usr/bin/env python3
"""
AI Client — direct API caller for WebForge agents.

Replaces the old pipeline handoff (write prompt file → wait → resume).

Supports both DeepSeek and Z.ai (GLM) APIs with OpenAI-compatible format.
DeepSeek is preferred. Falls back to Z.ai if DeepSeek key is missing.

PRINCIPLE: The script controls the AI call. Synchronous blocking call.
No file writing, no pipeline signals, no resume needed.
"""

import json
import os
import time
import urllib.request
import urllib.error
from pathlib import Path

# ── Provider Configuration ──

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"

ZAI_API_URL = "https://api.z.ai/api/paas/v4/chat/completions"
ZAI_MODEL = "glm-4-flash"

# ── Key Loading ──

def _load_deepseek_key() -> str:
    """Load DeepSeek API key from env or config file."""
    env_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if env_key:
        return env_key
    key_file = Path.home() / ".config" / "opencode" / "deepseek-key.txt"
    if key_file.exists():
        return key_file.read_text(encoding="utf-8").strip()
    return ""


def _load_zai_key() -> str:
    """Load Z.ai API key from config file."""
    key_file = Path.home() / ".config" / "opencode" / "zai-key.txt"
    if key_file.exists():
        return key_file.read_text(encoding="utf-8").strip()
    return ""


def _pick_provider() -> tuple:
    """
    Pick the best available provider.
    Returns (url, api_key, model_name) or raises RuntimeError if none available.
    """
    # Try DeepSeek first
    ds_key = _load_deepseek_key()
    if ds_key:
        return (DEEPSEEK_API_URL, ds_key, DEEPSEEK_MODEL, "deepseek")

    # Fall back to Z.ai
    zai_key = _load_zai_key()
    if zai_key:
        return (ZAI_API_URL, zai_key, ZAI_MODEL, "zai")

    raise RuntimeError(
        "No AI API key found. Configure one of:\n"
        "  - DeepSeek: set DEEPSEEK_API_KEY env var or create ~/.config/opencode/deepseek-key.txt\n"
        "  - Z.ai: ensure ~/.config/opencode/zai-key.txt exists"
    )


# ── API Call ──

def call_ai(
    messages: list,
    model: str = None,
    temperature: float = 0.7,
    max_tokens: int = 2000,
    timeout: int = 120,
) -> str:
    """
    Call the AI API with the given messages.

    This is a SYNCHRONOUS blocking call. The agent waits for the response.

    Args:
        messages: List of {"role": "...", "content": "..."} dicts
        model: Override model name (optional)
        temperature: 0.0 to 1.0 (default 0.7)
        max_tokens: Max tokens in response (default 2000)
        timeout: Request timeout in seconds (default 120)

    Returns:
        The response text content from the AI

    Raises:
        RuntimeError: If API call fails or no key configured
    """
    url, api_key, model_name, provider = _pick_provider()
    model = model or model_name

    body = json.dumps({
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        return result["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"AI API error ({provider}, {e.code}): {error_body[:500]}"
        )
    except (KeyError, IndexError) as e:
        raise RuntimeError(
            f"AI API unexpected response format ({provider}): {e}"
        )
    except urllib.error.URLError as e:
        raise RuntimeError(
            f"AI API connection error ({provider}): {e.reason}"
        )


def call_ai_json(
    system_prompt: str,
    user_instruction: str,
    model: str = None,
    temperature: float = 0.3,
    max_tokens: int = 2000,
    timeout: int = 120,
) -> dict:
    """
    Call the AI and parse the response as JSON.

    This is the primary method agents should use when they need structured
    responses from the AI (classifications, routing decisions, etc.)

    Args:
        system_prompt: The system prompt describing the agent's role
        user_instruction: The user's instruction/question
        model: Override model name
        temperature: Lower = more deterministic (default 0.3)
        max_tokens: Max tokens in response
        timeout: Request timeout

    Returns:
        dict parsed from AI's JSON response, or {"status": "error", ...} on failure
    """
    messages = [
        {
            "role": "system",
            "content": (
                f"{system_prompt}\n\n"
                f"ALWAYS respond with valid JSON only. "
                f"No markdown, no code fences, no explanation — just the JSON object."
            ),
        },
        {"role": "user", "content": user_instruction},
    ]

    try:
        text = call_ai(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )
    except RuntimeError as e:
        return {"status": "error", "message": str(e)}

    # Parse JSON from response (strip markdown fences if present)
    text = text.strip()
    if text.startswith("```"):
        # Remove markdown code fences
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        return {
            "status": "error",
            "message": f"AI response was not valid JSON: {e}\n\nRaw response:\n{text[:500]}",
        }
