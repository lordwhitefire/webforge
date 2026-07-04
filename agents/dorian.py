#!/usr/bin/env python3
"""Dorian Agent — UI Researcher. The script IS Dorian."""
import sys
from pathlib import Path
WEBFORGE_HOME = Path.home() / "webforge"
sys.path.insert(0, str(WEBFORGE_HOME / "agents"))
sys.path.insert(0, str(WEBFORGE_HOME / "mcp"))
from base import Agent

class Dorian(Agent):
    name = "Dorian"
    department = "Intelligence"
    skill_file = "intelligence/dorian.md"
    reports_to = "Athena"
    can_route_to = ["Athena"]
    allowed_actions = ["research", "answer_question", "route"]
    forbidden_actions = ["write_code", "create_bugfix_task", "create_feature_task",
        "run_standup", "generate_docs", "run_quality_check", "review_code", "learn"]
    correction_rules = []

    def execute(self, action, data, context):
        if action == "research":
            return {"agent": self.name, "action": "research",
                "ai_prompt": self._formulate_prompt(f"Research UI/UX for: {data.get('topic','')}", context),
                "message": f"I'm Dorian. I research UI/UX design references. Topic: {data.get('topic', data.get('message',''))}",
                "next_step": "AI researches → Dorian saves to knowledge → routes to @Athena"}
        elif action == "answer_question":
            return {"agent": self.name, "action": action,
                "message": f"I'm Dorian. I research UI/UX design. Ask me to research design references.", "next_step": None}
        elif action == "route":
            return self._route_to(data.get("target", "Athena"), data.get("message", ""))
        return {"agent": self.name, "action": action, "message": f"I am Dorian.", "next_step": None}

def run(message, context=None):
    return Dorian().run(message, context)

if __name__ == "__main__":
    if len(sys.argv) < 2: print("Dorian Agent — UI Researcher"); sys.exit(1)
    result = run(" ".join(sys.argv[1:]))
    print(result.get("message", result))
