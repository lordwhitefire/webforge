#!/usr/bin/env python3
"""
MCP 3 — Skill Loader MCP
Tier 1 — Foundation

When an agent starts a task, this MCP fetches the correct skill MD files
for that agent and that area. The agent does not search for its own files
— this MCP delivers them.

Owner: Hermes
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import SKILLS_DIR, write_log, success, fail, McpResult


def find_skill_files(agent_name: str, area: str = None) -> McpResult:
    """
    Find all skill MD files for a given agent.
    An agent can have multiple skill files (Law 4).
    Returns the list of file paths.

    Args:
        agent_name: e.g. "Probe-Orion", "Jr-Hawk", "Hermes"
        area: optional area filter, e.g. "01-05"
    """
    if not SKILLS_DIR.exists():
        return fail(f"Skills directory not found: {SKILLS_DIR}")

    # Normalize agent name to filename
    # Probe-Orion → probe-orion.md
    safe_name = agent_name.lower().replace(" ", "-")
    
    # Search all subdirectories
    matches = []
    for sub in SKILLS_DIR.iterdir():
        if not sub.is_dir():
            continue
        # Direct match: probe-orion.md
        direct = sub / f"{safe_name}.md"
        if direct.exists():
            matches.append(direct)
        # Multi-file: probe-orion-1.md, probe-orion-2.md (Law 2 split)
        for f in sub.glob(f"{safe_name}*.md"):
            if f not in matches:
                matches.append(f)

    if not matches:
        return fail(f"No skill files found for agent: {agent_name}")

    # Load content of each file
    files_data = []
    for f in sorted(matches):
        content = f.read_text(encoding="utf-8")
        files_data.append({
            "file": str(f),
            "name": f.name,
            "lines": content.count("\n") + 1,
            "content": content,
        })

    write_log("SkillLoader", "Hermes", "delivered_skills",
              {"agent": agent_name, "files": len(files_data), "area": area})
    return success({"agent": agent_name, "files": files_data})


def list_all_skills() -> McpResult:
    """List all skill files in the system."""
    if not SKILLS_DIR.exists():
        return fail(f"Skills directory not found: {SKILLS_DIR}")

    all_files = []
    for sub in SKILLS_DIR.iterdir():
        if not sub.is_dir():
            continue
        for f in sub.glob("*.md"):
            all_files.append({
                "department": sub.name,
                "file": f.name,
                "path": str(f),
                "lines": f.read_text(encoding="utf-8").count("\n") + 1,
            })
    return success({"total": len(all_files), "files": all_files})


def list_skills_for_department(dept: str) -> McpResult:
    """List all skill files in a department folder."""
    dept_dir = SKILLS_DIR / dept.lower()
    if not dept_dir.exists():
        return fail(f"Department not found: {dept}")

    files = []
    for f in sorted(dept_dir.glob("*.md")):
        content = f.read_text(encoding="utf-8")
        files.append({
            "file": f.name,
            "path": str(f),
            "lines": content.count("\n") + 1,
        })
    return success({"department": dept, "total": len(files), "files": files})


def check_skill_file_size() -> McpResult:
    """Check all skill files for Law 2 compliance (max 300 lines)."""
    from common import SKILL_MAX_LINES
    result = list_all_skills()
    if not result.ok:
        return result

    violations = []
    for f in result.data["files"]:
        if f["lines"] > SKILL_MAX_LINES:
            violations.append({
                "file": f["path"],
                "lines": f["lines"],
                "over_by": f["lines"] - SKILL_MAX_LINES,
            })
    return success({
        "total_files": result.data["total"],
        "violations": violations,
        "compliant": len(violations) == 0,
    })


# CLI
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python skill_loader.py <command> [args]")
        print("Commands: get <agent> [area], list, list-dept <dept>, check-size")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "get":
        agent = sys.argv[2]
        area = sys.argv[3] if len(sys.argv) > 3 else None
        result = find_skill_files(agent, area)
        if result.ok:
            print(f"Found {len(result.data['files'])} file(s) for {agent}:")
            for f in result.data["files"]:
                print(f"  - {f['name']} ({f['lines']} lines)")
        else:
            print(result.error)
    elif cmd == "list":
        result = list_all_skills()
        if result.ok:
            print(f"Total: {result.data['total']} skill files")
            for f in result.data["files"]:
                print(f"  {f['department']}/{f['file']} ({f['lines']} lines)")
        else:
            print(result.error)
    elif cmd == "list-dept":
        result = list_skills_for_department(sys.argv[2])
        if result.ok:
            print(f"Department: {result.data['department']}")
            print(f"Total: {result.data['total']} files")
            for f in result.data["files"]:
                print(f"  {f['file']} ({f['lines']} lines)")
        else:
            print(result.error)
    elif cmd == "check-size":
        result = check_skill_file_size()
        if result.ok:
            if result.data["compliant"]:
                print(f"All {result.data['total_files']} skill files are compliant (<= 300 lines)")
            else:
                print(f"VIOLATIONS ({len(result.data['violations'])}):")
                for v in result.data["violations"]:
                    print(f"  {v['file']}: {v['lines']} lines (over by {v['over_by']})")
        else:
            print(result.error)
    else:
        print(f"Unknown command: {cmd}")
