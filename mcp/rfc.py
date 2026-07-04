#!/usr/bin/env python3
"""
RFC MCP — Request for Comments

Industry pattern: RFCs (Uber, Amazon, Rust, Meta) — written proposals
circulated for feedback BEFORE coding starts.

WebForge uses the Amazon "two-way door" pattern:
  - One-way doors (features, L effort) → RFC required before coding
  - Two-way doors (bugfixes, tests, S/M effort) → skip RFC, just code

When a task is approved (/task-approve), WebForge checks:
  - If task type is 'feature' OR effort is 'L' → generate RFC, wait for approval
  - Otherwise → skip RFC, start coding immediately

RFC files live in: <project>/.webforge/rfcs/
  Format: task-NNN-<slug>.md
"""

import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))
from common import write_log, success, fail, utc_now, McpResult, get_project_root
from memory import session_append


# ── Paths ──
def rfcs_dir() -> Path:
    d = get_project_root() / ".webforge" / "rfcs"
    d.mkdir(parents=True, exist_ok=True)
    return d

def rfc_file(task_id: str) -> Path:
    return rfcs_dir() / f"{task_id}.md"


# ── One-way vs two-way door (Amazon pattern) ──
ONE_WAY_DOOR_TYPES = {"feature", "refactor", "architecture"}
ONE_WAY_DOOR_EFFORTS = {"L"}


def is_one_way_door(task: dict) -> bool:
    """
    Determine if a task needs an RFC (one-way door) or can skip (two-way door).
    One-way = irreversible or hard to reverse (features, large refactors)
    Two-way = easily reversible (bugfixes, tests, small changes)
    """
    if task.get("type") in ONE_WAY_DOOR_TYPES:
        return True
    if task.get("effort") in ONE_WAY_DOOR_EFFORTS:
        return True
    return False


def info() -> dict:
    return {
        "id": "m-rfc",
        "name": "RFC MCP",
        "tier": 1,
        "owner": "Athena",
        "job": "Generate and manage RFCs. One-way door tasks (features, L effort) require RFC before coding.",
    }


