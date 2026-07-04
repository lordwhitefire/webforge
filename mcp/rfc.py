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
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter

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


# ── Real codebase scanner (replaces "Athena will fill in" prompt-placeholders) ──
def scan_project(project_root: str | Path = None) -> dict:
    """
    Scan the project directory for real data: deps, files, components, routes.
    Returns a dict usable as project_scan in rfc_generate().
    Code enforces, prompts describe.
    """
    if project_root is None:
        project_root = get_project_root()
    project_root = Path(project_root)

    scan: dict = {
        "stack": {"dependencies": [], "dev_dependencies": [], "scripts": [], "framework": ""},
        "pages": [],
        "components": [],
        "api_routes": [],
        "files": [],
        "directories": [],
    }

    # ── package.json scan ──
    pkg_json = project_root / "package.json"
    if pkg_json.exists():
        try:
            pkg = json.loads(pkg_json.read_text())
            scan["stack"]["dependencies"] = list(pkg.get("dependencies", {}).keys())
            scan["stack"]["dev_dependencies"] = list(pkg.get("devDependencies", {}).keys())
            scan["stack"]["scripts"] = list(pkg.get("scripts", {}).keys())
            # Detect framework from deps
            all_deps = set(scan["stack"]["dependencies"]) | set(scan["stack"]["dev_dependencies"])
            for dep in all_deps:
                if dep in ("next", "next.js"):
                    scan["stack"]["framework"] = "next"
                    break
                elif dep in ("react", "react-dom"):
                    scan["stack"]["framework"] = "react"
                elif dep == "astro":
                    scan["stack"]["framework"] = "astro"
                    break
                elif dep in ("svelte", "@sveltejs/kit"):
                    scan["stack"]["framework"] = "svelte"
                    break
                elif dep == "vue":
                    scan["stack"]["framework"] = "vue"
                    break
        except (json.JSONDecodeError, OSError):
            write_log("RFC", "Athena", "scan_package_failed", {})

    # ── Python project scan ──
    pyproject = project_root / "pyproject.toml"
    if pyproject.exists():
        scan["stack"]["framework"] = "python"
        try:
            content = pyproject.read_text()
            if "django" in content.lower():
                scan["stack"]["framework"] = "django"
            elif "flask" in content.lower():
                scan["stack"]["framework"] = "flask"
            elif "fastapi" in content.lower():
                scan["stack"]["framework"] = "fastapi"
        except OSError:
            pass

    # ── Scan directory structure ──
    src_dirs = []
    for candidate in ["src", "app", "lib", "components", "pages", "routes"]:
        d = project_root / candidate
        if d.is_dir():
            src_dirs.append(candidate)

    for d in src_dirs:
        dir_path = project_root / d
        for f in sorted(dir_path.rglob("*")):
            if f.is_file() and f.suffix in (".ts", ".tsx", ".js", ".jsx", ".py", ".vue", ".svelte"):
                rel = f.relative_to(project_root)
                scan["files"].append(str(rel))
                # Categorize by path
                if "component" in str(rel).lower() or "/components/" in str(rel):
                    scan["components"].append(str(rel))
                elif "/pages/" in str(rel) or "/app/" in str(rel):
                    scan["pages"].append(str(rel))
                elif "/api/" in str(rel) or "/routes/" in str(rel):
                    scan["api_routes"].append(str(rel))

    scan["directories"] = src_dirs

    # ── Count most common imports for design hints ──
    all_imports = Counter()
    for filepath in scan["files"][:100]:  # Check first 100 files
        full_path = project_root / filepath
        try:
            content = full_path.read_text(errors="ignore")
            for imp in re.findall(r'(?:import|from)\s+([\w_.-]+)', content):
                all_imports[imp.strip()] += 1
        except OSError:
            pass
    scan["common_imports"] = [imp for imp, _ in all_imports.most_common(10)]

    return scan


def _make_design_hints(project_scan: dict) -> str:
    """Generate concrete design hints from project scan."""
    hints = []
    deps = project_scan.get("stack", {}).get("dependencies", [])
    all_deps = set(deps) | set(project_scan.get("stack", {}).get("dev_dependencies", []))
    framework = project_scan.get("stack", {}).get("framework", "")

    dep_map = {
        "next": "Use Next.js App Router conventions (server components by default)",
        "@supabase/supabase-js": "Use Supabase client for data operations",
        "react-hook-form": "Use react-hook-form for forms",
        "zustand": "Use Zustand for state management",
        "zod": "Use Zod for validation",
        "prisma": "Use Prisma for database access",
        "drizzle-orm": "Use Drizzle ORM for database access",
        "tailwindcss": "Use Tailwind CSS utility classes — no custom CSS files",
        "@sanity/client": "Use Sanity client for content queries",
        "react-query": "Use React Query / TanStack Query for server state",
        "@tanstack/react-query": "Use TanStack Query for server state",
        "axios": "Use axios for HTTP requests",
    }

    for dep, hint in dep_map.items():
        if dep in all_deps:
            hints.append(f"- {hint}")

    if framework == "next":
        hints.append("- Use Next.js App Router (app/ directory, not pages/)")
        hints.append("- Prefer server components; add 'use client' only for interactivity")
    elif framework == "react":
        hints.append("- Standard React project — use functional components with hooks")

    if not hints:
        hints.append("- Follow existing patterns in the codebase")

    return "\n".join(hints)


