#!/usr/bin/env python3
"""
Enforce MCP — the enforcement engine.

PRINCIPLE: Prompts describe. Code enforces.

Every correction the developer makes should produce a Python check file
in .webforge/checks/ — not a .md rule file. The check has a check(project_root)
function that returns pass/fail. It runs automatically in the quality gate
on every task. If it fails, the task is ACTUALLY blocked (lock file, not message).

Three layers of quality:
  1. Existing lint/test/build checks (quality.py)
  2. Enforcement checks from .webforge/checks/*.py (this MCP)
  3. Block on failure with a lock file that task_done() reads

How corrections become enforcement:
  1. Developer says "don't do X, do Y"
  2. /correct creates a .md rule (for the LLM to read)
  3. Meta Engineering's learn() ALSO creates a .py check file
  4. The check file has a check(project_root) function
  5. On every /task-done, enforce.py runs ALL check files
  6. If any fail → lock file written → task_done() refuses
  7. Developer can override with /check-approve (but it's logged)
"""

import os
import sys
import json
import importlib.util
import inspect
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))
from common import write_log, success, fail, utc_now, McpResult, get_project_root
from memory import session_append


def info() -> dict:
    return {
        "id": "m-enforce",
        "name": "Enforce MCP",
        "tier": 1,
        "owner": "Minos",
        "job": "Discover and run check files. Code enforces, prompts describe.",
    }


# ── Paths ──
def checks_dir() -> Path:
    d = get_project_root() / ".webforge" / "checks"
    d.mkdir(parents=True, exist_ok=True)
    return d

def lock_file(task_id: str) -> Path:
    """Lock file that blocks task_done()."""
    return checks_dir() / f"{task_id}.lock"


# ── Discover all check files ──
def discover_checks() -> list:
    """Find all .py check files in .webforge/checks/."""
    d = checks_dir()
    check_files = []

    for f in sorted(d.glob("check_*.py")):
        check_files.append({
            "file": f.name,
            "path": str(f),
            "name": f.stem,  # e.g. "check_never_use_localStorage"
        })

    return check_files


# ── Run a single check file ──
def run_check(check_path: str, project_root: str) -> dict:
    """
    Load a check file and run its check() function.
    Returns: { name, passed, message }
    """
    check_name = Path(check_path).stem

    try:
        # Dynamically import the check module
        spec = importlib.util.spec_from_file_location(check_name, check_path)
        if not spec or not spec.loader:
            return {"name": check_name, "passed": False, "message": "Failed to load module"}

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Check if it has a check() function
        if not hasattr(module, "check"):
            return {"name": check_name, "passed": False, "message": "No check() function found"}

        # Run the check
        result = module.check(project_root)

        # Handle different return types
        if isinstance(result, bool):
            return {
                "name": check_name,
                "passed": result,
                "message": "OK" if result else "Check failed",
            }
        elif isinstance(result, dict):
            return {
                "name": check_name,
                "passed": result.get("passed", False),
                "message": result.get("message", "No message"),
            }
        elif isinstance(result, tuple) and len(result) == 2:
            passed, message = result
            return {"name": check_name, "passed": passed, "message": message}
        else:
            return {"name": check_name, "passed": False, "message": f"Unexpected return type: {type(result)}"}

    except Exception as e:
        return {"name": check_name, "passed": False, "message": f"Error: {e}"}


# ── Run ALL checks ──
def run_all_checks(project_root: str = None) -> McpResult:
    """
    Run all enforcement checks.
    Returns pass/fail for each + overall result.
    """
    if project_root is None:
        project_root = str(get_project_root())

    checks = discover_checks()

    if not checks:
        return success({
            "checks": [],
            "count": 0,
            "all_passed": True,
            "message": "No enforcement checks registered. (Corrections with /correct will create them.)",
        })

    results = []
    all_passed = True

    for check in checks:
        result = run_check(check["path"], project_root)
        results.append(result)
        if not result["passed"]:
            all_passed = False

    return success({
        "checks": results,
        "count": len(results),
        "passed": sum(1 for r in results if r["passed"]),
        "failed": sum(1 for r in results if not r["passed"]),
        "all_passed": all_passed,
    })


