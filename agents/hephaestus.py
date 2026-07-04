#!/usr/bin/env python3
"""
Hephaestus Agent — Build Director

THE BODY: This script IS Hephaestus. It controls what the AI does.
THE BRAIN: OpenCode only reasons when Hephaestus calls ask_ai().

Hephaestus's job (enforced by code):
  1. Pick up tasks from Hermes (direct call)
  2. Ask AI to plan the build
  3. Write the code directly
  4. Route to Minos for quality review when done

Hephaestus does NOT (enforced by code):
  - Create tasks (that's Hermes)
  - Research (that's Athena)
  - Test code (that's Minos)
  - Generate docs (that's Thoth)
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
    can_route_to = ["Minos"]

    allowed_actions = [
        "write_code",
        "review_code",
        "route",
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
        """Execute the action. CODE calls AI only when needed."""

        if action == "write_code":
            return self._handle_build(data, context)

        elif action == "review_code":
            return self._handle_review(data)

        elif action == "route":
            return self._call_agent(data.get("target", "Minos"), data.get("message", ""))

        return {
            "agent": self.name,
            "action": action,
            "message": f"I am Hephaestus. I build code. Tell me what to build.",
            "next_step": None,
        }

    def _handle_build(self, data: dict, context: dict) -> dict:
        """
        Handle a build request. Ask AI to plan, then build directly.
        """
        task = data.get("task", data.get("message", ""))
        task_id = (context or {}).get("task_id", "unknown")

        # Step 1: Ask AI to plan the build
        plan_response = self.ask_ai(
            f"Plan the implementation for this task:\n"
            f"Task: {task}\n"
            f"Task ID: {task_id}\n\n"
            f"List the files that need to be created or modified and a brief plan.\n\n"
            f"Respond with:\n"
            f"STATUS: ready or needs_clarification\n"
            f"ACTION: write_code\n"
            f"FILES: comma-separated list of file paths\n"
            f"MESSAGE: implementation plan"
        )

        if plan_response.get("status") == "error":
            return {
                "agent": self.name,
                "action": "write_code",
                "message": f"I'm Hephaestus. The AI is not available: {plan_response.get('message', 'unknown error')}. I've saved the task. Say 'continue' to retry.",
                "next_step": "continue",
            }

        files = plan_response.get("files", "")
        plan = plan_response.get("message", "")

        # Step 2: Ask AI to write the actual code for each file
        if files:
            ai_response = self.ask_ai(
                f"Write the code for this task.\n"
                f"Task: {task}\n"
                f"Plan: {plan}\n"
                f"Files to create/modify: {files}\n\n"
                f"For each file, provide the full file path and complete code content.\n\n"
                f"Respond with:\n"
                f"STATUS: done or error\n"
                f"ACTION: write_files\n"
                f"FILES: JSON object with filename as key and code content as value\n"
                f"MESSAGE: summary of what was written"
            )

            if ai_response.get("status") == "error":
                return {
                    "agent": self.name,
                    "action": "write_code",
                    "message": f"AI error while writing code for task {task_id}: {ai_response.get('message', 'unknown error')}. Saved state. Say 'continue' to retry.",
                    "next_step": "continue",
                }

            # Write the files DIRECTLY (no temp files, no pipeline)
            files_written = []
            files_data = ai_response.get("files", {})
            if isinstance(files_data, dict):
                for filepath, content in files_data.items():
                    try:
                        full_path = Path(self.project_root) / filepath
                        full_path.parent.mkdir(parents=True, exist_ok=True)
                        full_path.write_text(content, encoding="utf-8")
                        files_written.append(filepath)
                    except Exception as e:
                        print(f"  ⚠️  Could not write {filepath}: {e}")

            summary = ai_response.get("message", "Code written.")

            # Route to Minos for quality review
            result = self._call_agent("Minos", f"Review code for task {task_id}: {files}", {"task_id": task_id})

            return {
                "agent": self.name,
                "action": "write_code",
                "files_written": files_written,
                "message": (
                    f"Built task {task_id}. {summary}\n"
                    f"Files: {', '.join(files_written) if files_written else 'none'}\n"
                    f"Routed to @Minos for quality review."
                ),
                "next_step": None,
                "agent_result": result,
            }

        return {
            "agent": self.name,
            "action": "write_code",
            "message": f"Build planned for task {task_id} but no files specified. {plan}",
            "next_step": None,
        }

    def _handle_review(self, data: dict) -> dict:
        """Review code. Calls AI to review, but script controls what happens."""
        task = data.get("task", data.get("message", ""))

        ai_response = self.ask_ai(
            f"Review this code:\n{task}\n\n"
            f"Check for bugs, security issues, and style problems.\n\n"
            f"Respond with:\n"
            f"STATUS: approved | changes_requested\n"
            f"ACTION: report_results\n"
            f"ISSUES: list of issues found (or 'none')\n"
            f"MESSAGE: review summary"
        )

        if ai_response.get("status") == "error":
            return {
                "agent": self.name,
                "action": "review_code",
                "message": f"AI error during review: {ai_response.get('message', 'unknown error')}. Saved state. Say 'continue' to retry.",
                "next_step": "continue",
            }

        return {
            "agent": self.name,
            "action": "review_code",
            "message": ai_response.get("message", "Review complete."),
            "next_step": None,
        }


# ── Entry point ──

def run(message: str, context: dict = None) -> dict:
    """Called when another agent or the developer talks to Hephaestus."""
    heph = Hephaestus()
    return heph.run(message, context)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Hephaestus Agent — Build Director")
        print("Usage: python hephaestus.py <message>")
        print()
        print("Examples:")
        print("  python hephaestus.py 'build login component for task-123'")
        sys.exit(1)

    message = " ".join(sys.argv[1:])
    result = run(message)
    print(result.get("message", json.dumps(result, indent=2)))
