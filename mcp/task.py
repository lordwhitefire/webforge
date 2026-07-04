#!/usr/bin/env python3
"""
Task MCP — Kanban-style task board for the Hephaestus department.

Replaces the rigid 13-step pipeline with a Kanban board:
  Backlog → TODO → DOING → DONE

WIP limits enforce focus (max items per column).

The /build command is an APPROVAL GATE:
  1. Find next unblocked task
  2. Propose it to the developer
  3. WAIT for approval (yes/no/pick different)
  4. Only then does the agent start

Industry patterns used:
  - Kanban (Atlassian, ProKanban) — visual board, WIP limits
  - Trunk-based dev (Google, Meta) — small tasks, merge often
  - Stacked diffs (Meta) — break large tasks into sub-tasks
  - Approval gates — developer reviews before agent acts (Law 5: No Inference)
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))
from common import write_log, success, fail, utc_now, McpResult, get_project_root
from memory import session_append


# ── Paths ──
def tasks_dir() -> Path:
    d = get_project_root() / ".webforge" / "tasks"
    d.mkdir(parents=True, exist_ok=True)
    return d

def board_file() -> Path:
    return tasks_dir() / "board.json"

# ── WIP limits (industry standard: small to force focus) ──
WIP_LIMITS = {
    "todo": 3,   # max 3 tasks ready to start
    "doing": 2,  # max 2 tasks in progress (focus, don't multitask)
}


def info() -> dict:
    return {
        "id": "m-task",
        "name": "Task MCP",
        "tier": 2,
        "owner": "Hephaestus",
        "job": "Kanban task board. Replaces rigid 13-step pipeline. Developer approves before agents start.",
    }


# ── Board management ──
def load_board() -> dict:
    """Load the board state."""
    bf = board_file()
    if not bf.exists():
        board = {
            "tasks": [],
            "next_id": 1,
            "wip_limits": WIP_LIMITS,
        }
        save_board(board)
        return board
    return json.loads(bf.read_text())

def save_board(board: dict):
    board_file().write_text(json.dumps(board, indent=2, ensure_ascii=False))

def find_task(board: dict, task_id: str) -> dict:
    for t in board["tasks"]:
        if t["id"] == task_id:
            return t
    return None


# ── Create task ──
def task_create(title: str, task_type: str = "feature", area: str = "",
                effort: str = "M", description: str = "") -> McpResult:
    """
    Create a new task in the backlog.
    task_type: feature, bugfix, refactor, test, docs
    effort: S, M, L
    """
    board = load_board()
    task_id = f"task-{board['next_id']:03d}"
    board["next_id"] += 1

    task = {
        "id": task_id,
        "title": title,
        "description": description,
        "type": task_type,
        "area": area,
        "effort": effort,
        "status": "backlog",
        "owner": None,
        "blocked_by": [],
        "created_at": utc_now(),
        "started_at": None,
        "completed_at": None,
    }
    board["tasks"].append(task)
    save_board(board)

    session_append(f"TASK CREATED — {task_id}: {title} ({task_type}, {effort})",
                   agent="Developer", kind="note")
    write_log("Task", "Hephaestus", "task_create",
              {"id": task_id, "title": title, "type": task_type})
    return success({"task": task, "id": task_id})


# ── List tasks / show board ──
def task_list(status: str = "all") -> McpResult:
    """List tasks. Status: all, backlog, todo, doing, done, blocked."""
    board = load_board()
    if status == "all":
        tasks = board["tasks"]
    else:
        tasks = [t for t in board["tasks"] if t["status"] == status]
    return success({"tasks": tasks, "count": len(tasks)})


def show_board() -> McpResult:
    """Show the full Kanban board."""
    board = load_board()
    columns = {
        "backlog": [],
        "todo": [],
        "doing": [],
        "done": [],
        "blocked": [],
    }
    for t in board["tasks"]:
        if t["status"] in columns:
            columns[t["status"]].append(t)

    # Format as text
    lines = []
    lines.append("=" * 70)
    lines.append("WEBFORGE KANBAN BOARD")
    lines.append("=" * 70)
    lines.append("")

    for col, tasks in columns.items():
        wip = WIP_LIMITS.get(col)
        wip_label = f" (WIP: {len(tasks)}/{wip})" if wip else f" ({len(tasks)})"
        lines.append(f"┌── {col.upper()}{wip_label} " + "─" * (50 - len(col) - len(wip_label)) + "┐")
        if not tasks:
            lines.append("│  (empty)                                                              │")
        else:
            for t in tasks[:10]:  # Show max 10 per column
                owner = f" [{t['owner']}]" if t["owner"] else ""
                effort_badge = {"S": "🟢", "M": "🟡", "L": "🔴"}.get(t["effort"], "⚪")
                title = t["title"][:50]
                lines.append(f"│  {effort_badge} {t['id']}: {title}{owner}".ljust(73) + "│")
        lines.append("└" + "─" * 71 + "└")
        lines.append("")

    lines.append("=" * 70)
    lines.append(f"Total tasks: {len(board['tasks'])} | "
                 f"Backlog: {len(columns['backlog'])} | "
                 f"TODO: {len(columns['todo'])} | "
                 f"DOING: {len(columns['doing'])} | "
                 f"Done: {len(columns['done'])} | "
                 f"Blocked: {len(columns['blocked'])}")
    lines.append("=" * 70)

    return success({"board_text": "\n".join(lines), "columns": {k: len(v) for k, v in columns.items()}})


# ── Move task (respects WIP limits) ──
def task_move(task_id: str, new_status: str) -> McpResult:
    """Move a task to a new status. Respects WIP limits."""
    if new_status not in ("backlog", "todo", "doing", "done", "blocked"):
        return fail(f"Invalid status: {new_status}")

    board = load_board()
    task = find_task(board, task_id)
    if not task:
        return fail(f"Task not found: {task_id}")

    # Check WIP limit
    if new_status in WIP_LIMITS:
        current_count = sum(1 for t in board["tasks"] if t["status"] == new_status)
        if current_count >= WIP_LIMITS[new_status]:
            return fail(f"WIP limit reached for '{new_status}' ({WIP_LIMITS[new_status]}). "
                        f"Move something out of {new_status} first.")

    old_status = task["status"]
    task["status"] = new_status

    # Track timestamps
    if new_status == "doing" and not task["started_at"]:
        task["started_at"] = utc_now()
    if new_status == "done" and not task["completed_at"]:
        task["completed_at"] = utc_now()

    save_board(board)

    session_append(f"TASK MOVED — {task_id}: {old_status} → {new_status}",
                   agent="Hephaestus", kind="note")
    write_log("Task", "Hephaestus", "task_move",
              {"id": task_id, "from": old_status, "to": new_status})
    return success({"task": task, "moved_from": old_status, "moved_to": new_status})


# ── Pick task (assign owner + move to doing) ──
def task_pick(task_id: str, agent: str) -> McpResult:
    """An agent picks up a task — assigns ownership and moves to DOING."""
    board = load_board()
    task = find_task(board, task_id)
    if not task:
        return fail(f"Task not found: {task_id}")

    # Check WIP for doing
    doing_count = sum(1 for t in board["tasks"] if t["status"] == "doing")
    if doing_count >= WIP_LIMITS["doing"] and task["status"] != "doing":
        return fail(f"DOING WIP limit reached ({WIP_LIMITS['doing']}). "
                    f"Finish a task first.")

    task["owner"] = agent
    old_status = task["status"]
    task["status"] = "doing"
    if not task["started_at"]:
        task["started_at"] = utc_now()

    save_board(board)
    session_append(f"TASK PICKED — {task_id}: {task['title']} (by {agent})",
                   agent=agent, kind="note")
    write_log("Task", agent, "task_pick",
              {"id": task_id, "title": task["title"]})
    return success({"task": task, "picked_by": agent})


# ── Mark task done ──
def task_done(task_id: str, summary: str = "") -> McpResult:
    """Mark a task as done. Logs to session."""
    board = load_board()
    task = find_task(board, task_id)
    if not task:
        return fail(f"Task not found: {task_id}")

    task["status"] = "done"
    task["completed_at"] = utc_now()
    save_board(board)

    log_msg = f"TASK DONE — {task_id}: {task['title']}"
    if summary:
        log_msg += f" — {summary}"
    session_append(log_msg, agent=task.get("owner") or "Hephaestus", kind="decision")
    write_log("Task", task.get("owner", "Hephaestus"), "task_done",
              {"id": task_id, "title": task["title"]})
    return success({"task": task})


# ── Block / unblock ──
def task_block(task_id: str, reason: str) -> McpResult:
    board = load_board()
    task = find_task(board, task_id)
    if not task:
        return fail(f"Task not found: {task_id}")
    task["status"] = "blocked"
    task["block_reason"] = reason
    save_board(board)
    session_append(f"TASK BLOCKED — {task_id}: {reason}",
                   agent="Hephaestus", kind="note")
    return success({"task": task})


def task_unblock(task_id: str) -> McpResult:
    board = load_board()
    task = find_task(board, task_id)
    if not task:
        return fail(f"Task not found: {task_id}")
    task["status"] = "todo"
    task.pop("block_reason", None)
    save_board(board)
    return success({"task": task})


# ── The approval gate: propose next task ──
def propose_next() -> McpResult:
    """
    Find the next unblocked task to work on.
    Returns it for developer approval.

    Priority:
      1. Top task in TODO (already prioritized)
      2. Top task in BACKLOG (auto-promote to TODO)

    Does NOT auto-start. Developer must approve.
    """
    board = load_board()

    # Check WIP for DOING — if at limit, no new task
    doing_count = sum(1 for t in board["tasks"] if t["status"] == "doing")
    if doing_count >= WIP_LIMITS["doing"]:
        doing_tasks = [t for t in board["tasks"] if t["status"] == "doing"]
        return success({
            "proposed": None,
            "reason": "DOING column at WIP limit",
            "doing_tasks": doing_tasks,
            "message": f"DOING column is full ({doing_count}/{WIP_LIMITS['doing']}). "
                       f"Finish one of these first:\n" +
                       "\n".join(f"  - {t['id']}: {t['title']} (owner: {t.get('owner', 'unassigned')})"
                                 for t in doing_tasks),
        })

    # Find next TODO task (unblocked)
    todo_tasks = [t for t in board["tasks"] if t["status"] == "todo"]
    if todo_tasks:
        proposed = todo_tasks[0]
    else:
        # Auto-promote from backlog
        backlog_tasks = [t for t in board["tasks"] if t["status"] == "backlog"]
        if not backlog_tasks:
            return success({
                "proposed": None,
                "reason": "no tasks",
                "message": "No tasks in backlog or TODO. Create one with: /task <title>",
            })
        proposed = backlog_tasks[0]
        # Auto-promote to TODO
        proposed["status"] = "todo"
        save_board(board)

    return success({
        "proposed": proposed,
        "message": (
            f"PROPOSED TASK: {proposed['id']}\n"
            f"  Title: {proposed['title']}\n"
            f"  Type: {proposed['type']} | Effort: {proposed['effort']} | Area: {proposed.get('area', 'n/a')}\n"
            f"  Description: {proposed.get('description', '(none)')}\n\n"
            f"Approve this task? Type:\n"
            f"  /task-approve {proposed['id']}            — start working on it\n"
            f"  /task-reject {proposed['id']} <reason>    — skip and propose next\n"
            f"  /tasks                                  — see full board"
        ),
    })


def task_approve(task_id: str, agent: str = "auto") -> McpResult:
    """
    Developer approved the proposed task.
    Auto-pulls: assigns owner and moves to DOING.
    """
    board = load_board()
    task = find_task(board, task_id)
    if not task:
        return fail(f"Task not found: {task_id}")

    # Determine owner
    if agent == "auto":
        # Auto-assign based on area (future: map areas to agents)
        # For now, use "Hephaestus" as the default
        owner = "Hephaestus"
    else:
        owner = agent

    return task_pick(task_id, owner)


def task_reject(task_id: str, reason: str = "") -> McpResult:
    """
    Developer rejected the proposed task.
    Moves it back to backlog and proposes the next one.
    """
    board = load_board()
    task = find_task(board, task_id)
    if not task:
        return fail(f"Task not found: {task_id}")

    task["status"] = "backlog"
    if reason:
        task["reject_reason"] = reason
    save_board(board)

    session_append(f"TASK REJECTED — {task_id}: {reason}",
                   agent="Developer", kind="note")

    # Propose next
    return propose_next()


# ── Show task details ──
def task_show(task_id: str) -> McpResult:
    board = load_board()
    task = find_task(board, task_id)
    if not task:
        return fail(f"Task not found: {task_id}")
    return success({"task": task})


# ── CLI ──
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Task MCP — Kanban board")
        print("Usage: python task.py <command> [args]")
        print()
        print("Commands:")
        print("  create <title> [type] [area] [effort]   Create a task")
        print("  list [status]                           List tasks")
        print("  board                                   Show Kanban board")
        print("  move <id> <status>                      Move task")
        print("  pick <id> <agent>                       Assign + start")
        print("  done <id> [summary]                     Mark done")
        print("  block <id> <reason>                     Mark blocked")
        print("  unblock <id>                            Unblock")
        print("  propose                                 Find next task (approval gate)")
        print("  approve <id> [agent]                    Approve proposed task")
        print("  reject <id> [reason]                    Reject, propose next")
        print("  show <id>                               Show task details")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "info":
        print(json.dumps(info(), indent=2))
    elif cmd == "create":
        title = sys.argv[2]
        task_type = sys.argv[3] if len(sys.argv) > 3 else "feature"
        area = sys.argv[4] if len(sys.argv) > 4 else ""
        effort = sys.argv[5] if len(sys.argv) > 5 else "M"
        print(task_create(title, task_type, area, effort).to_dict())
    elif cmd == "list":
        status = sys.argv[2] if len(sys.argv) > 2 else "all"
        print(task_list(status).to_dict())
    elif cmd == "board":
        result = show_board()
        print(result.data["board_text"])
    elif cmd == "move":
        print(task_move(sys.argv[2], sys.argv[3]).to_dict())
    elif cmd == "pick":
        agent = sys.argv[3] if len(sys.argv) > 3 else "auto"
        print(task_pick(sys.argv[2], agent).to_dict())
    elif cmd == "done":
        summary = sys.argv[3] if len(sys.argv) > 3 else ""
        print(task_done(sys.argv[2], summary).to_dict())
    elif cmd == "block":
        print(task_block(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "").to_dict())
    elif cmd == "unblock":
        print(task_unblock(sys.argv[2]).to_dict())
    elif cmd == "propose":
        result = propose_next()
        print(result.data.get("message", "No task proposed."))
    elif cmd == "approve":
        agent = sys.argv[3] if len(sys.argv) > 3 else "auto"
        print(task_approve(sys.argv[2], agent).to_dict())
    elif cmd == "reject":
        reason = sys.argv[3] if len(sys.argv) > 3 else ""
        print(task_reject(sys.argv[2], reason).to_dict())
    elif cmd == "show":
        print(task_show(sys.argv[2]).to_dict())
    else:
        print(f"Unknown command: {cmd}")
