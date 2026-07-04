#!/usr/bin/env python3
"""
Pipeline — Hook system for agent execution.

THE PIPELINE IS THE LAUNCHER. It runs agent scripts and shows their output.

What the pipeline does:
  1. Detects @AgentName or /talk in user messages
  2. Creates a session dir for tracking
  3. Runs the agent script as a subprocess
  4. Shows output in real-time
  5. Session cleanup on completion

What the pipeline does NOT do:
  - Call AI (agents do that directly via ai_client.py)
  - Resume/handoff (agents use synchronous API calls)
  - Route between agents (scripts call each other directly)

FLOW:
  trigger: run script → script runs (may call AI inline) → script finishes → done

USAGE:
  python3 pipeline.py trigger <agent_name> <message>
  python3 pipeline.py status [session_id]
  python3 pipeline.py <@AgentName message>
"""

import json
import sys
import os
import re
import time
import uuid
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import write_log, utc_now, success, fail, McpResult

AGENTS_DIR = Path.home() / "webforge" / "agents"
SESSION_BASE = Path("/tmp")
SESSION_TTL = 3600


# ── Session Management ──

def create_session(user_message: str, agent_name: str) -> tuple:
    """Create a new session directory. Returns (session_dir, session_id)."""
    session_id = uuid.uuid4().hex[:12]
    session_dir = SESSION_BASE / f"wf-sess-{session_id}"
    session_dir.mkdir(parents=True, exist_ok=True)

    session_data = {
        "session_id": session_id,
        "agent_name": agent_name,
        "user_message": user_message,
        "started_at": utc_now(),
        "status": "running",
    }
    with open(session_dir / "session.json", "w", encoding="utf-8") as f:
        json.dump(session_data, f, indent=2)

    return session_dir, session_id


def load_session(session_dir: Path) -> dict:
    """Load session data from a session directory."""
    session_file = session_dir / "session.json"
    if not session_file.exists():
        return {}
    with open(session_file, "r", encoding="utf-8") as f:
        return json.load(f)


def save_session(session_dir: Path, data: dict):
    """Save session data."""
    with open(session_dir / "session.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def find_session(session_id: str) -> Path:
    """Find a session directory by ID."""
    candidate = SESSION_BASE / f"wf-sess-{session_id}"
    if candidate.exists():
        return candidate
    return None


def clean_session(session_dir: Path):
    """Clean up a session directory."""
    if not session_dir or not session_dir.exists():
        return
    try:
        import shutil
        shutil.rmtree(session_dir)
    except Exception as e:
        print(f"  ⚠️  Could not clean session: {e}", file=sys.stderr)


# ── Parsing ──

def parse_agent_message(raw_message: str) -> tuple:
    """
    Parse @AgentName or /talk AgentName from a message.
    Returns (agent_name, message_without_trigger).
    """
    text = raw_message.strip()
    at_match = re.match(r'@(\w[\w-]*)\s*(.*)', text)
    if at_match:
        return at_match.group(1), at_match.group(2).strip()
    talk_match = re.match(r'/talk\s+(\w[\w-]*)\s*(.*)', text, re.IGNORECASE)
    if talk_match:
        return talk_match.group(1), talk_match.group(2).strip()
    return None, raw_message


def find_agent_script(agent_name: str) -> Path:
    """Find the agent script file by name."""
    file_name = re.sub(r'[-\s]', '_', agent_name).lower()
    script = AGENTS_DIR / f"{file_name}.py"
    if script.exists():
        return script
    file_name2 = agent_name.lower().replace(' ', '_').replace('-', '_')
    script2 = AGENTS_DIR / f"{file_name2}.py"
    if script2.exists():
        return script2
    return None


# ── Trigger ──

def trigger(agent_name: str, message: str) -> McpResult:
    """
    Trigger an agent script.

    Runs the script as a subprocess. The script may make direct API calls
    (ai_client.py) which block until the AI responds. The pipeline just
    shows output and waits for the script to finish.
    """
    script = find_agent_script(agent_name)
    if not script:
        return fail(f"Agent not found: @{agent_name}")

    # Create session
    session_dir, session_id = create_session(message, agent_name)

    print(f"  ▶️  Running @{agent_name}")
    print(f"  📁 Session: {session_id}")
    sys.stdout.flush()

    # Run the script
    cmd = [sys.executable, str(script), message]
    env = os.environ.copy()
    env["WF_SESSION_ID"] = session_id
    env["WF_SESSION_DIR"] = str(session_dir)
    env["WEBFORGE_PROJECT"] = os.environ.get("WEBFORGE_PROJECT", str(Path.cwd()))

    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, env=env, bufsize=1,
    )

    # Read stdout until script exits
    for line in iter(process.stdout.readline, ''):
        line = line.rstrip()
        if not line:
            continue
        print(line)
        sys.stdout.flush()

    process.wait()

    # Mark session completed
    session_data = load_session(session_dir)
    session_data["status"] = "completed"
    session_data["return_code"] = process.returncode
    save_session(session_dir, session_data)

    clean_session(session_dir)

    return_code = process.returncode
    if return_code != 0:
        return fail(f"@{agent_name} exited with code {return_code}")

    return success({
        "agent": agent_name,
        "session_id": session_id,
        "status": "completed",
        "return_code": return_code,
    })


