#!/usr/bin/env python3
"""
Dispatch MCP — the chain of command (solves the routing gap)

THE PROBLEM:
  1. Task is created → nobody knows which department should get it
  2. Department head gets notified → doesn't automatically route down
  3. Work finishes → nobody automatically reports up

THE SOLUTION:
  Every task routes through the chain of command automatically:
    Developer → Department Head → Tech Lead → Senior → Junior
    Junior → Senior → Tech Lead → Department Head → Developer

  Auto-routing on task creation:
    - Feature/Bugfix/Refactor  → Hephaestus (Build)
    - Research/Architecture    → Athena (Intelligence)
    - Test                     → Minos (Quality)
    - Docs                     → Thoth (Documentation)

  Auto-routing on task assignment:
    - Each level auto-pings the next level down
    - Each level auto-reports back up when done

  Commands:
    /dispatch <task-id>             — Show routing for a task
    /dispatch-route <task-id>       — Auto-route a task (if not already)
    /dispatch-chain [agent]         — Show chain of command for an agent
    /dispatch-pending               — Show all un-routed or stuck tasks
"""

import os
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import write_log, success, fail, utc_now, McpResult, get_project_root
from memory import session_append


def info() -> dict:
    return {
        "id": "m-dispatch",
        "name": "Dispatch MCP",
        "tier": 1,
        "owner": "Hermes",
        "job": "Routes tasks through the chain of command. Every task goes to the right department, then down to the right person, and results flow back up.",
    }


# ── Department Routing Table ──
# Maps task type → department → department head
TASK_TYPE_TO_DEPT = {
    "feature": "build",
    "bugfix": "build",
    "refactor": "build",
    "test": "quality",
    "docs": "documentation",
    "research": "intelligence",
    "architecture": "intelligence",
    "design": "intelligence",
    "ui": "intelligence",
    "security": "quality",
    "devops": "build",
    "content": "documentation",
}

DEPARTMENT_HEADS = {
    "build": "Hephaestus",
    "frontend": "Aurora",
    "backend": "Titan",
    "database": "Zephyr",
    "intelligence": "Athena",
    "quality": "Minos",
    "documentation": "Thoth",
    "meta": "Daedalus",
    "executive": "Hermes",
    "hr": "Voss",
}

# Chain of command for each department (top → bottom)
CHAIN_OF_COMMAND = {
    "build": {
        "director": "Hephaestus",
        "head_frontend": "Aurora",
        "head_backend": "Titan",
        "head_database": "Zephyr",
        "tech_lead_frontend": "Lead-Faro",
        "tech_lead_backend": "Lead-Terra",
        "tech_lead_database": "Lead-Zen",
        "seniors_frontend": ["Sr-Hale", "Sr-Vance", "Sr-Brook", "Sr-Quill2"],
        "seniors_backend": ["Sr-Stone", "Sr-Iron", "Sr-Wood", "Sr-Steel"],
        "seniors_database": ["Sr-Cloud", "Sr-Earth", "Sr-Fire", "Sr-Water"],
        "juniors_frontend": ["Jr-Hawk", "Jr-Finch", "Jr-Wisp", "Jr-Cole", "Jr-Reed",
                            "Jr-Sage", "Jr-Birch", "Jr-Pike", "Jr-Moss", "Jr-Cliff",
                            "Jr-Fern", "Jr-Slate", "Jr-Wren", "Jr-Cove", "Jr-Bram",
                            "Jr-Talon", "Jr-Aster"],
        "juniors_backend": ["Jr-Granite", "Jr-Slate", "Jr-Marble", "Jr-Quartz",
                           "Jr-Copper", "Jr-Bronze", "Jr-Silver", "Jr-Gold",
                           "Jr-Oak", "Jr-Pine", "Jr-Cedar", "Jr-Birch",
                           "Jr-Titan", "Jr-Vanadium", "Jr-Chromium", "Jr-Nickel", "Jr-Cobalt"],
        "juniors_database": ["Jr-Sky", "Jr-Storm", "Jr-Rain", "Jr-Wind",
                            "Jr-Mountain", "Jr-Hill", "Jr-Valley", "Jr-Plain",
                            "Jr-Flame", "Jr-Ember", "Jr-Ash", "Jr-Coal",
                            "Jr-River", "Jr-Lake", "Jr-Ocean", "Jr-Sea", "Jr-Lake2"],
    },
    "intelligence": {
        "director": "Athena",
        "probe_team": ["Probe-Orion", "Probe-Wren", "Probe-Beacon", "Probe-Sable",
                       "Probe-Quartz", "Probe-Flint", "Probe-Ridge", "Probe-Marsh",
                       "Probe-Coral", "Probe-Vale", "Probe-Thorne", "Probe-Brisk",
                       "Probe-Hollow", "Probe-Crag", "Probe-Drift", "Probe-Ember", "Probe-Lyric"],
        "odin_team": ["Odin-Sage", "Odin-Reed", "Odin-Birch", "Odin-Cliff",
                      "Odin-Moss", "Odin-Slate", "Odin-Fern", "Odin-Pike",
                      "Odin-Wisp", "Odin-Cove", "Odin-Bramble", "Odin-Talon",
                      "Odin-Marrow", "Odin-Glade", "Odin-Heron", "Odin-Frost", "Odin-Aster"],
        "ui_researcher": "Dorian",
    },
    "quality": {
        "director": "Minos",
        "standards": "Verdict team (17 agents)",
        "unit_tests": "Pixel team (17 agents)",
        "e2e_tests": "Scalpel team (17 agents)",
        "security": "Janus team (17 agents)",
        "bug_fixes": "Pulse team (17 agents)",
    },
    "documentation": {
        "director": "Thoth",
        "quill_team": ["Quill", "Scroll", "Stamp", "Ledger", "Draft"],
        "memory_team": ["Memory-Architecture", "Memory-Choices", "Memory-Forgotten"],
    },
}


