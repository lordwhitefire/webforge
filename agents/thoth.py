#!/usr/bin/env python3
"""
Thoth Agent — Documentation Director
The script IS Thoth. Controls what AI does.
"""
import sys, os
from pathlib import Path
WEBFORGE_HOME = Path.home() / "webforge"
sys.path.insert(0, str(WEBFORGE_HOME / "agents"))
sys.path.insert(0, str(WEBFORGE_HOME / "mcp"))
from base import Agent

class Thoth(Agent):
    name = "Thoth"
    department = "Documentation"
    skill_file = "documentation/thoth.md"
    reports_to = "Hermes"
    can_route_to = ["Hermes"]
    allowed_actions = ["generate_docs", "answer_question", "route"]
    forbidden_actions = ["write_code", "create_bugfix_task", "create_feature_task",
        "run_standup", "research", "run_quality_check", "review_code", "learn"]
    correction_rules = []

    def execute(self, action, data, context):
        if action == "generate_docs":
            return self._generate(data)
        elif action == "answer_question":
            return {"agent": self.name, "action": action,
                "message": f"I'm Thoth. I generate docs from project state. Use /readme, /changelog, /api-docs, /env-docs, /onboard, or /docs.",
                "next_step": None}
        elif action == "route":
            return self._route_to(data.get("target", "Hermes"), data.get("message", ""))
        return {"agent": self.name, "action": action,
            "message": f"I am Thoth. I generate documentation.", "next_step": None}

    def _generate(self, data):
        doc_type = data.get("doc_type", data.get("message", "")).lower()
        try:
            from docs import readme_generate, changelog_generate, api_docs_generate, env_docs_generate, onboard_generate, generate_all
            if "readme" in doc_type:
                r = readme_generate()
            elif "changelog" in doc_type:
                r = changelog_generate()
            elif "api" in doc_type:
                r = api_docs_generate()
            elif "env" in doc_type:
                r = env_docs_generate()
            elif "onboard" in doc_type:
                r = onboard_generate()
            else:
                r = generate_all()
            return {"agent": self.name, "action": "generate_docs",
                "message": r.data.get("output", r.data.get("message", "Docs generated.")),
                "next_step": None}
        except Exception as e:
            return {"agent": self.name, "action": "generate_docs",
                "message": f"Doc generation failed: {e}", "next_step": None}

def run(message, context=None):
    return Thoth().run(message, context)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Thoth Agent — Documentation Director"); sys.exit(1)
    result = run(" ".join(sys.argv[1:]))
    print(result.get("message", result))
