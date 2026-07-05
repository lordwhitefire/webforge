#!/usr/bin/env python3
"""
WebForge Mailbox MCP — real inter-agent messaging.

Replaces notify.py's flat JSON inboxes with SQLite-backed mailboxes that
have proper send/receive/ack/reply/wait semantics. Inspired by Shire's
inter-agent mailboxes.

Each agent has a mailbox (a row in the `messages` table filtered by
to_agent). Messages can:
  - Be threaded (parent_id links replies to originals)
  - Be acked (sender knows the receiver saw it)
  - Be replied to (full conversation per task)
  - Be waited on (an agent blocks until a matching reply arrives)
  - Be queried (SELECT * FROM messages WHERE to_agent=? AND status='unread')

Message types:
  TASK_CREATED, TASK_ASSIGNED, TASK_ACK, TASK_PROGRESS,
  TASK_DONE, TASK_BLOCKED, REVIEW_NEEDED, REVIEW_RESULT,
  QUESTION, ANSWER, ESCALATION, INFO
"""

import os
import sys
import json
import time
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))
from common import write_log, success, fail, utc_now, McpResult, get_project_root
from memory import session_append
import state


# ── Message types ──

MSG_TYPES = {
    "TASK_CREATED", "TASK_ASSIGNED", "TASK_ACK", "TASK_PROGRESS",
    "TASK_DONE", "TASK_BLOCKED", "REVIEW_NEEDED", "REVIEW_RESULT",
    "QUESTION", "ANSWER", "ESCALATION", "INFO",
}

# Priority levels
PRIORITY_NORMAL = 0
PRIORITY_HIGH = 1
PRIORITY_URGENT = 2


# ── Message dataclass (lightweight, dict-based) ──

class Message:
    """A mailbox message. Wraps a dict row from the messages table."""

    def __init__(self, data: dict):
        self.data = data

    def __getattr__(self, name):
        if name in self.data:
            return self.data[name]
        raise AttributeError(name)

    def __repr__(self):
        return (f"Message(id={self.data.get('id')}, "
                f"from={self.data.get('from_agent')}, "
                f"to={self.data.get('to_agent')}, "
                f"type={self.data.get('type')}, "
                f"subject={self.data.get('subject', '')[:40]!r})")


# ── Mailbox class ──