# ── Routing storage ──
def routing_file() -> Path:
    d = get_project_root() / ".webforge" / "routing"
    d.mkdir(parents=True, exist_ok=True)
    return d / "routes.json"


def load_routes() -> dict:
    rf = routing_file()
    if rf.exists():
        return json.loads(rf.read_text())
    return {"routes": []}


def save_routes(data: dict):
    routing_file().write_text(json.dumps(data, indent=2, ensure_ascii=False))


# ── Core routing logic ──
def get_department(task_type: str) -> str:
    """Get the department name for a task type."""
    return TASK_TYPE_TO_DEPT.get(task_type, "build")


def get_department_head(department: str) -> str:
    """Get the department head for a department."""
    return DEPARTMENT_HEADS.get(department, "Hephaestus")


def route_task(task_id: str, from_agent: str = "Hermes") -> McpResult:
    """
    Route a task to the right department head.
    Uses task_pick to assign ownership and notify to ping them.
    """
    # Load the task from the board
    sys.path.insert(0, str(Path(__file__).parent))
    from task import load_board, find_task

    board = load_board()
    task = find_task(board, task_id)

    if not task:
        return fail(f"Task not found: {task_id}")

    # Already routed?
    routes = load_routes()
    for r in routes["routes"]:
        if r["task_id"] == task_id and r["status"] == "routed":
            return success({
                "message": f"Task {task_id} already routed to @{r['routed_to']}",
                "route": r,
            })

    # Determine department
    dept = get_department(task.get("type", "feature"))
    dept_head = get_department_head(dept)

    # Pick the task (assign ownership to department head)
    try:
        from task import task_pick
        pick_result = task_pick(task_id, dept_head, bypass_gate=True)
        if not pick_result.ok:
            return fail(f"Could not assign task: {pick_result.error}")
    except Exception as e:
        return fail(f"Could not assign task: {e}")

    # Notify the department head
    try:
        from notify import notify_task_assigned
        notify_task_assigned(task_id, task["title"], dept_head, from_agent=from_agent)
    except Exception as e:
        write_log("Dispatch", from_agent, "notify_failed",
                  {"task_id": task_id, "error": str(e)})

    # Record the route
    route = {
        "task_id": task_id,
        "title": task["title"],
        "type": task["type"],
        "department": dept,
        "routed_to": dept_head,
        "routed_by": from_agent,
        "status": "routed",
        "routed_at": utc_now(),
        "chain_position": "department_head",
    }
    routes["routes"].append(route)
    save_routes(routes)

    # Log
    session_append(
        f"DISPATCH → {task_id}: {task['title']} → @{dept_head} ({dept})",
        agent=from_agent, kind="note"
    )
    write_log("Dispatch", from_agent, "route",
              {"task_id": task_id, "department": dept, "head": dept_head})

    return success({
        "message": f"📬 Task {task_id} routed to @{dept_head} ({dept} department)",
        "route": route,
    })


