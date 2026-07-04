#!/usr/bin/env python3
"""
WebForge Agent Framework — base Agent class

PRINCIPLE: The script is the body. The AI is the brain. The body controls the brain.

Each agent is a Python class that:
  1. Receives a message from the developer or another agent
  2. Does deterministic work IN CODE (create task, route, notify)
  3. Calls the AI for reasoning ONLY when needed via ask_ai()
  4. Takes the AI's response and decides what to do with it
  5. REFUSES if the AI tries to go outside the agent's role
  6. Saves state so it can resume if the process is killed mid-way

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
import importlib
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
    allowed_actions = []

    # What this agent CANNOT do (code-enforced)
    forbidden_actions = []

    # Who this agent reports to
    reports_to = None

    # Who this agent can route to
    can_route_to = []

    # Per-agent correction rules (Daedalus adds rules here)
    correction_rules = []

    def __init__(self):
        """Initialize the agent. Set up session from env var."""
        self.project_root = self._get_project_root()
        self.session_dir = None
        self.agent_dir = None
        session_id = os.environ.get("WF_SESSION_ID")
        if session_id:
            self.session_dir = Path(f"/tmp/wf-sess-{session_id}")
            self.agent_dir = self.session_dir / self._dir_name()
            self.agent_dir.mkdir(parents=True, exist_ok=True)

    def _dir_name(self) -> str:
        """Return the directory name for this agent (lowercase, no hyphens)."""
        return re.sub(r'[^a-z0-9]', '', self.name.lower())

    def _get_project_root(self) -> Path:
        """Get the current project root from env or cwd."""
        project = os.environ.get("WEBFORGE_PROJECT")
        if project:
            return Path(project).expanduser().resolve()
        return Path.cwd().resolve()

    def _set_project_env(self):
        """Set WEBFORGE_PROJECT so MCPs work."""
        os.environ["WEBFORGE_PROJECT"] = str(self.project_root)

    # ── MAIN ENTRY POINT ──

    def run(self, message: str, context: dict = None) -> dict:
        """
        Called when the developer or another agent talks to this agent.

        This is THE method that controls everything:
        1. Parse the message
        2. Determine what action is needed
        3. Check if this agent is ALLOWED to do it
        4. Execute the action IN CODE
        5. If AI reasoning is needed, call ask_ai() (makes direct API call)
        6. Return the result

        The AI never controls this flow. The script does.
        """
        self._set_project_env()
        context = context or {}
        context["agent_name"] = self.name

        # ── NORMAL FLOW ──
        # (No resume check needed — ask_ai() now makes direct API calls synchronously)
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

        # 6. Check per-agent correction rules
        if "message" in result:
            passed, reason = self._check_correction_rules(result["message"])
            if not passed:
                return self._refuse(
                    f"Correction rule violated in {self.name}: {reason}. "
                    f"The AI tried to do something a previous correction forbade."
                )

        return result

    def parse_message(self, message: str, context: dict) -> dict:
        """
        Parse the message to determine what action is needed.
        This is code — the AI doesn't decide what action to take.
        """
        message_lower = message.lower().strip()

        action = "respond"
        data = {"message": message, "raw": message}

        # Detect correction requests (CEO correcting an agent's behavior)
        if any(word in message_lower for word in ["correct agent", "correct hermes", "correct hephaestus", "correct athena", "correct minos", "correct thoth", "correct daedalus", "correct jr", "correct sr", "stop agent", "agent should not", "agent must not", "tell daedalus to fix"]):
            action = "correct_agent"
            data["message"] = message

        # Detect clone requests
        elif any(word in message_lower for word in ["clone", "clone repo", "clone project", "git clone"]):
            action = "clone_project"
            data["message"] = message

        # Detect Daedalus-specific actions (when talking to Daedalus directly)
        elif any(word in message_lower for word in ["add rule", "correction rule", "blocking", "patch agent", "fix agent", "learn from corrections"]):
            action = "add_correction_rule"
            import re as _re
            agent_match = _re.search(r'(?:to|into)\s+(\w+)\s+(?:blocking|block|preventing|for)', message_lower)
            pattern_match = _re.search(r'blocking\s+(.+?)(?:$|\.)', message_lower)
            if agent_match:
                data["agent_name"] = agent_match.group(1)
            if pattern_match:
                data["pattern"] = pattern_match.group(1).strip()
            if "learn" in message_lower:
                action = "learn"

        elif any(word in message_lower for word in ["bug", "broken", "not working", "fix", "error", "crash", "nan", "undefined"]):
            action = "create_bugfix_task"
            data["title"] = message
            data["type"] = "bugfix"

        elif any(word in message_lower for word in ["add", "create", "implement", "build", "new feature", "i want"]):
            action = "create_feature_task"
            data["title"] = message
            data["type"] = "feature"

        elif any(word in message_lower for word in ["research", "investigate", "find out", "what's the best", "how does", "standards", "survey", "scan", "analyze", "explore"]):
            action = "research"
            data["topic"] = message

        elif any(word in message_lower for word in ["document", "readme", "changelog", "docs", "api docs"]):
            action = "generate_docs"
            data["doc_type"] = message

        elif any(word in message_lower for word in ["what", "why", "how", "should", "which", "can you"]):
            action = "answer_question"
            data["question"] = message

        elif any(word in message_lower for word in ["status", "standup", "progress", "what's happening", "where are we"]):
            action = "run_standup"

        elif any(word in message_lower for word in ["code", "write", "function", "component", "refactor", "deploy"]):
            action = "write_code"
            data["task"] = message

        return {"action": action, "data": data}

    def is_allowed(self, action: str) -> bool:
        """Check if this agent is allowed to do this action."""
        if not self.allowed_actions:
            return True
        return action in self.allowed_actions

    def is_forbidden(self, action: str) -> bool:
        """Check if this action is explicitly forbidden."""
        return action in self.forbidden_actions

    def execute(self, action: str, data: dict, context: dict) -> dict:
        """Override in subclasses. The base class just returns a message."""
        return {
            "agent": self.name,
            "action": action,
            "message": f"{self.name} received: {data.get('message', '')}",
            "next_step": None,
        }

    # ── AI COMMUNICATION (ask_ai) ──

    def ask_ai(self, instruction: str, response_format: str = "") -> dict:
        """
        Call the AI directly via HTTP API (DeepSeek or Z.ai).

        SYNCHRONOUS — blocks until the AI responds. No pipeline handoff,
        no file writing, no resume needed.

        The AI is just the brain. The script calls it, gets the answer,
        and continues executing. No handoff.

        Args:
            instruction: What the AI needs to reason about
            response_format: Optional format hint (appended to instruction)

        Returns:
            dict parsed from AI's JSON response (keys: status, action, target, message, etc.)
        """
        from ai_client import call_ai_json

        skill = self._load_skill()

        # Build the system prompt: who the AI is, what its role is
        system_prompt = (
            f"You are {self.name}. {self.department} department.\n\n"
            f"Your role (from skill file):\n{skill[:2000]}\n\n"
            f"Respond with a JSON object containing the fields requested.\n"
            f"Never suggest actions outside your role. Stay in character.\n"
            f"Be concise and direct."
        )

        # Build the user instruction
        user_parts = [instruction]
        if response_format:
            user_parts.append(f"\n\nExpected response format:\n{response_format}")
        user_parts.append(
            "\n\nRespond with valid JSON only. No markdown, no code fences, "
            "no extra explanation outside the JSON."
        )
        user_instruction = "\n".join(user_parts)

        # Call the AI directly (blocking)
        response = call_ai_json(
            system_prompt=system_prompt,
            user_instruction=user_instruction,
            temperature=0.3,
            max_tokens=2000,
        )

        # Log the AI interaction
        self._log(f"ask_ai → {self.name}: {instruction[:100]}...")

        # Check correction rules on the response
        message_text = response.get("message", "")
        passed, reason = self._check_correction_rules(message_text)
        if not passed:
            return {
                "status": "correction_violated",
                "action": "refused",
                "message": f"AI response violated correction rule: {reason}",
            }

        return response

    # ── DIRECT AGENT CALLS ──

    def _call_agent(self, agent_name: str, message: str, context: dict = None) -> dict:
        """
        Call another agent DIRECTLY. Blocks until it returns.

        This is how agents talk to each other without going through the pipeline.
        The caller waits for the callee to finish.
        """
        context = context or {}
        context["caller"] = self.name
        context["agent_name"] = agent_name

        # Save state: waiting for agent
        self._save_state({
            "status": "waiting_for_agent",
            "waiting_for": agent_name,
            "message_sent": message[:200],
        })

        try:
            # Import the agent module dynamically
            file_name = re.sub(r'[-\s]', '_', agent_name).lower()
            class_name = re.sub(r'[-\s]', '', agent_name.title())

            module = importlib.import_module(file_name)
            agent_class = getattr(module, class_name)
            agent = agent_class()

            # Pass session down
            if self.session_dir:
                agent.session_dir = self.session_dir
                agent.agent_dir = self.session_dir / agent._dir_name()
                agent.agent_dir.mkdir(parents=True, exist_ok=True)

            result = agent.run(message, context)
            self._save_state({"status": "got_agent_result", "from": agent_name})
            return result

        except ModuleNotFoundError:
            return {"status": "error", "message": f"Agent module not found: {agent_name}"}
        except AttributeError:
            return {"status": "error", "message": f"Agent class not found in module: {class_name}"}
        except Exception as e:
            return {"status": "error", "message": f"Error calling {agent_name}: {e}"}

    def _report_up(self, result: dict) -> dict:
        """
        Send a result up the chain of command.
        Calls reports_to directly.
        """
        if not self.reports_to:
            return result  # No one to report to (top of chain)

        return self._call_agent(self.reports_to, json.dumps(result))

    # ── STATE MANAGEMENT ──

    def _save_state(self, state: dict):
        """Save this agent's state to the session dir."""
        if not self.agent_dir:
            return
        state["agent"] = self.name
        state["timestamp"] = datetime.now(timezone.utc).isoformat()
        state_path = self.agent_dir / "state.json"
        try:
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except Exception:
            pass

    def _load_state(self) -> dict:
        """Load this agent's state from the session dir."""
        if not self.agent_dir:
            return {}
        state_path = self.agent_dir / "state.json"
        if not state_path.exists():
            return {}
        try:
            with open(state_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _clear_state(self):
        """Clear this agent's state."""
        if not self.agent_dir:
            return
        state_path = self.agent_dir / "state.json"
        try:
            if state_path.exists():
                state_path.unlink()
        except Exception:
            pass

    # ── HELPERS ──

    def _refuse(self, reason: str) -> dict:
        """The script refuses to do something. The AI doesn't get a say."""
        return {
            "agent": self.name,
            "action": "refused",
            "message": reason,
            "next_step": None,
            "refused": True,
        }

    def _sanitize_result(self, result: dict) -> dict:
        """Strip forbidden suggestions from AI output."""
        if "message" not in result:
            return result

        message = result["message"]

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
                    message = re.sub(
                        rf'(?i){re.escape(keyword)}[^.]*\.?',
                        f"(I am {self.name} — that's not my job.)",
                        message
                    )

        result["message"] = message
        return result

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

    def _log(self, message: str):
        """Log this agent's action to the session log."""
        try:
            from memory import session_append
            session_append(message, agent=self.name, kind="note")
        except Exception:
            pass

    def _load_skill(self) -> str:
        """Load the skill .md file for AI personality context."""
        if not self.skill_file:
            return ""
        skill_path = WEBFORGE_HOME / "skills" / self.skill_file
        if skill_path.exists():
            return skill_path.read_text(encoding="utf-8")
        return ""

    def _check_correction_rules(self, message: str) -> tuple:
        """
        Check the AI's response against all per-agent correction rules.
        Returns (passed: bool, reason: str).
        """
        for rule_name, check_func, description in self.correction_rules:
            try:
                if not check_func(message):
                    return (False, f"Rule '{rule_name}' violated: {description}")
            except Exception as e:
                return (False, f"Rule '{rule_name}' errored: {e}")
        return (True, "All rules passed")

    def _formulate_prompt(self, task: str, context: dict = None) -> str:
        """Formulate a constrained prompt for the AI."""
        skill = self._load_skill()
        return (
            f"You are {self.name}. {self.department} department.\n\n"
            f"Your role (from skill file):\n{skill[:500]}\n\n"
            f"Task: {task}\n"
            f"Context: {json.dumps(context or {})}\n\n"
            f"Respond concisely. Stay in character. Do NOT suggest actions "
            f"outside your role."
        )

    def _route_to(self, agent_name: str, message: str, task_id: str = "") -> dict:
        """Route work to another agent. Now uses _call_agent instead."""
        if agent_name not in self.can_route_to:
            return self._refuse(
                f"I am {self.name}. I cannot route to @{agent_name}. "
                f"I can only route to: {', '.join(self.can_route_to)}"
            )
        return self._call_agent(agent_name, message, {"task_id": task_id})

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

    def _handle_ai_response(self, response: dict, context: dict) -> dict:
        """
        Handle a response from ask_ai() after resume.
        Subclasses override this to react to the AI response.
        Default: just return the response as-is.
        """
        return response
