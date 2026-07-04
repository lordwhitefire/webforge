#!/usr/bin/env python3
"""
Voss Agent — HR Director
The script IS Voss. Controls what AI does.
"""
import sys, os, json
from pathlib import Path
WEBFORGE_HOME = Path.home() / "webforge"
sys.path.insert(0, str(WEBFORGE_HOME / "agents"))
sys.path.insert(0, str(WEBFORGE_HOME / "mcp"))
from base import Agent

class Voss(Agent):
    name = "Voss"
    department = "HR"
    skill_file = "hr/voss.md"
    reports_to = "Hermes"
    can_route_to = ["Hermes", "Rook", "Weld"]
    allowed_actions = ["answer_question", "route"]
    forbidden_actions = ["write_code", "create_bugfix_task", "create_feature_task",
        "run_standup", "research", "generate_docs", "run_quality_check", "review_code", "learn"]
    correction_rules = []

    def execute(self, action, data, context):
        if action == "answer_question":
            return {"agent": self.name, "action": action,
                "message": f"I'm Voss (HR). I manage agents — recruit, activate, deactivate, spawn temporary workers.\nUse /hr for HR operations.",
                "next_step": None}
        elif action == "route":
            return self._route_to(data.get("target", "Hermes"), data.get("message", ""))
        return {"agent": self.name, "action": action,
            "message": f"I am Voss. I manage agents.", "next_step": None}

def run(message, context=None):
    return Voss().run(message, context)

if __name__ == "__main__":
    if len(sys.argv) < 2: print("Voss Agent — HR Director"); sys.exit(1)
    result = run(" ".join(sys.argv[1:]))
    print(result.get("message", result))
