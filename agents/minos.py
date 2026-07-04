#!/usr/bin/env python3
"""
Minos Agent — Quality Director

THE BODY: This script IS Minos. It controls what the AI does.
THE BRAIN: The AI only reasons when Minos asks it to.

Minos's job (enforced by code):
  1. Run quality checks (lint, test, build, security)
  2. Run enforcement checks (from .webforge/checks/)
  3. Create bug tasks when bugs are found
  4. Generate code review checklists
  5. Block task-done if checks fail (lock file, not message)

Minos does NOT (enforced by code):
  - Write code (that's Hephaestus)
  - Create feature tasks (that's Hermes)
  - Research (that's Athena)
  - Generate docs (that's Thoth)
"""

import sys
from pathlib import Path

WEBFORGE_HOME = Path.home() / "webforge"
sys.path.insert(0, str(WEBFORGE_HOME / "agents"))
sys.path.insert(0, str(WEBFORGE_HOME / "mcp"))

from base import Agent


class Minos(Agent):
    """
    Minos — Quality Director

    The script controls the AI. Minos checks quality, nothing else.
    """

    name = "Minos"
    department = "Quality"
    skill_file = "quality/minos.md"
    reports_to = "Hermes"
    can_route_to = ["Hermes", "Hephaestus"]  # Routes bugs to Hephaestus

    allowed_actions = [
        "run_quality_check",
        "review_code",
        "answer_question",
        "route",
    ]

    forbidden_actions = [
        "write_code",
        "create_bugfix_task",  # Minos can create BUG tasks specifically
        "create_feature_task",
        "run_standup",
        "research",
        "generate_docs",
        "learn",
    ]

    def execute(self, action: str, data: dict, context: dict) -> dict:
        """Execute the action. CODE, not AI."""

        if action == "run_quality_check":
            return self._handle_check(data)

        elif action == "review_code":
            return self._handle_review(data)

        elif action == "answer_question":
            return self._handle_question(data)

        elif action == "route":
            return self._route_to(data.get("target", "Hermes"), data.get("message", ""))

        return {
            "agent": self.name,
            "action": action,
            "message": f"I am Minos. I check quality. Tell me what to check.",
            "next_step": None,
        }

    def _handle_check(self, data: dict) -> dict:
        """Run quality checks. CODE, not AI."""
        task_id = data.get("task_id", data.get("message", ""))

        try:
            from quality import check_run
            result = check_run(task_id)
            return {
                "agent": self.name,
                "action": "run_quality_check",
                "message": result.data.get("output", "Check complete."),
                "all_passed": result.data.get("all_passed", False),
                "next_step": None,
            }
        except Exception as e:
            return {
                "agent": self.name,
                "action": "run_quality_check",
                "message": f"Quality check failed: {e}",
                "next_step": None,
            }

    def _handle_review(self, data: dict) -> dict:
        """Generate a code review checklist. CODE, not AI."""
        task_id = data.get("task_id", data.get("message", "").replace("review", "").strip())

        try:
            from review import review_generate
            result = review_generate(task_id)
            return {
                "agent": self.name,
                "action": "review_code",
                "message": result.data.get("output", "Review complete."),
                "next_step": None,
            }
        except Exception as e:
            return {
                "agent": self.name,
                "action": "review_code",
                "message": f"Review failed: {e}",
                "next_step": None,
            }

    def _handle_question(self, data: dict) -> dict:
        """Answer a quality-related question."""
        question = data.get("question", "")
        return {
            "agent": self.name,
            "action": "answer_question",
            "message": (
                f"I'm Minos (Quality Director). I run checks, track bugs, and review code.\n"
                f"Your question: {question}\n\n"
                f"Use: /check <task-id> for quality checks\n"
                f"Use: /review <task-id> for code review\n"
                f"Use: /bug <description> to report a bug"
            ),
            "next_step": None,
        }


def run(message: str, context: dict = None) -> dict:
    """Called when developer talks to Minos."""
    minos = Minos()
    return minos.run(message, context)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Minos Agent — Quality Director")
        print("Usage: python minos.py <message>")
        sys.exit(1)

    message = " ".join(sys.argv[1:])
    result = run(message)
    print(result.get("message", json.dumps(result, indent=2)))