# ── Write a lock file (blocks task_done) ──
def write_lock(task_id: str, failed_checks: list) -> McpResult:
    """Write a lock file that blocks task_done()."""
    lock = lock_file(task_id)
    lock_data = {
        "task_id": task_id,
        "locked_at": utc_now(),
        "failed_checks": failed_checks,
        "message": f"Task {task_id} is locked because {len(failed_checks)} enforcement check(s) failed.",
    }
    lock.write_text(json.dumps(lock_data, indent=2))
    write_log("Enforce", "Minos", "write_lock",
              {"task_id": task_id, "failed_count": len(failed_checks)})
    return success({"locked": True, "task_id": task_id})


# ── Remove a lock file ──
def remove_lock(task_id: str) -> McpResult:
    """Remove a lock file (when checks pass or developer overrides)."""
    lock = lock_file(task_id)
    if lock.exists():
        lock.unlink()
        return success({"unlocked": True, "task_id": task_id})
    return success({"unlocked": False, "message": "No lock file found"})


# ── Check if a task is locked ──
def is_locked(task_id: str) -> bool:
    """Check if a task has a lock file (enforcement checks failed)."""
    return lock_file(task_id).exists()


# ── Run enforcement + write lock if failed ──
def enforce(task_id: str = "") -> McpResult:
    """
    Run all enforcement checks. If any fail, write a lock file.
    Returns the results for display.
    """
    result = run_all_checks()

    if not result.data["all_passed"]:
        failed = [r for r in result.data["checks"] if not r["passed"]]
        if task_id:
            write_lock(task_id, failed)

        lines = []
        lines.append("=" * 60)
        lines.append("🛡️ ENFORCEMENT CHECKS — FAILED")
        lines.append("=" * 60)
        lines.append("")

        for r in result.data["checks"]:
            emoji = "✓" if r["passed"] else "✗"
            lines.append(f"  {emoji} {r['name']}: {r['message']}")

        lines.append("")
        lines.append(f"Result: {result.data['passed']} passed, {result.data['failed']} failed")
        if task_id:
            lines.append(f"\n🔒 Task {task_id} is LOCKED. /task-done will refuse.")
            lines.append(f"   Fix the issues, then: /check {task_id}")
            lines.append(f"   Or override: /check-approve {task_id}")

        return success({
            "output": "\n".join(lines),
            "all_passed": False,
            "locked": bool(task_id),
            "task_id": task_id,
        })
    else:
        if task_id:
            remove_lock(task_id)

        lines = []
        lines.append("=" * 60)
        lines.append("🛡️ ENFORCEMENT CHECKS — ALL PASSED")
        lines.append("=" * 60)
        lines.append("")

        for r in result.data["checks"]:
            lines.append(f"  ✓ {r['name']}: {r['message']}")

        lines.append(f"\nAll {result.data['count']} enforcement check(s) passed.")

        return success({
            "output": "\n".join(lines),
            "all_passed": True,
            "locked": False,
            "task_id": task_id,
        })