class Mailbox:
    """
    A mailbox for one agent.

    Usage:
        mb = Mailbox("Hephaestus")
        mb.send("Hermes", "TASK_ACK", "On it", "I've picked up the task")
        msgs = mb.inbox(unread_only=True)
        for m in msgs:
            print(m.subject, m.body)
            mb.read(m.id)
            mb.ack(m.id)
    """

    def __init__(self, agent_name: str):
        self.agent = agent_name
        state.init_schema()

    # ── Send ──

    def send(self, to: str, msg_type: str, subject: str = "", body: str = "",
             task_id: str = None, parent_id: str = None,
             priority: int = PRIORITY_NORMAL) -> str:
        """
        Send a message to another agent's mailbox.

        Args:
            to: Recipient agent name
            msg_type: One of MSG_TYPES
            subject: Short subject line
            body: Full message body
            task_id: Related task (optional)
            parent_id: Parent message ID (for threading/replies)
            priority: 0=normal, 1=high, 2=urgent

        Returns:
            The new message ID (e.g. "msg-042")
        """
        if msg_type not in MSG_TYPES:
            raise ValueError(f"Unknown message type: {msg_type}. "
                             f"Must be one of {MSG_TYPES}")

        msg_id = state.next_id("msg", "msg-")
        now = utc_now()

        state.execute(
            """INSERT INTO messages
               (id, parent_id, from_agent, to_agent, type, subject, body,
                task_id, priority, created_at, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'unread')""",
            (msg_id, parent_id, self.agent, to, msg_type, subject, body,
             task_id, priority, now)
        )

        write_log("Mailbox", self.agent, "send",
                  {"msg_id": msg_id, "to": to, "type": msg_type,
                   "task_id": task_id, "subject": subject[:80]})

        return msg_id

    # ── Inbox ──

    def inbox(self, unread_only: bool = True, task_id: str = None,
              msg_type: str = None, from_agent: str = None) -> list:
        """
        List messages in my inbox.

        Args:
            unread_only: If True, only return unread messages
            task_id: Filter by task
            msg_type: Filter by message type
            from_agent: Filter by sender

        Returns:
            List of Message objects, newest first
        """
        sql = "SELECT * FROM messages WHERE to_agent=?"
        params = [self.agent]
        if unread_only:
            sql += " AND status='unread'"
        if task_id:
            sql += " AND task_id=?"
            params.append(task_id)
        if msg_type:
            sql += " AND type=?"
            params.append(msg_type)
        if from_agent:
            sql += " AND from_agent=?"
            params.append(from_agent)
        sql += " ORDER BY priority DESC, created_at ASC"

        rows = state.query(sql, tuple(params))
        return [Message(r) for r in rows]

    def all_messages(self, task_id: str = None) -> list:
        """List ALL messages involving me (sent or received), optionally for a task."""
        sql = ("SELECT * FROM messages WHERE to_agent=? OR from_agent=?")
        params = [self.agent, self.agent]
        if task_id:
            sql += " AND task_id=?"
            params.append(task_id)
        sql += " ORDER BY created_at ASC"
        rows = state.query(sql, tuple(params))
        return [Message(r) for r in rows]

    # ── Read ──

    def read(self, msg_id: str) -> Message | None:
        """
        Read a message. Marks it as 'read' (sets read_at timestamp).

        Returns:
            The Message object, or None if not found / not addressed to me.
        """
        msg = state.query_one("SELECT * FROM messages WHERE id=?", (msg_id,))
        if msg is None:
            return None
        if msg["to_agent"] != self.agent and msg["from_agent"] != self.agent:
            return None  # Not my message

        # Mark as read if it was unread and I'm the recipient
        if msg["to_agent"] == self.agent and msg["status"] == "unread":
            now = utc_now()
            state.execute(
                "UPDATE messages SET status='read', read_at=? WHERE id=?",
                (now, msg_id)
            )
            msg = state.query_one("SELECT * FROM messages WHERE id=?", (msg_id,))

        return Message(msg)

    # ── Ack ──

    def ack(self, msg_id: str, note: str = "") -> str | None:
        """
        Acknowledge a message. Marks it as 'acked' and sends an ACK reply
        to the original sender.

        Args:
            msg_id: The message to ack
            note: Optional note to include in the ACK

        Returns:
            The ACK message ID, or None if the original message wasn't mine.
        """
        msg = state.query_one("SELECT * FROM messages WHERE id=?", (msg_id,))
        if msg is None:
            return None
        if msg["to_agent"] != self.agent:
            return None  # Can't ack a message that wasn't sent to me

        now = utc_now()
        # Mark original as acked
        state.execute(
            "UPDATE messages SET status='acked', acked_at=? WHERE id=?",
            (now, msg_id)
        )

        # Send ACK reply to original sender
        ack_body = note or "Acknowledged."
        ack_id = self.send(
            to=msg["from_agent"],
            msg_type="TASK_ACK",
            subject=f"ACK: {msg.get('subject', '')}",
            body=ack_body,
            task_id=msg.get("task_id"),
            parent_id=msg_id,
        )

        return ack_id

    # ── Reply ──

    def reply(self, msg_id: str, body: str, msg_type: str = "ANSWER",
              subject: str = "") -> str | None:
        """
        Reply to a message. Creates a new message with parent_id set.

        Args:
            msg_id: The message to reply to
            body: Reply body
            msg_type: Defaults to "ANSWER" (use "TASK_PROGRESS" etc. for other replies)
            subject: Optional new subject (defaults to "Re: <original>")

        Returns:
            The reply message ID, or None if original not found.
        """
        msg = state.query_one("SELECT * FROM messages WHERE id=?", (msg_id,))
        if msg is None:
            return None

        if not subject:
            orig_subject = msg.get("subject", "")
            subject = f"Re: {orig_subject}" if orig_subject else "Reply"

        # Reply goes to the original sender
        reply_id = self.send(
            to=msg["from_agent"],
            msg_type=msg_type,
            subject=subject,
            body=body,
            task_id=msg.get("task_id"),
            parent_id=msg_id,
        )

        # Mark original as replied
        now = utc_now()
        state.execute(
            "UPDATE messages SET status='replied' WHERE id=?",
            (msg_id,)
        )

        return reply_id

    # ── Archive ──

    def archive(self, msg_id: str):
        """Archive a message (marks as archived, removes from inbox)."""
        state.execute(
            "UPDATE messages SET status='archived' WHERE id=? AND to_agent=?",
            (msg_id, self.agent)
        )

    # ── Wait for a message ──

    def wait_for(self, from_agent: str = None, msg_type: str = None,
                 task_id: str = None, timeout: int = 30,
                 poll_interval: float = 0.1) -> Message | None:
        """
        Block until a matching message arrives in my inbox.

        Uses SQLite polling with backoff. For our scale (single machine,
        dozens of agents), polling at 100ms is fine. For higher throughput
        we could use SQLite's update_hook or a Unix socket.

        Args:
            from_agent: Wait for a message from this agent
            msg_type: Wait for this message type
            task_id: Wait for a message about this task
            timeout: Max seconds to wait (default 30)
            poll_interval: Seconds between polls (default 0.1)

        Returns:
            The matching Message, or None on timeout.
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            sql = "SELECT * FROM messages WHERE to_agent=? AND status='unread'"
            params = [self.agent]
            if from_agent:
                sql += " AND from_agent=?"
                params.append(from_agent)
            if msg_type:
                sql += " AND type=?"
                params.append(msg_type)
            if task_id:
                sql += " AND task_id=?"
                params.append(task_id)
            sql += " ORDER BY created_at ASC LIMIT 1"

            row = state.query_one(sql, tuple(params))
            if row:
                return Message(row)

            time.sleep(poll_interval)

        return None

    # ── Thread ──

    def get_thread(self, msg_id: str) -> list:
        """
        Get the full conversation thread for a message.
        Walks up to the root parent, then collects all replies.
        """
        # Walk up to root
        root = msg_id
        while True:
            msg = state.query_one("SELECT * FROM messages WHERE id=?", (root,))
            if msg is None or msg.get("parent_id") is None:
                break
            root = msg["parent_id"]

        # Collect all descendants
        thread = []
        queue = [root]
        while queue:
            current = queue.pop(0)
            msg = state.query_one("SELECT * FROM messages WHERE id=?", (current,))
            if msg:
                thread.append(Message(msg))
                # Find children
                children = state.query(
                    "SELECT id FROM messages WHERE parent_id=? ORDER BY created_at",
                    (current,)
                )
                queue.extend([c["id"] for c in children])

        return thread


# ── Convenience functions (drop-in replacements for notify.py) ──

def notify(agent_name: str, event: str, message: str, task_id: str = "",
           from_agent: str = "System") -> McpResult:
    """
    Drop-in replacement for notify.notify(). Sends a message to an agent's mailbox.

    Old code that did:
        from notify import notify
        notify("Hephaestus", "TASK_ASSIGNED", "...", task_id, from_agent="Hermes")
    Now does:
        from mailbox import notify
        notify("Hephaestus", "TASK_ASSIGNED", "...", task_id, from_agent="Hermes")
    """
    try:
        # Map old event names to new msg_types
        msg_type = event.upper().replace(" ", "_")
        if msg_type not in MSG_TYPES:
            msg_type = "INFO"

        mb = Mailbox(from_agent)
        msg_id = mb.send(
            to=agent_name,
            msg_type=msg_type,
            subject=event,
            body=message,
            task_id=task_id if task_id else None,
        )
        return success({"notification_id": msg_id, "to": agent_name, "event": event})
    except Exception as e:
        write_log("Mailbox", from_agent, "notify_failed",
                  {"to": agent_name, "event": event, "error": str(e)})
        return fail(f"notify failed: {e}")


def notify_task_created(task_id: str, title: str, task_type: str,
                        from_agent: str = "Hermes") -> McpResult:
    """Drop-in replacement for notify.notify_task_created()."""
    return notify(
        agent_name="Hermes",
        event="TASK_CREATED",
        message=f"New task {task_id}: {title} (type: {task_type}).",
        task_id=task_id,
        from_agent=from_agent,
    )


def notify_task_assigned(task_id: str, title: str, assigned_to: str,
                         from_agent: str = "Hermes") -> McpResult:
    """Drop-in replacement for notify.notify_task_assigned()."""
    return notify(
        agent_name=assigned_to,
        event="TASK_ASSIGNED",
        message=f"Task {task_id} assigned to you: {title}. Start working on it.",
        task_id=task_id,
        from_agent=from_agent,
    )


def notify_task_done(task_id: str, title: str, done_by: str,
                     from_agent: str = "Hephaestus") -> McpResult:
    """Drop-in replacement for notify.notify_task_done()."""
    # Notify Developer
    notify("Developer", "TASK_DONE",
           f"Task {task_id} completed by @{done_by}: {title}.",
           task_id, from_agent=from_agent)
    # Notify Minos (Quality) for review
    notify("Minos", "REVIEW_NEEDED",
           f"Task {task_id} marked done by @{done_by}: {title}. Run quality check.",
           task_id, from_agent=from_agent)
    return success({"message": f"Notifications sent: Developer + @Minos for task {task_id}"})


def notify_task_blocked(task_id: str, title: str, reason: str,
                        from_agent: str = "Hephaestus") -> McpResult:
    """Drop-in replacement for notify.notify_task_blocked()."""
    return notify(
        agent_name="Developer",
        event="TASK_BLOCKED",
        message=f"Task {task_id} blocked: {reason}. Title: {title}",
        task_id=task_id,
        from_agent=from_agent,
    )


# ── Aggregate queries (for the frontend / standup) ──

def get_all_unread() -> list:
    """
    Get all unread messages across ALL agents.
    Used by the frontend to show the notification panel.
    """
    state.init_schema()
    rows = state.query(
        "SELECT * FROM messages WHERE status='unread' "
        "ORDER BY priority DESC, created_at ASC"
    )
    return rows


def get_agent_inbox(agent_name: str, unread_only: bool = True) -> list:
    """Get an agent's inbox (used by /standup and agent scripts)."""
    state.init_schema()
    sql = "SELECT * FROM messages WHERE to_agent=?"
    if unread_only:
        sql += " AND status='unread'"
    sql += " ORDER BY priority DESC, created_at ASC"
    return state.query(sql, (agent_name,))


