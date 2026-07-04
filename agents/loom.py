#!/usr/bin/env python3
"""Loom Agent — Agent Creator. The script IS Loom."""
import sys
from pathlib import Path
WEBFORGE_HOME = Path.home() / "webforge"
sys.path.insert(0, str(WEBFORGE_HOME / "agents"))
sys.path.insert(0, str(WEBFORGE_HOME / "mcp"))
from base import Agent

class Loom(Agent):
    name = "Loom"
    department = "Meta"
    skill_file = "meta/loom.md"
    reports_to = "Daedalus"
    can_route_to = ["Daedalus"]
    allowed_actions = ["answer_question", "route"]
    forbidden_actions = ["write_code", "create_bugfix_task", "create_feature_task",
        "run_standup", "research", "generate_docs", "run_quality_check", "review_code"]
    correction_rules = []

    def execute(self, action, data, context):
        if action == "answer_question":
            return {"agent": self.name, "action": action,
                "message": f"I'm Loom. I create new agent scripts when HR needs more agents. Tell @Daedalus what agent you need.",
                "next_step": None}
        elif action == "route":
            return self._route_to(data.get("target", "Daedalus"), data.get("message", ""))
        return {"agent": self.name, "action": action, "message": f"I am Loom.", "next_step": None}

def run(message, context=None):
    return Loom().run(message, context)

if __name__ == "__main__":
    if len(sys.argv) < 2: print("Loom Agent — Agent Creator"); sys.exit(1)
    result = run(" ".join(sys.argv[1:]))
    print(result.get("message", result))