# ── Generate RFC ──
def rfc_generate(task: dict, project_scan: dict = None) -> McpResult:
    """
    Auto-generate an RFC for a task.
    The RFC is a PROPOSAL — the developer reviews and approves/rejects it.
    """
    task_id = task["id"]
    title = task["title"]
    task_type = task.get("type", "feature")
    effort = task.get("effort", "M")
    area = task.get("area", "")
    description = task.get("description", "")

    # Build the RFC content
    # This is a template — the LLM (Athena) will fill in the details
    # when it reviews the task and project context

    # Determine motivation based on task type
    if task_type == "feature":
        motivation = f"This feature adds new functionality to the project."
    elif task_type == "bugfix":
        motivation = f"This fix addresses a bug affecting users."
    elif task_type == "refactor":
        motivation = f"This refactor improves code quality without changing behavior."
    elif task_type == "architecture":
        motivation = f"This change affects the project's architecture."
    else:
        motivation = f"This task addresses a specific need in the project."

    # Determine design approach based on area
    design_hint = ""
    if project_scan and "stack" in project_scan:
        stack = project_scan["stack"]
        deps = stack.get("dependencies", [])
        if "next" in deps:
            design_hint += "- Use Next.js App Router conventions (server components by default)\n"
        if "@supabase/supabase-js" in deps:
            design_hint += "- Use Supabase client for data operations\n"
        if "react-hook-form" in deps:
            design_hint += "- Use react-hook-form for any forms\n"
        if "zustand" in deps:
            design_hint += "- Use Zustand for state management\n"
        if "zod" in deps:
            design_hint += "- Use Zod for validation\n"

    if not design_hint:
        design_hint = "- (Athena will fill in based on project scan)\n"

    # Find related files in the project
    related_files = ""
    if project_scan:
        # Find files that might be related to the task
        title_words = [w.lower() for w in re.findall(r'\w+', title) if len(w) > 3]
        all_files = []
        for key in ["pages", "components", "api_routes"]:
            all_files.extend(project_scan.get(key, []))

        related = []
        for f in all_files[:50]:  # Check first 50
            f_lower = f.lower()
            if any(word in f_lower for word in title_words):
                related.append(f)

        if related:
            related_files = "\n".join(f"- `{f}`" for f in related[:10])
        else:
            related_files = "- (no obviously related files found — Athena will investigate)"

    # Get existing rules that apply
    try:
        from memory import read_rules
        rules_text = read_rules()
        rules_section = rules_text if rules_text != "(no rules set)" else "(no rules set)"
    except:
        rules_section = "(unable to load rules)"

    # Get existing ADRs
    try:
        from memory import list_adrs
        adrs_result = list_adrs()
        adrs = adrs_result.data.get("adrs", [])
        if adrs:
            adrs_section = "\n".join(f"- {a['file']}: {a['title']}" for a in adrs)
        else:
            adrs_section = "(no ADRs yet)"
    except:
        adrs_section = "(unable to load ADRs)"

    rfc_content = f"""# RFC: {title}

- **Task ID:** {task_id}
- **Type:** {task_type}
- **Effort:** {effort}
- **Area:** {area or "n/a"}
- **Status:** Proposed
- **Created:** {utc_now()}

## Summary

{description or "(Athena will fill in the summary based on the task description)"}

## Motivation

{motivation}

## Detailed Design

{design_hint}

### Implementation Steps

1. (Athena will fill in based on project analysis)
2.
3.

### Files to Create/Modify

{related_files or "(Athena will identify files)"}

## Alternatives Considered

1. **(Alternative 1)**
   - Pros:
   - Cons:
   - Why rejected:

2. **(Alternative 2)**
   - Pros:
   - Cons:
   - Why rejected:

## Risks

- (Athena will identify risks)

## Rules That Apply

{rules_section}

## Related ADRs

{adrs_section}

## Open Questions

- (Questions for the developer will appear here)

---

*This RFC was auto-generated by WebForge. Review it, then:*
- `/rfc-approve {task_id}` — approve this design, unlock coding
- `/rfc-reject {task_id} <reason>` — reject, send back for redesign
"""

    # Save the RFC
    filepath = rfc_file(task_id)
    filepath.write_text(rfc_content, encoding="utf-8")

    session_append(f"RFC GENERATED — {task_id}: {title}", agent="Athena", kind="note")
    write_log("RFC", "Athena", "rfc_generate",
              {"task_id": task_id, "title": title, "file": filepath.name})

    return success({
        "file": filepath.name,
        "task_id": task_id,
        "title": title,
        "one_way_door": True,
        "message": (
            f"RFC GENERATED for {task_id}: {title}\n\n"
            f"This is a {task_type} (one-way door). An RFC has been written.\n"
            f"Review it with: /rfc {task_id}\n"
            f"Then approve: /rfc-approve {task_id}\n"
            f"Or reject: /rfc-reject {task_id} <reason>"
        ),
    })


# ── Show RFC ──
def rfc_show(task_id: str) -> McpResult:
    """Show the RFC for a task."""
    filepath = rfc_file(task_id)
    if not filepath.exists():
        return fail(f"No RFC found for task: {task_id}. "
                    f"RFCs are auto-generated when you /task-approve a one-way door task.")
    content = filepath.read_text(encoding="utf-8")
    return success({"task_id": task_id, "file": filepath.name, "content": content})


# ── Approve RFC ──
def rfc_approve(task_id: str) -> McpResult:
    """Approve the RFC — unlocks coding for this task."""
    filepath = rfc_file(task_id)
    if not filepath.exists():
        return fail(f"No RFC found for task: {task_id}")

    content = filepath.read_text(encoding="utf-8")
    # Update status from Proposed to Approved
    content = content.replace("**Status:** Proposed", "**Status:** Approved")
    content += f"\n\n## Approval\n\n- **Approved by:** Developer\n- **Approved at:** {utc_now()}\n"
    filepath.write_text(content, encoding="utf-8")

    session_append(f"RFC APPROVED — {task_id}", agent="Developer", kind="decision")
    write_log("RFC", "Developer", "rfc_approve", {"task_id": task_id})

    return success({
        "task_id": task_id,
        "status": "approved",
        "message": (
            f"RFC APPROVED for {task_id}. Hephaestus can now start coding.\n"
            f"The task is in DOING. When done: /task-done {task_id}"
        ),
    })


