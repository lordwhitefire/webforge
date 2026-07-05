#!/usr/bin/env python3
"""
WebForge Context MCP — focused per-task context for AI calls.

Solves context rot (GSD's central insight): as the context window fills,
quality degrades silently. The fix: every AI call gets a purpose-built
prompt assembled from task-relevant sources, not from the agent's full
skill file.

Each ContextBuilder.build() call assembles ~1500 tokens of focused context:
  - Project summary (from PROJECT.md, ~300 tokens)
  - Task spec (from SQLite, ~200 tokens)
  - Relevant files (paths + summaries, ~500 tokens)
  - Decisions log (task-scoped, ~200 tokens)
  - Agent constraints (compact: allowed/forbidden actions, ~100 tokens)
  - Call-specific context (per call_type, ~200 tokens)

The agent's personality (skill .md) is loaded ONCE at orchestrator level
and used to format the response, not inlined into every AI call.

Output handling: ask_ai_focused() writes the full AI response to the run
directory, returns only the parsed JSON summary to the agent. This keeps
the orchestrator lean.
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))
from common import write_log, success, fail, utc_now, McpResult, get_project_root
import state


# ── Token budget (approximate: 1 token ≈ 4 chars) ──

TOKEN_BUDGETS = {
    "project_summary": 1200,   # ~300 tokens
    "task_spec":       800,    # ~200 tokens
    "relevant_files":  2000,   # ~500 tokens
    "decisions":       800,    # ~200 tokens
    "agent_constraints": 400,  # ~100 tokens
    "call_specific":   800,    # ~200 tokens
}

# Total: ~6800 chars ≈ ~1700 tokens of focused context


# ── Call types — each has a specific prompt template ──

CALL_TYPES = {
    "code":       "Write or fix code",
    "review":     "Review code that was written",
    "research":   "Research a topic / investigate options",
    "plan":       "Plan how to implement a task",
    "test":       "Write tests",
    "docs":       "Write documentation",
    "answer":     "Answer a question",
    "debug":      "Debug a problem",
    "refactor":   "Refactor existing code",
}


# ── Source functions — each returns a string, scoped to the task ──

def _truncate(text: str, max_chars: int) -> str:
    """Truncate text to max_chars, adding '...' if truncated."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars - 3] + "..."


def project_summary() -> str:
    """
    Load project summary from .webforge/memory/PROJECT.md.
    Returns empty string if not yet created.
    """
    project_md = get_project_root() / ".webforge" / "memory" / "PROJECT.md"
    if not project_md.exists():
        return "(PROJECT.md not yet created. Run /init-project to create it.)"
    content = project_md.read_text(encoding="utf-8")
    # Strip the first H1 header (we add our own)
    lines = content.split("\n")
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    return _truncate("\n".join(lines).strip(), TOKEN_BUDGETS["project_summary"])


def state_summary() -> str:
    """Load current state from .webforge/memory/STATE.md."""
    state_md = get_project_root() / ".webforge" / "memory" / "STATE.md"
    if not state_md.exists():
        return "(STATE.md not yet created.)"
    return _truncate(state_md.read_text(encoding="utf-8").strip(),
                     TOKEN_BUDGETS["project_summary"])


def task_spec(task_id: str) -> str:
    """Load task details from SQLite."""
    if not task_id:
        return "(no task_id — general call)"
    task = state.query_one("SELECT * FROM tasks WHERE id=?", (task_id,))
    if task is None:
        return f"(task {task_id} not found)"
    spec = (
        f"Task ID: {task['id']}\n"
        f"Title: {task['title']}\n"
        f"Type: {task['type']}\n"
        f"Effort: {task['effort']}\n"
        f"Area: {task.get('area', 'n/a')}\n"
        f"Status: {task['status']}\n"
        f"Owner: {task.get('owner', 'unassigned')}\n"
        f"Description: {task.get('description', '(none)')}\n"
    )
    return _truncate(spec, TOKEN_BUDGETS["task_spec"])