def mark_read(msg_id: str):
    """Mark a message as read (used by frontend when user clicks it)."""
    state.execute(
        "UPDATE messages SET status='read', read_at=? WHERE id=?",
        (utc_now(), msg_id)
    )


# ── CLI ──

def info() -> dict:
    return {
        "id": "m-mailbox",
        "name": "Mailbox MCP",
        "tier": 1,
        "owner": "System",
        "job": "Inter-agent mailboxes with send/read/ack/reply/wait semantics. Replaces notify.py's flat JSON.",
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Mailbox MCP — inter-agent messaging")
        print("Usage: python mailbox.py <command>")
        print()
        print("Commands:")
        print("  send <from> <to> <type> <subject> <body> [task_id]")
        print("  inbox <agent> [--all]                List inbox")
        print("  read <msg_id>                        Read + mark as read")
        print("  thread <msg_id>                      Show conversation thread")
        print("  unread                               All unread across all agents")
        print("  stats                                Message statistics")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "info":
        print(json.dumps(info(), indent=2))
    elif cmd == "send":
        if len(sys.argv) < 7:
            print("Usage: send <from> <to> <type> <subject> <body> [task_id]")
            sys.exit(1)
        mb = Mailbox(sys.argv[2])
        msg_id = mb.send(sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6],
                         task_id=sys.argv[7] if len(sys.argv) > 7 else None)
        print(f"Sent: {msg_id}")
    elif cmd == "inbox":
        if len(sys.argv) < 3:
            print("Usage: inbox <agent> [--all]")
            sys.exit(1)
        agent = sys.argv[2]
        unread_only = "--all" not in sys.argv
        mb = Mailbox(agent)
        msgs = mb.inbox(unread_only=unread_only)
        for m in msgs:
            print(f"  {m.id} [{m.type}] from @{m.from_agent}: {m.subject}")
            print(f"    {m.body[:80]}")
        print(f"\nTotal: {len(msgs)}")
    elif cmd == "read":
        if len(sys.argv) < 3:
            print("Usage: read <msg_id>")
            sys.exit(1)
        # Read needs an agent context — use 'System'
        mb = Mailbox("System")
        msg = mb.read(sys.argv[2])
        if msg:
            print(json.dumps(msg.data, indent=2, default=str))
        else:
            print("Not found")
    elif cmd == "thread":
        if len(sys.argv) < 3:
            print("Usage: thread <msg_id>")
            sys.exit(1)
        mb = Mailbox("System")
        thread = mb.get_thread(sys.argv[2])
        for m in thread:
            indent = "  " if m.parent_id else ""
            print(f"{indent}{m.id} [{m.type}] @{m.from_agent} → @{m.to_agent}: {m.subject}")
            print(f"{indent}  {m.body[:100]}")
    elif cmd == "unread":
        unread = get_all_unread()
        for n in unread:
            print(f"  [{n['type']}] @{n['from_agent']} → @{n['to_agent']}: {n['subject']}")
        print(f"\nTotal unread: {len(unread)}")
    elif cmd == "stats":
        for status in ("unread", "read", "acked", "replied", "archived"):
            n = state.query_one(
                "SELECT COUNT(*) AS n FROM messages WHERE status=?", (status,)
            )["n"]
            print(f"  {status}: {n}")
        total = state.query_one("SELECT COUNT(*) AS n FROM messages")["n"]
        print(f"  total: {total}")
    else:
        print(f"Unknown command: {cmd}")