def _build_agent_ranks() -> dict[str, int]:
    """
    Build a flat map of agent_name → rank (lower = higher authority).
    Sources: CHAIN_OF_COMMAND dict + skills/ directory naming patterns.
    
    Rank tiers:
        0   = CEO
        100 = Hermes (COO)
        200 = Department Directors (Hephaestus, Athena, Minos, Thoth)
        300 = Department Heads (Aurora, Titan, Zephyr, Dorian, etc.)
        400 = Leads (Lead-*, etc.)
        500 = Seniors, Specialists (Sr-*, Probe-*, Odin-*, Verdict, etc.)
        600 = Juniors (Jr-*)
    """
    ranks: dict[str, int] = {}

    # ── Executive tier ──
    ranks["CEO"] = 0
    ranks["Hermes"] = 100

    # ── Extract from CHAIN_OF_COMMAND ──
    for dept_name, dept_config in CHAIN_OF_COMMAND.items():
        if not isinstance(dept_config, dict):
            continue

        # Directors (rank 200)
        director = dept_config.get("director", "")
        if director and director not in ranks:
            ranks[director] = 200

        # Department heads (rank 300) — any key containing "head"
        for key, value in dept_config.items():
            if "head" in key and isinstance(value, str) and value not in ranks:
                ranks[value] = 300

        # Leads / Tech Leads / Senior Editors (rank 400)
        for key in ["tech_lead", "tech_lead_frontend", "tech_lead_backend", "tech_lead_database",
                     "lead", "senior_editor"]:
            value = dept_config.get(key, "")
            if isinstance(value, str) and value and value not in ranks:
                ranks[value] = 400
            elif isinstance(value, list):
                for agent in value:
                    if agent not in ranks:
                        ranks[agent] = 400

        # Seniors (rank 500)
        for key in dept_config:
            if key.startswith("senior"):
                value = dept_config[key]
                if isinstance(value, str) and value not in ranks:
                    ranks[value] = 500
                elif isinstance(value, list):
                    for agent in value:
                        if agent not in ranks:
                            ranks[agent] = 500

        # Juniors (rank 600)
        for key in dept_config:
            if key.startswith("junior"):
                value = dept_config[key]
                if isinstance(value, str) and value not in ranks:
                    ranks[value] = 600
                elif isinstance(value, list):
                    for agent in value:
                        if agent not in ranks:
                            ranks[agent] = 600

        # Intelligence specialist teams (Probe-*, Odin-*) → rank 500
        for key in dept_config:
            if key in ("probe_team", "odin_team", "quill_team", "memory_team"):
                for agent in dept_config.get(key, []):
                    if agent not in ranks:
                        ranks[agent] = 500

    # ── Scan skills directory for any agents not yet ranked ──
    try:
        skills_dir = Path(__file__).parent.parent / "skills"
        if skills_dir.is_dir():
            for dept_dir in sorted(skills_dir.iterdir()):
                if not dept_dir.is_dir():
                    continue
                for skill_file in sorted(dept_dir.glob("*.md")):
                    name = skill_file.stem
                    if name not in ranks:
                        # Determine rank from name pattern
                        if name.startswith("Jr-") or name.startswith("Draft"):
                            ranks[name] = 600
                        elif name.startswith(("Sr-", "Probe-", "Odin-")):
                            ranks[name] = 500
                        elif name.startswith("Lead-"):
                            ranks[name] = 400
                        elif name in ("Quill", "Scroll", "Stamp", "Ledger"):
                            ranks[name] = 500
                        elif name in ("Memory-Architecture", "Memory-Choices", "Memory-Forgotten"):
                            ranks[name] = 500
                        else:
                            # Default: specialist (rank 500)
                            ranks[name] = 500
    except (OSError, ImportError, AttributeError):
        pass  # Skills directory may not exist — use CHAIN_OF_COMMAND only

    return ranks

_AGENT_RANKS: dict[str, int] = _build_agent_ranks()