def relevant_files(task_id: str, agent_role: str = "build") -> str:
    """
    List files relevant to this task.

    For now, this is a stub — returns files mentioned in the task description
    or recently modified. In a full implementation, this would:
      - Parse @file references from the task description
      - Look at git diff to see what's been touched
      - Ask the agent to declare what files it needs

    Files are listed by path + one-line summary, NOT inlined.
    OpenCode can read them via tools when it needs the full content.
    """
    if not task_id:
        return "(no task_id)"

    task = state.query_one("SELECT * FROM tasks WHERE id=?", (task_id,))
    if task is None:
        return "(task not found)"

    description = task.get("description", "") or ""
    title = task.get("title", "") or ""
    text = f"{title} {description}"

    # Extract @file references (e.g. "@/src/lib/auth.ts" or "src/lib/auth.ts")
    import re
    file_refs = set()
    # Match @path/to/file.ext or path/to/file.ext (with extension)
    for match in re.finditer(r'(?:@)?([\w./\-]+\.(?:ts|tsx|js|jsx|py|md|json|yml|yaml|sh))', text):
        file_refs.add(match.group(1))

    if not file_refs:
        return "(no specific files mentioned in task — agent should explore)"

    lines = []
    for f in sorted(file_refs)[:10]:  # max 10 files
        full_path = get_project_root() / f
        if full_path.exists():
            size = full_path.stat().st_size
            lines.append(f"  - {f} ({size} bytes)")
        else:
            lines.append(f"  - {f} (not found)")

    return "\n".join(lines) if lines else "(no specific files mentioned)"


def decisions_log(task_id: str = None, area: str = None, limit: int = 5) -> str:
    """
    Load recent decisions from SQLite.
    Filtered by task_id if provided, otherwise most recent.
    """
    sql = "SELECT * FROM decisions"
    params = []
    if task_id:
        sql += " WHERE task_id=?"
        params.append(task_id)
    sql += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    rows = state.query(sql, tuple(params))
    if not rows:
        return "(no prior decisions)"

    lines = []
    for r in rows:
        lines.append(f"  - [{r['timestamp'][:10]}] {r['agent']}: {r['decision']}")
        if r.get("rationale"):
            lines.append(f"    rationale: {r['rationale']}")
    return "\n".join(lines)


def agent_constraints(agent_name: str) -> str:
    """
    Load compact agent constraints (allowed/forbidden actions + correction rules).
    NOT the full skill file — that's too big.

    Looks for either:
      - A class subclassing Agent with allowed_actions/forbidden_actions, OR
      - A module-level CONSTRAINTS dict with keys: allowed, forbidden, role
    """
    try:
        sys.path.insert(0, str(Path.home() / "webforge" / "agents"))
        mod_name = agent_name.lower().replace("-", "_")
        mod = __import__(mod_name)

        # Option 1: module-level CONSTRAINTS dict (used by standalone agent scripts)
        if hasattr(mod, "CONSTRAINTS") and isinstance(mod.CONSTRAINTS, dict):
            c = mod.CONSTRAINTS
            lines = []
            if c.get("allowed"):
                lines.append(f"Allowed: {', '.join(c['allowed'])}")
            if c.get("forbidden"):
                lines.append(f"Forbidden: {', '.join(c['forbidden'])}")
            if c.get("role"):
                lines.append(f"Role: {c['role']}")
            return "\n".join(lines) if lines else "(no specific constraints)"

        # Option 2: Agent subclass (used by class-based agents)
        for attr in dir(mod):
            obj = getattr(mod, attr)
            if (isinstance(obj, type) and hasattr(obj, "allowed_actions")
                    and hasattr(obj, "name")):
                if obj.name.lower() == agent_name.lower():
                    lines = []
                    if obj.allowed_actions:
                        lines.append(f"Allowed: {', '.join(obj.allowed_actions)}")
                    if obj.forbidden_actions:
                        lines.append(f"Forbidden: {', '.join(obj.forbidden_actions)}")
                    if obj.correction_rules:
                        lines.append(f"Correction rules: {len(obj.correction_rules)} active")
                    return "\n".join(lines) if lines else "(no specific constraints)"
    except Exception:
        pass

    return f"(constraints for {agent_name} not loadable)"


# ── Call-specific context ──

