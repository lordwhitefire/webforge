#!/usr/bin/env python3
"""
Hephaestus Agent — Build Director

THE BODY: This script IS Hephaestus. It controls what the AI does.
THE BRAIN: The AI only reasons when Hephaestus asks it to.

Hephaestus's job (enforced by code):
  1. Pick up tasks from the Kanban board
  2. Call AI to write code for the task
  3. Commit the code via Git MCP
  4. Route to Minos for quality review when done

Hephaestus does NOT (enforced by code):
  - Create tasks (that's Hermes/Developer)
  - Route to other departments (that's Hermes)
  - Test code (that's Minos)
  - Research (that's Athena)
  - Generate docs (that's Thoth)

If the AI suggests doing any of these → Hephaestus REFUSES.
"""

import sys
import os
from pathlib import Path

WEBFORGE_HOME = Path.home() / "webforge"
sys.path.insert(0, str(WEBFORGE_HOME / "agents"))
sys.path.insert(0, str(WEBFORGE_HOME / "mcp"))

from base import Agent


class Hephaestus(Agent):
    """
    Hephaestus — Build Director

    The script controls the AI. Hephaestus builds, nothing else.
    """

    name = "Hephaestus"
    department = "Build"
    skill_file = "build/hephaestus.md"
    reports_to = "Hermes"
    can_route_to = ["Minos"]  # Only routes to Quality when done

    allowed_actions = [
        "write_code",
        "review_code",
        "route",  # Only to Minos for quality check
    ]

    forbidden_actions = [
        "create_bugfix_task",
        "create_feature_task",
        "run_standup",
        "research",
        "generate_docs",
        "run_quality_check",
        "answer_question",
        "learn",
    ]

    def execute(self, action: str, data: dict, context: dict) -> dict:
        """Execute the action. CODE, not AI."""

        if action == "write_code":
            return self._handle_build(data, context)

        elif action == "review_code":
            return self._handle_review(data)

        elif action == "route":
            return self._route_to(data.get("target", "Minos"), data.get("message", ""))

        return {
            "agent": self.name,
            "action": action,
            "message": f"I am Hephaestus. I build code. Tell me what to build.",
            "next_step": None,
        }

    def _handle_build(self, data: dict, context: dict) -> dict:
        """
        Handle a build request. This is where Hephaestus calls the AI
        to write code. But the SCRIPT controls the flow — not the AI.

        The AI gets a CONSTRAINED prompt: "write code for this task."
        The AI does NOT decide whether to build, what to build, or who to route to.
        """
        task = data.get("task", data.get("message", ""))

        # Formulate a CONSTRAINED prompt for the AI
        # The AI only writes code. It doesn't decide anything else.
        ai_prompt = self._formulate_prompt(
            task=f"Write code for this task: {task}",
            context=context,
        )

        return {
            "agent": self.name,
            "action": "write_code",
            "ai_prompt": ai_prompt,
            "message": (
                f"I'm Hephaestus (Build Director). I'm ready to build.\n"
                f"Task: {task}\n\n"
                f"I need the AI to write the code. The AI prompt is formulated.\n"
                f"When the code is written, I will:\n"
                f"  1. Commit it via Git MCP\n"
                f"  2. Route to @Minos for quality review\n"
                f"\n"
                f"I will NOT create tasks, research, or generate docs — that's not my job."
            ),
            "next_step": "AI writes code → Hephaestus commits → routes to @Minos",
        }

    def _handle_review(self, data: dict) -> dict:
        """Review code. Calls AI for review, but script controls what happens."""
        return {
            "agent": self.name,
            "action": "review_code",
            "message": (
                f"I'm Hephaestus. I can review code, but for quality checks "
                f"use @Minos (Quality Director). /review <task-id>"
            ),
            "next_step": "/review <task-id>",
        }


def run(message: str, context: dict = None) -> dict:
    """Called when developer talks to Hephaestus."""
    hephaestus = Hephaestus()
    return hephaestus.run(message, context)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Hephaestus Agent — Build Director")
        print("Usage: python hephaestus.py <message>")
        sys.exit(1)

    message = " ".join(sys.argv[1:])
    result = run(message)
    print(result.get("message", json.dumps(result, indent=2)))
