#!/usr/bin/env python3
"""Compass Agent — System Tester. The script IS Compass."""
import sys
from pathlib import Path
WEBFORGE_HOME = Path.home() / "webforge"
sys.path.insert(0, str(WEBFORGE_HOME / "agents"))
sys.path.insert(0, str(WEBFORGE_HOME / "mcp"))
from base import Agent

class Compass(Agent):
    name = "Compass"
    department = "Meta"
    skill_file = "meta/compass.md"
    reports_to = "Daedalus"
    can_route_to = ["Daedalus"]
    allowed_actions = ["run_quality_check", "answer_question", "route"]
    forbidden_actions = ["write_code", "create_bugfix_task", "create_feature_task",
        "run_standup", "research", "generate_docs", "review_code"]
    correction_rules = []

    def execute(self, action, data, context):
        if action == "run_quality_check":
            try:
                from quality import check_run
                r = check_run("")
                return {"agent": self.name, "action": action,
                    "message": r.data.get("output", "System test complete."),
                    "next_step": None}
            except Exception as e:
                return {"agent": self.name, "action": action,
                    "message": f"System test failed: {e}", "next_step": None}
        elif action == "answer_question":
            return {"agent": self.name, "action": action,
                "message": f"I'm Compass. I test the WebForge system. Use /check to run quality checks.",
                "next_step": None}
        elif action == "route":
            return self._route_to(data.get("target", "Daedalus"), data.get("message", ""))
        return {"agent": self.name, "action": action, "message": f"I am Compass.", "next_step": None}

def run(message, context=None):
    return Compass().run(message, context)

if __name__ == "__main__":
    if len(sys.argv) < 2: print("Compass Agent — System Tester"); sys.exit(1)
    result = run(" ".join(sys.argv[1:]))
    print(result.get("message", result))