def _find_related_files(project_scan: dict, title: str) -> str:
    """Find project files related to the task title by keyword matching."""
    title_words = {w.lower() for w in re.findall(r'\w+', title) if len(w) > 3}
    all_files = project_scan.get("files", [])
    related = [f for f in all_files[:50] if any(w in f.lower() for w in title_words)]
    if related:
        return "\n".join(f"- `{f}`" for f in related[:10])
    return "(none obviously related — will identify during implementation)"


def _make_alternatives(task_type: str) -> str:
    """Generate realistic alternatives based on task type."""
    alternatives = {
        "feature": [
            ("Build from scratch", "Full control, no legacy baggage",
             "Takes longer", "Too slow for this effort level"),
            ("Use an off-the-shelf library/package",
             "Faster to implement, battle-tested",
             "May not fit perfectly, dependency risk", "Viable if fit is good"),
        ],
        "bugfix": [
            ("Fix root cause", "Permanent fix",
             "Higher risk of regression", "Preferred approach"),
            ("Hotfix / patch over symptom", "Quick to deploy",
             "Doesn't address root cause", "Only if root cause is too risky"),
        ],
        "refactor": [
            ("Keep existing structure, improve incrementally",
             "Lower risk, easier to review",
             "Slower, may leave inconsistencies", "Good for M effort"),
            ("Rewrite from scratch", "Clean slate, no tech debt",
             "High risk, longer timeline", "Only if current code is unmaintainable"),
        ],
        "architecture": [
            ("Incremental migration", "Lower risk, works alongside existing system",
             "Takes longer, dual maintenance", "Preferred for active projects"),
            ("Big-bang rewrite", "Faster in calendar time, clean break",
             "Extremely high risk, no rollback", "Only for greenfield projects"),
        ],
    }
    alts = alternatives.get(task_type, alternatives["feature"])
    lines = []
    for i, (name, pros, cons, rejected_reason) in enumerate(alts, 1):
        lines.append(f"{i}. **{name}**")
        lines.append(f"   - Pros: {pros}")
        lines.append(f"   - Cons: {cons}")
        lines.append(f"   - Why rejected: {rejected_reason}")
    return "\n".join(lines)


def _make_risks(project_scan: dict, task_type: str) -> str:
    """Generate concrete risks from project scan + task type."""
    risks = []
    deps = project_scan.get("stack", {}).get("dependencies", [])
    framework = project_scan.get("stack", {}).get("framework", "")

    if "supabase" in deps or "@supabase/supabase-js" in deps:
        risks.append("- Database schema migration may be needed — review Supabase migrations")
        risks.append("- Auth changes could affect existing sessions — test with real users")
    if "next" in deps or framework == "next":
        risks.append("- App Router changes affect routing — verify no broken links")
        risks.append("- Server component vs client component boundaries must be correct")
    if task_type in ("architecture", "refactor"):
        risks.append("- High regression risk — ensure test coverage before merging")
    if task_type in ("feature", "architecture"):
        risks.append("- New dependencies increase maintenance surface — evaluate carefully")

    if not risks:
        risks.append("- (Identify during review — scan didn't find framework-specific concerns)")

    return "\n".join(risks)


def _make_implementation_steps(task_type: str, area: str) -> str:
    """Generate concrete implementation steps from task type + area."""
    all_steps = {
        "feature": [
            "1. Scaffold the component/module structure",
            "2. Implement core logic",
            "3. Wire up data layer (API calls, database, state)",
            "4. Add UI components and pages",
            "5. Write tests",
        ],
        "bugfix": [
            "1. Reproduce the bug — write a test that fails",
            "2. Identify root cause in the codebase",
            "3. Apply the fix",
            "4. Verify all existing tests still pass",
            "5. Deploy the hotfix",
        ],
        "refactor": [
            "1. Map current code paths and identify the target pattern",
            "2. Write adapter/compatibility layer if needed",
            "3. Refactor one module at a time",
            "4. Run full test suite after each module",
            "5. Remove old code and verify no regression",
        ],
        "architecture": [
            "1. Document current architecture and pain points",
            "2. Design the target architecture",
            "3. Plan migration path with rollback points",
            "4. Implement core infrastructure changes",
            "5. Migrate one domain at a time",
        ],
    }
    steps = all_steps.get(task_type, all_steps["feature"])
    if area:
        steps.append(f"6. Verify {area} integration points")
    return "\n".join(steps)