def _validate_route_down(from_agent: str, to_agent: str) -> str | None:
    """Return error message if from_agent is NOT above to_agent. None = valid."""
    f_rank = _AGENT_RANKS.get(from_agent)
    t_rank = _AGENT_RANKS.get(to_agent)
    if f_rank is None:
        return f"'{from_agent}' is not in the chain of command"
    if t_rank is None:
        return f"'{to_agent}' is not in the chain of command"
    if f_rank >= t_rank:
        return (f"'{from_agent}' (rank {f_rank}) is not above "
                f"'{to_agent}' (rank {t_rank}) in chain of command")
    return None

def route_down(task_id: str, to_agent: str, from_agent: str = "") -> McpResult:
    """
    Route a task DOWN the chain from one agent to another.
    e.g., Department Head → Tech Lead, or Tech Lead → Senior, or Senior → Junior
    """
    # Load the task
    sys.path.insert(0, str(Path(__file__).parent))
    from task import load_board, find_task, task_pick

    board = load_board()
    task = find_task(board, task_id)

    if not task:
        return fail(f"Task not found: {task_id}")

    # ── Chain-of-command validation ──
    if from_agent:
        error = _validate_route_down(from_agent, to_agent)
        if error:
            write_log("Dispatch", from_agent, "route_down_rejected",
                      {"task_id": task_id, "from": from_agent,
                       "to": to_agent, "reason": error})
            return fail(f"Route down rejected: {error}")

    # Assign to the new agent
    pick_result = task_pick(task_id, to_agent, bypass_gate=True)
    if not pick_result.ok:
        return fail(f"Could not assign: {pick_result.error}")

    # Notify the new agent
    try:
        from notify import notify
        notify(
            agent_name=to_agent,
            event="TASK_ASSIGNED",
            message=f"Task {task_id} assigned to you from @{from_agent}: {task['title']}",
            task_id=task_id,
            from_agent=from_agent or "Dispatch",
        )
    except Exception as e:
        write_log("Dispatch", to_agent, "notify_failed",
                  {"error": str(e), "task_id": task_id})

    # Record the route
    routes = load_routes()
    route = {
        "task_id": task_id,
        "title": task["title"],
        "routed_from": from_agent,
        "routed_to": to_agent,
        "status": "routed",
        "routed_at": utc_now(),
        "chain_position": "down",
    }
    routes["routes"].append(route)
    save_routes(routes)

    session_append(
        f"DISPATCH DOWN → {task_id}: {task['title']} → @{from_agent} → @{to_agent}",
        agent=from_agent or "System", kind="note"
    )

    return success({
        "message": f"📬 Task {task_id} routed down: @{from_agent} → @{to_agent}",
    })


def route_up(task_id: str, from_agent: str, to_agent: str = "") -> McpResult:
    """
    Route a task UP the chain (report completion or progress).
    If to_agent is empty, route up one level automatically.
    """
    routes = load_routes()
    task_routes = [r for r in routes["routes"] if r["task_id"] == task_id]

    if not to_agent:
        # Find who routed it down to from_agent
        for r in reversed(task_routes):
            if r.get("routed_to", "").lower() == from_agent.lower():
                to_agent = r.get("routed_from", "Hermes")
                break
        if not to_agent:
            to_agent = "Hermes"

    route = {
        "task_id": task_id,
        "routed_from": from_agent,
        "routed_to": to_agent,
        "status": "reporting_up",
        "routed_at": utc_now(),
        "chain_position": "up",
    }
    routes["routes"].append(route)
    save_routes(routes)

    # Notify the agent up the chain
    try:
        from notify import notify
        notify(
            agent_name=to_agent,
            event="TASK_DONE",
            message=f"@{from_agent} reports task {task_id} is ready for your review",
            task_id=task_id,
            from_agent=from_agent,
        )
    except Exception as e:
        write_log("Dispatch", from_agent, "notify_failed",
                  {"task_id": task_id, "error": str(e)})

    session_append(
        f"DISPATCH UP → {task_id}: @{from_agent} → @{to_agent}",
        agent=from_agent, kind="note"
    )

    return success({
        "message": f"📬 @{from_agent} reports up to @{to_agent} for task {task_id}",
    })