# ── Generate a check file from a correction ──
def generate_check_file(rule_text: str, wrong: str, right: str) -> McpResult:
    """
    Generate a Python check file from a correction.
    The check file has a check(project_root) function that scans the codebase
    for the pattern the developer said is wrong.

    This is what Meta Engineering's learn() should call.
    """
    # Create a slug from the rule
    import hashlib
    slug_hash = hashlib.md5(rule_text.encode()).hexdigest()[:8]

    # Try to extract a search pattern from "wrong"
    # e.g. "using localStorage for auth tokens" → search for "localStorage"
    search_terms = []
    wrong_lower = wrong.lower()

    # Extract quoted strings
    import re
    quoted = re.findall(r'"([^"]+)"', wrong)
    if quoted:
        search_terms = quoted
    else:
        # Extract key words (skip common words)
        stop_words = {"using", "the", "a", "an", "for", "to", "in", "on", "at", "is", "are", "was", "were", "do", "does", "did", "not", "no", "never", "always", "should", "must", "and", "or", "but"}
        words = [w for w in wrong_lower.split() if w not in stop_words and len(w) > 3]
        if words:
            search_terms = words[:3]  # Top 3 meaningful words

    # Build the check file
    search_list = json.dumps(search_terms)
    file_exclude = [".git", "node_modules", ".next", ".webforge", "__pycache__", "*.pyc"]

    check_content = f'''#!/usr/bin/env python3
"""
Enforcement check: {rule_text}

Auto-generated by Meta Engineering from a developer correction.
- Wrong: {wrong}
- Right: {right}

This check scans the codebase for patterns the developer said are wrong.
If found, the check fails and the task is blocked.
"""

import os
from pathlib import Path

SEARCH_TERMS = {search_list}
EXCLUDE_DIRS = {file_exclude}


def check(project_root):
    """
    Scan the codebase for the patterns the developer said are wrong.
    Returns: {{ "passed": bool, "message": str }}
    """
    if not SEARCH_TERMS:
        return {{"passed": True, "message": "No search terms — check is informational only"}}

    root = Path(project_root)
    violations = []

    for file_path in root.rglob("*"):
        if not file_path.is_file():
            continue

        # Skip excluded directories
        parts_str = str(file_path)
        if any(excl in parts_str for excl in EXCLUDE_DIRS):
            continue

        # Only check text files
        if file_path.suffix not in (".ts", ".tsx", ".js", ".jsx", ".py", ".json", ".md", ".env", ".env.local", ".env.example"):
            continue

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except:
            continue

        for term in SEARCH_TERMS:
            if term.lower() in content.lower():
                violations.append(str(file_path.relative_to(root)))
                break  # One violation per file is enough

    if violations:
        return {{
            "passed": False,
            "message": f"Found {{len(violations)}} file(s) with pattern: {{', '.join(SEARCH_TERMS)}}. Files: {{', '.join(violations[:5])}}"
        }}
    else:
        return {{
            "passed": True,
            "message": f"No instances of {{', '.join(SEARCH_TERMS)}} found"
        }}
'''

    filename = f"check_{slug_hash}.py"
    filepath = checks_dir() / filename
    filepath.write_text(check_content, encoding="utf-8")

    write_log("Enforce", "Daedalus", "generate_check_file",
              {"file": filename, "rule": rule_text, "search_terms": search_terms})

    return success({
        "file": filename,
        "path": str(filepath),
        "search_terms": search_terms,
        "message": f"✅ Enforcement check created: {filename}\n   Searches for: {', '.join(search_terms) if search_terms else '(no terms extracted)'}\n   This check runs automatically on every /task-done",
    })


# ── List all check files ──
def list_checks() -> McpResult:
    """List all enforcement check files."""
    checks = discover_checks()
    return success({
        "checks": checks,
        "count": len(checks),
    })


# ── CLI ──
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Enforce MCP — code enforces, prompts describe")
        print("Usage: python enforce.py <command> [args]")
        print()
        print("Commands:")
        print("  run [task_id]              Run all enforcement checks")
        print("  discover                   List all check files")
        print("  generate <rule> <wrong> <right>  Generate a check file from a correction")
        print("  lock <task_id>             Check if task is locked")
        print("  unlock <task_id>           Remove lock file")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "info":
        print(json.dumps(info(), indent=2))
    elif cmd == "run":
        task_id = sys.argv[2] if len(sys.argv) > 2 else ""
        result = enforce(task_id)
        print(result.data.get("output", result.to_dict()))
    elif cmd == "discover":
        result = list_checks()
        print(json.dumps(result.to_dict(), indent=2))
    elif cmd == "generate":
        rule = sys.argv[2] if len(sys.argv) > 2 else ""
        wrong = sys.argv[3] if len(sys.argv) > 3 else ""
        right = sys.argv[4] if len(sys.argv) > 4 else ""
        if rule and wrong and right:
            result = generate_check_file(rule, wrong, right)
            print(result.data.get("message", result.to_dict()))
        else:
            print("Usage: generate <rule> <wrong> <right>")
    elif cmd == "lock":
        task_id = sys.argv[2] if len(sys.argv) > 2 else ""
        print(json.dumps({"locked": is_locked(task_id)}))
    elif cmd == "unlock":
        task_id = sys.argv[2] if len(sys.argv) > 2 else ""
        result = remove_lock(task_id)
        print(result.to_dict())
    else:
        print(f"Unknown command: {cmd}")
