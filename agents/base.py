#!/usr/bin/env python3
"""
WebForge Agent Framework — base Agent class

PRINCIPLE: The script is the body. The AI is the brain. The body controls the brain.

Each agent is a Python class that:
  1. Receives a message from the developer or another agent
  2. Does deterministic work IN CODE (create task, route, notify)
  3. Calls the AI for reasoning ONLY when needed (formulates a specific prompt)
  4. Takes the AI's response and decides what to do with it
  5. REFUSES if the AI tries to go outside the agent's role

The skill .md file describes personality/style (for the AI prompt).
The .py file IS the agent — it enforces behavior.

The AI never decides what to do. The script decides. The AI only reasons
when the script asks it to. If the AI suggests something outside scope,
the script ignores it and does what it's supposed to do.
"""

import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime, timezone

# Set up paths
WEBFORGE_HOME = Path.home() / "webforge"
MCP_DIR = WEBFORGE_HOME / "mcp"
sys.path.insert(0, str(MCP_DIR))


class Agent:
    """
    Base class for all WebForge agents.

    The agent IS the script. The AI is just the reasoning engine inside it.
    """

    # Identity
    name = "Base Agent"
    department = "Unknown"
    skill_file = None  # path to .md for personality/style

    # What this agent CAN do (code-enforced)
    # If an action is not in this list, the agent CANNOT do it
    allowed_actions = []

    # What this agent CANNOT do (code-enforced)
    # If the AI suggests any of these, the script REFUSES
    forbidden_actions = []

    # Who this agent reports to
    reports_to = None

    # Who this agent can route to
    can_route_to = []

    # ── Per-agent correction rules ──
    # Daedalus adds rules here when the developer corrects this agent.
    # Each rule is a Python function that checks the AI's response.
    # If the check fails, the response is rejected.
    #
    # Format:
    #   correction_rules = [
    #       ("rule_name", lambda message: "localStorage" not in message.lower(),
    #        "Hermes must never suggest using localStorage"),
    #   ]
    correction_rules = []

    def _check_correction_rules(self, message: str) -> tuple:
        """
        Check the AI's response against all per-agent correction rules.
        Returns (passed: bool, reason: str).
        If any rule fails, the response is REJECTED.
        """
        for rule_name, check_func, description in self.correction_rules:
            try:
                if not check_func(message):
                    return (False, f"Rule '{rule_name}' violated: {description}")
            except Exception as e:
                # If the check function errors, fail safe (reject)
                return (False, f"Rule '{rule_name}' errored: {e}")
        return (True, "All rules passed")

    def __init__(self):
        """Initialize the agent."""
        self.project_root = self._get_project_root()

    def _get_project_root(self) -> Path:
        """Get the current project root from env or cwd."""
        project = os.environ.get("WEBFORGE_PROJECT")
        if project:
            return Path(project).expanduser().resolve()
        return Path.cwd().resolve()

    def _set_project_env(self):
        """Set WEBFORGE_PROJECT so MCPs work."""
        os.environ["WEBFORGE_PROJECT"] = str(self.project_root)

    # ── The main entry point ──
    def run(self, message: str, context: dict = None) -> dict:
        """
        Called when the developer or another agent talks to this agent.

        This is THE method that controls everything:
        1. Parse the message
        2. Determine what action is needed
        3. Check if this agent is ALLOWED to do it
        4. Execute the action IN CODE
        5. If AI reasoning is needed, formulate a specific prompt
        6. Return the result

        The AI never controls this flow. The script does.
        """
        self._set_project_env()
        context = context or {}

        # 1. Parse the message
        parsed = self.parse_message(message, context)

        # 2. Check if the action is allowed
        if not self.is_allowed(parsed["action"]):
            return self._refuse(
                f"I am {self.name}. I cannot do '{parsed['action']}'. "
                f"That's not my job. {self._suggest_who(parsed['action'])}"
            )

        # 3. Check if the AI is trying to do something forbidden
        if self.is_forbidden(parsed["action"]):
            return self._refuse(
                f"I am {self.name}. I am NOT allowed to '{parsed['action']}'. "
                f"{self._suggest_who(parsed['action'])}"
            )

        # 4. Execute the action (this is in code, not AI)
        result = self.execute(parsed["action"], parsed["data"], context)

        # 5. If the result contains AI suggestions outside scope, strip them
        result = self._sanitize_result(result)

        # 6. Check per-agent correction rules (Daedalus adds these)
        # If any rule fails, the response is REJECTED
        if "message" in result:
            passed, reason = self._check_correction_rules(result["message"])
            if not passed:
                return self._refuse(
                    f"Correction rule violated in {self.name}: {reason}. "
                    f"The AI tried to do something a previous correction forbade."
                )

        # 7. Log to session
        self._log(f"{self.name} executed: {parsed['action']}")

        return result

    # ── Parse the developer's message ──
    def parse_message(self, message: str, context: dict) -> dict:
        """
        Parse the message to determine what action is needed.
        This is code — the AI doesn't decide what action to take.
        The script parses keywords and patterns.
        """
        message_lower = message.lower().strip()

        # Default action
        action = "respond"
        data = {"message": message, "raw": message}

        # Detect Daedalus-specific actions FIRST (before generic "add" catches)
        if any(word in message_lower for word in ["add rule", "correction rule", "blocking", "patch agent", "fix agent", "learn from corrections"]):
            action = "add_correction_rule"
            # Parse: "add rule to hermes blocking localStorage"
            # Extract agent name and pattern
            import re as _re
            agent_match = _re.search(r'(?:to|into)\s+(\w+)\s+(?:blocking|block|preventing|for)', message_lower)
            pattern_match = _re.search(r'blocking\s+(.+?)(?:$|\.)', message_lower)
            if agent_match:
                data["agent_name"] = agent_match.group(1)
            if pattern_match:
                data["pattern"] = pattern_match.group(1).strip()
            if "learn" in message_lower:
                action = "learn"

        # Detect bug reports
        elif any(word in message_lower for word in ["bug", "broken", "not working", "fix", "error", "crash", "nan", "undefined"]):
            action = "create_bugfix_task"
            data["title"] = message
            data["type"] = "bugfix"

        # Detect feature requests (but not "add rule" which is caught above)
        elif any(word in message_lower for word in ["add", "create", "implement", "build", "new feature", "i want"]):
            action = "create_feature_task"
            data["title"] = message
            data["type"] = "feature"

        # Detect research requests
        elif any(word in message_lower for word in ["research", "investigate", "find out", "what's the best", "how does", "standards"]):
            action = "research"
            data["topic"] = message

        # Detect documentation requests
        elif any(word in message_lower for word in ["document", "readme", "changelog", "docs", "api docs"]):
            action = "generate_docs"
            data["doc_type"] = message

        # Detect questions
        elif any(word in message_lower for word in ["what", "why", "how", "should", "which", "can you"]):
            action = "answer_question"
            data["question"] = message

        # Detect status checks
        elif any(word in message_lower for word in ["status", "standup", "progress", "what's happening", "where are we"]):
            action = "run_standup"

        # Detect code requests (most agents should refuse this)
        elif any(word in message_lower for word in ["code", "write", "function", "component", "refactor", "deploy"]):
            action = "write_code"
            data["task"] = message

        return {"action": action, "data": data}

    # ── Check if action is allowed ──
    def is_allowed(self, action: str) -> bool:
        """Check if this agent is allowed to do this action."""
        if not self.allowed_actions:
            return True  # Base agent allows everything
        return action in self.allowed_actions

    # ── Check if action is forbidden ──
    def is_forbidden(self, action: str) -> bool:
        """Check if this action is explicitly forbidden."""
        return action in self.forbidden_actions

    # ── Execute the action (override in subclasses) ──
    def execute(self, action: str, data: dict, context: dict) -> dict:
        """
        Execute the action. This is overridden by each agent subclass.
        The base class just returns a message.
        """
        return {
            "agent": self.name,
            "action": action,
            "message": f"{self.name} received: {data.get('message', '')}",
            "next_step": None,
        }

    # ── Refuse an action ──
    def _refuse(self, reason: str) -> dict:
        """The script refuses to do something. The AI doesn't get a say."""
        return {
            "agent": self.name,
            "action": "refused",
            "message": f"🚫 REFUSED: {reason}",
            "next_step": None,
            "refused": True,
        }

    # ── Sanitize AI output ──
    def _sanitize_result(self, result: dict) -> dict:
        """
        If the AI's response contains suggestions outside this agent's scope,
        strip them. The script only keeps what's relevant.
        """
        if "message" not in result:
            return result

        message = result["message"]

        # Check for forbidden patterns in the AI's response
        for forbidden in self.forbidden_actions:
            forbidden_keywords = {
                "write_code": ["i can code", "i can write", "i can fix", "let me write", "i'll code", "i can implement"],
                "create_bugfix_task": ["i can fix", "let me fix", "i'll fix"],
                "research": ["i can research", "let me research"],
                "generate_docs": ["i can document", "let me write docs"],
                "run_standup": [],
                "answer_question": [],
            }.get(forbidden, [])

            for keyword in forbidden_keywords:
                if keyword.lower() in message.lower():
                    # Strip the suggestion — the script refuses
                    message = re.sub(
                        rf'(?i){re.escape(keyword)}[^.]*\.?',
                        f"(I am {self.name} — that's not my job.)",
                        message
                    )

        result["message"] = message
        return result

    # ── Suggest who should do this action ──
    def _suggest_who(self, action: str) -> str:
        """When refusing, suggest who SHOULD do this action."""
        suggestions = {
            "write_code": "Ask @Hephaestus (Build Director).",
            "create_bugfix_task": "Ask @Hephaestus to create a bugfix task.",
            "create_feature_task": "Ask @Hephaestus to create a feature task.",
            "research": "Ask @Athena (Intelligence Director).",
            "generate_docs": "Ask @Thoth (Documentation Director).",
            "run_standup": "Ask @Hermes (COO).",
            "answer_question": "Ask @Hermes to route your question.",
            "run_quality_check": "Ask @Minos (Quality Director).",
            "review_code": "Ask @Minos to review.",
            "learn": "Ask @Daedalus (Meta Engineering).",
        }
        return suggestions.get(action, "Use /agents to see who can help.")

    # ── Log to session ──
    def _log(self, message: str):
        """Log this agent's action to the session log."""
        try:
            from memory import session_append
            session_append(message, agent=self.name, kind="note")
        except:
            pass  # Don't fail if memory is unavailable

    # ── Load skill file for AI context ──
    def _load_skill(self) -> str:
        """Load the skill .md file for AI personality context."""
        if not self.skill_file:
            return ""
        skill_path = WEBFORGE_HOME / "skills" / self.skill_file
        if skill_path.exists():
            return skill_path.read_text(encoding="utf-8")
        return ""

    # ── Route to another agent ──
    def _route_to(self, agent_name: str, message: str, task_id: str = "") -> dict:
        """
        Route work to another agent. This is CODE — not AI.
        The script calls the other agent's script.
        """
        if agent_name not in self.can_route_to:
            return self._refuse(
                f"I am {self.name}. I cannot route to @{agent_name}. "
                f"I can only route to: {', '.join(self.can_route_to)}"
            )

        # Log the routing
        self._log(f"{self.name} routing to @{agent_name}: {message}")

        # Send notification
        try:
            from notify import notify
            notify(agent_name, "TASK_ROUTED", message, task_id, from_agent=self.name)
        except:
            pass

        return {
            "agent": self.name,
            "action": "route",
            "routed_to": agent_name,
            "message": f"📤 Routed to @{agent_name}: {message}",
            "next_step": f"Talk to @{agent_name} or use /build to start.",
        }

    # ── Create a task (code, not AI) ──
    def _create_task(self, title: str, task_type: str = "feature",
                     area: str = "", effort: str = "M") -> dict:
        """Create a task in the Kanban board. This is CODE."""
        try:
            from task import task_create
            result = task_create(title, task_type, area, effort)
            if result.ok:
                return result.data
            return {"error": result.error}
        except Exception as e:
            return {"error": str(e)}

    # ── Generate AI prompt ──
    def _formulate_prompt(self, task: str, context: dict = None) -> str:
        """
        Formulate a specific prompt for the AI.
        The AI gets a CONSTRAINED question — not open-ended.

        Example: "Analyze this message and tell me if it's a bug or feature.
        Reply with one word: 'bug' or 'feature'."
        """
        skill = self._load_skill()
        return (
            f"You are {self.name}. {self.department} department.\n\n"
            f"Your role (from skill file):\n{skill[:500]}\n\n"
            f"Task: {task}\n"
            f"Context: {json.dumps(context or {})}\n\n"
            f"Respond concisely. Stay in character. Do NOT suggest actions "
            f"outside your role."
        )