# ── Show dispatch status ──
def dispatch_status(task_id: str = "") -> McpResult:
    """Show the routing status of tasks."""
    routes = load_routes()

    if task_id:
        task_routes = [r for r in routes["routes"] if r["task_id"] == task_id]
        if not task_routes:
            return success({"message": f"Task {task_id} has not been routed yet. Use /dispatch-route {task_id}"})

        lines = [f"DISPATCH HISTORY — {task_id}"]
        lines.append("=" * 50)
        for r in task_routes:
            status_icon = "📤" if r["chain_position"] == "down" else "📥" if r["chain_position"] == "up" else "📬"
            lines.append(f"  {status_icon} {r['routed_from']} → {r['routed_to']} ({r['status']})")
        return success({"message": "\n".join(lines), "routes": task_routes})

    # Show all pending/routed tasks
    lines = ["DISPATCH STATUS", "=" * 60, ""]

    # Group by task
    by_task = {}
    for r in routes["routes"]:
        tid = r["task_id"]
        if tid not in by_task:
            by_task[tid] = []
        by_task[tid].append(r)

    if not by_task:
        lines.append("  No tasks have been routed yet.")
    else:
        for tid, task_routes in by_task.items():
            last = task_routes[-1]
            icon = "✅" if last["status"] == "done" else "🔄" if last["chain_position"] == "down" else "📬"
            lines.append(f"  {icon} {tid}: {last.get('title', '')}")
            for r in task_routes:
                arrow = "↓" if r["chain_position"] == "down" else "↑" if r["chain_position"] == "up" else "→"
                lines.append(f"       {arrow} {r.get('routed_from', '?')} → {r.get('routed_to', '?')}")
            lines.append("")

    return success({"message": "\n".join(lines)})


def pending_tasks() -> McpResult:
    """Show tasks on the board that haven't been routed yet."""
    sys.path.insert(0, str(Path(__file__).parent))
    from task import load_board

    board = load_board()
    routes = load_routes()
    routed_ids = {r["task_id"] for r in routes["routes"]}

    pending = [t for t in board["tasks"]
               if t["status"] in ("backlog", "todo") and t["id"] not in routed_ids]

    if not pending:
        return success({"message": "✅ All tasks have been routed.", "tasks": []})

    lines = ["📬 PENDING DISPATCH", "=" * 50]
    for t in pending:
        dept = get_department(t.get("type", "feature"))
        head = get_department_head(dept)
        lines.append(f"  {t['id']}: {t['title']} ({t['type']}) → should go to @{head}")

    return success({"message": "\n".join(lines), "tasks": pending})


# ── Show chain of command ──
def show_chain(agent_name: str = "") -> McpResult:
    """Show the chain of command for an agent or department."""
    if not agent_name:
        # Show all departments
        lines = ["CHAIN OF COMMAND", "=" * 60, ""]
        for dept, chain in CHAIN_OF_COMMAND.items():
            lines.append(f"  {dept.upper()}")
            lines.append(f"    Director: @{chain.get('director', '?')}")
            if "head_frontend" in chain:
                lines.append(f"    Frontend Head: @{chain['head_frontend']}")
                lines.append(f"    Tech Lead: @{chain['tech_lead_frontend']}")
                lines.append(f"    Seniors: {', '.join('@'+s for s in chain.get('seniors_frontend', []))}")
                lines.append(f"    Juniors: {', '.join('@'+j for j in chain.get('juniors_frontend', []))}")
            if "probe_team" in chain:
                lines.append(f"    Probe Team: {', '.join('@'+a for a in chain['probe_team'][:3])}...")
                lines.append(f"    Odin Team: {', '.join('@'+a for a in chain['odin_team'][:3])}...")
            if "quill_team" in chain:
                lines.append(f"    Team: {', '.join('@'+a for a in chain['quill_team'])}")
            lines.append("")
        return success({"message": "\n".join(lines)})

    # Find which department this agent belongs to
    dept_name = None
    role = None
    for dept, chain in CHAIN_OF_COMMAND.items():
        for key, value in chain.items():
            if isinstance(value, list):
                if agent_name.lower() in [a.lower() for a in value]:
                    dept_name = dept
                    role = key
                    break
            elif isinstance(value, str) and value.lower() == agent_name.lower():
                dept_name = dept
                role = key
                break

    if not dept_name:
        return fail(f"Agent @{agent_name} not found in any department chain.")

    chain = CHAIN_OF_COMMAND[dept_name]

    lines = [f"@{agent_name} — {role} ({dept_name})", "=" * 50]

    # Show who's above
    lines.append("")
    lines.append("  Reports UP to:")
    if role == "director":
        lines.append("    @Hermes (COO) → Developer (CEO)")
    elif role in ("head_frontend", "head_backend", "head_database"):
        lines.append(f"    @{chain['director']} (Director)")
    elif role in ("tech_lead_frontend", "tech_lead_backend", "tech_lead_database"):
        head_key = role.replace("tech_lead_", "head_")
        lines.append(f"    @{chain.get(head_key, '?')} (Department Head)")
    elif "seniors" in role or "senior" in role.lower():
        lines.append(f"    Tech Lead")
    elif "juniors" in role or "junior" in role.lower():
        lines.append(f"    Senior Dev")

    # Show who's below
    lines.append("")
    lines.append("  Routes DOWN to:")
    if role == "director":
        for key in chain:
            if key.startswith("head_"):
                lines.append(f"    @{chain[key]} ({key.replace('head_', '').title()})")
    elif role in ("head_frontend", "head_backend", "head_database"):
        tl_key = role.replace("head_", "tech_lead_")
        lines.append(f"    @{chain.get(tl_key, '?')} (Tech Lead)")
    elif role in ("tech_lead_frontend", "tech_lead_backend", "tech_lead_database"):
        prefix = role.replace("tech_lead_", "seniors_")
        for s in chain.get(prefix, []):
            lines.append(f"    @{s} (Senior)")
    elif "senior" in role.lower():
        prefix = role.replace("seniors_", "juniors_")
        for j in chain.get(prefix, []):
            lines.append(f"    @{j} (Junior)")
    elif "junior" in role.lower():
        lines.append("    (nobody — they do the actual work)")

    return success({"message": "\n".join(lines)})


