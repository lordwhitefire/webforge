"""
WebForge MCP Common Library
Shared utilities used by all MCPs.

Every MCP in /mcp/ imports from this module.
"""

import os
import json
import time
import hashlib
from pathlib import Path
from datetime import datetime, timezone

# Paths
WEBFORGE_ROOT = Path(os.path.expanduser("~/webforge"))
SKILLS_DIR = WEBFORGE_ROOT / "skills"
LOGS_DIR = WEBFORGE_ROOT / "logs"
REGISTRY_FILE = WEBFORGE_ROOT / "REGISTRY.md"
LAWS_FILE = WEBFORGE_ROOT / "LAWS.md"
AREAS_FILE = WEBFORGE_ROOT / "AREAS.md"


def get_project_root() -> Path:
    """
    Get the current project root.

    Project path is set via WEBFORGE_PROJECT environment variable.
    If not set, defaults to current working directory.

    Memory and project-specific files go HERE, not in WebForge.
    WebForge is just the system — it does not own project data.
    """
    project = os.environ.get("WEBFORGE_PROJECT")
    if project:
        return Path(project).expanduser().resolve()
    return Path.cwd().resolve()


def get_project_memory_dir() -> Path:
    """Memory lives in the project, not in WebForge."""
    mem = get_project_root() / "memory"
    mem.mkdir(parents=True, exist_ok=True)
    return mem


def get_project_logs_dir() -> Path:
    """Project-specific logs (audit, bugs, progress) live in the project."""
    logs = get_project_root() / ".webforge" / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    return logs


# Backward-compat: MEMORY_DIR points to project memory (not WebForge memory)
# Old code that imports MEMORY_DIR will now write to the project folder.
MEMORY_DIR = get_project_memory_dir()

# 300-line rule (Law 2)
MEMORY_MAX_LINES = 300
MEMORY_SPLIT_THRESHOLD = 240  # 80% of 300
SKILL_MAX_LINES = 300


def utc_now() -> str:
    """Return ISO 8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


def write_log(mcp_name: str, agent: str, action: str, details: dict = None):
    """Append to the audit log (Law 6 — Real-Time Documentation).

    Logs go to the project's .webforge/logs/ folder, not WebForge's.
    """
    log_dir = get_project_logs_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"audit-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.log"
    entry = {
        "timestamp": utc_now(),
        "mcp": mcp_name,
        "agent": agent,
        "action": action,
        "details": details or {},
    }
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def count_lines(file_path: Path) -> int:
    """Count lines in a file (for Law 2 — 300-line rule)."""
    if not file_path.exists():
        return 0
    with open(file_path, "r", encoding="utf-8") as f:
        return sum(1 for _ in f)


def ask_developer(question: str, agent: str, area: str = "") -> str:
    """
    Law 5 — No Inference. Ever.
    Print a question for the developer and wait for an answer.
    The agent must STOP and wait.
    """
    print("\n" + "=" * 60)
    print(f"[{agent}] QUESTION FOR DEVELOPER" + (f" (area {area})" if area else ""))
    print("=" * 60)
    print(question)
    print("=" * 60)
    print("Type your answer below (or 'skip' to defer):")
    answer = input("> ").strip()
    write_log("CEO-Communication", agent, "asked_developer",
              {"question": question, "answer": answer, "area": area})
    return answer


def notify_hermes(message: str, from_agent: str):
    """Send a message to Hermes (the scheduler)."""
    write_log("Pipeline", from_agent, "notified_hermes", {"message": message})


def check_law_5(decision_made: bool, question: str, agent: str, area: str = "") -> str:
    """
    Implement Law 5: No inference.
    If the decision has not been made, stop and ask.
    Returns the developer's answer.
    """
    if not decision_made:
        return ask_developer(question, agent, area)
    return ""


def make_id(text: str) -> str:
    """Generate a stable ID from text."""
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:8]


class McpResult:
    """Standard result envelope returned by every MCP."""
    def __init__(self, ok: bool, data: dict = None, error: str = ""):
        self.ok = ok
        self.data = data or {}
        self.error = error

    def to_dict(self):
        return {"ok": self.ok, "data": self.data, "error": self.error}

    def __repr__(self):
        if self.ok:
            return f"McpResult(ok=True, data={self.data})"
        return f"McpResult(ok=False, error={self.error})"


def success(data: dict = None) -> McpResult:
    return McpResult(ok=True, data=data)


def fail(error: str) -> McpResult:
    return McpResult(ok=False, error=error)
