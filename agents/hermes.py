#!/usr/bin/env python3
"""
Hermes Agent — COO / Coordinator

THE BODY: This script IS Hermes. It controls what the AI does.
THE BRAIN: OpenCode (the AI) only reasons when Hermes asks it to via ask_ai().

Hermes's job (enforced by code):
  1. Listen to the developer
  2. Ask OpenCode to classify the request
  3. Create tasks in the Kanban board
  4. Route tasks to the right department via _call_agent()
  5. Run standups
  6. Escalate decisions to the developer

Hermes does NOT (enforced by code):
  - Write code (that's Hephaestus)
  - Fix bugs (that's Hephaestus)
  - Test code (that's Minos)
  - Research (that's Athena)
  - Generate docs (that's Thoth)

If the AI suggests doing any of these → Hermes REFUSES.
"""

import sys
import os
import json
from pathlib import Path

WEBFORGE_HOME = Path.home() / "webforge"
sys.path.insert(0, str(WEBFORGE_HOME / "agents"))
sys.path.insert(0, str(WEBFORGE_HOME / "mcp"))

from base import Agent


class Hermes(Agent):
    """
    Hermes — COO / Coordinator

    THE CEO'S SOLE POINT OF CONTACT.
    The CEO does NOT talk to other agents for work routing.
    The CEO talks to Hermes. Hermes talks to all other agents.

    The script controls the AI. The AI is the brain, Hermes is the body.

    AUTONOMOUS OPERATION:
    - The system runs autonomously. Agents work on their own.
    - They only come to the CEO when they need human input:
      a question, a decision, something they can't figure out.
    - Hermes coordinates everything and reports to the CEO.

    CORRECTION FLOW:
    - CEO tells Hermes "correct agent X's behavior"
    - Hermes routes to Daedalus
    - Daedalus rewrites that agent's script with the correction in code
    - The agent never makes that mistake again
    """

    name = "Hermes"
    department = "Executive"
    skill_file = "executive/hermes.md"
    reports_to = "CEO (Developer)"
    can_route_to = ["Hephaestus", "Athena", "Minos", "Thoth", "Daedalus", "Voss"]

    allowed_actions = [
        "create_bugfix_task",
        "create_feature_task",
        "run_standup",
        "answer_question",
        "route",
        "respond",
        "correct_agent",  # CEO tells Hermes to correct an agent's behavior
        "clone_project",  # CEO tells Hermes to clone a repo for the build team
    ]

    forbidden_actions = [
        "write_code",
        "research",
        "generate_docs",
        "run_quality_check",
        "review_code",
        "learn",
    ]

    correction_rules = [
        ("rule_console", lambda msg: "console".lower() not in msg.lower(),
         "Block pattern: console"),
        ("rule_localstorage", lambda msg: "localstorage".lower() not in msg.lower(),
         "Block pattern: localstorage"),
    ]

    def execute(self, action: str, data: dict, context: dict) -> dict:
        """Execute the action. CODE calls AI only when needed."""

        if action == "create_bugfix_task":
            return self._handle_bug(data, context)

        elif action == "create_feature_task":
            return self._handle_feature(data, context)

        elif action == "run_standup":
            return self._handle_standup()

        elif action == "answer_question":
            return self._handle_question(data)

        elif action == "correct_agent":
            return self._handle_correction(data)

        elif action == "clone_project":
            return self._handle_clone(data, context)

        elif action == "route":
            target = data.get("target", "")
            msg = data.get("message", data.get("raw", ""))
            return self._call_agent(target, msg)

        # Unknown action — ask AI to classify
        raw_message = data.get("raw", data.get("message", ""))
        ai_response = self.ask_ai(
            f"The user said: '{raw_message}'\n\n"
            f"Classify this request. What does the user want to do?\n"
            f"Options:\n"
            f"1. create_task — a new feature or bug\n"
            f"2. close_task — mark a task as done\n"
            f"3. research — investigate something\n"
            f"4. question — asking something\n"
            f"5. route — send to another agent\n"
            f"6. status — check progress\n\n"
            f"If close_task, extract the task ID (e.g. task-002).\n\n"
            f"Respond with:\n"
            f"STATUS: ready or needs_clarification\n"
            f"ACTION: create_task | close_task | research | question | route | status\n"
            f"TASK_ID: task ID if close_task or create_task\n"
            f"TARGET: department or agent name if routing\n"
            f"MESSAGE: brief explanation"
        )

        if ai_response.get("status") == "error":
            return {
                "agent": self.name,
                "action": "respond",
                "message": f"I'm Hermes. The AI is not available right now: {ai_response.get('message', 'unknown error')}. Please try again.",
                "next_step": None,
            }

        action_from_ai = ai_response.get("action", "")

        if action_from_ai == "close_task":
            task_id = ai_response.get("task_id", "")
            if task_id:
                try:
                    from task import task_done
                    result = task_done(task_id, ai_response.get("message", "Closed"))
                    return {
                        "agent": self.name,
                        "action": "close_task",
                        "task_id": task_id,
                        "message": f"Closed {task_id}. {ai_response.get('message', '')}",
                        "next_step": None,
                    }
                except Exception as e:
                    return {
                        "agent": self.name,
                        "action": "close_task",
                        "message": f"Failed to close {task_id}: {e}",
                        "next_step": None,
                    }
            return {
                "agent": self.name,
                "action": "close_task",
                "message": f"Which task should I close?",
                "next_step": None,
            }

        if action_from_ai == "create_task" and "bug" in raw_message.lower():
            return self._handle_bug(data, context)
        if action_from_ai == "create_task":
            return self._handle_feature(data, context)
        if action_from_ai == "research":
            return self._call_agent("Athena", raw_message)
        if action_from_ai == "question":
            return self._handle_question(data)
        if action_from_ai == "status":
            return self._handle_standup()
        if action_from_ai == "route":
            target = ai_response.get("target", "")
            if target in self.can_route_to:
                return self._call_agent(target, raw_message)

        return {
            "agent": self.name,
            "action": "respond",
            "message": ai_response.get("message", f"Hermes here. I received: {raw_message}"),
            "next_step": None,
        }

    # ── Handle bug report ──

    def _handle_bug(self, data: dict, context: dict) -> dict:
        """Handle a bug report. Ask AI to classify, then create task and route."""
        title = data.get("title", data.get("message", "Unknown bug"))

        # Ask AI to classify the bug
        ai_response = self.ask_ai(
            f"Classify this bug report and determine the department to route it to.\n"
            f"Bug: {title}\n\n"
            f"Respond with:\n"
            f"STATUS: ready or needs_clarification\n"
            f"ACTION: create_bugfix_task\n"
            f"TARGET: department head (Hephaestus for build, Athena for research, etc)\n"
            f"MESSAGE: brief explanation"
        )

        if ai_response.get("status") == "error":
            return {
                "agent": self.name,
                "action": "create_bugfix_task",
                "message": f"I'm Hermes. The AI is not available right now: {ai_response.get('message', 'unknown error')}. I've saved your bug report. Say 'continue' to retry.",
                "next_step": "continue",
            }

        target = ai_response.get("target", "Hephaestus")
        explanation = ai_response.get("message", "")

        # Create the task
        task_result = self._create_task(
            title=f"[BUG] {title}",
            task_type="bugfix",
            effort="S",
        )

        if "error" in task_result:
            return {
                "agent": self.name,
                "action": "create_bugfix_task",
                "message": f"Failed to create task: {task_result['error']}",
                "next_step": None,
            }

        task_id = task_result.get("id", "unknown")

        # Route to the department head DIRECTLY
        if target in self.can_route_to:
            agent_result = self._call_agent(target, f"Bug fix needed: {title}", {"task_id": task_id})
            return {
                "agent": self.name,
                "action": "create_bugfix_task",
                "task_id": task_id,
                "routed_to": target,
                "message": (
                    f"Got it. I've created {task_id} (bugfix) and routed it to @{target}.\n"
                    f"  Bug: {title}\n"
                    f"I will NOT fix this myself — that's @{target}'s job."
                ),
                "next_step": None,
                "agent_result": agent_result,
            }

        return {
            "agent": self.name,
            "action": "create_bugfix_task",
            "task_id": task_id,
            "message": f"Created {task_id} (bugfix). Could not route to {target}.",
            "next_step": None,
        }

    # ── Handle feature request ──

    def _handle_feature(self, data: dict, context: dict) -> dict:
        """Handle a feature request. Ask AI to classify, create task, route."""
        title = data.get("title", data.get("message", "Unknown feature"))

        # Ask AI to classify the feature
        ai_response = self.ask_ai(
            f"Classify this feature request and determine the department to route it to.\n"
            f"Feature: {title}\n\n"
            f"Also determine if this needs an RFC (one-way door decisions like new architecture, "
            f"new database, breaking API changes).\n\n"
            f"Respond with:\n"
            f"STATUS: ready or needs_clarification\n"
            f"ACTION: create_feature_task\n"
            f"TARGET: department head\n"
            f"NEEDS_RFC: yes or no\n"
            f"MESSAGE: brief explanation"
        )

        if ai_response.get("status") == "error":
            return {
                "agent": self.name,
                "action": "create_feature_task",
                "message": f"I'm Hermes. The AI is not available right now: {ai_response.get('message', 'unknown error')}. I've saved your request. Say 'continue' to retry.",
                "next_step": "continue",
            }

        target = ai_response.get("target", "Hephaestus")
        needs_rfc = ai_response.get("needs_rfc", "no")
        explanation = ai_response.get("message", "")

        # Create the task
        task_result = self._create_task(
            title=title,
            task_type="feature",
            effort="M",
        )

        if "error" in task_result:
            return {
                "agent": self.name,
                "action": "create_feature_task",
                "message": f"Failed to create task: {task_result['error']}",
                "next_step": None,
            }

        task_id = task_result.get("id", "unknown")
        rfc_note = "\n  ⚠️ RFC needed for this feature." if needs_rfc == "yes" else ""

        # Route to the department head DIRECTLY
        if target in self.can_route_to:
            agent_result = self._call_agent(target, f"Feature needed: {title}", {"task_id": task_id, "needs_rfc": needs_rfc})
            return {
                "agent": self.name,
                "action": "create_feature_task",
                "task_id": task_id,
                "routed_to": target,
                "message": (
                    f"Great idea. I've created {task_id} (feature) and routed it to @{target}.{rfc_note}\n"
                    f"I will NOT build this myself — that's @{target}'s job."
                ),
                "next_step": None,
                "agent_result": agent_result,
            }

        return {
            "agent": self.name,
            "action": "create_feature_task",
            "task_id": task_id,
            "message": f"Created {task_id} (feature). Could not route to {target}.",
            "next_step": None,
        }

    # ── Handle standup ──

    def _handle_standup(self) -> dict:
        """Run the standup. Calls standup MCP directly."""
        try:
            from standup import standup_run
            result = standup_run()
            return {
                "agent": self.name,
                "action": "run_standup",
                "message": result.data.get("output", "Standup unavailable."),
                "next_step": None,
            }
        except Exception as e:
            return {
                "agent": self.name,
                "action": "run_standup",
                "message": f"Standup failed: {e}",
                "next_step": None,
            }

    # ── Handle correction request ──
    # CEO says: "correct agent X — they did Y wrong, they should do Z instead"
    # Hermes routes this to Daedalus, who rewrites that agent's script

    def _handle_correction(self, data: dict) -> dict:
        """
        CEO wants to correct an agent's behavior.
        Hermes routes to Daedalus to patch the agent's script.

        Flow: CEO → Hermes → Daedalus → rewrites agent .py file
        """
        message = data.get("message", data.get("raw", ""))

        # Ask AI to parse: which agent, what's wrong, what to do instead
        ai_response = self.ask_ai(
            f"The CEO wants to correct an agent's behavior.\n"
            f"CEO's message: '{message}'\n\n"
            f"Extract:\n"
            f"AGENT: which agent name (e.g. hermes, hephaestus, jr-hawk)\n"
            f"PATTERN: what pattern/behavior to block (e.g. 'localStorage', 'console.log')\n"
            f"DESCRIPTION: why this is wrong\n\n"
            f"Respond with:\n"
            f"AGENT: <name>\n"
            f"PATTERN: <pattern>\n"
            f"DESCRIPTION: <description>"
        )

        agent_name = ai_response.get("agent", "")
        pattern = ai_response.get("pattern", "")
        description = ai_response.get("description", "")

        if not agent_name or not pattern:
            return {
                "agent": self.name,
                "action": "correct_agent",
                "message": (
                    f"I need to know which agent to correct and what behavior to block.\n"
                    f"Example: 'correct hermes — stop suggesting localStorage, use httpOnly cookies instead'"
                ),
                "next_step": None,
            }

        # Route to Daedalus to patch the agent's script
        try:
            import sys
            sys.path.insert(0, str(Path.home() / "webforge" / "agents"))
            from daedalus import Daedalus
            daedalus = Daedalus()
            result = daedalus._add_rule({
                "agent_name": agent_name,
                "pattern": pattern,
                "description": description,
            })
            return {
                "agent": self.name,
                "action": "correct_agent",
                "corrected_agent": agent_name,
                "message": (
                    f"I've routed this correction to @Daedalus.\n"
                    f"{result.get('message', 'Correction applied.')}\n\n"
                    f"The agent @{agent_name} will never make this mistake again. "
                    f"The correction is now permanently in their script."
                ),
                "next_step": None,
            }
        except Exception as e:
            return {
                "agent": self.name,
                "action": "correct_agent",
                "message": f"Failed to route correction to Daedalus: {e}",
                "next_step": None,
            }

    # ── Handle clone project request ──
    # CEO says: "clone this repo for the build team"
    # Hermes routes to Hephaestus to do the cloning

    def _handle_clone(self, data: dict, context: dict) -> dict:
        """
        CEO wants to clone a project/repo.
        Hermes creates a task and routes to Hephaestus.
        Hermes does NOT tell the CEO to talk to Hephaestus directly.
        """
        message = data.get("message", data.get("raw", ""))

        # Ask AI to extract the repo URL
        ai_response = self.ask_ai(
            f"The CEO wants to clone a project.\n"
            f"CEO's message: '{message}'\n\n"
            f"Extract the repository URL.\n"
            f"Respond with:\n"
            f"REPO_URL: <url>\n"
            f"DESCRIPTION: what the CEO wants to do with it"
        )

        repo_url = ai_response.get("repo_url", "")
        description = ai_response.get("description", message)

        if not repo_url:
            return {
                "agent": self.name,
                "action": "clone_project",
                "message": "I need a repository URL to clone. What's the repo URL?",
                "next_step": None,
            }

        # Create a task for Hephaestus
        task_result = self._create_task(
            title=f"Clone repo: {repo_url}",
            task_type="feature",
            effort="S",
        )

        if "error" in task_result:
            return {
                "agent": self.name,
                "action": "clone_project",
                "message": f"Failed to create task: {task_result['error']}",
                "next_step": None,
            }

        task_id = task_result.get("id", "unknown")

        # Route to Hephaestus — Hermes does the talking, NOT the CEO
        self._route_to("Hephaestus", f"Clone this repo: {repo_url}. {description}", task_id)

        return {
            "agent": self.name,
            "action": "clone_project",
            "task_id": task_id,
            "routed_to": "Hephaestus",
            "message": (
                f"Got it. I've created {task_id} and routed it to @Hephaestus.\n"
                f"  Repo: {repo_url}\n"
                f"  Task: {description}\n\n"
                f"I will handle this — you don't need to talk to @Hephaestus directly.\n"
                f"I'll let you know when it's done."
            ),
            "next_step": None,
        }

    # ── Handle question ──

    def _handle_question(self, data: dict) -> dict:
        """
        Handle a question. Ask AI to determine what to do with it.
        """
        question = data.get("question", data.get("message", ""))

        ai_response = self.ask_ai(
            f"A user asked me (Hermes, the COO) this question:\n"
            f"{question}\n\n"
            f"Determine what to do with this question:\n"
            f"1. Does it need a decision from the CEO? (keywords: should, which, do you prefer)\n"
            f"2. Does it need research? (keywords: what's the best, how does, research)\n"
            f"3. Can I answer it directly?\n\n"
            f"Respond with:\n"
            f"STATUS: ready or needs_clarification\n"
            f"ACTION: escalate_to_ceo | route_to_athena | answer_directly\n"
            f"TARGET: CEO or Athena or none\n"
            f"MESSAGE: your answer or explanation"
        )

        if ai_response.get("status") == "error":
            return {
                "agent": self.name,
                "action": "answer_question",
                "message": f"I'm Hermes. The AI is not available right now: {ai_response.get('message', 'unknown error')}. Please try again later or use /escalate.",
                "next_step": None,
            }

        action_taken = ai_response.get("action", "answer_directly")

        if action_taken == "escalate_to_ceo":
            # Show the question to the developer
            return {
                "agent": self.name,
                "action": "escalate",
                "message": (
                    f"🙋 I need your input on this question:\n"
                    f"  {question}\n\n"
                    f"Please answer so I can proceed."
                ),
                "next_step": None,
            }

        elif action_taken == "route_to_athena":
            agent_result = self._call_agent("Athena", f"Research needed: {question}")
            return {
                "agent": self.name,
                "action": "answer_question",
                "message": f"I've routed your question to @Athena for research.",
                "next_step": None,
                "agent_result": agent_result,
            }

        # answer_directly
        return {
            "agent": self.name,
            "action": "answer_question",
            "message": ai_response.get("message", f"I'm Hermes. I coordinate work. Your question: {question}"),
            "next_step": None,
        }

    # ── AI Resume Handler ──

    def _handle_ai_response(self, response: dict, context: dict) -> dict:
        """
        Called when the pipeline resumes after AI responded to ask_ai().
        Takes the AI's decision and actually executes it (route, escalate, etc).
        """
        action = response.get("action", "")
        target = response.get("target", "")
        message = response.get("message", "")

        # Route to Athena for research
        if action == "route_to_athena" or target == "Athena":
            agent_result = self._call_agent("Athena", message)
            return {
                "agent": self.name,
                "action": "route_to_athena",
                "message": f"Routed to @Athena. {message}",
                "next_step": None,
                "agent_result": agent_result,
            }

        # Escalate to CEO (user)
        if action == "escalate_to_ceo" or target == "CEO":
            return {
                "agent": self.name,
                "action": "escalate",
                "message": f"🙋 Need your input:\n{message}",
                "next_step": None,
            }

        # Create and route a feature task
        if action == "create_feature_task":
            task_result = self._create_task(message, "feature", "M")
            if "error" in task_result:
                return {"agent": self.name, "action": "create_feature_task",
                        "message": f"Failed to create task: {task_result['error']}", "next_step": None}
            task_id = task_result.get("id", "unknown")
            route_target = target if target in self.can_route_to else "Hephaestus"
            if route_target in self.can_route_to:
                agent_result = self._call_agent(route_target, message, {"task_id": task_id})
                return {
                    "agent": self.name, "action": "create_feature_task",
                    "task_id": task_id, "routed_to": route_target,
                    "message": f"Created {task_id} (feature) and routed to @{route_target}.",
                    "next_step": None, "agent_result": agent_result,
                }
            return {"agent": self.name, "action": "create_feature_task",
                    "task_id": task_id, "message": f"Created {task_id}.", "next_step": None}

        # Create and route a bugfix task
        if action == "create_bugfix_task":
            task_result = self._create_task(f"[BUG] {message}", "bugfix", "S")
            if "error" in task_result:
                return {"agent": self.name, "action": "create_bugfix_task",
                        "message": f"Failed to create task: {task_result['error']}", "next_step": None}
            task_id = task_result.get("id", "unknown")
            route_target = target if target in self.can_route_to else "Hephaestus"
            if route_target in self.can_route_to:
                agent_result = self._call_agent(route_target, f"Bug: {message}", {"task_id": task_id})
                return {
                    "agent": self.name, "action": "create_bugfix_task",
                    "task_id": task_id, "routed_to": route_target,
                    "message": f"Created {task_id} (bugfix) and routed to @{route_target}.",
                    "next_step": None, "agent_result": agent_result,
                }
            return {"agent": self.name, "action": "create_bugfix_task",
                    "task_id": task_id, "message": f"Created {task_id}.", "next_step": None}

        # Default: just respond with the AI's message
        return {
            "agent": self.name,
            "action": "respond",
            "message": message or "Done.",
            "next_step": None,
        }

    # ── Refusal → Route ──

    def run(self, message: str, context: dict = None) -> dict:
        """Override: save original message before processing, so _refuse can route with it."""
        self._last_message = message
        return super().run(message, context)

    def _refuse(self, reason: str) -> dict:
        """
        Override: instead of just refusing, route to the right agent.
        Hermes is the COO — it routes work, it doesn't tell the user to do it.
        """
        import re
        match = re.search(r'@(\w[\w-]+)', reason)
        if match:
            target = match.group(1)
            target_lower = target.lower()
            can_route_lower = [a.lower() for a in self.can_route_to]
            if target_lower in can_route_lower:
                return self._call_agent(target, getattr(self, '_last_message', reason))
        return super()._refuse(reason)


# ── Entry point ──

def run(message: str, context: dict = None) -> dict:
    """Called when developer talks to Hermes. This IS Hermes."""
    hermes = Hermes()
    return hermes.run(message, context)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Hermes Agent — COO / Coordinator")
        print("Usage: python hermes.py <message>")
        print()
        print("Examples:")
        print("  python hermes.py 'fix the cart bug'")
        print("  python hermes.py 'add a wishlist feature'")
        print("  python hermes.py 'what's the status?'")
        sys.exit(1)

    message = " ".join(sys.argv[1:])
    result = run(message)
    print(result.get("message", json.dumps(result, indent=2)))
