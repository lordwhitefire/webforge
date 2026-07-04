#!/usr/bin/env python3
"""
Daedalus Agent — Meta Engineering Director

THE BODY: This script IS Daedalus. It controls what the AI does.
THE BRAIN: The AI only reasons when Daedalus asks it to.

Daedalus's job (enforced by code):
  1. When developer corrects an agent → Daedalus writes a Python rule
     INTO that agent's script file
  2. The rule is a lambda function added to the agent's correction_rules list
  3. The rule runs automatically every time that agent runs
  4. If the AI tries the same mistake again → the rule blocks it → REFUSED

This is the REAL Meta Engineering loop:
  Developer: "Hermes tried to write code, tell Daedalus to fix it"
  Daedalus: opens hermes.py, adds a correction rule that checks for
            code-writing patterns, saves the file
  Next time Hermes runs: the rule checks the AI's output → if it
  suggests writing code → REFUSED

Daedalus does NOT:
  - Write application code (that's Hephaestus)
  - Create tasks (that's Hermes)
  - Test code (that's Minos)
  - Research (that's Athena)
"""

import sys
import os
import json
import re
from pathlib import Path

WEBFORGE_HOME = Path.home() / "webforge"
sys.path.insert(0, str(WEBFORGE_HOME / "agents"))
sys.path.insert(0, str(WEBFORGE_HOME / "mcp"))

from base import Agent