# ── Reject RFC ──
def rfc_reject(task_id: str, reason: str = "") -> McpResult:
    """Reject the RFC — send back for redesign."""
    filepath = rfc_file(task_id)
    if not filepath.exists():
        return fail(f"No RFC found for task: {task_id}")

    content = filepath.read_text(encoding="utf-8")
    content = content.replace("**Status:** Proposed", "**Status:** Rejected")
    content += f"\n\n## Rejection\n\n- **Rejected by:** Developer\n- **Rejected at:** {utc_now()}\n- **Reason:** {reason}\n"
    filepath.write_text(content, encoding="utf-8")

    session_append(f"RFC REJECTED — {task_id}: {reason}", agent="Developer", kind="correction")
    write_log("RFC", "Developer", "rfc_reject",
              {"task_id": task_id, "reason": reason})

    # Move task back to backlog (can't code without approved RFC)
    try:
        from task import task_move
        task_move(task_id, "backlog")
    except:
        pass

    return success({
        "task_id": task_id,
        "status": "rejected",
        "reason": reason,
        "message": (
            f"RFC REJECTED for {task_id}. Task moved back to backlog.\n"
            f"Reason: {reason}\n"
            f"Create a new task or modify this one, then /build again."
        ),
    })


# ── List all RFCs ──
def rfc_list() -> McpResult:
    """List all RFCs."""
    rfcs = []
    for f in sorted(rfcs_dir().glob("*.md")):
        # Extract status from content
        content = f.read_text(encoding="utf-8")
        status_match = re.search(r'\*\*Status:\*\*\s*(\w+)', content)
        status = status_match.group(1) if status_match else "unknown"
        title_line = content.split("\n")[0].lstrip("# ").strip()
        rfcs.append({
            "file": f.name,
            "task_id": f.stem,
            "title": title_line,
            "status": status,
        })
    return success({"rfcs": rfcs, "count": len(rfcs)})


# ── Check if task needs RFC ──
def needs_rfc(task: dict) -> bool:
    """Check if a task requires an RFC before coding."""
    return is_one_way_door(task)


# ── Check if task has approved RFC ──
def has_approved_rfc(task_id: str) -> bool:
    """Check if a task has an approved RFC."""
    filepath = rfc_file(task_id)
    if not filepath.exists():
        return False
    content = filepath.read_text(encoding="utf-8")
    return "**Status:** Approved" in content


# ── CLI ──
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("RFC MCP — Request for Comments")
        print("Usage: python rfc.py <command> [args]")
        print()
        print("Commands:")
        print("  generate <task_json>     Generate RFC for a task")
        print("  show <task_id>           Show RFC for a task")
        print("  approve <task_id>        Approve RFC (unlocks coding)")
        print("  reject <task_id> [reason] Reject RFC (sends back)")
        print("  list                     List all RFCs")
        print("  check <task_json>        Check if task needs RFC")
        print("  approved <task_id>       Check if task has approved RFC")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "info":
        print(json.dumps(info(), indent=2))
    elif cmd == "generate":
        # task_json is a JSON string
        task = json.loads(sys.argv[2])
        result = rfc_generate(task)
        print(result.data.get("message", result.to_dict()))
    elif cmd == "show":
        result = rfc_show(sys.argv[2])
        if result.ok:
            print(result.data["content"])
        else:
            print(result.error)
    elif cmd == "approve":
        result = rfc_approve(sys.argv[2])
        print(result.data.get("message", result.to_dict()))
    elif cmd == "reject":
        reason = sys.argv[3] if len(sys.argv) > 3 else ""
        result = rfc_reject(sys.argv[2], reason)
        print(result.data.get("message", result.to_dict()))
    elif cmd == "list":
        print(json.dumps(rfc_list().to_dict(), indent=2))
    elif cmd == "check":
        task = json.loads(sys.argv[2])
        print(json.dumps({"needs_rfc": needs_rfc(task), "task_id": task.get("id")}))
    elif cmd == "approved":
        print(json.dumps({"has_approved_rfc": has_approved_rfc(sys.argv[2])}))
    else:
        print(f"Unknown command: {cmd}")