CALL_TEMPLATES = {
    "code": """## What to do
1. Read the files mentioned above (use your file-reading tools).
2. Identify the minimal change needed.
3. Write the code.
4. Run any relevant tests to verify.
5. Report: what was wrong, what you changed, why it works.

## Coding standards
- Make the smallest change that fixes the problem.
- Don't refactor unrelated code.
- Follow existing conventions in the file.
- If you're unsure about a design decision, say so — don't guess.
""",
    "review": """## What to do
1. Read the code that was written/changed.
2. Check for: correctness, security, performance, readability, test coverage.
3. Do NOT write code yourself — only review.
4. Report: issues found (severity: blocker/major/minor/nit), suggestions.

## Review checklist
- Does the code do what the task asked?
- Are there edge cases not handled?
- Are there security issues (injection, auth, secrets)?
- Is the code readable? Naming, structure, comments?
- Are there tests? Do they cover the change?
""",
    "research": """## What to do
1. Investigate the topic below.
2. Look at the codebase for existing patterns.
3. If needed, search the web for current best practices.
4. Report: findings, options (with pros/cons), recommendation.

## Research guidelines
- Cite specific files/lines in the codebase.
- Cite URLs for web sources.
- Don't just summarize — give a recommendation with reasoning.
""",
    "plan": """## What to do
1. Read the task description and relevant files.
2. Break the task into ordered steps.
3. For each step: what to do, which file, estimated effort.
4. Identify risks and dependencies.
5. Report: step-by-step plan, risks, total estimated effort.

## Planning guidelines
- Each step should be small enough to verify independently.
- Call out anything that needs a decision from the developer.
- If the task is too big, propose splitting it.
""",
    "test": """## What to do
1. Read the code that needs testing.
2. Write tests covering: happy path, edge cases, error cases.
3. Run the tests to confirm they pass.
4. Report: test files created, what they cover, pass/fail status.
""",
    "docs": """## What to do
1. Read the code/feature being documented.
2. Write clear, concise documentation.
3. Include: what it does, how to use it, examples, gotchas.
4. Report: doc files created/updated, summary of content.
""",
    "answer": """## What to do
1. Answer the question below.
2. Be concise but complete.
3. Cite sources (files, URLs) where relevant.
4. If you don't know, say so — don't hallucinate.
""",
    "debug": """## What to do
1. Read the error message and the relevant code.
2. Identify the root cause (not just the symptom).
3. Propose a fix (don't apply it yet — just propose).
4. Report: root cause, proposed fix, files to change, risk assessment.
""",
    "refactor": """## What to do
1. Read the existing code.
2. Identify what can be improved (without changing behavior).
3. Make the changes incrementally.
4. Run tests after each change to verify no regressions.
5. Report: what was refactored, why, test status.
""",
}


def call_specific_context(call_type: str) -> str:
    """Get the call-type-specific instructions."""
    return CALL_TEMPLATES.get(call_type, CALL_TEMPLATES["answer"])


# ── The builder ──

class ContextBuilder:
    """
    Assembles a focused prompt for an AI call.

    Usage:
        cb = ContextBuilder()
        prompt = cb.build(
            agent_name="Hephaestus",
            task_id="task-001",
            call_type="code",
            instruction="Fix the login bug",
        )
        # prompt is now a focused ~1700-token prompt
        # Pass it to ask_opencode(prompt)
    """

    def build(self, agent_name: str, task_id: str, call_type: str,
              instruction: str, response_format: str = "") -> str:
        """
        Build a focused prompt for an AI call.

        Args:
            agent_name: Which agent is calling (e.g. "Hephaestus")
            task_id: Which task this is for (e.g. "task-001")
            call_type: One of CALL_TYPES (code, review, research, plan, etc.)
            instruction: The specific instruction for this call
            response_format: Optional JSON format description

        Returns:
            A focused prompt string (~1700 tokens)
        """
        sections = []

        # Header — minimal, just identity
        sections.append(f"# {agent_name} — {call_type} call\n")
        sections.append(f"You are {agent_name} from the WebForge {call_type} pipeline.")
        sections.append("Stay in character. Don't suggest actions outside your role.\n")

        # Project context
        proj = project_summary()
        if proj:
            sections.append("## Project")
        sections.append(proj)
        sections.append("")

        # Task spec
        sections.append("## Task")
        sections.append(task_spec(task_id))
        sections.append("")

        # Relevant files
        sections.append("## Relevant files")
        sections.append(relevant_files(task_id, agent_name))
        sections.append("(Use your file-reading tools to read these. Don't inline them.)\n")

        # Decisions
        sections.append("## Prior decisions")
        sections.append(decisions_log(task_id=task_id))
        sections.append("")

        # Agent constraints
        sections.append("## Your constraints")
        sections.append(agent_constraints(agent_name))
        sections.append("")

        # Call-specific instructions
        sections.append(call_specific_context(call_type))

        # The actual instruction
        sections.append(f"## Instruction\n{instruction}\n")

        # Response format
        if response_format:
            sections.append(f"## Response format\n{response_format}\n")
        else:
            sections.append(
                "## Response format\n"
                "Respond with valid JSON only. No markdown, no code fences.\n"
                "Include at minimum: {\"summary\": \"...\", \"status\": \"ok|error\"}\n"
            )

        return "\n".join(sections)


