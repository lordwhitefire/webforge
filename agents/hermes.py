#!/usr/bin/env python3
"""
Hermes Agent — COO / Coordinator

THE BODY: This script IS Hermes. It controls what the AI does.
THE BRAIN: OpenCode (the AI) only reasons when Hermes asks it to via ask_ai().

PRINCIPLE: The script does NOT call OpenCode for simple tasks.
- "fix the cart bug" → Python parser detects "bug" → creates bugfix task → assigns to Hephaestus. NO AI.
- "add a wishlist feature" → Python parser detects "add" → creates feature task → assigns. NO AI.
- "clone this repo" → Python regex extracts URL → creates task → assigns. NO AI.
- "correct agent X" → Python regex extracts agent name + pattern → routes to Daedalus. NO AI.

ROUTING: Hermes does NOT call other agents' scripts directly. Instead:
  1. Creates task in Kanban board
  2. Assigns task to the right agent (task_pick) → UI shows agent as yellow (working)
  3. Sends notification to that agent → UI shows blue dot
  4. Returns response to CEO
  The UI polls the board every 3s, so the CEO sees agents light up.

CEO'S SOLE POINT OF CONTACT:
The CEO does NOT talk to other agents for work routing.
The CEO talks to Hermes. Hermes talks to all other agents.
"""

import sys
import os
import json
import re
from pathlib import Path

WEBFORGE_HOME = Path.home() / "webforge"
sys.path.insert(0, str(WEBFORGE_HOME / "agents"))
sys.path.insert(0, str(WEBFORGE_HOME / "mcp"))

from base import Agent


