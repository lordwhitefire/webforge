#!/usr/bin/env python3
"""
AI Client — calls OpenCode CLI for AI reasoning.

Uses a persistent OpenCode server to avoid cold-start overhead.
Each `opencode run` from a script normally takes 5-60s because it
re-initializes everything. With `opencode serve` + `--attach`, calls
are nearly instant because the server stays warm.

PRINCIPLE: The script is the body. OpenCode is the brain.
The script does deterministic work (create task, route, notify).
When AI reasoning is needed, the script calls `opencode run --attach`
which connects to the already-running server. No API key needed.

Server lifecycle:
  - start_server(): starts `opencode serve` in background (once)
  - ask_opencode(): calls `opencode run --attach http://localhost:PORT`
  - stop_server(): kills the background server (on exit)
"""

import subprocess
import os
import json
import time
import signal
import atexit
from pathlib import Path

# ── Configuration ──
OPENCODE_PORT = 4096
OPENCODE_HOST = "127.0.0.1"
OPENCODE_URL = f"http://{OPENCODE_HOST}:{OPENCODE_PORT}"

# Free models (tried in order)
FREE_MODELS = [
    "opencode/deepseek-v4-flash-free",
    "opencode/north-mini-code-free",
    "opencode/mimo-v2.5-free",
    "opencode/nemotron-3-ultra-free",
    "opencode/big-pickle",
]

# Server process (kept alive across calls)
_server_process = None


def _find_opencode() -> str:
    """Find the opencode binary."""
    candidates = [
        os.path.expanduser("~/.opencode/bin/opencode"),
        "/usr/local/bin/opencode",
        "/usr/bin/opencode",
    ]
    for c in candidates:
        if os.path.isfile(c) and os.access(c, os.X_OK):
            return c

    result = subprocess.run(["which", "opencode"], capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout.strip()

    return ""


def _get_default_model() -> str:
    """Get the default model to use."""
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
    return FREE_MODELS[0]


def _get_env() -> dict:
    """Get environment with opencode in PATH."""
    env = os.environ.copy()
    opencode_dir = os.path.expanduser("~/.opencode/bin")
    env["PATH"] = f"{opencode_dir}:{env.get('PATH', '')}"
    return env


# ── Server management ──

def start_server(port: int = OPENCODE_PORT) -> bool:
    """
    Start the OpenCode server in background.
    Call this once at startup. Subsequent ask_opencode() calls will be fast.
    """
    global _server_process

    if _server_process is not None:
        return True  # Already running

    # Check if a server is already running on this port
    if _is_server_running(port):
        return True

    opencode_bin = _find_opencode()
    if not opencode_bin:
        return False

    cmd = [
        opencode_bin,
        "serve",
        "--port", str(port),
        "--hostname", OPENCODE_HOST,
    ]

    try:
        _server_process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=_get_env(),
            # Start in background — don't block
            start_new_session=True,
        )

        # Wait for server to be ready (max 30 seconds)
        for _ in range(30):
            if _is_server_running(port):
                # Register cleanup on exit
                atexit.register(stop_server)
                return True
            time.sleep(1)

        # Server didn't start in time
        return False

    except Exception:
        return False


def stop_server():
    """Stop the OpenCode server."""
    global _server_process
    if _server_process is not None:
        try:
            _server_process.terminate()
            _server_process.wait(timeout=5)
        except:
            try:
                _server_process.kill()
            except:
                pass
        _server_process = None


def _is_server_running(port: int) -> bool:
    """Check if the OpenCode server is running on the given port."""
    try:
        import urllib.request
        req = urllib.request.Request(f"http://{OPENCODE_HOST}:{port}/")
        req.add_header("User-Agent", "webforge-ai-client")
        urllib.request.urlopen(req, timeout=2)
        return True
    except:
        # Connection refused = not running
        # But also check if process is alive
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            result = s.connect_ex((OPENCODE_HOST, port))
            s.close()
            return result == 0
        except:
            return False


# ── Main function: ask OpenCode for AI reasoning ──

def ask_opencode(prompt: str, model: str = "", timeout: int = 60) -> dict:
    """
    Call OpenCode to get AI reasoning.

    Uses --attach to connect to a running server (fast, no cold start).
    Falls back to direct `opencode run` if no server is running.

    Args:
        prompt: The prompt to send to the AI
        model: Model to use (default: free model)
        timeout: Max seconds to wait

    Returns:
        {
            "status": "ok" | "error",
            "response": str,
            "model": str,
        }
    """
    opencode_bin = _find_opencode()

    if not opencode_bin:
        return {
            "status": "error",
            "response": "",
            "error": "OpenCode not found. Install: curl -fsSL https://opencode.ai/install | bash",
        }

    if not model:
        model = _get_default_model()

    env = _get_env()

    # Build command — try --attach first (fast, uses warm server)
    if _is_server_running(OPENCODE_PORT):
        cmd = [
            opencode_bin,
            "run",
            prompt,
            "--auto",
            "-m", model,
            "--attach", OPENCODE_URL,
        ]
    else:
        # No server running — use direct run (slower but works)
        cmd = [
            opencode_bin,
            "run",
            prompt,
            "--auto",
            "-m", model,
        ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )

        if result.returncode == 0:
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
            "error": f"OpenCode timed out after {timeout}s",
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
    """Simple wrapper — returns just the response text."""
    result = ask_opencode(prompt, timeout=timeout)
    if result["status"] == "ok":
        return result["response"]
    return ""


# ── CLI for testing ──
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("AI Client — OpenCode CLI wrapper with persistent server")
        print("Usage: python ai_client.py <prompt>")
        print("       python ai_client.py --start-server")
        print("       python ai_client.py --stop-server")
        print()
        print("To avoid cold-start overhead:")
        print("  1. Start server once: python ai_client.py --start-server")
        print("  2. All subsequent calls are fast (uses --attach)")
        print()
        print(f"Server URL: {OPENCODE_URL}")
        print(f"Default model: {_get_default_model()}")
        sys.exit(1)

    if sys.argv[1] == "--start-server":
        print(f"Starting OpenCode server on {OPENCODE_URL}...")
        if start_server():
            print(f"✅ Server running at {OPENCODE_URL}")
            print("Subsequent ask_opencode() calls will be fast.")
            print("Press Ctrl+C to stop.")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                stop_server()
                print("Server stopped.")
        else:
            print("❌ Failed to start server.")
        sys.exit(0)

    if sys.argv[1] == "--stop-server":
        stop_server()
        print("Server stopped.")
        sys.exit(0)

    prompt = " ".join(sys.argv[1:])
    print(f"Prompt: {prompt[:80]}...")
    print(f"Model: {_get_default_model()}")
    print(f"Server: {'running' if _is_server_running(OPENCODE_PORT) else 'not running (cold start)'}")
    print()

    start = time.time()
    result = ask_opencode(prompt)
    elapsed = time.time() - start

    if result["status"] == "ok":
        print(f"=== AI RESPONSE ({elapsed:.1f}s) ===")
        print(result["response"])
    else:
        print(f"ERROR ({elapsed:.1f}s): {result.get('error', 'unknown')}")