# ── Auto-dispatch on task creation — routes through Hermes to department head ──
def auto_dispatch(task_id: str, task_type: str, title: str,
                  from_agent: str = "Agent") -> McpResult:
    """
    Called automatically when a task is created by ANY agent.
    Routes through Hermes to the correct department head in one shot.
    No AI intervention needed — the code knows where it should go.
    """
    sys.path.insert(0, str(Path(__file__).parent))
    from task import load_board, find_task, task_pick

    board = load_board()
    task = find_task(board, task_id)
    if not task:
        return fail(f"Task not found: {task_id}")

    dept = get_department(task_type)
    dept_head = get_department_head(dept)

    # Assign to Hermes first (for audit trail), then immediately route to dept head
    pick_result = task_pick(task_id, "Hermes", bypass_gate=True)
    if not pick_result.ok:
        return fail(f"Could not assign to Hermes: {pick_result.error}")

    # Record route to Hermes
    routes = load_routes()
    route = {
        "task_id": task_id,
        "title": title,
        "type": task_type,
        "routed_from": from_agent or "System",
        "routed_to": "Hermes",
        "status": "auto_routed",
        "routed_at": utc_now(),
        "chain_position": "hermes_inbox",
    }
    routes["routes"].append(route)
    save_routes(routes)

    # Immediately route to department head — no AI needed
    try:
        hermes_route(task_id, from_agent="System (auto-dispatch)")
    except Exception as e:
        write_log("Dispatch", "System", "auto_route_failed",
                  {"task_id": task_id, "error": str(e)})
        # Notify Hermes that auto-route failed
        try:
            from notify import notify
            notify(
                agent_name="Hermes",
                event="TASK_CREATED",
                message=f"Task {task_id} from @{from_agent}: {title}. Auto-route to @{dept_head} FAILED: {e}. Route manually with: /dispatch-route {task_id}",
                task_id=task_id,
                from_agent="System",
            )
        except Exception as notify_e:
            write_log("Dispatch", "System", "notify_failed",
                      {"task_id": task_id, "error": str(notify_e)})
        return fail(f"Auto-route failed: {e}")

    session_append(
        f"AUTO-DISPATCH → {task_id}: {title} → @Hermes → @{dept_head} ({dept})",
        agent=from_agent or "System", kind="note"
    )

    return success({
        "message": f"📬 Task {task_id} auto-routed through @Hermes to @{dept_head} ({dept})",
        "task_id": task_id,
        "assigned_to": dept_head,
        "department": dept,
        "department_head": dept_head,
    })


