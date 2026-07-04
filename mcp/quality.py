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
        return {"type": "unknown", "tools": {
            "lint_cmd": None, "typecheck_cmd": None, "test_cmd": None,
            "build_cmd": None, "security_cmd": None,
        }, "scripts": []}

    try:
        pkg = json.loads(pkg_path.read_text())
    except Exception as _e:
        write_log("Quality", "Minos", "parse package.json", {"error": str(_e)})
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

    # ── ALSO RUN ENFORCEMENT CHECKS ──
    enforce_checks = []
    enforce_passed = True
    try:
        from enforce import run_all_checks, write_lock, remove_lock
        enforce_result = run_all_checks(str(project_root))
        enforce_checks = enforce_result.data.get("checks", [])
        enforce_passed = enforce_result.data.get("all_passed", True)

        if enforce_checks:
            lines.append("")
            lines.append("🛡️ ENFORCEMENT CHECKS")
            for ec in enforce_checks:
                emoji = "✓" if ec["passed"] else "✗"
                lines.append(f"  {emoji} {ec['name']}: {ec['message']}")

            if not enforce_passed:
                all_passed = False
                failed += len([ec for ec in enforce_checks if not ec["passed"]])
    except ImportError:
        pass

    # Combine results
    check_result["enforcement_checks"] = enforce_checks
    check_result["all_passed"] = all_passed and enforce_passed

    # ── WRITE LOCK FILE IF FAILED ──
    if task_id and not all_passed:
        try:
            from enforce import write_lock
            failed_list = [c for c in checks if c["status"] == "failed"]
            failed_list.extend([ec for ec in enforce_checks if not ec.get("passed", True)])
            write_lock(task_id, failed_list)
        except ImportError:
            pass
    elif task_id and all_passed:
        try:
            from enforce import remove_lock
            remove_lock(task_id)
        except ImportError:
            pass

    # Save to .webforge for reference
    check_dir = project_root / ".webforge" / "checks"
    check_dir.mkdir(parents=True, exist_ok=True)
    check_file = check_dir / f"{task_id or 'manual'}.json"
    check_file.write_text(json.dumps(check_result, indent=2))

    write_log("Quality", "Minos", "check_run",
              {"task_id": task_id, "passed": passed, "failed": failed,
               "enforcement_passed": enforce_passed})

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
    # Pipeline gate — refuse if pipeline is active
    try:
        from common import is_pipeline_active
        if is_pipeline_active():
            return fail(
                f"PIPELINE ACTIVE — {task_id}\n\n"
                f"A pipeline session is running. Let the agent script handle this.\n"
                f"Do NOT approve quality gates yourself.\n"
                f"Wait for the pipeline to finish, or say 'continue' if it timed out."
            )
    except ImportError:
        pass

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
    """
    Check if a task has passed quality checks or has an override.
    
    FIX: If the agent script already ran quality check + approve,
    the override file exists and we return True.
    If no checks have been run at all, allow (don't block the system).
    Only block if checks were run AND failed (lock file exists).
    """
    project_root = get_project_root()
    check_dir = project_root / ".webforge" / "checks"

    # Check for override (developer or agent approved)
    override_file = check_dir / f"{task_id}-override.json"
    if override_file.exists():
        return True

    # Check for enforcement lock file (enforce.py wrote it — checks FAILED)
    try:
        from enforce import is_locked
        if is_locked(task_id):
            return False  # Lock file exists — checks failed, blocked
    except ImportError:
        pass

    # Check if quality checks have been run AND passed
    check_file = check_dir / f"{task_id}.json"
    if check_file.exists():
        result = json.loads(check_file.read_text())
        if result.get("all_passed"):
            return True
        # Checks ran but failed — blocked
        return False

    # No checks have been run → ALLOW (don't block the system from working)
    return True


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