class Daedalus(Agent):
    """
    Daedalus — Meta Engineering Director

    Writes correction rules into other agents' scripts.
    When an agent makes a mistake, Daedalus patches that agent's .py file.
    """

    name = "Daedalus"
    department = "Meta"
    skill_file = "meta/daedalus.md"
    reports_to = "Hermes"
    can_route_to = ["Hermes"]

    allowed_actions = [
        "add_correction_rule",  # Write a rule into an agent's script
        "learn",                # Scan corrections and auto-generate rules
        "answer_question",
        "route",
    ]

    forbidden_actions = [
        "write_code",           # Not app code — that's Hephaestus
        "create_bugfix_task",
        "create_feature_task",
        "run_standup",
        "research",
        "generate_docs",
        "run_quality_check",
        "review_code",
    ]

    # Path to agents directory
    AGENTS_DIR = WEBFORGE_HOME / "agents"

    def execute(self, action: str, data: dict, context: dict) -> dict:
        """Execute the action. CODE, not AI."""

        if action == "add_correction_rule":
            return self._add_rule(data)

        elif action == "learn":
            return self._learn_from_corrections()

        elif action == "answer_question":
            return self._handle_question(data)

        elif action == "route":
            return self._route_to(data.get("target", "Hermes"), data.get("message", ""))

        return {
            "agent": self.name,
            "action": action,
            "message": f"I am Daedalus. I fix agents by writing correction rules into their scripts. Tell me what went wrong.",
            "next_step": None,
        }

    # ── The core function: write a rule into an agent's script ──
    def _add_rule(self, data: dict) -> dict:
        """
        Write a correction rule into an agent's .py file.

        data should contain:
          - agent_name: which agent to patch (e.g. "hermes")
          - pattern: what pattern to block (e.g. "localStorage")
          - rule_name: short name for the rule
          - description: human-readable description
        """
        agent_name = data.get("agent_name", "").lower().strip()
        pattern = data.get("pattern", "")
        rule_name = data.get("rule_name", f"rule_{pattern[:20].replace(' ', '_')}")
        description = data.get("description", f"Block pattern: {pattern}")

        # If agent_name is empty, try to parse from message
        if not agent_name:
            message = data.get("message", "")
            import re as _re
            agent_match = _re.search(r'(?:to|into)\s+(\w+(?:-\w+)*)\s+(?:blocking|block|preventing)', message.lower())
            if agent_match:
                agent_name = agent_match.group(1)
            pattern_match = _re.search(r'blocking\s+(.+?)(?:$|\.)', message.lower())
            if pattern_match:
                pattern = pattern_match.group(1).strip()

        if not agent_name or not pattern:
            return {
                "agent": self.name,
                "action": "add_correction_rule",
                "message": "Could not parse agent name or pattern. Usage: add rule to <agent> blocking <pattern>",
                "next_step": None,
            }

        # Find the agent's script
        agent_file = self.AGENTS_DIR / f"{agent_name}.py"

        if not agent_file.exists():
            return {
                "agent": self.name,
                "action": "add_correction_rule",
                "message": f"Agent script not found: {agent_file}. Available: {self._list_agents()}",
                "next_step": None,
            }

        # Read the current script
        content = agent_file.read_text(encoding="utf-8")

        # Check if this rule already exists
        if rule_name in content:
            return {
                "agent": self.name,
                "action": "add_correction_rule",
                "message": f"Rule '{rule_name}' already exists in {agent_name}.py",
                "next_step": None,
            }

        # Build the rule code
        # This is a lambda that checks if the pattern appears in the AI's response
        pattern_escaped = pattern.replace('"', '\\"').replace("'", "\\'")
        rule_code = f'''        ("{rule_name}", lambda msg: "{pattern_escaped}".lower() not in msg.lower(),
         "{description}"),
'''

        # Find the correction_rules list and add the rule
        # Look for: correction_rules = [
        if "correction_rules = [" in content:
            # Insert after the opening bracket
            insert_point = content.find("correction_rules = [") + len("correction_rules = [")
            # Check if there's already content (not empty)
            remaining = content[insert_point:]
            if remaining.strip().startswith("]"):
                # Empty list — insert right after [
                content = content[:insert_point] + "\n" + rule_code + "    ]" + content[insert_point + remaining.find("]") + 1:]
            else:
                # Non-empty list — insert at the beginning
                content = content[:insert_point] + "\n" + rule_code + content[insert_point:]

            # Write the updated script
            agent_file.write_text(content, encoding="utf-8")

            # Log
            self._log(f"Daedalus added rule '{rule_name}' to {agent_name}.py: blocks '{pattern}'")

            return {
                "agent": self.name,
                "action": "add_correction_rule",
                "agent_patched": agent_name,
                "rule_name": rule_name,
                "pattern": pattern,
                "message": (
                    f"✅ PATCHED {agent_name}.py\n"
                    f"  Rule: {rule_name}\n"
                    f"  Blocks: '{pattern}'\n"
                    f"  Description: {description}\n\n"
                    f"  Next time {agent_name.title()} runs, if the AI's response "
                    f"contains '{pattern}', it will be REFUSED.\n"
                    f"  This rule is now permanently in {agent_name}.py."
                ),
                "next_step": None,
            }
        else:
            # The agent doesn't have a correction_rules list yet
            return {
                "agent": self.name,
                "action": "add_correction_rule",
                "message": (
                    f"❌ {agent_name}.py doesn't have a correction_rules list. "
                    f"The agent needs to inherit from base.Agent to support rules."
                ),
                "next_step": None,
            }

    # ── Learn from all corrections in session log ──
    def _learn_from_corrections(self) -> dict:
        """
        Scan session log for corrections, then write rules into
        the relevant agent scripts.
        """
        try:
            from meta_engineering import find_corrections_in_session
            corrections = find_corrections_in_session(30)
        except:
            return {
                "agent": self.name,
                "action": "learn",
                "message": "Could not scan session log for corrections.",
                "next_step": None,
            }

        if not corrections:
            return {
                "agent": self.name,
                "action": "learn",
                "message": "✅ No corrections found. Nothing to learn.",
                "next_step": None,
            }

        rules_added = 0
        results = []

        for c in corrections:
            entry = c["entry"]

            # Parse the correction
            wrong_match = re.search(r'Wrong:\s*(.+?)\s*→', entry)
            right_match = re.search(r'Right:\s*(.+?)\s*→', entry)

            if not wrong_match:
                continue

            wrong = wrong_match.group(1).strip()
            pattern = wrong

            # Determine which agent to patch
            # If the correction mentions an agent, patch that agent
            # Otherwise, patch all key agents
            agent_to_patch = "hermes"  # Default: Hermes is the coordinator
            for agent_name in ["hermes", "hephaestus", "athena", "minos", "thoth", "daedalus"]:
                if agent_name in entry.lower():
                    agent_to_patch = agent_name
                    break

            # Generate rule name
            import hashlib
            rule_hash = hashlib.md5(pattern.encode()).hexdigest()[:8]
            rule_name = f"rule_{rule_hash}"

            # Add the rule
            result = self._add_rule({
                "agent_name": agent_to_patch,
                "rule_name": rule_name,
                "pattern": pattern,
                "description": f"Auto-generated from correction: never {wrong}",
            })

            if "PATCHED" in result.get("message", ""):
                rules_added += 1
                results.append(f"  ✅ {agent_to_patch}.py: blocks '{pattern}'")
            elif "already exists" in result.get("message", ""):
                results.append(f"  ⏭️ {agent_to_patch}.py: rule already exists for '{pattern}'")
            else:
                results.append(f"  ❌ {agent_to_patch}.py: {result.get('message', 'unknown error')}")

        return {
            "agent": self.name,
            "action": "learn",
            "rules_added": rules_added,
            "message": (
                f"🛠️ DAEDALUS LEARNED — {rules_added} rule(s) added to agent scripts.\n\n"
                + "\n".join(results)
                + f"\n\nThese rules are now permanently in the agent scripts. "
                f"They will block the AI from making the same mistakes."
            ),
            "next_step": None,
        }

    # ── List available agents ──
    def _list_agents(self) -> str:
        """List all agent scripts that can be patched."""
        agents = []
        for f in sorted(self.AGENTS_DIR.glob("*.py")):
            if f.name not in ("base.py", "__init__.py", "__pycache__"):
                agents.append(f.stem)
        return ", ".join(agents)

    # ── Handle question ──
    def _handle_question(self, data: dict) -> dict:
        question = data.get("question", "")
        return {
            "agent": self.name,
            "action": "answer_question",
            "message": (
                f"I'm Daedalus (Meta Engineering). I fix agents by writing "
                f"correction rules into their Python scripts.\n\n"
                f"Your question: {question}\n\n"
                f"What I can do:\n"
                f"  - Add a rule to an agent: tell me 'add rule to hermes blocking localStorage'\n"
                f"  - Learn from corrections: tell me 'learn from corrections'\n"
                f"  - List agents: tell me 'list agents'\n\n"
                f"Agents I can patch: {self._list_agents()}"
            ),
            "next_step": None,
        }


def run(message: str, context: dict = None) -> dict:
    """Called when developer talks to Daedalus."""
    daedalus = Daedalus()
    return daedalus.run(message, context)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Daedalus Agent — Meta Engineering Director")
        print("Usage: python daedalus.py <message>")
        print()
        print("Examples:")
        print("  python daedalus.py 'add rule to hermes blocking localStorage'")
        print("  python daedalus.py 'learn from corrections'")
        print("  python daedalus.py 'list agents'")
        sys.exit(1)

    message = " ".join(sys.argv[1:])
    result = run(message)
    print(result.get("message", json.dumps(result, indent=2)))
