#!/usr/bin/env python3
"""
Hermes Agent — COO / Coordinator

THE BODY: This script IS Hermes. It controls what the AI does.
THE BRAIN: The AI only reasons when Hermes asks it to.

Hermes's job (enforced by code):
  1. Listen to the developer
  2. Create tasks in the Kanban board
  3. Route tasks to the right department
  4. Send notifications
  5. Run standups
  6. Escalate decisions to the developer

Hermes does NOT (enforced by code):
  - Write code (that's Hephaestus)
  - Fix bugs (that's Hephaestus)
  - Test code (that's Minos)
  - Research (that's Athena)
  - Generate docs (that's Thoth)

If the AI suggests doing any of these → Hermes REFUSES.
The script takes only the task creation and routing parts.
"""

import sys
import os
import json
from pathlib import Path

# Set up paths
WEBFORGE_HOME = Path.home() / "webforge"
sys.path.insert(0, str(WEBFORGE_HOME / "agents"))
sys.path.insert(0, str(WEBFORGE_HOME / "mcp"))

from base import Agent


class Hermes(Agent):
    """
    Hermes — COO / Coordinator

    The script controls the AI. The AI is the brain, Hermes is the body.
    """

    name = "Hermes"
    department = "Executive"
    skill_file = "executive/hermes.md"
    reports_to = "CEO (Developer)"
    can_route_to = ["Hephaestus", "Athena", "Minos", "Thoth", "Daedalus", "Voss"]

    # What Hermes CAN do (code-enforced)
    allowed_actions = [
        "create_bugfix_task",
        "create_feature_task",
        "run_standup",
        "answer_question",
        "route",
        "respond",  # Allow general responses
    ]

    # What Hermes CANNOT do (code-enforced — AI is REFUSED)
    forbidden_actions = [
        "write_code",
        "research",
        "generate_docs",
        "run_quality_check",
        "review_code",
        "learn",
    ]

    # Per-agent correction rules (Daedalus adds rules here)
    correction_rules = [
        ("rule_console", lambda msg: "console".lower() not in msg.lower(),
         "Block pattern: console"),

        ("rule_localstorage", lambda msg: "localstorage".lower() not in msg.lower(),
         "Block pattern: localstorage"),
    ]

    def execute(self, action: str, data: dict, context: dict) -> dict:
        """Execute the action. This is CODE, not AI."""

        # ── Create a bugfix task ──
        if action == "create_bugfix_task":
            return self._handle_bug(data)

        # ── Create a feature task ──
        elif action == "create_feature_task":
            return self._handle_feature(data)

        # ── Run standup ──
        elif action == "run_standup":
            return self._handle_standup()

        # ── Answer a question ──
        elif action == "answer_question":
            return self._handle_question(data)

        # ── Route to another agent ──
        elif action == "route":
            return self._route_to(data.get("target", ""), data.get("message", ""))

        # ── Anything else ──
        return {
            "agent": self.name,
            "action": action,
            "message": f"I am Hermes. I received your message but I'm not sure what to do with it. "
                       f"Try: report a bug, request a feature, ask for status, or ask a question.",
            "next_step": None,
        }

    # ── Handle bug report ──
    def _handle_bug(self, data: dict) -> dict:
        """Create a bugfix task and route to Hephaestus. CODE, not AI."""
        title = data.get("title", data.get("message", "Unknown bug"))

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
        routing = self._route_to("Hephaestus", f"Bug fix needed: {title}", task_id)

        return {
            "agent": self.name,
            "action": "create_bugfix_task",
            "task_id": task_id,
            "routed_to": "Hephaestus",
            "message": (
                f"Got it. I've created {task_id} (bugfix) and routed it to @Hephaestus.\n"
                f"  Bug: {title}\n"
                f"\n"
                f"To start: /build\n"
                f"I will NOT fix this myself — that's @Hephaestus's job."
            ),
            "next_step": "/build",
        }

    # ── Handle feature request ──
    def _handle_feature(self, data: dict) -> dict:
        """Create a feature task and route to Hephaestus. CODE, not AI."""
        title = data.get("title", data.get("message", "Unknown feature"))

        # Create the task (code)
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

        # Route to Hephaestus (code)
        routing = self._route_to("Hephaestus", f"Feature needed: {title}", task_id)

        # Check if RFC will be needed (one-way door)
        rfc_note = ""
        if task_result.get("task", {}).get("type") == "feature":
            rfc_note = "\n  ⚠️ This is a feature (one-way door). An RFC will be generated when you approve."

        return {
            "agent": self.name,
            "action": "create_feature_task",
            "task_id": task_id,
            "routed_to": "Hephaestus",
            "message": (
                f"Great idea. I've created {task_id} (feature) and routed it to @Hephaestus."
                f"{rfc_note}\n"
                f"\n"
                f"To start: /build\n"
                f"I will NOT build this myself — that's @Hephaestus's job."
            ),
            "next_step": "/build",
        }

    # ── Handle standup request ──
    def _handle_standup(self) -> dict:
        """Run the standup. CODE, not AI."""
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

    # ── Handle question ──
    def _handle_question(self, data: dict) -> dict:
        """
        Answer a question. If it needs a decision → escalate.
        If it needs research → route to Athena.
        CODE decides which, not AI.
        """
        question = data.get("question", "")

        # Check if this needs a developer decision
        decision_keywords = ["should", "which", "do you prefer", "shall we", "can we"]
        needs_decision = any(kw in question.lower() for kw in decision_keywords)

        if needs_decision:
            # Escalate to developer (code)
            try:
                from escalate import escalate_ask
                result = escalate_ask(question, context="Hermes detected this needs your decision")
                return {
                    "agent": self.name,
                    "action": "escalate",
                    "message": result.data.get("message", "Escalated to developer."),
                    "next_step": f"/answer <id> <your answer>",
                }
            except:
                pass

        # Check if this needs research
        research_keywords = ["what's the best", "how does", "what are the standards", "research"]
        needs_research = any(kw in question.lower() for kw in research_keywords)

        if needs_research:
            return self._route_to("Athena", f"Research needed: {question}")

        # Otherwise, give a general answer
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

    if result.get("next_step"):
        print(f"\n→ Next: {result['next_step']}")
