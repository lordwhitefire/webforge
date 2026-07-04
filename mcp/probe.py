#!/usr/bin/env python3
"""
Probe MCP v2 — scans an existing project, doesn't ask from scratch.

Two modes:
  - fresh:    For new projects. Asks the developer questions.
  - existing: For projects that already have code. Scans, doesn't ask.

This solves gap #8: "No incomplete project support"
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))
from common import write_log, success, fail, utc_now, McpResult, get_project_root


def info() -> dict:
    return {
        "id": "m-probe",
        "name": "Probe MCP v2",
        "tier": 1,
        "owner": "Athena",
        "job": "Scan project, identify what's decided/missing. Two modes: fresh, existing.",
    }


def scan_project() -> dict:
    """
    Scan an existing project and build a complete map.
    This is the 'existing' mode — no questions asked, just observation.
    """
    project = get_project_root()
    result = {
        "project_root": str(project),
        "scanned_at": utc_now(),
        "stack": {},
        "pages": [],
        "api_routes": [],
        "components": [],
        "data_files": [],
        "adrs": [],
        "env_files": [],
        "tests": [],
        "git_info": {},
        "stats": {},
    }

    # 1. package.json — identifies stack
    pkg_path = project / "package.json"
    if pkg_path.exists():
        try:
            pkg = json.loads(pkg_path.read_text())
            result["stack"] = {
                "name": pkg.get("name", "unknown"),
                "scripts": list(pkg.get("scripts", {}).keys()),
                "dependencies": list(pkg.get("dependencies", {}).keys()),
                "dev_dependencies": list(pkg.get("devDependencies", {}).keys()),
            }
        except Exception as _e:
            write_log("Probe", "Athena", "parse package.json", {"error": str(_e)})

    # 2. Pages (Next.js App Router)
    src_app = project / "src" / "app"
    if src_app.exists():
        pages = list(src_app.rglob("page.tsx")) + list(src_app.rglob("page.ts"))
        result["pages"] = [str(p.relative_to(project)) for p in pages]

    # 3. API routes
    api_dir = project / "src" / "app" / "api"
    if api_dir.exists():
        routes = list(api_dir.rglob("route.ts")) + list(api_dir.rglob("route.js"))
        result["api_routes"] = [str(r.relative_to(project)) for r in routes]

    # 4. Components
    components_dir = project / "src" / "components"
    if components_dir.exists():
        components = list(components_dir.rglob("*.tsx")) + list(components_dir.rglob("*.ts"))
        result["components"] = [str(c.relative_to(project)) for c in components]

    # 5. Data files (JSON)
    data_dir = project / "src" / "data"
    if data_dir.exists():
        data_files = list(data_dir.rglob("*.json"))
        result["data_files"] = [str(d.relative_to(project)) for d in data_files]

    # 6. ADRs
    adr_dir = project / "docs" / "adr"
    if adr_dir.exists():
        adrs = list(adr_dir.glob("*.md"))
        result["adrs"] = [str(a.relative_to(project)) for a in adrs]

    # 7. Env files
    for env_name in [".env", ".env.local", ".env.example", ".env.development", ".env.production"]:
        if (project / env_name).exists():
            result["env_files"].append(env_name)

    # 8. Tests
    test_patterns = ["**/*.test.ts", "**/*.test.tsx", "**/*.spec.ts", "**/*.spec.tsx"]
    for pattern in test_patterns:
        for t in project.rglob(pattern):
            if "node_modules" not in str(t):
                result["tests"].append(str(t.relative_to(project)))

    # 9. Git info
    try:
        log_result = subprocess.run(
            ["git", "log", "-10", "--oneline"],
            cwd=project, capture_output=True, text=True, timeout=5
        )
        if log_result.returncode == 0:
            result["git_info"]["recent_commits"] = log_result.stdout.strip().split("\n")

        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=project, capture_output=True, text=True, timeout=5
        )
        if status_result.returncode == 0:
            changes = [l for l in status_result.stdout.strip().split("\n") if l]
            result["git_info"]["uncommitted_changes"] = len(changes)
    except Exception as _e:
        write_log("Probe", "Athena", "get git info", {"error": str(_e)})

    # 10. Stats
    all_files = [f for f in project.rglob("*") if f.is_file()
                 and ".git" not in str(f) and "node_modules" not in str(f)
                 and ".next" not in str(f)]
    result["stats"]["total_files"] = len(all_files)

    by_ext = {}
    for f in all_files:
        ext = f.suffix or "(no ext)"
        by_ext[ext] = by_ext.get(ext, 0) + 1
    result["stats"]["by_extension"] = dict(sorted(by_ext.items(), key=lambda x: -x[1])[:15])

    return result


def probe_existing() -> McpResult:
    """
    Probe an existing project.
    Returns a complete map without asking the developer anything.
    """
    scan = scan_project()

    # Save the scan to memory
    sys.path.insert(0, str(Path(__file__).parent))
    try:
        from memory import session_append
        session_append(
            f"PROBE EXISTING — Scanned project. {scan['stats']['total_files']} files, "
            f"{len(scan['pages'])} pages, {len(scan['components'])} components, "
            f"{len(scan['api_routes'])} API routes, {len(scan['adrs'])} ADRs.",
            agent="Athena",
            kind="note"
        )
    except Exception as _e:
        write_log("Probe", "Athena", "save scan to memory", {"error": str(_e)})

    write_log("Probe", "Athena", "probe_existing", {
        "files": scan["stats"]["total_files"],
        "pages": len(scan["pages"]),
        "components": len(scan["components"]),
    })

    return success(scan)


def probe_fresh() -> McpResult:
    """
    Probe a fresh project (no code yet).
    Asks the developer questions.
    """
    # For fresh projects, we'd ask questions. But for now, just return a prompt.
    return success({
        "mode": "fresh",
        "message": "Fresh project detected. Use /areas to review the 88-area checklist.",
        "next_step": "Read AREAS.md and mark each area as [D] Decided, [S] Skip, or [P] Pending.",
    })


def probe(mode: str = "auto") -> McpResult:
    """
    Main entry point.
    mode: 'auto' (default), 'fresh', or 'existing'
    """
    if mode == "auto":
        # Detect: if there's a package.json or src/ folder, use 'existing'
        project = get_project_root()
        if (project / "package.json").exists() or (project / "src").exists():
            mode = "existing"
        else:
            mode = "fresh"

    if mode == "existing":
        return probe_existing()
    else:
        return probe_fresh()


# CLI
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Probe MCP v2")
        print("Usage: python probe.py <command> [args]")
        print()
        print("Commands:")
        print("  scan          Scan project and print map")
        print("  probe [mode]  Probe (auto/fresh/existing)")
        print("  info          Show MCP info")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "info":
        print(json.dumps(info(), indent=2))
    elif cmd == "scan":
        print(json.dumps(scan_project(), indent=2, default=str))
    elif cmd == "probe":
        mode = sys.argv[2] if len(sys.argv) > 2 else "auto"
        result = probe(mode)
        print(json.dumps(result.to_dict(), indent=2, default=str))
    else:
        print(f"Unknown command: {cmd}")
