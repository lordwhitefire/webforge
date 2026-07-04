#!/usr/bin/env python3
"""
Review MCP — code review checklist (Google/Meta pattern)

Industry pattern: No code merges without review (Google Engineering Practices).
WebForge generates a review checklist based on:
  - Project rules
  - PR size (should be < 400 lines — Meta/Google standard)
  - Test coverage
  - RFC compliance (did the code follow the approved design?)

The checklist is a guide for the developer (or AI) to review before merging.
"""

import os
import sys
import json
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import write_log, success, fail, utc_now, McpResult, get_project_root
from memory import session_append, read_rules


def info() -> dict:
    return {
        "id": "m-review",
        "name": "Review MCP",
        "tier": 4,
        "owner": "Minos",
        "job": "Generate code review checklist. Google/Meta pattern: no merge without review.",
    }


def review_generate(task_id: str) -> McpResult:
    """
    Generate a code review checklist for a task.
    Checks: rules compliance, PR size, test coverage, RFC compliance.
    """
    project_root = get_project_root()

    # Load task
    try:
        from task import load_board, find_task
        board = load_board()
        task = find_task(board, task_id)
        if not task:
            return fail(f"Task not found: {task_id}")
    except:
        return fail("Task MCP not available")

    # Check git diff (what changed)
    diff_stat = ""
    diff_lines = 0
    try:
        result = subprocess.run(
            ["git", "diff", "--stat", "HEAD~1"],
            cwd=str(project_root), capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            diff_stat = result.stdout.strip()
            # Count total lines changed
            for line in diff_stat.split("\n"):
                if "insertion" in line or "deletion" in line:
                    parts = line.split()
                    for p in parts:
                        if p.isdigit():
                            diff_lines += int(p)
    except:
        pass

    # Check if there are tests for this task
    test_files = []
    try:
        # Look for test files modified recently
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~1"],
            cwd=str(project_root), capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            for f in result.stdout.strip().split("\n"):
                if "test" in f.lower() or "spec" in f.lower():
                    test_files.append(f)
    except:
        pass

    # Load rules
    rules_text = read_rules()

    # Check if RFC exists and was approved
    rfc_status = "no RFC (two-way door)"
    try:
        from rfc import has_approved_rfc, rfc_file
        if rfc_file(task_id).exists():
            if has_approved_rfc(task_id):
                rfc_status = "✓ RFC approved"
            else:
                rfc_status = "⚠ RFC exists but NOT approved"
    except:
        pass

    # Generate checklist
    lines = []
    lines.append("=" * 60)
    lines.append(f"CODE REVIEW CHECKLIST — {task_id}")
    lines.append(f"Task: {task['title']}")
    lines.append(f"Type: {task['type']} | Effort: {task['effort']}")
    lines.append(f"Date: {utc_now()}")
    lines.append("=" * 60)
    lines.append("")

    # 1. PR Size (Meta/Google: < 400 lines)
    lines.append("## PR Size (Meta/Google standard: < 400 lines)")
    if diff_lines > 0:
        size_status = "✓ OK" if diff_lines < 400 else f"⚠ LARGE ({diff_lines} lines)"
        lines.append(f"  [{size_status}] Lines changed: {diff_lines}")
    else:
        lines.append("  [○] No git diff detected (may not be committed yet)")
    lines.append("")

    # 2. Test Coverage
    lines.append("## Test Coverage")
    if test_files:
        lines.append(f"  [✓] Test files found: {len(test_files)}")
        for tf in test_files[:5]:
            lines.append(f"    - {tf}")
    else:
        if task["type"] in ("feature", "bugfix"):
            lines.append("  [⚠] NO TEST FILES FOUND — tests should be written for this task")
            lines.append("       Bugfixes need regression tests. Features need unit tests.")
        else:
            lines.append("  [○] No tests needed for this task type")
    lines.append("")

    # 3. RFC Compliance
    lines.append("## RFC Compliance")
    lines.append(f"  [{rfc_status}]")
    lines.append("")

    # 4. Rules Compliance
    lines.append("## Project Rules Compliance")
    if rules_text and rules_text != "(no rules set)":
        lines.append("  Check that the code follows these rules:")
        for rule_line in rules_text.split("\n"):
            if rule_line.strip().startswith("-"):
                lines.append(f"  [ ] {rule_line.strip('- ').strip()}")
    else:
        lines.append("  [○] No project rules set")
    lines.append("")

    # 5. General checklist (Google Engineering Practices)
    lines.append("## General Checklist (Google Engineering Practices)")
    general_checks = [
        "Does the code follow the project's naming conventions?",
        "Are there any console.log / debug statements left?",
        "Are there hardcoded values that should be environment variables?",
        "Is error handling in place for API calls?",
        "Are there any TODO/FIXME comments that should be addressed?",
        "Does the code handle edge cases (empty data, null, errors)?",
        "Is the code readable? (clear variable names, reasonable function length)",
        "Are imports organized? (no unused imports)",
    ]
    for check in general_checks:
        lines.append(f"  [ ] {check}")
    lines.append("")

    # 6. Summary
    lines.append("=" * 60)
    lines.append("REVIEW SUMMARY")
    lines.append("=" * 60)

    issues = []
    if diff_lines >= 400:
        issues.append(f"PR is large ({diff_lines} lines) — consider splitting")
    if not test_files and task["type"] in ("feature", "bugfix"):
        issues.append("No tests written — add tests before merging")
    if "NOT approved" in rfc_status:
        issues.append("RFC not approved — approve before merging")

    if issues:
        lines.append("\n⚠ ISSUES TO ADDRESS:")
        for i in issues:
            lines.append(f"  - {i}")
    else:
        lines.append("\n✅ No automated issues detected. Complete the checklist manually.")

    lines.append("")
    lines.append("After review: /task-done " + task_id)

    # Log
    session_append(f"REVIEW GENERATED — {task_id}", agent="Minos", kind="note")
    write_log("Review", "Minos", "review_generate", {"task_id": task_id})

    return success({
        "task_id": task_id,
        "output": "\n".join(lines),
        "issues": issues,
        "diff_lines": diff_lines,
        "test_files": test_files,
    })


# CLI
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Review MCP — code review checklist")
        print("Usage: python review.py <command> [args]")
        print()
        print("Commands:")
        print("  generate <task_id>  Generate review checklist for a task")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "info":
        print(json.dumps(info(), indent=2))
    elif cmd == "generate":
        result = review_generate(sys.argv[2])
        if result.ok:
            print(result.data["output"])
        else:
            print(result.error)
    else:
        print(f"Unknown command: {cmd}")