# ── Hermes routes to department head ──
def hermes_route(task_id: str, from_agent: str = "Hermes") -> McpResult:
    """
    Hermes routes a task from his inbox to the right department head.
    This is called after Hermes reviews a task.
    """
    # Determine department and route
    sys.path.insert(0, str(Path(__file__).parent))
    from task import load_board, find_task, task_pick

    board = load_board()
    task = find_task(board, task_id)
    if not task:
        return fail(f"Task not found: {task_id}")

    task_type = task.get("type", "feature")
    dept = get_department(task_type)
    dept_head = get_department_head(dept)

    # Assign to department head
    pick_result = task_pick(task_id, dept_head, bypass_gate=True)
    if not pick_result.ok:
        return fail(f"Could not assign to @{dept_head}: {pick_result.error}")

    # Notify department head
    try:
        from notify import notify_task_assigned
        notify_task_assigned(task_id, task["title"], dept_head, from_agent="Hermes")
    except Exception as e:
        write_log("Dispatch", "Hermes", "notify_failed",
                  {"task_id": task_id, "error": str(e)})

    # Record route from Hermes to dept head
    routes = load_routes()
    route = {
        "task_id": task_id,
        "title": task["title"],
        "routed_from": "Hermes",
        "routed_to": dept_head,
        "department": dept,
        "status": "routed",
        "routed_at": utc_now(),
        "chain_position": "hermes_to_dept",
    }
    routes["routes"].append(route)
    save_routes(routes)

    session_append(
        f"HERMES ROUTE → {task_id}: {task['title']} → @{dept_head} ({dept})",
        agent="Hermes", kind="note"
    )

    return success({
        "message": f"📬 Hermes routed task {task_id} to @{dept_head} ({dept})",
        "task_id": task_id,
        "routed_to": dept_head,
        "department": dept,
    })


# ── CLI ──
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Dispatch MCP — Chain of Command Router")
        print()
        print("Commands:")
        print("  route <task-id>              Route a task to its department head")
        print("  route-down <id> <agent>      Route a task DOWN to a specific agent")
        print("  route-up <id> [from] [to]    Route results UP the chain")
        print("  status [task-id]             Show routing status")
        print("  pending                      Show un-routed tasks")
        print("  chain [agent]                Show chain of command")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "info":
        print(json.dumps(info(), indent=2))
    elif cmd == "route":
        task_id = sys.argv[2] if len(sys.argv) > 2 else ""
        from_agent = sys.argv[3] if len(sys.argv) > 3 else "Hermes"
        if task_id:
            result = route_task(task_id, from_agent)
            print(result.data.get("message", result.to_dict()))
        else:
            print("Usage: route <task-id> [from-agent]")
    elif cmd == "route-down":
        task_id = sys.argv[2] if len(sys.argv) > 2 else ""
        to_agent = sys.argv[3] if len(sys.argv) > 3 else ""
        from_agent = sys.argv[4] if len(sys.argv) > 4 else "Dispatch"
        if task_id and to_agent:
            result = route_down(task_id, to_agent, from_agent)
            print(result.data.get("message", result.to_dict()))
        else:
            print("Usage: route-down <task-id> <to-agent> [from-agent]")
    elif cmd == "route-up":
        task_id = sys.argv[2] if len(sys.argv) > 2 else ""
        from_agent = sys.argv[3] if len(sys.argv) > 3 else ""
        to_agent = sys.argv[4] if len(sys.argv) > 4 else ""
        if task_id and from_agent:
            result = route_up(task_id, from_agent, to_agent)
            print(result.data.get("message", result.to_dict()))
        else:
            print("Usage: route-up <task-id> <from-agent> [to-agent]")
    elif cmd == "status":
        task_id = sys.argv[2] if len(sys.argv) > 2 else ""
        result = dispatch_status(task_id)
        print(result.data.get("message", result.to_dict()))
    elif cmd == "pending":
        result = pending_tasks()
        print(result.data.get("message", result.to_dict()))
    elif cmd == "chain":
        agent = sys.argv[2] if len(sys.argv) > 2 else ""
        result = show_chain(agent)
        print(result.data.get("message", result.to_dict()))
    else:
        print(f"Unknown command: {cmd}")
