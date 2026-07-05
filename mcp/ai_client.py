#!/usr/bin/env python3
"""
WebForge AI Client — supports DeepSeek v4 Flash + GLM 4.5 Flash.

Two backends:
  1. DeepSeek v4 Flash via OpenRouter (REST API)
     - Good for: code generation, debugging, complex reasoning
     - API key: DEEPSEEK_API_KEY env var (OpenRouter key)

  2. GLM 4.5 Flash via z-ai-web-dev-sdk (Node.js CLI)
     - Good for: documentation, summarization, quick answers
     - No API key needed (SDK is pre-authenticated)

Usage:
    from ai_client import ask_ai
    result = ask_ai("Write a hello world function", model="deepseek")
    print(result["response"])

Model selection:
    - "deepseek" → deepseek/deepseek-v4-flash (via OpenRouter)
    - "glm"      → glm-4.5-flash (via z-ai SDK)
    - "auto"     → picks based on task type (code→deepseek, docs→glm)
"""

import os
import sys
import json
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))
from common import write_log, utc_now


# ── Configuration ──

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek/deepseek-v4-flash"
GLM_MODEL = "glm-4.5-flash"

# Task type → model mapping (for "auto" mode)
TASK_MODEL_MAP = {
    "code": "deepseek",       # code generation → DeepSeek
    "debug": "deepseek",      # debugging → DeepSeek
    "refactor": "deepseek",   # refactoring → DeepSeek
    "review": "deepseek",     # code review → DeepSeek
    "research": "glm",        # research → GLM
    "docs": "glm",            # documentation → GLM
    "plan": "glm",            # planning → GLM
    "answer": "glm",          # general questions → GLM
    "test": "deepseek",       # test writing → DeepSeek
}


def get_deepseek_key() -> str:
    """Get the DeepSeek (OpenRouter) API key from environment."""
    # Check env var
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if key:
        return key

    # Check .env file
    env_file = Path.cwd() / ".env"
    if not env_file.exists():
        env_file = Path(os.environ.get("WEBFORGE_PROJECT", "")) / ".env"
    if env_file.exists():
        for line in env_file.read_text().split("\n"):
            if line.startswith("DEEPSEEK_API_KEY="):
                return line.split("=", 1)[1].strip()

    return ""


