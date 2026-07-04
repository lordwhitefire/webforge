#!/usr/bin/env python3
"""
Athena Agent — Intelligence Director

THE BODY: This script IS Athena. It controls what the AI does.
THE BRAIN: The AI only reasons when Athena asks it to.

Athena's job (enforced by code):
  1. Research topics (calls AI to search/research)
  2. Generate RFCs for one-way door tasks
  3. Add findings to the knowledge base
  4. Route results back to Hermes

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
        """Execute the action. CODE, not AI."""

        if action == "research":
            return self._handle_research(data, context)

        elif action == "answer_question":
            return self._handle_question(data)

        elif action == "route":
            return self._route_to(data.get("target", "Hermes"), data.get("message", ""))

        return {
            "agent": self.name,
            "action": action,
            "message": f"I am Athena. I research and generate RFCs. Tell me what to research.",
            "next_step": None,
        }

    def _handle_research(self, data: dict, context: dict) -> dict:
        """
        Research a topic. Calls AI for the research, but script controls
        what happens with the results.

        The AI gets a CONSTRAINED prompt: "research this topic."
        The script saves the result to the knowledge base and routes back to Hermes.
        """
        topic = data.get("topic", data.get("message", ""))

        # Formulate a CONSTRAINED prompt for the AI
        ai_prompt = self._formulate_prompt(
            task=f"Research this topic and provide findings: {topic}",
            context=context,
        )

        # Save to knowledge base (code, not AI)
        try:
            from knowledge import knowledge_add
            knowledge_add(topic, "(AI research pending — see prompt)", "standards")
        except:
            pass

        return {
            "agent": self.name,
            "action": "research",
            "ai_prompt": ai_prompt,
            "topic": topic,
            "message": (
                f"I'm Athena (Intelligence Director). I'm researching: {topic}\n\n"
                f"I've formulated a research prompt for the AI.\n"
                f"When the AI returns findings, I will:\n"
                f"  1. Save them to the knowledge base\n"
                f"  2. Route the results back to @Hermes\n"
                f"\n"
                f"I will NOT write code, create tasks, or test — that's not my job."
            ),
            "next_step": "AI researches → Athena saves to knowledge → routes to @Hermes",
        }

    def _handle_question(self, data: dict) -> dict:
        """Answer a question using intelligence knowledge."""
        question = data.get("question", "")

        # Search knowledge base first (code, not AI)
        try:
            from knowledge import knowledge_search
            result = knowledge_search(question)
            if result.data.get("count", 0) > 0:
                findings = result.data.get("results", [])
                findings_text = "\n".join(f"  - [{f['category']}] {f['title']}" for f in findings[:5])
                return {
                    "agent": self.name,
                    "action": "answer_question",
                    "message": f"I found relevant research:\n{findings_text}\n\nUse /knowledge \"{question}\" for details.",
                    "next_step": None,
                }
        except:
            pass

        return {
            "agent": self.name,
            "action": "answer_question",
            "message": (
                f"I'm Athena. I don't have research on that yet.\n"
                f"Ask me to research: /talk Athena \"research {question}\""
            ),
            "next_step": None,
        }


def run(message: str, context: dict = None) -> dict:
    """Called when developer talks to Athena."""
    athena = Athena()
    return athena.run(message, context)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Athena Agent — Intelligence Director")
        print("Usage: python athena.py <message>")
        sys.exit(1)

    message = " ".join(sys.argv[1:])
    result = run(message)
    print(result.get("message", json.dumps(result, indent=2)))