# ── Generate RFC ──
def rfc_generate(task: dict, project_scan: dict = None) -> McpResult:
    """
    Auto-generate an RFC for a task by scanning the actual codebase.
    The RFC is a PROPOSAL — the developer reviews and approves/rejects it.
    No more 'Athena will fill in' — code scans the project and generates real data.
    """
    task_id = task["id"]
    title = task["title"]
    task_type = task.get("type", "feature")
    effort = task.get("effort", "M")
    area = task.get("area", "")
    description = task.get("description", "")

    # Auto-scan project if no scan provided — code enforces, prompts describe
    if project_scan is None:
        try:
            project_scan = scan_project()
        except Exception as e:
            write_log("RFC", "Athena", "scan_failed", {"error": str(e)})
            project_scan = {"stack": {"dependencies": [], "dev_dependencies": [], "scripts": [], "framework": ""},
                            "files": [], "components": [], "pages": [], "api_routes": [], "directories": [],
                            "common_imports": []}

    # Generated sections — all real, no placeholders
    design_hint = _make_design_hints(project_scan)
    related_files = _find_related_files(project_scan, title)
    alternatives_text = _make_alternatives(task_type)
    risks_text = _make_risks(project_scan, task_type)
    steps_text = _make_implementation_steps(task_type, area)

    # Motivation — specific to task type
    motivation_map = {
        "feature": "This feature adds new functionality to the project.",
        "bugfix": "This fix addresses a bug affecting users.",
        "refactor": "This refactor improves code quality without changing behavior.",
        "architecture": "This change affects the project's architecture.",
    }
    motivation = motivation_map.get(task_type, "This task addresses a specific need in the project.")

    # Get existing rules
    try:
        from memory import read_rules
        rules_text = read_rules()
        rules_section = rules_text if rules_text != "(no rules set)" else "(no rules set)"
    except ImportError:
        rules_section = "(unable to load rules — memory module not available)"
    except Exception as e:
        write_log("RFC", "Athena", "load_rules_failed", {"error": str(e)})
        rules_section = "(unable to load rules)"

    # Get existing ADRs
    try:
        from memory import list_adrs
        adrs_result = list_adrs()
        adrs = adrs_result.data.get("adrs", [])
        adrs_section = "\n".join(f"- {a['file']}: {a['title']}" for a in adrs) if adrs else "(no ADRs yet)"
    except ImportError:
        adrs_section = "(unable to load ADRs — memory module not available)"
    except Exception as e:
        write_log("RFC", "Athena", "load_adrs_failed", {"error": str(e)})
        adrs_section = "(unable to load ADRs)"

    # Build project context summary from scan
    if project_scan.get("files"):
        file_count = len(project_scan["files"])
        dir_count = len(project_scan["directories"])
        common_imports = project_scan.get("common_imports", [])
        imp_text = f"Common imports: {', '.join(common_imports[:5])}" if common_imports else ""
        project_context = (
            f"**Project structure:** {file_count} source files in {dir_count} directories\n"
            + (f"{imp_text}\n" if imp_text else "")
        )
    else:
        project_context = ""

    rfc_content = f"""# RFC: {title}

- **Task ID:** {task_id}
- **Type:** {task_type}
- **Effort:** {effort}
- **Area:** {area or "n/a"}
- **Status:** Proposed
- **Created:** {utc_now()}

## Summary

{description or f"{task_type} to {title.lower().strip()}. See Motivation and Design for details."}

## Motivation

{motivation}

## Detailed Design

{design_hint}

### Project Context

{project_context or "(no source files detected — this is likely a new project)"}

### Implementation Steps

{steps_text}

### Files to Create/Modify

{related_files}

## Alternatives Considered

{alternatives_text}

## Risks

{risks_text}

## Existing Rules

{rules_section}

## Related ADRs

{adrs_section}

## Open Questions for Developer

- Review the implementation steps above — do they cover everything?
- Are there any constraints not captured here?
- Is the effort estimate ({effort}) accurate for this approach?

---

*This RFC was auto-generated by WebForge with real project data. Review it, then:*
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
    except ImportError:
        pass  # Task module not available
    except Exception as e:
        write_log("RFC", "Athena", "move_to_backlog_failed",
                  {"task_id": task_id, "error": str(e)})

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