def ask_deepseek(prompt: str, system: str = "", timeout: int = 120) -> dict:
    """
    Call DeepSeek v4 Flash via OpenRouter.

    Args:
        prompt: The user prompt
        system: Optional system prompt
        timeout: Timeout in seconds

    Returns:
        {"status": "ok", "response": "...", "model": "...", "usage": {...}}
        {"status": "error", "error": "..."}
    """
    api_key = get_deepseek_key()
    if not api_key:
        return {"status": "error", "error": "DEEPSEEK_API_KEY not set"}

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "max_tokens": 4096,
        "temperature": 0.7,
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://webforge.local",
        "X-Title": "WebForge",
    }

    try:
        req = urllib.request.Request(
            OPENROUTER_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        response_text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        usage = data.get("usage", {})

        write_log("AIClient", "System", "ask_deepseek", {
            "model": DEEPSEEK_MODEL,
            "prompt_chars": len(prompt),
            "response_chars": len(response_text),
            "tokens": usage.get("total_tokens", 0),
        })

        return {
            "status": "ok",
            "response": response_text,
            "model": data.get("model", DEEPSEEK_MODEL),
            "usage": usage,
        }

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        return {"status": "error", "error": f"HTTP {e.code}: {error_body[:200]}"}
    except urllib.error.URLError as e:
        return {"status": "error", "error": f"Network error: {e.reason}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def ask_glm(prompt: str, system: str = "", timeout: int = 120) -> dict:
    """
    Call GLM 4.5 Flash via z-ai-web-dev-sdk (Node.js CLI).

    Args:
        prompt: The user prompt
        system: Optional system prompt
        timeout: Timeout in seconds

    Returns:
        {"status": "ok", "response": "...", "model": "glm-4.5-flash"}
        {"status": "error", "error": "..."}
    """
    # Build messages array
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    messages_json = json.dumps(messages)

    # Build the Node.js script (no f-string to avoid brace conflicts)
    node_script = """import ZAI from 'z-ai-web-dev-sdk';

async function main() {
    const zai = await ZAI.create();
    const completion = await zai.chat.completions.create({
        messages: MESSAGES_PLACEHOLDER,
        model: 'glm-4.5-flash',
        max_tokens: 4096,
        thinking: { type: 'disabled' }
    });
    console.log(JSON.stringify({
        status: 'ok',
        response: completion.choices[0]?.message?.content || '',
        model: completion.model || 'glm-4.5-flash',
        usage: completion.usage || {}
    }));
}

main().catch(e => console.log(JSON.stringify({
    status: 'error',
    error: e.message
})));
""".replace("MESSAGES_PLACEHOLDER", messages_json)

    # Find the project root (where node_modules is)
    project_root = os.environ.get("WEBFORGE_PROJECT", str(Path.cwd()))
    project_root = Path(project_root).resolve()

    # Write the script to the project directory (so Node.js can find node_modules)
    scripts_dir = project_root / ".webforge" / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    script_path = scripts_dir / "wf_glm_call.mjs"
    script_path.write_text(node_script, encoding="utf-8")

    try:
        result = subprocess.run(
            ["node", str(script_path)],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(project_root),
        )

        if result.returncode != 0:
            return {
                "status": "error",
                "error": f"Node.js failed: {result.stderr[:200]}",
            }

        # Parse the output
        output = result.stdout.strip()
        data = json.loads(output)

        if data.get("status") == "ok":
            write_log("AIClient", "System", "ask_glm", {
                "model": GLM_MODEL,
                "prompt_chars": len(prompt),
                "response_chars": len(data.get("response", "")),
            })

        return data

    except subprocess.TimeoutExpired:
        return {"status": "error", "error": f"GLM call timed out ({timeout}s)"}
    except json.JSONDecodeError as e:
        return {"status": "error", "error": f"Failed to parse GLM response: {e}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}
    finally:
        # Clean up temp file
        if script_path.exists():
            script_path.unlink()


def ask_ai(prompt: str, model: str = "auto", system: str = "",
           task_type: str = None, timeout: int = 120) -> dict:
    """
    Call an AI model with automatic model selection.

    Args:
        prompt: The prompt to send
        model: "deepseek", "glm", or "auto"
        system: Optional system prompt
        task_type: One of code/debug/refactor/review/research/docs/plan/answer/test
                   (used for "auto" model selection)
        timeout: Timeout in seconds

    Returns:
        {"status": "ok", "response": "...", "model": "...", "usage": {...}}
        {"status": "error", "error": "..."}
    """
    # Auto-select model based on task type
    if model == "auto":
        if task_type and task_type in TASK_MODEL_MAP:
            model = TASK_MODEL_MAP[task_type]
        else:
            model = "deepseek"  # default

    if model == "deepseek":
        return ask_deepseek(prompt, system, timeout)
    elif model == "glm":
        return ask_glm(prompt, system, timeout)
    else:
        return {"status": "error", "error": f"Unknown model: {model}"}


def info() -> dict:
    return {
        "id": "m-ai-client",
        "name": "AI Client",
        "tier": 1,
        "owner": "System",
        "job": "Calls DeepSeek v4 Flash + GLM 4.5 Flash for AI reasoning",
        "models": {
            "deepseek": DEEPSEEK_MODEL,
            "glm": GLM_MODEL,
        },
        "deepseek_key_set": bool(get_deepseek_key()),
    }


# ── CLI ──

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("AI Client — DeepSeek + GLM")
        print("Usage: python ai_client.py <command>")
        print()
        print("Commands:")
        print("  info                          Show config")
        print("  test [model]                  Test a model (deepseek/glm/both)")
        print("  ask <model> <prompt>          Ask a question")
        print("  ask-code <prompt>             Ask DeepSeek to write code")
        print("  ask-docs <prompt>             Ask GLM to write docs")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "info":
        print(json.dumps(info(), indent=2))

    elif cmd == "test":
        model = sys.argv[2] if len(sys.argv) > 2 else "both"
        prompt = "Say hello in one word."

        if model in ("deepseek", "both"):
            print("=== DeepSeek v4 Flash ===")
            r = ask_deepseek(prompt)
            print(f"Status: {r['status']}")
            if r["status"] == "ok":
                print(f"Response: {r['response']}")
                print(f"Model: {r['model']}")
                print(f"Tokens: {r.get('usage', {}).get('total_tokens', '?')}")
            else:
                print(f"Error: {r['error']}")
            print()

        if model in ("glm", "both"):
            print("=== GLM 4.5 Flash ===")
            r = ask_glm(prompt)
            print(f"Status: {r['status']}")
            if r["status"] == "ok":
                print(f"Response: {r['response']}")
                print(f"Model: {r['model']}")
            else:
                print(f"Error: {r['error']}")

    elif cmd == "ask":
        if len(sys.argv) < 4:
            print("Usage: ask <model> <prompt>")
            sys.exit(1)
        model = sys.argv[2]
        prompt = " ".join(sys.argv[3:])
        r = ask_ai(prompt, model=model)
        if r["status"] == "ok":
            print(r["response"])
        else:
            print(f"Error: {r['error']}", file=sys.stderr)
            sys.exit(1)

    elif cmd == "ask-code":
        if len(sys.argv) < 3:
            print("Usage: ask-code <prompt>")
            sys.exit(1)
        prompt = " ".join(sys.argv[2:])
        r = ask_ai(prompt, model="deepseek", task_type="code")
        if r["status"] == "ok":
            print(r["response"])
        else:
            print(f"Error: {r['error']}", file=sys.stderr)
            sys.exit(1)

    elif cmd == "ask-docs":
        if len(sys.argv) < 3:
            print("Usage: ask-docs <prompt>")
            sys.exit(1)
        prompt = " ".join(sys.argv[2:])
        r = ask_ai(prompt, model="glm", task_type="docs")
        if r["status"] == "ok":
            print(r["response"])
        else:
            print(f"Error: {r['error']}", file=sys.stderr)
            sys.exit(1)

    else:
        print(f"Unknown command: {cmd}")
