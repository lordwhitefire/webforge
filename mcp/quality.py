#!/usr/bin/env python3
"""
Quality MCP — continuous quality checks (replaces rigid 108-agent audit)

Industry patterns:
  - Testing Pyramid (Martin Fowler): unit > integration > e2e
  - Shift Left: test during coding, not after
  - CI/CD Pipeline: lint → type-check → test → build → security
  - Quality Gate: block task-done if checks fail (configurable override)

When /task-done is called, this MCP runs automatically:
  1. Lint (ESLint)
  2. Type check (tsc --noEmit)
  3. Unit tests (vitest or jest)
  4. Build (next build or tsc)
  5. Security scan (npm audit)

If any check fails → task-done is BLOCKED (strict by default).
Developer can override with /check-approve <task-id>.
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))
from common import write_log, success, fail, utc_now, McpResult, get_project_root
from memory import session_append


def info() -> dict:
    return {
        "id": "m-quality",
        "name": "Quality MCP",
        "tier": 4,
        "owner": "Minos",
        "job": "Run lint, type-check, tests, build, security. Quality gate before task-done.",
    }


# ── Detect project type ──
def detect_project_type(project_root: Path) -> dict:
    """Detect what kind of project this is and what tools to use."""
    pkg_path = project_root / "package.json"
    if not pkg_path.exists():
        return {"type": "unknown", "tools": {}}

    try:
        pkg = json.loads(pkg_path.read_text())
    except:
        return {"type": "unknown", "tools": {}}

    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
    scripts = pkg.get("scripts", {})

    tools = {
        "lint_cmd": None,
        "typecheck_cmd": None,
        "test_cmd": None,
        "build_cmd": None,
        "security_cmd": None,
    }

    # Lint
    if "lint" in scripts:
        tools["lint_cmd"] = "npm run lint"
    elif "eslint" in deps:
        tools["lint_cmd"] = "npx eslint ."

    # Type check
    if "typecheck" in scripts:
        tools["typecheck_cmd"] = "npm run typecheck"
    elif "typescript" in deps:
        tools["typecheck_cmd"] = "npx tsc --noEmit"

    # Test
    if "test" in scripts:
        tools["test_cmd"] = "npm test"
    elif "vitest" in deps:
        tools["test_cmd"] = "npx vitest run"
    elif "jest" in deps:
        tools["test_cmd"] = "npx jest"

    # Build
    if "build" in scripts:
        tools["build_cmd"] = "npm run build"

    # Security
    tools["security_cmd"] = "npm audit --audit-level=low"

    # Detect framework
    project_type = "node"
    if "next" in deps:
        project_type = "nextjs"
    elif "react" in deps and "vite" in deps:
        project_type = "vite-react"
    elif "react" in deps:
        project_type = "react"

    return {"type": project_type, "tools": tools, "scripts": list(scripts.keys())}


# ── Run a single check ──
def run_check(name: str, command: str, project_root: Path, timeout: int = 120) -> dict:
    """Run a single quality check and return the result."""
    if not command:
        return {"name": name, "status": "skipped", "output": "(no command configured)"}

    try:
        result = subprocess.run(
            command, shell=True, cwd=str(project_root),
            capture_output=True, text=True, timeout=timeout
        )
        status = "passed" if result.returncode == 0 else "failed"
        output = result.stdout[-500:] + result.stderr[-500:]  # Last 1000 chars
        return {
            "name": name,
            "status": status,
            "command": command,
            "exit_code": result.returncode,
            "output": output.strip(),
        }
    except subprocess.TimeoutExpired:
        return {"name": name, "status": "timeout", "output": f"Timed out after {timeout}s"}
    except Exception as e:
        return {"name": name, "status": "error", "output": str(e)}


# ── Run all checks ──
def check_run(task_id: str = "") -> McpResult:
    """
    Run all quality checks for the project.
    Returns pass/fail for each check.
    """
    project_root = get_project_root()
    project_info = detect_project_type(project_root)
    tools = project_info["tools"]

    checks = []

    # 1. Lint
    if tools["lint_cmd"]:
        print(f"  Running lint...")
        checks.append(run_check("lint", tools["lint_cmd"], project_root))

    # 2. Type check
    if tools["typecheck_cmd"]:
        print(f"  Running type check...")
        checks.append(run_check("typecheck", tools["typecheck_cmd"], project_root))

    # 3. Tests
    if tools["test_cmd"]:
        print(f"  Running tests...")
        checks.append(run_check("tests", tools["test_cmd"], project_root, timeout=300))

    # 4. Build
    if tools["build_cmd"]:
        print(f"  Running build...")
        checks.append(run_check("build", tools["build_cmd"], project_root, timeout=300))

    # 5. Security
    if tools["security_cmd"]:
        print(f"  Running security scan...")
        checks.append(run_check("security", tools["security_cmd"], project_root))

    # Summarize
    passed = sum(1 for c in checks if c["status"] == "passed")
    failed = sum(1 for c in checks if c["status"] == "failed")
    skipped = sum(1 for c in checks if c["status"] == "skipped")
    errors = sum(1 for c in checks if c["status"] in ("error", "timeout"))

    all_passed = (failed == 0 and errors == 0)

    # Format output
    lines = []
    lines.append("=" * 60)
    lines.append(f"QUALITY CHECK{' for ' + task_id if task_id else ''}")
    lines.append(f"Project type: {project_info['type']}")
    lines.append(f"Date: {utc_now()}")
    lines.append("=" * 60)
    lines.append("")

    for c in checks:
        emoji = {"passed": "✓", "failed": "✗", "skipped": "○", "error": "⚠", "timeout": "⏱"}.get(c["status"], "?")
        lines.append(f"  {emoji} {c['name']:15s} — {c['status']}")
        if c["status"] == "failed" and c.get("output"):
            # Show last few lines of output
            output_lines = c["output"].split("\n")[-5:]
            for ol in output_lines:
                lines.append(f"      {ol}")

    lines.append("")
    lines.append("=" * 60)
    lines.append(f"Result: {passed} passed, {failed} failed, {skipped} skipped, {errors} errors")
    lines.append("=" * 60)

    if all_passed:
        lines.append("\n✅ ALL CHECKS PASSED — task can be marked done.")
    else:
        lines.append(f"\n❌ {failed + errors} CHECK(S) FAILED — task-done is BLOCKED.")
        lines.append(f"   Fix the issues, then re-run: /check {task_id}")
        lines.append(f"   Or override (you're the boss): /check-approve {task_id}")

    # Log to session
    session_append(
        f"QUALITY CHECK{' for ' + task_id if task_id else ''} — {passed} passed, {failed} failed, {skipped} skipped",
        agent="Minos", kind="note"
    )

    # Save check result
    check_result = {
        "task_id": task_id,
        "timestamp": utc_now(),
        "checks": checks,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "errors": errors,
        "all_passed": all_passed,
    }

    # Save to .webforge for reference
    check_dir = project_root / ".webforge" / "checks"
    check_dir.mkdir(parents=True, exist_ok=True)
    check_file = check_dir / f"{task_id or 'manual'}.json"
    check_file.write_text(json.dumps(check_result, indent=2))

    write_log("Quality", "Minos", "check_run",
              {"task_id": task_id, "passed": passed, "failed": failed})

    return success({
        "check_result": check_result,
        "output": "\n".join(lines),
        "all_passed": all_passed,
    })


# ── Override (developer approves despite failures) ──
def check_approve(task_id: str, reason: str = "") -> McpResult:
    """
    Developer overrides failed checks.
    'I know about the warning, mark it done anyway.'
    """
    session_append(
        f"CHECK OVERRIDE — {task_id}: {reason or 'Developer approved despite check failures'}",
        agent="Developer", kind="decision"
    )
    write_log("Quality", "Developer", "check_approve",
              {"task_id": task_id, "reason": reason})

    return success({
        "task_id": task_id,
        "approved": True,
        "message": (
            f"✅ CHECK OVERRIDDEN for {task_id}.\n"
            f"Reason: {reason or 'Developer override'}\n"
            f"Task can now be marked done: /task-done {task_id}"
        ),
    })


# ── Check if task is approved (passed checks OR override given) ──
def is_quality_approved(task_id: str) -> bool:
    """Check if a task has passed quality checks or has an override."""
    project_root = get_project_root()
    check_dir = project_root / ".webforge" / "checks"

    # Check if override exists (in session log)
    # For simplicity: if check_approve was called, it's in the session log
    # We check the last check result
    check_file = check_dir / f"{task_id}.json"
    if check_file.exists():
        result = json.loads(check_file.read_text())
        if result.get("all_passed"):
            return True

    # Check for override in a separate file
    override_file = check_dir / f"{task_id}-override.json"
    if override_file.exists():
        return True

    # No check run yet — allow (first time)
    if not check_file.exists():
        return True

    return False


# ── CLI ──
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Quality MCP — continuous quality checks")
        print("Usage: python quality.py <command> [args]")
        print()
        print("Commands:")
        print("  check [task_id]          Run all quality checks")
        print("  approve <task_id> [reason]  Override failed checks")
        print("  approved <task_id>       Check if task is quality-approved")
        print("  detect                   Detect project type and tools")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "info":
        print(json.dumps(info(), indent=2))
    elif cmd == "detect":
        project_root = get_project_root()
        print(json.dumps(detect_project_type(project_root), indent=2))
    elif cmd == "check":
        task_id = sys.argv[2] if len(sys.argv) > 2 else ""
        result = check_run(task_id)
        print(result.data.get("output", result.to_dict()))
    elif cmd == "approve":
        task_id = sys.argv[2]
        reason = sys.argv[3] if len(sys.argv) > 3 else ""
        # Save override
        project_root = get_project_root()
        check_dir = project_root / ".webforge" / "checks"
        check_dir.mkdir(parents=True, exist_ok=True)
        (check_dir / f"{task_id}-override.json").write_text(
            json.dumps({"task_id": task_id, "reason": reason, "timestamp": utc_now()})
        )
        result = check_approve(task_id, reason)
        print(result.data.get("message", result.to_dict()))
    elif cmd == "approved":
        task_id = sys.argv[2]
        print(json.dumps({"quality_approved": is_quality_approved(task_id)}))
    else:
        print(f"Unknown command: {cmd}")
