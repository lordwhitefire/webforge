#!/usr/bin/env python3
"""
Task MCP — Kanban-style task board, SQLite-backed.

Replaces the flat board.json with SQLite (WAL mode) for:
  - Concurrency-safe mutations (no last-writer-wins)
  - Atomic transactions across task + run + message tables
  - Crash recovery (WAL is journaled)
  - Queryable history

Public API (unchanged from old task.py — drop-in replacement):
  task_create(title, type, area, effort, description) → McpResult
  task_list(status) → McpResult
  task_show(id) → McpResult
  task_move(id, status) → McpResult
  task_pick(id, agent, bypass_gate=False) → McpResult
  task_done(id, summary="") → McpResult
  task_block(id, reason) → McpResult
  task_unblock(id) → McpResult
  propose_next() → McpResult
  task_approve(id, agent="auto") → McpResult
  task_reject(id, reason="") → McpResult
  show_board() → McpResult

  Legacy file-API (deprecated, kept for backward compat):
  load_board() → dict   — reads from SQLite, returns dict shaped like old board.json
  save_board() → NO-OP  — SQLite is the source of truth now

WIP limits enforce focus (max items per column).

The /build command is an APPROVAL GATE:
  1. Find next unblocked task
  2. Propose it to the developer
  3. WAIT for approval (yes/no/pick different)
  4. Only then does the agent start
"""

import os
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import write_log, success, fail, utc_now, McpResult, get_project_root
from memory import session_append
import state


# ── WIP limits (industry standard: small to force focus) ──
WIP_LIMITS = {
    "todo": 3,   # max 3 tasks ready to start
    "doing": 2,  # max 2 tasks in progress (focus, don't multitask)
}

# Ensure schema exists on every import (idempotent)
state.init_schema()


def info() -> dict:
    return {
        "id": "m-task",
        "name": "Task MCP (SQLite)",
        "tier": 2,
        "owner": "Hephaestus",
        "job": "Kanban task board backed by SQLite. Concurrency-safe, crash-safe.",
        "wip_limits": WIP_LIMITS,
    }


# ── Row → dict (parse JSON columns) ──

def _row_to_task(row: dict) -> dict:
    """Convert a SQLite row dict to a task dict matching the old format."""
    if row is None:
        return None
    task = dict(row)
    # blocked_by is stored as JSON array text
    try:
        task["blocked_by"] = json.loads(task.get("blocked_by") or "[]")
    except (json.JSONDecodeError, TypeError):
        task["blocked_by"] = []
    return task


# ── Create task ──

def task_create(title: str, task_type: str = "feature", area: str = "",
                effort: str = "M", description: str = "") -> McpResult:
    """Create a new task in the backlog."""
    now = utc_now()
    task_id = state.next_id("task", "task-")

    with state.transaction() as conn:
        conn.execute(
            """INSERT INTO tasks
               (id, title, description, type, area, effort, status, owner,
                blocked_by, created_at, started_at, completed_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, 'backlog', NULL, '[]', ?, NULL, NULL, ?)""",
            (task_id, title, description, task_type, area, effort, now, now)
        )

    task = _row_to_task(state.query_one(
        "SELECT * FROM tasks WHERE id=?", (task_id,)
    ))

    session_append(f"TASK CREATED — {task_id}: {title} ({task_type}, {effort})",
                   agent="Developer", kind="note")
    write_log("Task", "Hephaestus", "task_create",
              {"id": task_id, "title": title, "type": task_type})

    # ── AUTO-DISPATCH (route to the right department head) ──
    try:
        from dispatch import auto_dispatch
        auto_dispatch(task_id, task_type, title, from_agent="Developer")
    except ImportError:
        pass
    except Exception as e:
        write_log("Task", "Hephaestus", "auto_dispatch_failed",
                  {"task_id": task_id, "error": str(e)})

    # ── SEND NOTIFICATION (mailbox if available, else notify.py) ──
    try:
        from mailbox import Mailbox
        Mailbox("Hermes").send(
            to="Hermes", msg_type="TASK_CREATED",
            subject=f"New task: {title}",
            body=f"New task {task_id}: {title} (type: {task_type}, effort: {effort}). "
                 f"Suggested route: Hephaestus (build).",
            task_id=task_id,
        )
    except ImportError:
        # Fall back to legacy notify.py if mailbox not yet wired
        try:
            from notify import notify_task_created
            notify_task_created(task_id, title, task_type, from_agent="Developer")
        except ImportError:
            pass
    except Exception as e:
        write_log("Task", "Hephaestus", "notify_failed",
                  {"task_id": task_id, "error": str(e)})

    return success({"task": task, "id": task_id})


