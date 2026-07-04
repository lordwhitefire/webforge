#!/usr/bin/env python3
"""Forge Agent — MCP Builder. The script IS Forge."""
import sys
from pathlib import Path
WEBFORGE_HOME = Path.home() / "webforge"
sys.path.insert(0, str(WEBFORGE_HOME / "agents"))
sys.path.insert(0, str(WEBFORGE_HOME / "mcp"))
from base import Agent

class Forge(Agent):
    name = "Forge"
    department = "Meta"
    skill_file = "meta/forge.md"
    reports_to = "Daedalus"
    can_route_to = ["Daedalus"]
    allowed_actions = ["answer_question", "route"]
    forbidden_actions = ["write_code", "create_bugfix_task", "create_feature_task",
        "run_standup", "research", "generate_docs", "run_quality_check", "review_code"]
    correction_rules = []

    def execute(self, action, data, context):
        if action == "answer_question":
            return {"agent": self.name, "action": action,
                "message": f"I'm Forge. I build new MCPs when WebForge needs new capabilities. Tell @Daedalus what you need.",
                "next_step": None}
        elif action == "route":
            return self._route_to(data.get("target", "Daedalus"), data.get("message", ""))
        return {"agent": self.name, "action": action, "message": f"I am Forge.", "next_step": None}

def run(message, context=None):
    return Forge().run(message, context)

if __name__ == "__main__":
    if len(sys.argv) < 2: print("Forge Agent — MCP Builder"); sys.exit(1)
    result = run(" ".join(sys.argv[1:]))
    print(result.get("message", result))
