#!/usr/bin/env python3
"""
Athena Agent — Intelligence Director

THE BODY: This script IS Athena. It controls what the AI does.
THE BRAIN: OpenCode only reasons when Athena calls ask_ai().

Athena's job (enforced by code):
  1. Research topics by asking AI
  2. Generate RFCs for one-way door tasks
  3. Add findings to the knowledge base
  4. Route results back

Athena does NOT (enforced by code):
  - Write code (that's Hephaestus)
  - Create tasks (that's Hermes)
  - Test code (that's Minos)
  - Generate docs (that's Thoth)
"""

import sys
from pathlib import Path

WEBFORGE_HOME = Path.home() / "webforge"
sys.path.insert(0, str(WEBFORGE_HOME / "agents"))
sys.path.insert(0, str(WEBFORGE_HOME / "mcp"))

from base import Agent


class Athena(Agent):
    """
    Athena — Intelligence Director

    The script controls the AI. Athena researches, nothing else.
    """

    name = "Athena"
    department = "Intelligence"
    skill_file = "intelligence/athena.md"
    reports_to = "Hermes"
    can_route_to = ["Hermes", "Dorian"]

    allowed_actions = [
        "research",
        "answer_question",
        "route",
    ]

    forbidden_actions = [
        "write_code",
        "create_bugfix_task",
        "create_feature_task",
        "run_standup",
        "generate_docs",
        "run_quality_check",
        "review_code",
        "learn",
    ]

    def execute(self, action: str, data: dict, context: dict) -> dict:
        """Execute the action. CODE calls AI only when needed."""

        if action == "research":
            return self._handle_research(data)

        elif action == "answer_question":
            return self._handle_question(data)

        elif action == "route":
            target = data.get("target", "Hermes")
            msg = data.get("message", data.get("raw", ""))
            return self._call_agent(target, msg)

        return {
            "agent": self.name,
            "action": action,
            "message": f"I am Athena. I research and analyze. Tell me what to research.",
            "next_step": None,
        }

    def _handle_research(self, data: dict) -> dict:
        """
        Research a topic. Ask AI to research, save to knowledge base, route back.
        """
        topic = data.get("topic", data.get("message", ""))

        # Ask AI to research
        ai_response = self.ask_ai(
            f"Research this topic thoroughly:\n"
            f"{topic}\n\n"
            f"Provide facts, options, pros/cons, and recommendations if applicable.\n\n"
            f"Respond with:\n"
            f"STATUS: ready or needs_clarification\n"
            f"ACTION: report_findings\n"
            f"FINDINGS: the research results (detailed)\n"
            f"MESSAGE: brief summary"
        )

        if ai_response.get("status") == "error":
            return {
                "agent": self.name,
                "action": "research",
                "message": f"I'm Athena. The AI is not available: {ai_response.get('message', 'unknown error')}. I've saved your research request. Say 'continue' to retry.",
                "next_step": "continue",
            }

        findings = ai_response.get("findings", ai_response.get("message", ""))
        summary = ai_response.get("message", "")

        # Save to knowledge base
        try:
            from knowledge import knowledge_add
            knowledge_add(topic, findings, "research")
        except Exception:
            pass

        # Route back to Hermes or reports_to
        route_result = {}
        if self.reports_to:
            route_result = self._call_agent(
                self.reports_to,
                f"Research complete on: {topic}\n{summary}",
                {"findings": findings[:500]}
            )

        return {
            "agent": self.name,
            "action": "research",
            "topic": topic,
            "message": (
                f"Research complete on: {topic}\n\n"
                f"{summary[:500]}\n\n"
                f"Full findings saved to knowledge base.\n"
                f"Routed to @{self.reports_to}."
            ),
            "next_step": None,
            "agent_result": route_result,
        }

    def _handle_question(self, data: dict) -> dict:
        """Handle a question by asking AI for the answer."""
        question = data.get("question", data.get("message", ""))

        ai_response = self.ask_ai(
            f"Answer this research question:\n"
            f"{question}\n\n"
            f"Provide accurate technical information. If you're not sure, say so.\n\n"
            f"Respond with:\n"
            f"STATUS: ready or needs_clarification\n"
            f"ACTION: answer\n"
            f"MESSAGE: your answer"
        )

        if ai_response.get("status") == "error":
            return {
                "agent": self.name,
                "action": "answer_question",
                "message": f"AI is not available: {ai_response.get('message', 'unknown error')}. Please try again later.",
                "next_step": None,
            }

        return {
            "agent": self.name,
            "action": "answer_question",
            "message": ai_response.get("message", f"I couldn't find an answer to: {question}"),
            "next_step": None,
        }


# ── Entry point ──

def run(message: str, context: dict = None) -> dict:
    """Called when another agent or the developer talks to Athena."""
    athena = Athena()
    return athena.run(message, context)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Athena Agent — Intelligence Director")
        print("Usage: python athena.py <message>")
        print()
        print("Examples:")
        print("  python athena.py 'research JWT authentication best practices'")
        sys.exit(1)

    message = " ".join(sys.argv[1:])
    result = run(message)
    print(result.get("message", json.dumps(result, indent=2)))