# ── List tasks / show board ──

def task_list(status: str = "all") -> McpResult:
    """List tasks. Status: all, backlog, todo, doing, done, blocked."""
    if status == "all":
        rows = state.query("SELECT * FROM tasks ORDER BY created_at ASC")
    else:
        rows = state.query(
            "SELECT * FROM tasks WHERE status=? ORDER BY created_at ASC",
            (status,)
        )
    tasks = [_row_to_task(r) for r in rows]
    return success({"tasks": tasks, "count": len(tasks)})


def show_board() -> McpResult:
    """Show the full Kanban board."""
    rows = state.query("SELECT * FROM tasks ORDER BY created_at ASC")
    all_tasks = [_row_to_task(r) for r in rows]

    columns = {
        "backlog": [],
        "todo": [],
        "doing": [],
        "done": [],
        "blocked": [],
    }
    for t in all_tasks:
        if t["status"] in columns:
            columns[t["status"]].append(t)

    # Format as text
    lines = []
    lines.append("=" * 70)
    lines.append("WEBFORGE KANBAN BOARD (SQLite-backed)")
    lines.append("=" * 70)
    lines.append("")

    for col, tasks in columns.items():
        wip = WIP_LIMITS.get(col)
        wip_label = f" (WIP: {len(tasks)}/{wip})" if wip else f" ({len(tasks)})"
        lines.append(f"┌── {col.upper()}{wip_label} " + "─" * (50 - len(col) - len(wip_label)) + "┐")
        if not tasks:
            lines.append("│  (empty)                                                              │")
        else:
            for t in tasks[:10]:
                owner = f" [{t['owner']}]" if t["owner"] else ""
                effort_badge = {"S": "🟢", "M": "🟡", "L": "🔴"}.get(t["effort"], "⚪")
                title = t["title"][:50]
                lines.append(f"│  {effort_badge} {t['id']}: {title}{owner}".ljust(73) + "│")
        lines.append("└" + "─" * 71 + "└")
        lines.append("")

    lines.append("=" * 70)
    lines.append(f"Total tasks: {len(all_tasks)} | "
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

    now = utc_now()

    with state.transaction() as conn:
        task = conn.execute(
            "SELECT * FROM tasks WHERE id=?", (task_id,)
        ).fetchone()
        if task is None:
            return fail(f"Task not found: {task_id}")
        task = dict(task)

        # Check WIP limit (skip for done/blocked — they don't count)
        if new_status in WIP_LIMITS:
            cur = conn.execute(
                "SELECT COUNT(*) AS n FROM tasks WHERE status=?", (new_status,)
            ).fetchone()
            if cur["n"] >= WIP_LIMITS[new_status] and task["status"] != new_status:
                return fail(f"WIP limit reached for '{new_status}' ({WIP_LIMITS[new_status]}). "
                            f"Move something out of {new_status} first.")

        old_status = task["status"]
        started_at = task["started_at"]
        completed_at = task["completed_at"]
        if new_status == "doing" and not started_at:
            started_at = now
        if new_status == "done" and not completed_at:
            completed_at = now

        conn.execute(
            "UPDATE tasks SET status=?, started_at=?, completed_at=?, updated_at=? WHERE id=?",
            (new_status, started_at, completed_at, now, task_id)
        )

    session_append(f"TASK MOVED — {task_id}: {old_status} → {new_status}",
                   agent="Hephaestus", kind="note")
    write_log("Task", "Hephaestus", "task_move",
              {"id": task_id, "from": old_status, "to": new_status})

    task = _row_to_task(state.query_one("SELECT * FROM tasks WHERE id=?", (task_id,)))
    return success({"task": task, "moved_from": old_status, "moved_to": new_status})


# ── Pick task (assign owner + move to doing) ──

def task_pick(task_id: str, agent: str, bypass_gate: bool = False) -> McpResult:
    """
    An agent picks up a task — assigns ownership and moves to DOING.

    Approval gate: if task is in 'backlog' and bypass_gate is False, refuse.
    The AI must call task_approve() first. Use bypass_gate=True only for
    internal routing (Hermes explicit assignment).

    WIP limit: when bypass_gate=True (Hermes explicit assignment), the WIP
    limit is also bypassed — Hermes is the COO; his assignments are
    authoritative.
    """
    now = utc_now()

    with state.transaction() as conn:
        task = conn.execute(
            "SELECT * FROM tasks WHERE id=?", (task_id,)
        ).fetchone()
        if task is None:
            return fail(f"Task not found: {task_id}")
        task = dict(task)

        # Approval gate
        if task["status"] == "backlog" and not bypass_gate:
            return fail(
                f"APPROVAL GATE — {task_id} is in backlog.\n"
                f"Propose it first: /task-propose\n"
                f"Then approve: /task-approve {task_id}"
            )

        # WIP limit — skip when bypass_gate=True (Hermes route)
        if not bypass_gate:
            cur = conn.execute(
                "SELECT COUNT(*) AS n FROM tasks WHERE status='doing'"
            ).fetchone()
            if cur["n"] >= WIP_LIMITS["doing"] and task["status"] != "doing":
                return fail(f"DOING WIP limit reached ({WIP_LIMITS['doing']}). "
                            f"Finish a task first.")

        old_status = task["status"]
        started_at = task["started_at"] or now

        conn.execute(
            "UPDATE tasks SET owner=?, status='doing', started_at=?, updated_at=? WHERE id=?",
            (agent, started_at, now, task_id)
        )

    task = _row_to_task(state.query_one("SELECT * FROM tasks WHERE id=?", (task_id,)))

    session_append(f"TASK PICKED — {task_id}: {task['title']} (by {agent})",
                   agent=agent, kind="note")
    write_log("Task", agent, "task_pick",
              {"id": task_id, "title": task["title"]})

    # ── SEND NOTIFICATION ──
    try:
        from mailbox import Mailbox
        Mailbox("Hermes").send(
            to=agent, msg_type="TASK_ASSIGNED",
            subject=f"Task {task_id}: {task['title']}",
            body=f"You have been assigned task {task_id}: {task['title']}. Start working on it.",
            task_id=task_id,
        )
    except ImportError:
        try:
            from notify import notify_task_assigned
            notify_task_assigned(task_id, task["title"], agent, from_agent="Hermes")
        except ImportError:
            pass
    except Exception as e:
        write_log("Task", agent, "notify_failed",
                  {"task_id": task_id, "error": str(e)})

    return success({"task": task, "picked_by": agent})


# ── Mark task done ──

def task_done(task_id: str, summary: str = "") -> McpResult:
    """
    Mark a task as done. Logs to session.

    QUALITY GATE: Before marking done, checks if quality checks passed.
    If checks failed and no override given → BLOCKS (strict by default).
    """
    # Pipeline gate
    try:
        from common import is_pipeline_active
        if is_pipeline_active():
            return fail(
                f"PIPELINE ACTIVE — {task_id}\n\n"
                f"A pipeline session is running. Let the agent script handle this.\n"
                f"Wait for the pipeline to finish, or say 'continue' if it timed out."
            )
    except ImportError:
        pass

    now = utc_now()

    with state.transaction() as conn:
        task = conn.execute(
            "SELECT * FROM tasks WHERE id=?", (task_id,)
        ).fetchone()
        if task is None:
            return fail(f"Task not found: {task_id}")
        task = dict(task)

        # Quality gate
        try:
            from quality import is_quality_approved
            if not is_quality_approved(task_id):
                return fail(
                    f"QUALITY GATE BLOCKED — {task_id}\n\n"
                    f"Quality checks have not passed for this task.\n"
                    f"Run: /check {task_id}\n"
                    f"If checks fail, fix the issues OR override: /check-approve {task_id}\n"
                    f"Then: /task-done {task_id}"
                )
        except ImportError:
            pass

        conn.execute(
            "UPDATE tasks SET status='done', completed_at=?, updated_at=? WHERE id=?",
            (now, now, task_id)
        )

    task = _row_to_task(state.query_one("SELECT * FROM tasks WHERE id=?", (task_id,)))

    log_msg = f"TASK DONE — {task_id}: {task['title']}"
    if summary:
        log_msg += f" — {summary}"
    session_append(log_msg, agent=task.get("owner") or "Hephaestus", kind="decision")
    write_log("Task", task.get("owner", "Hephaestus"), "task_done",
              {"id": task_id, "title": task["title"]})

    # ── SEND NOTIFICATION ──
    try:
        from mailbox import Mailbox
        done_by = task.get("owner") or "Hephaestus"
        Mailbox("Hermes").send(
            to="Developer", msg_type="TASK_DONE",
            subject=f"Task {task_id} completed",
            body=f"Task {task_id} completed by @{done_by}: {task['title']}. "
                 f"Quality checks may be needed: /check {task_id}",
            task_id=task_id,
        )
        Mailbox("Hermes").send(
            to="Minos", msg_type="REVIEW_NEEDED",
            subject=f"Review needed: {task_id}",
            body=f"Task {task_id} marked done by @{done_by}: {task['title']}. "
                 f"Run quality check: /check {task_id}",
            task_id=task_id,
        )
    except ImportError:
        try:
            from notify import notify_task_done
            done_by = task.get("owner") or "Hephaestus"
            notify_task_done(task_id, task["title"], done_by, from_agent=done_by)
        except ImportError:
            pass
    except Exception as e:
        write_log("Task", done_by, "notify_failed",
                  {"task_id": task_id, "error": str(e)})

    return success({"task": task})


# ── Block / unblock ──

def task_block(task_id: str, reason: str) -> McpResult:
    now = utc_now()
    with state.transaction() as conn:
        cur = conn.execute(
            "UPDATE tasks SET status='blocked', block_reason=?, updated_at=? WHERE id=?",
            (reason, now, task_id)
        )
        if cur.rowcount == 0:
            return fail(f"Task not found: {task_id}")

    task = _row_to_task(state.query_one("SELECT * FROM tasks WHERE id=?", (task_id,)))
    session_append(f"TASK BLOCKED — {task_id}: {reason}",
                   agent="Hephaestus", kind="note")

    try:
        from mailbox import Mailbox
        Mailbox("Hermes").send(
            to="Developer", msg_type="TASK_BLOCKED",
            subject=f"Task blocked: {task_id}",
            body=f"Task {task_id} blocked: {reason}",
            task_id=task_id, priority=1,
        )
    except ImportError:
        try:
            from notify import notify_task_blocked
            notify_task_blocked(task_id, task["title"], reason, from_agent="Hephaestus")
        except ImportError:
            pass
    except Exception as e:
        write_log("Task", "Hephaestus", "notify_failed",
                  {"task_id": task_id, "error": str(e)})

    return success({"task": task})


def task_unblock(task_id: str) -> McpResult:
    now = utc_now()
    with state.transaction() as conn:
        cur = conn.execute(
            "UPDATE tasks SET status='todo', block_reason=NULL, updated_at=? WHERE id=?",
            (now, task_id)
        )
        if cur.rowcount == 0:
            return fail(f"Task not found: {task_id}")
    task = _row_to_task(state.query_one("SELECT * FROM tasks WHERE id=?", (task_id,)))
    return success({"task": task})


# ── The approval gate: propose next task ──

def propose_next() -> McpResult:
    """Find the next unblocked task. Does NOT auto-start."""
    doing_count = state.query_one(
        "SELECT COUNT(*) AS n FROM tasks WHERE status='doing'"
    )["n"]
    if doing_count >= WIP_LIMITS["doing"]:
        doing_tasks = state.query(
            "SELECT * FROM tasks WHERE status='doing' ORDER BY started_at"
        )
        doing_tasks = [_row_to_task(r) for r in doing_tasks]
        return success({
            "proposed": None,
            "reason": "DOING column at WIP limit",
            "doing_tasks": doing_tasks,
            "message": f"DOING column is full ({doing_count}/{WIP_LIMITS['doing']}). "
                       f"Finish one of these first:\n" +
                       "\n".join(f"  - {t['id']}: {t['title']} (owner: {t.get('owner', 'unassigned')})"
                                 for t in doing_tasks),
        })

    todo_tasks = state.query("SELECT * FROM tasks WHERE status='todo' ORDER BY created_at")
    backlog_tasks = state.query("SELECT * FROM tasks WHERE status='backlog' ORDER BY created_at")

    if todo_tasks:
        proposed = _row_to_task(todo_tasks[0])
    elif backlog_tasks:
        proposed = _row_to_task(backlog_tasks[0])
    else:
        return success({
            "proposed": None,
            "reason": "no tasks",
            "message": "No tasks in backlog or TODO. Create one with: /task <title>",
        })

    return success({
        "proposed": proposed,
        "message": (
            f"PROPOSED TASK: {proposed['id']}\n"
            f"  Title: {proposed['title']}\n"
            f"  Type: {proposed['type']} | Effort: {proposed['effort']} | Area: {proposed.get('area', 'n/a')}\n"
            f"  Description: {proposed.get('description', '(none)')}\n\n"
            f"⚠️ Task is NOT approved yet. To start:\n"
            f"  /task-approve {proposed['id']}            — approve and start\n"
            f"  /task-reject {proposed['id']} <reason>    — skip and propose next\n"
            f"  /tasks                                  — see full board"
        ),
    })


def task_approve(task_id: str, agent: str = "auto") -> McpResult:
    """Developer approved the proposed task. Auto-pulls: assigns owner + moves to DOING."""
    task = state.query_one("SELECT * FROM tasks WHERE id=?", (task_id,))
    if task is None:
        return fail(f"Task not found: {task_id}")

    owner = "Hephaestus" if agent == "auto" else agent

    result = task_pick(task_id, owner, bypass_gate=True)
    if not result.ok:
        return result

    # RFC gate (one-way door)
    try:
        from rfc import needs_rfc, rfc_generate, has_approved_rfc
        task = _row_to_task(state.query_one("SELECT * FROM tasks WHERE id=?", (task_id,)))
        if needs_rfc(task) and not has_approved_rfc(task_id):
            rfc_result = rfc_generate(task)
            if rfc_result.ok:
                return success({
                    "task": task,
                    "picked_by": owner,
                    "rfc_required": True,
                    "rfc_message": rfc_result.data.get("message", ""),
                    "message": (
                        f"Task {task_id} approved and picked up by {owner}.\n\n"
                        f"⚠️ RFC REQUIRED — This is a {task.get('type', 'feature')} "
                        f"(one-way door). An RFC has been generated.\n"
                        f"Review it: /rfc {task_id}\n"
                        f"Approve design: /rfc-approve {task_id}\n"
                        f"Reject design: /rfc-reject {task_id} <reason>\n\n"
                        f"Coding is BLOCKED until the RFC is approved."
                    ),
                })
    except ImportError:
        pass

    return result


def task_reject(task_id: str, reason: str = "") -> McpResult:
    """Developer rejected the proposed task. Moves to backlog and proposes next."""
    now = utc_now()
    with state.transaction() as conn:
        cur = conn.execute(
            "UPDATE tasks SET status='backlog', updated_at=? WHERE id=?",
            (now, task_id)
        )
        if cur.rowcount == 0:
            return fail(f"Task not found: {task_id}")

    session_append(f"TASK REJECTED — {task_id}: {reason}",
                   agent="Developer", kind="note")

    return propose_next()


# ── Show task details ──

def task_show(task_id: str) -> McpResult:
    task = _row_to_task(state.query_one("SELECT * FROM tasks WHERE id=?", (task_id,)))
    if task is None:
        return fail(f"Task not found: {task_id}")
    return success({"task": task})


# ── LEGACY COMPAT: load_board / save_board ──
# Old code (Hermes, frontend) may call these. Keep them working
# but route through SQLite. save_board is a no-op — SQLite is source of truth.

def load_board() -> dict:
    """Return a dict shaped like the old board.json. Read-only."""
    rows = state.query("SELECT * FROM tasks ORDER BY created_at ASC")
    tasks = [_row_to_task(r) for r in rows]
    max_id = 0
    for t in tasks:
        try:
            n = int(t["id"].replace("task-", ""))
            if n > max_id:
                max_id = n
        except (ValueError, AttributeError):
            pass
    return {
        "tasks": tasks,
        "next_id": max_id + 1,
        "wip_limits": WIP_LIMITS,
    }


def save_board(board: dict):
    """
    DEPRECATED — no-op. SQLite is the source of truth.

    Old code that did load_board() → modify → save_board() will now
    silently do nothing on save. Use the task_* functions instead.
    """
    write_log("Task", "System", "save_board_noop",
              {"msg": "save_board is deprecated; SQLite is source of truth"})
    return None


# ── CLI ──

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Task MCP — Kanban board (SQLite-backed)")
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