class Hermes(Agent):
    """Hermes — COO / Coordinator. CEO's sole point of contact."""

    name = "Hermes"
    department = "Executive"
    skill_file = "executive/hermes.md"
    reports_to = "CEO (Developer)"
    can_route_to = ["Hephaestus", "Athena", "Minos", "Thoth", "Daedalus", "Voss"]

    allowed_actions = [
        "create_bugfix_task", "create_feature_task", "run_standup",
        "answer_question", "route", "respond", "correct_agent", "clone_project",
    ]

    forbidden_actions = [
        "write_code", "research", "generate_docs",
        "run_quality_check", "review_code", "learn",
    ]

    correction_rules = []

    def execute(self, action: str, data: dict, context: dict) -> dict:
        """Execute the action. CODE does the work. NO AI for common tasks."""

        if action == "create_bugfix_task":
            return self._handle_bug(data)
        elif action == "create_feature_task":
            return self._handle_feature(data)
        elif action == "run_standup":
            return self._handle_standup()
        elif action == "answer_question":
            return self._handle_question(data)
        elif action == "correct_agent":
            return self._handle_correction(data)
        elif action == "clone_project":
            return self._handle_clone(data)
        elif action == "route":
            return self._handle_route(data)

        return {
            "agent": self.name, "action": "respond",
            "message": "I'm Hermes. I can create tasks, clone repos, correct agents, run standup, and answer questions.",
            "next_step": None,
        }

    # ── Route task to an agent (assign + notify, NOT call script) ──
    def _handle_route(self, data: dict) -> dict:
        """Route a task to a specific agent. Assign in Kanban + send notification."""
        target = data.get("target", "Hephaestus")
        message = data.get("message", data.get("raw", ""))
        task_id = data.get("task_id", "")

        return self._assign_to_agent(target, message, task_id)

    def _assign_to_agent(self, agent_name: str, message: str, task_id: str = "") -> dict:
        """
        Assign a task to an agent AND TRIGGER THEIR SCRIPT.

        Uses the new infrastructure:
          1. task_pick (SQLite, WIP-bypass for Hermes explicit assignments)
          2. Mailbox.send (real inter-agent messaging with ack/reply semantics)
          3. runs.create_run + start_run (crash recovery, on-disk state)
          4. Agent script triggered in background, logs to .webforge/runs/<run_id>/

        The agent's script will:
          - Check its mailbox for TASK_ASSIGNED messages
          - ACK the task (sender gets notified)
          - Checkpoint progress (resumable if crashed)
          - Execute the work
          - Mark task done + send TASK_DONE message
        """
        import subprocess

        # 1. Set the owner on the task — bypass_gate=True (Hermes is authoritative)
        pick_ok = True
        pick_error = ""
        if task_id:
            try:
                from task import task_pick
                result = task_pick(task_id, agent_name, bypass_gate=True)
                if not result.ok:
                    pick_ok = False
                    pick_error = result.error or "unknown pick error"
                    # Pick failed — at least set the owner in place
                    try:
                        import state as _state
                        _state.execute(
                            "UPDATE tasks SET owner=? WHERE id=?",
                            (agent_name, task_id)
                        )
                    except Exception:
                        pass
            except Exception as e:
                pick_ok = False
                pick_error = str(e)

        # 2. Create a run record (for crash recovery + on-disk state)
        run_id = None
        run_dir_path = None
        try:
            from runs import create_run, start_run, run_dir
            run = create_run(
                task_id=task_id,
                agent=agent_name,
                trigger=self.name,
                input_data={"message": message, "task_id": task_id},
            )
            run_id = run["id"]
            run_dir_path = run["run_dir"]
        except Exception as e:
            # Run creation failed — agent can still run, but no crash recovery
            try:
                from memory import session_append
                session_append(
                    f"HERMES WARNING — could not create run for {agent_name}: {e}",
                    agent=self.name, kind="note"
                )
            except Exception:
                pass

        # 3. Send TASK_ASSIGNED message via Mailbox (replaces notify.py)
        try:
            from mailbox import Mailbox
            mb = Mailbox(self.name)
            mb.send(
                to=agent_name,
                msg_type="TASK_ASSIGNED",
                subject=f"Task {task_id}: {message[:80]}" if task_id else message[:80],
                body=message if not task_id else f"Task {task_id}: {message}",
                task_id=task_id if task_id else None,
                priority=1,  # high priority — task assignment
            )
            # Also notify the Developer (CEO) so the chat panel shows the route
            mb.send(
                to="Developer",
                msg_type="TASK_ASSIGNED",
                subject=f"@{agent_name} assigned: {message[:60]}",
                body=f"@{agent_name} was assigned task {task_id}: {message}"
                     if task_id else f"@{agent_name} routed: {message}",
                task_id=task_id if task_id else None,
            )
        except Exception as e:
            try:
                from memory import session_append
                session_append(
                    f"HERMES WARNING — mailbox send failed: {e}",
                    agent=self.name, kind="note"
                )
            except Exception:
                pass

        # If pick failed, send a visible block notification
        if not pick_ok:
            try:
                from mailbox import Mailbox
                Mailbox(self.name).send(
                    to="Developer",
                    msg_type="TASK_BLOCKED",
                    subject=f"Could not move {task_id} to DOING",
                    body=f"Pick error: {pick_error}",
                    task_id=task_id if task_id else None,
                    priority=2,  # urgent
                )
            except Exception:
                pass

        # 4. TRIGGER THE AGENT'S SCRIPT IN BACKGROUND
        # Logs go to .webforge/runs/<run_id>/transcript.log (not DEVNULL)
        triggered = False
        try:
            agent_script = WEBFORGE_HOME / "agents" / f"{agent_name.lower()}.py"
            if agent_script.exists():
                env = os.environ.copy()
                env["WEBFORGE_PROJECT"] = str(self.project_root)
                env["WEBFORGE_TASK_ID"] = task_id
                env["WEBFORGE_AGENT_TRIGGER"] = self.name
                if run_id:
                    env["WEBFORGE_RUN_ID"] = run_id

                # Log to run directory if available, else to .webforge/logs/
                if run_dir_path:
                    from pathlib import Path
                    log_fp = open(Path(run_dir_path) / "transcript.log", "a")
                else:
                    log_dir = self.project_root / ".webforge" / "logs"
                    log_dir.mkdir(parents=True, exist_ok=True)
                    log_fp = open(log_dir / f"{agent_name.lower()}.log", "w")

                proc = subprocess.Popen(
                    ["python3", str(agent_script), "work"],
                    stdout=log_fp,
                    stderr=subprocess.STDOUT,
                    env=env,
                    start_new_session=True,  # Detach from parent
                )

                # Mark run as started (records the pid for the reaper)
                if run_id:
                    try:
                        from runs import start_run
                        start_run(run_id, proc.pid)
                    except Exception:
                        pass

                triggered = True
        except Exception as e:
            try:
                from memory import session_append
                session_append(
                    f"HERMES ERROR — failed to trigger {agent_name}: {e}",
                    agent=self.name, kind="error"
                )
            except Exception:
                pass

        # Compose a visible message — tell the user what happened
        if not pick_ok:
            return {
                "agent": self.name,
                "action": "route",
                "routed_to": agent_name,
                "task_id": task_id,
                "run_id": run_id,
                "message": (
                    f"📤 Routed to @{agent_name}: {message}\n"
                    f"   ⚠️ Could not move task to DOING: {pick_error}\n"
                    f"   Task stays in TODO with @{agent_name} as owner.\n"
                    f"   {'✅ Agent script triggered (run ' + run_id + ').' if triggered and run_id else '✅ Agent script triggered.' if triggered else '❌ Agent script NOT triggered.'}"
                ),
                "next_step": f"Watch @{agent_name} — they should still pick it up from TODO",
            }

        return {
            "agent": self.name,
            "action": "route",
            "routed_to": agent_name,
            "task_id": task_id,
            "run_id": run_id,
            "message": (
                f"📤 Assigned to @{agent_name}: {message}\n"
                f"   Task moved to DOING. @{agent_name}'s script triggered.\n"
                f"   {'Run ' + run_id + ' created — crash-recoverable.' if run_id else ''}\n"
                f"   @{agent_name} will:\n"
                f"     1. Check mailbox (ACK sent back to you)\n"
                f"     2. Checkpoint progress (resumable)\n"
                f"     3. Execute the work\n"
                f"     4. Mark done + send TASK_DONE"
            ),
            "next_step": f"Watch @{agent_name} — they should ACK shortly",
        }

    # ── Handle bug report (NO AI — pure Python) ──
    def _handle_bug(self, data: dict) -> dict:
        """Create a bugfix task and assign to Hephaestus. Pure code."""
        title = data.get("title", data.get("message", "Unknown bug"))
        title = title.replace("fix ", "").replace("Fix ", "").strip()
        if not title:
            title = data.get("message", "Unknown bug")

        # Create the task
        task_result = self._create_task(title=f"[BUG] {title}", task_type="bugfix", effort="S")
        if "error" in task_result:
            return {"agent": self.name, "action": "create_bugfix_task",
                    "message": f"Failed to create task: {task_result['error']}", "next_step": None}

        task_id = task_result.get("id", "unknown")

        # Assign to Hephaestus (makes him yellow on UI)
        assign_result = self._assign_to_agent("Hephaestus", f"Bug fix: {title}", task_id)
        run_id = assign_result.get("run_id") if isinstance(assign_result, dict) else None

        return {
            "agent": self.name, "action": "create_bugfix_task",
            "task_id": task_id, "routed_to": "Hephaestus",
            "run_id": run_id,
            "message": (
                f"Got it. I've created {task_id} (bugfix) and assigned it to @Hephaestus.\n"
                f"  Bug: {title}\n"
                + (f"  Run {run_id} created — crash-recoverable.\n" if run_id else "")
                + f"\nTo start: /build\n"
                f"I will NOT fix this myself — that's @Hephaestus's job.\n"
                f"You should see @Hephaestus light up (yellow = working)."
            ),
            "next_step": "/build",
        }

    # ── Handle feature request (NO AI — pure Python) ──
    def _handle_feature(self, data: dict) -> dict:
        """Create a feature task and assign to Hephaestus. Pure code."""
        title = data.get("title", data.get("message", "Unknown feature"))
        for prefix in ["add ", "create ", "implement ", "build ", "i want "]:
            if title.lower().startswith(prefix):
                title = title[len(prefix):].strip()
                break
        if not title:
            title = data.get("message", "Unknown feature")

        task_result = self._create_task(title=title.capitalize(), task_type="feature", effort="M")
        if "error" in task_result:
            return {"agent": self.name, "action": "create_feature_task",
                    "message": f"Failed: {task_result['error']}", "next_step": None}

        task_id = task_result.get("id", "unknown")

        # Assign to Hephaestus (makes him yellow on UI)
        assign_result = self._assign_to_agent("Hephaestus", f"Feature: {title}", task_id)
        run_id = assign_result.get("run_id") if isinstance(assign_result, dict) else None

        return {
            "agent": self.name, "action": "create_feature_task",
            "task_id": task_id, "routed_to": "Hephaestus",
            "run_id": run_id,
            "message": (
                f"Great idea. I've created {task_id} (feature) and assigned it to @Hephaestus.\n"
                f"  Feature: {title}\n"
                + (f"  Run {run_id} created — crash-recoverable.\n" if run_id else "")
                + f"  ⚠️ One-way door — RFC will be generated when you approve.\n\n"
                f"To start: /build\n"
                f"You should see @Hephaestus light up (yellow = working)."
            ),
            "next_step": "/build",
        }

    # ── Handle standup (NO AI — pure Python) ──
    def _handle_standup(self) -> dict:
        try:
            from standup import standup_run
            result = standup_run()
            return {"agent": self.name, "action": "run_standup",
                    "message": result.data.get("output", "Standup unavailable."), "next_step": None}
        except Exception as e:
            return {"agent": self.name, "action": "run_standup",
                    "message": f"Standup failed: {e}", "next_step": None}

    # ── Handle correction (NO AI — pure Python regex) ──
    def _handle_correction(self, data: dict) -> dict:
        """CEO corrects an agent. Parse with regex, route to Daedalus."""
        message = data.get("message", data.get("raw", ""))
        message_lower = message.lower()

        # Extract agent name
        agent_name = ""
        for pattern in [r'correct\s+(\w+(?:-\w+)*)', r'fix\s+(\w+(?:-\w+)*)',
                        r'tell\s+daedalus.*?(?:fix|correct)\s+(\w+(?:-\w+)*)',
                        r'stop\s+(\w+(?:-\w+)*)\s+from']:
            match = re.search(pattern, message_lower)
            if match:
                agent_name = match.group(1)
                break

        # Extract pattern to block
        pattern_to_block = ""
        for pattern in [r'blocking\s+(.+?)(?:$|\.)', r'block\s+(.+?)(?:$|\.)',
                        r'stop.*?from\s+(.+?)(?:$|\.)', r'stop\s+suggesting\s+(.+?)(?:$|,|\.)',
                        r'no\s+more\s+(.+?)(?:$|,|\.)', r'don\'t\s+(?:use|do)\s+(.+?)(?:$|,|\.)',
                        r'never\s+(?:use|do)\s+(.+?)(?:$|,|\.)']:
            match = re.search(pattern, message_lower)
            if match:
                pattern_to_block = match.group(1).strip()
                break

        if not agent_name or not pattern_to_block:
            return {"agent": self.name, "action": "correct_agent",
                    "message": "I need: which agent + what to block. Example: 'correct jr-hawk blocking console.log'",
                    "next_step": None}

        # Route to Daedalus
        try:
            from daedalus import Daedalus
            daedalus = Daedalus()
            result = daedalus._add_rule({"agent_name": agent_name, "pattern": pattern_to_block,
                                         "description": f"CEO correction: {message[:100]}"})
            return {"agent": self.name, "action": "correct_agent", "corrected_agent": agent_name,
                    "message": f"I've routed this to @Daedalus.\n{result.get('message', 'Done.')}\n\n@{agent_name} will never make this mistake again.",
                    "next_step": None}
        except Exception as e:
            return {"agent": self.name, "action": "correct_agent",
                    "message": f"Failed: {e}", "next_step": None}

    # ── Handle clone (NO AI — pure Python regex) ──
    def _handle_clone(self, data: dict) -> dict:
        """CEO wants to clone a repo. Extract URL with regex."""
        message = data.get("message", data.get("raw", ""))
        url_match = re.search(r'https?://[^\s]+\.git|https?://github\.com/[^\s]+', message)
        repo_url = url_match.group(0) if url_match else ""

        if not repo_url:
            return {"agent": self.name, "action": "clone_project",
                    "message": "I need a repository URL. What's the repo URL?", "next_step": None}

        task_result = self._create_task(title=f"Clone repo: {repo_url}", task_type="feature", effort="S")
        if "error" in task_result:
            return {"agent": self.name, "action": "clone_project",
                    "message": f"Failed: {task_result['error']}", "next_step": None}

        task_id = task_result.get("id", "unknown")

        # Assign to Hephaestus (makes him yellow on UI)
        assign_result = self._assign_to_agent("Hephaestus", f"Clone repo: {repo_url}", task_id)
        run_id = assign_result.get("run_id") if isinstance(assign_result, dict) else None

        return {
            "agent": self.name, "action": "clone_project",
            "task_id": task_id, "routed_to": "Hephaestus",
            "run_id": run_id,
            "message": (
                f"Got it. I've created {task_id} and assigned it to @Hephaestus.\n"
                f"  Repo: {repo_url}\n"
                + (f"  Run {run_id} created — crash-recoverable.\n" if run_id else "")
                + f"\nI will handle this — you don't need to talk to @Hephaestus directly.\n"
                f"You should see @Hephaestus light up (yellow = working).\n"
                f"I'll let you know when it's done."
            ),
            "next_step": None,
        }

    # ── Handle question (NO AI — pure Python) ──
    def _handle_question(self, data: dict) -> dict:
        question = data.get("question", data.get("message", ""))

        if any(kw in question.lower() for kw in ["should", "which", "do you prefer", "shall we", "or"]):
            try:
                from escalate import escalate_ask
                result = escalate_ask(question, context="Needs your decision")
                return {"agent": self.name, "action": "escalate",
                        "message": result.data.get("message", "Escalated."), "next_step": "/answer <id> <answer>"}
            except:
                pass

        if any(kw in question.lower() for kw in ["what's the best", "how does", "standards", "research"]):
            return self._assign_to_agent("Athena", f"Research: {question}")

        return {"agent": self.name, "action": "answer_question",
                "message": f"I'm Hermes (COO). I coordinate work.\nQuestion: {question}\n\n/escalate for decisions\n/talk Athena for research\n/build or /tasks for tasks",
                "next_step": None}


def run(message: str, context: dict = None) -> dict:
    hermes = Hermes()
    return hermes.run(message, context)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Hermes Agent — COO / Coordinator")
        print("Usage: python hermes.py <message>")
        sys.exit(1)
    result = run(" ".join(sys.argv[1:]))
    print(result.get("message", json.dumps(result, indent=2)))
    if result.get("next_step"):
        print(f"\n→ Next: {result['next_step']}")