# ── Status ──

def status(session_id: str = None) -> McpResult:
    """Check the status of a session or list all active sessions."""
    if session_id:
        session_dir = find_session(session_id)
        if not session_dir:
            return fail(f"Session not found: {session_id}")
        data = load_session(session_dir)
        return success(data)

    sessions = []
    for item in sorted(SESSION_BASE.glob("wf-sess-*")):
        if item.is_dir() and time.time() - item.stat().st_mtime < SESSION_TTL:
            data = load_session(item)
            sessions.append({
                "session_id": item.name.replace("wf-sess-", ""),
                "agent": data.get("agent_name", "?"),
                "status": data.get("status", "?"),
                "age_seconds": int(time.time() - item.stat().st_mtime),
            })

    # Clean old sessions
    for item in SESSION_BASE.glob("wf-sess-*"):
        if item.is_dir() and time.time() - item.stat().st_mtime > SESSION_TTL:
            clean_session(item)

    return success({"sessions": sessions, "count": len(sessions)})


# ── CLI Entry Point ──

def handle_message(raw_message: str) -> str:
    """Main entry point. Detects @AgentName and triggers pipeline."""
    agent_name, message = parse_agent_message(raw_message)
    if agent_name:
        result = trigger(agent_name, message)
        return json.dumps(result.to_dict(), indent=2)
    print("  ℹ️  No agent mentioned. Message goes directly to OpenCode.")
    return json.dumps({"status": "direct", "message": raw_message})


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("WebForge Pipeline — Agent Launcher")
        print()
        print("Usage:")
        print("  python pipeline.py trigger <agent_name> <message>")
        print("  python pipeline.py status [session_id]")
        print("  python pipeline.py <@AgentName message>")
        print("  python pipeline.py </talk AgentName message>")
        print()
        print("Examples:")
        print("  python pipeline.py trigger hermes 'close task-003'")
        print("  python pipeline.py '@Hermes research the codebase'")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd in ("trigger", "talk") and len(sys.argv) >= 4:
        agent_name = sys.argv[2].lstrip("@")
        message = " ".join(sys.argv[3:])
        result = trigger(agent_name, message)
        print(json.dumps(result.to_dict(), indent=2))

    elif cmd == "status":
        result = status(sys.argv[2] if len(sys.argv) >= 3 else None)
        print(json.dumps(result.to_dict(), indent=2))

    elif cmd.startswith("@") or cmd.lower() == "/talk":
        raw = " ".join(sys.argv[1:])
        result = handle_message(raw)
        print(result)

    elif cmd == "resume":
        print("  ℹ️  Resume is no longer needed. Agents call AI directly now.")
        print("  ℹ️  Just run the agent fresh: pipeline.py trigger <agent> <message>")
        sys.exit(0)

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