# ── High-level: build + call OpenCode + save output ──

def ask_ai_focused(agent_name: str, task_id: str, call_type: str,
                   instruction: str, response_format: str = "",
                   run_id: str = None, timeout: int = 120) -> dict:
    """
    Build a focused prompt, call OpenCode, save full output to run dir,
    return only the parsed JSON summary.

    This is the function agents should call instead of base.ask_ai().
    It:
      1. Builds a focused prompt via ContextBuilder
      2. Calls OpenCode via ai_client.ask_opencode
      3. Writes the full response to .webforge/runs/<run_id>/output.md
      4. Parses the JSON response
      5. Returns only the parsed dict (keeps orchestrator lean)

    Args:
        agent_name: Which agent is calling
        task_id: Which task
        call_type: One of CALL_TYPES
        instruction: The specific instruction
        response_format: Optional JSON format hint
        run_id: Optional run ID (for saving output to run dir)
        timeout: OpenCode timeout in seconds

    Returns:
        dict with: status, response (parsed JSON), raw (full text), prompt
    """
    cb = ContextBuilder()
    prompt = cb.build(agent_name, task_id, call_type, instruction, response_format)

    # Call OpenCode
    try:
        sys.path.insert(0, str(Path.home() / "webforge" / "agents"))
        from ai_client import ask_opencode
        result = ask_opencode(prompt, timeout=timeout)
    except Exception as e:
        return {
            "status": "error",
            "error": f"OpenCode call failed: {e}",
            "prompt": prompt,
        }

    if result.get("status") != "ok":
        return {
            "status": "error",
            "error": result.get("error", "OpenCode call failed"),
            "prompt": prompt,
        }

    response_text = result["response"]

    # Save full output to run dir
    if run_id:
        try:
            from runs import run_dir
            output_path = run_dir(run_id) / "output.md"
            output_path.write_text(
                f"# AI call: {agent_name} / {call_type} / {task_id}\n\n"
                f"## Prompt\n```\n{prompt}\n```\n\n"
                f"## Response\n```\n{response_text}\n```\n",
                encoding="utf-8"
            )
        except Exception:
            pass

    # Parse JSON response
    try:
        parsed = json.loads(response_text)
    except (json.JSONDecodeError, TypeError):
        # Wrap non-JSON response
        parsed = {
            "status": "ok",
            "summary": response_text[:500],
            "raw_response": True,
        }

    write_log("Context", agent_name, "ask_ai_focused",
              {"task_id": task_id, "call_type": call_type,
               "prompt_chars": len(prompt), "response_chars": len(response_text)})

    return {
        "status": "ok",
        "response": parsed,
        "raw": response_text,
        "prompt": prompt,
    }


# ── Markdown memory initialization ──

def init_project_memory(name: str = "", description: str = "",
                        tech_stack: list = None, conventions: list = None) -> McpResult:
    """
    Create .webforge/memory/PROJECT.md with project metadata.
    Called once when a project is set up.
    """
    mem_dir = get_project_root() / ".webforge" / "memory"
    mem_dir.mkdir(parents=True, exist_ok=True)

    project_md = mem_dir / "PROJECT.md"
    if project_md.exists():
        return fail(f"PROJECT.md already exists at {project_md}")

    content = f"""# {name or get_project_root().name}

## Description
{description or "(add description here)"}

## Tech stack
"""
    for tech in (tech_stack or []):
        content += f"- {tech}\n"
    content += "\n## Conventions\n"
    for conv in (conventions or []):
        content += f"- {conv}\n"
    content += "\n## Constraints\n- (add any project constraints here)\n"

    project_md.write_text(content, encoding="utf-8")

    # Also create STATE.md
    state_md = mem_dir / "STATE.md"
    state_md.write_text(f"""# Current State

Last updated: {utc_now()}

## In flight
- (nothing yet)

## Blocked
- (nothing)

## Recent decisions
- (none yet)
""", encoding="utf-8")

    return success({"project_md": str(project_md), "state_md": str(state_md)})


