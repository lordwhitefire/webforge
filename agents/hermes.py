#!/usr/bin/env python3
"""
Hermes Agent — COO / Coordinator

THE BODY: This script IS Hermes. It controls what the AI does.
THE BRAIN: OpenCode (the AI) only reasons when Hermes asks it to via ask_ai().

PRINCIPLE: The script does NOT call OpenCode for simple tasks.
- "fix the cart bug" → Python parser detects "bug" → creates bugfix task → routes. NO AI.
- "add a wishlist feature" → Python parser detects "add" → creates feature task → routes. NO AI.
- "clone this repo" → Python regex extracts URL → creates task → routes. NO AI.
- "correct agent X" → Python regex extracts agent name + pattern → routes to Daedalus. NO AI.

AI is ONLY needed for truly ambiguous messages that Python can't parse.
In that case, ask_ai() returns a prompt for the frontend to send to OpenCode.
The script NEVER blocks waiting for OpenCode to respond.

CEO'S SOLE POINT OF CONTACT:
The CEO does NOT talk to other agents for work routing.
The CEO talks to Hermes. Hermes talks to all other agents.
"""

import sys
import os
import json
import re
from pathlib import Path

# Set up paths
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
        "correct_agent",
        "clone_project",
    ]

    forbidden_actions = [
        "write_code",
        "research",
        "generate_docs",
        "run_quality_check",
        "review_code",
        "learn",
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
            target = data.get("target", "")
            msg = data.get("message", data.get("raw", ""))
            return self._call_agent(target, msg)

        # Unknown action — return without calling AI
        return {
            "agent": self.name,
            "action": "respond",
            "message": (
                f"I'm Hermes (COO). I didn't understand that request.\n"
                f"I can:\n"
                f"  - Create tasks (bugs, features)\n"
                f"  - Clone repos\n"
                f"  - Correct agent behavior\n"
                f"  - Run standup\n"
                f"  - Answer questions\n"
                f"Tell me what you need."
            ),
            "next_step": None,
        }

    # ── Handle bug report (NO AI — pure Python) ──
    def _handle_bug(self, data: dict) -> dict:
        """Create a bugfix task and route to Hephaestus. Pure code, no AI."""
        title = data.get("title", data.get("message", "Unknown bug"))

        # Clean up the title
        title = title.replace("fix ", "").replace("Fix ", "").strip()
        if not title:
            title = data.get("message", "Unknown bug")

        # Create the task (code)
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

        # Route to Hephaestus (code)
        self._route_to("Hephaestus", f"Bug fix needed: {title}", task_id)

        return {
            "agent": self.name,
            "action": "create_bugfix_task",
            "task_id": task_id,
            "routed_to": "Hephaestus",
            "message": (
                f"Got it. I've created {task_id} (bugfix) and routed it to @Hephaestus.\n"
                f"  Bug: {title}\n"
                f"\nTo start: /build\n"
                f"I will NOT fix this myself — that's @Hephaestus's job."
            ),
            "next_step": "/build",
        }

    # ── Handle feature request (NO AI — pure Python) ──
    def _handle_feature(self, data: dict) -> dict:
        """Create a feature task and route to Hephaestus. Pure code, no AI."""
        title = data.get("title", data.get("message", "Unknown feature"))

        # Clean up the title
        for prefix in ["add ", "create ", "implement ", "build ", "i want "]:
            if title.lower().startswith(prefix):
                title = title[len(prefix):].strip()
                break

        if not title:
            title = data.get("message", "Unknown feature")

        # Create the task (code)
        task_result = self._create_task(
            title=title.capitalize(),
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

        # Route to Hephaestus (code)
        self._route_to("Hephaestus", f"Feature needed: {title}", task_id)

        return {
            "agent": self.name,
            "action": "create_feature_task",
            "task_id": task_id,
            "routed_to": "Hephaestus",
            "message": (
                f"Great idea. I've created {task_id} (feature) and routed it to @Hephaestus.\n"
                f"  Feature: {title}\n"
                f"  ⚠️ This is a feature (one-way door). An RFC will be generated when you approve.\n"
                f"\nTo start: /build\n"
                f"I will NOT build this myself — that's @Hephaestus's job."
            ),
            "next_step": "/build",
        }

    # ── Handle standup (NO AI — pure Python) ──
    def _handle_standup(self) -> dict:
        """Run the standup. Pure code, no AI."""
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

    # ── Handle correction (NO AI — pure Python regex) ──
    def _handle_correction(self, data: dict) -> dict:
        """
        CEO wants to correct an agent's behavior.
        Parse with Python regex — no AI needed.

        Examples:
          "correct hermes — stop suggesting localStorage"
          "correct jr-hawk blocking console.log"
          "tell daedalus to fix hermes — he keeps writing code"
        """
        message = data.get("message", data.get("raw", ""))
        message_lower = message.lower()

        # Extract agent name
        agent_name = ""
        patterns = [
            r'correct\s+(\w+(?:-\w+)*)',
            r'fix\s+(\w+(?:-\w+)*)\s+(?:script|agent|behavior)',
            r'tell\s+daedalus.*?(?:fix|correct)\s+(\w+(?:-\w+)*)',
            r'stop\s+(\w+(?:-\w+)*)\s+from',
        ]
        for pattern in patterns:
            match = re.search(pattern, message_lower)
            if match:
                agent_name = match.group(1)
                break

        # Extract pattern to block
        pattern_to_block = ""
        block_patterns = [
            r'blocking\s+(.+?)(?:$|\.)',
            r'block\s+(.+?)(?:$|\.)',
            r'stop.*?from\s+(.+?)(?:$|\.)',
            r'stop\s+suggesting\s+(.+?)(?:$|,|\.)',
            r'no\s+more\s+(.+?)(?:$|,|\.)',
            r'don\'t\s+(?:use|do)\s+(.+?)(?:$|,|\.)',
            r'never\s+(?:use|do)\s+(.+?)(?:$|,|\.)',
        ]
        for pattern in block_patterns:
            match = re.search(pattern, message_lower)
            if match:
                pattern_to_block = match.group(1).strip()
                break

        if not agent_name or not pattern_to_block:
            return {
                "agent": self.name,
                "action": "correct_agent",
                "message": (
                    f"I need to know which agent to correct and what behavior to block.\n"
                    f"Example: 'correct jr-hawk blocking console.log'\n"
                    f"Example: 'correct hermes — stop suggesting localStorage'"
                ),
                "next_step": None,
            }

        # Route to Daedalus to patch the agent's script (code)
        try:
            from daedalus import Daedalus
            daedalus = Daedalus()
            result = daedalus._add_rule({
                "agent_name": agent_name,
                "pattern": pattern_to_block,
                "description": f"Auto-corrected by CEO via Hermes: {message[:100]}",
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

    # ── Handle clone (NO AI — pure Python regex) ──
    def _handle_clone(self, data: dict) -> dict:
        """
        CEO wants to clone a repo. Extract URL with regex — no AI needed.
        """
        message = data.get("message", data.get("raw", ""))

        # Extract repo URL with regex
        url_match = re.search(r'https?://[^\s]+\.git|https?://github\.com/[^\s]+', message)
        repo_url = url_match.group(0) if url_match else ""

        if not repo_url:
            return {
                "agent": self.name,
                "action": "clone_project",
                "message": "I need a repository URL to clone. What's the repo URL?",
                "next_step": None,
            }

        # Create a task for Hephaestus (code)
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

        # Route to Hephaestus — Hermes handles it, NOT the CEO
        self._route_to("Hephaestus", f"Clone this repo: {repo_url}", task_id)

        return {
            "agent": self.name,
            "action": "clone_project",
            "task_id": task_id,
            "routed_to": "Hephaestus",
            "message": (
                f"Got it. I've created {task_id} and routed it to @Hephaestus.\n"
                f"  Repo: {repo_url}\n\n"
                f"I will handle this — you don't need to talk to @Hephaestus directly.\n"
                f"I'll let you know when it's done."
            ),
            "next_step": None,
        }

    # ── Handle question (NO AI — pure Python) ──
    def _handle_question(self, data: dict) -> dict:
        """Answer a question. Use Python logic, not AI."""
        question = data.get("question", data.get("message", ""))

        # Check if this needs a developer decision
        decision_keywords = ["should", "which", "do you prefer", "shall we", "can we", "or"]
        needs_decision = any(kw in question.lower() for kw in decision_keywords)

        if needs_decision:
            try:
                from escalate import escalate_ask
                result = escalate_ask(question, context="Hermes detected this needs your decision")
                return {
                    "agent": self.name,
                    "action": "escalate",
                    "message": result.data.get("message", "Escalated to developer."),
                    "next_step": "/answer <id> <your answer>",
                }
            except:
                pass

        # Check if this needs research
        research_keywords = ["what's the best", "how does", "what are the standards", "research"]
        needs_research = any(kw in question.lower() for kw in research_keywords)

        if needs_research:
            return self._route_to("Athena", f"Research needed: {question}")

        # General answer
        return {
            "agent": self.name,
            "action": "answer_question",
            "message": (
                f"I'm Hermes (COO). I coordinate work — I don't have deep technical knowledge.\n"
                f"Your question: {question}\n\n"
                f"If this is a decision for you: /escalate \"{question}\"\n"
                f"If this needs research: /talk Athena \"{question}\"\n"
                f"If this is about a task: /build or /tasks"
            ),
            "next_step": None,
        }


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
        print("  python hermes.py 'correct jr-hawk blocking console.log'")
        print("  python hermes.py 'clone https://github.com/user/repo'")
        sys.exit(1)

    message = " ".join(sys.argv[1:])
    result = run(message)
    print(result.get("message", json.dumps(result, indent=2)))

    if result.get("next_step"):
        print(f"\n→ Next: {result['next_step']}")