def update_state(in_flight: list = None, blocked: list = None,
                 recent_decisions: list = None) -> McpResult:
    """Update STATE.md with current project state."""
    state_md = get_project_root() / ".webforge" / "memory" / "STATE.md"

    content = f"""# Current State

Last updated: {utc_now()}

## In flight
"""
    for item in (in_flight or []):
        content += f"- {item}\n"
    if not in_flight:
        content += "- (nothing)\n"

    content += "\n## Blocked\n"
    for item in (blocked or []):
        content += f"- {item}\n"
    if not blocked:
        content += "- (nothing)\n"

    content += "\n## Recent decisions\n"
    for item in (recent_decisions or []):
        content += f"- {item}\n"
    if not recent_decisions:
        content += "- (none yet)\n"

    state_md.write_text(content, encoding="utf-8")
    return success({"updated": str(state_md)})


def record_decision(decision: str, agent: str = "Unknown",
                    rationale: str = "", task_id: str = None) -> McpResult:
    """Record a decision in both SQLite and the decisions/ markdown folder."""
    now = utc_now()

    # SQLite
    state.execute(
        "INSERT INTO decisions (task_id, agent, decision, rationale, timestamp) VALUES (?, ?, ?, ?, ?)",
        (task_id, agent, decision, rationale, now)
    )

    # Markdown (ADR-style)
    dec_dir = get_project_root() / ".webforge" / "memory" / "decisions"
    dec_dir.mkdir(parents=True, exist_ok=True)

    # Find next number
    existing = sorted(dec_dir.glob("*.md"))
    n = len(existing) + 1

    slug = decision.lower()[:50].replace(" ", "-").replace("/", "-")
    slug = "".join(c for c in slug if c.isalnum() or c == "-")

    filename = f"{n:04d}-{slug}.md"
    content = f"""# Decision {n:04d}: {decision}

- **Date**: {now}
- **Agent**: {agent}
- **Task**: {task_id or 'n/a'}

## Decision
{decision}

## Rationale
{rationale or '(not provided)'}

## Consequences
- (to be filled in as we learn)
"""
    (dec_dir / filename).write_text(content, encoding="utf-8")

    return success({"decision_id": n, "file": str(dec_dir / filename)})


# ── CLI ──

def info() -> dict:
    return {
        "id": "m-context",
        "name": "Context MCP",
        "tier": 1,
        "owner": "System",
        "job": "Builds focused per-task prompts for AI calls. Solves context rot by giving each call exactly the context it needs.",
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Context MCP — focused per-task prompts")
        print("Usage: python context.py <command>")
        print()
        print("Commands:")
        print("  init-project <name> <description>         Create PROJECT.md + STATE.md")
        print("  build <agent> <task_id> <call_type> <instruction>")
        print("                                            Build a focused prompt")
        print("  decision <text> [agent] [rationale] [task_id]")
        print("                                            Record a decision")
        print("  show-context <task_id>                    Show context sources for a task")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "info":
        print(json.dumps(info(), indent=2))
    elif cmd == "init-project":
        name = sys.argv[2] if len(sys.argv) > 2 else ""
        desc = sys.argv[3] if len(sys.argv) > 3 else ""
        r = init_project_memory(name, desc)
        print(r.to_dict())
    elif cmd == "build":
        if len(sys.argv) < 6:
            print("Usage: build <agent> <task_id> <call_type> <instruction>")
            sys.exit(1)
        cb = ContextBuilder()
        prompt = cb.build(sys.argv[2], sys.argv[3], sys.argv[4],
                          " ".join(sys.argv[5:]))
        print(prompt)
        print(f"\n--- Prompt size: {len(prompt)} chars (~{len(prompt)//4} tokens) ---")
    elif cmd == "decision":
        if len(sys.argv) < 3:
            print("Usage: decision <text> [agent] [rationale] [task_id]")
            sys.exit(1)
        text = sys.argv[2]
        agent = sys.argv[3] if len(sys.argv) > 3 else "Unknown"
        rationale = sys.argv[4] if len(sys.argv) > 4 else ""
        task_id = sys.argv[5] if len(sys.argv) > 5 else None
        r = record_decision(text, agent, rationale, task_id)
        print(r.to_dict())
    elif cmd == "show-context":
        if len(sys.argv) < 3:
            print("Usage: show-context <task_id>")
            sys.exit(1)
        task_id = sys.argv[2]
        print("=== Project summary ===")
        print(project_summary())
        print("\n=== Task spec ===")
        print(task_spec(task_id))
        print("\n=== Relevant files ===")
        print(relevant_files(task_id))
        print("\n=== Decisions ===")
        print(decisions_log(task_id=task_id))
    else:
        print(f"Unknown command: {cmd}")
