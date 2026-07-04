#!/usr/bin/env python3
"""
Chain Executor — runs the entire chain automatically without stopping.

HOW MY SUB-AGENTS WORK (for reference):
  When I launch a sub-agent, it runs autonomously:
    1. I give it a prompt + tools
    2. It works until done — reads files, writes code, searches
    3. When finished, it returns the result
    4. I do NOT check on it mid-work. It just finishes.

HOW THIS EXECUTOR WORKS:
  Same pattern. Takes a task, executes the ENTIRE chain:
    1. Routes through every level (Hermes → Dept Head → Lead → Senior → Junior)
    2. Does NOT stop at each level — keeps going
    3. When it reaches the executor (Junior/Probe/Odin), it outputs the work prompt
    4. Only stops if CEO decision needed
    5. When work is done, routes results back up automatically

  The AI reads the output and launches a sub-agent for the executor level.
  The sub-agent runs autonomously and reports back.
  Then the executor routes results up the chain automatically.
"""

import os
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import write_log, success, fail, utc_now, McpResult, get_project_root
from memory import session_append


def info() -> dict:
    return {
        "id": "m-executor",
        "name": "Chain Executor",
        "tier": 1,
        "owner": "Hermes",
        "job": "Executes the entire chain of command without stopping. Routes down, does work, routes back up. Only stops for CEO decisions.",
    }


# ── Department chain definitions ──
# Each department has a list of levels. Each level has:
#   agent: who handles it
#   action: what they do
#   can_route_down: whether this level can route to the next
#   is_executor: whether this level does the actual work

DEPT_CHAINS = {
    "intelligence": {
        "levels": [
            {"level": "coordinator", "agent": "Hermes",
             "action": "review and route to department head",
             "can_route_down": True, "is_executor": False},
            {"level": "director", "agent": "Athena",
             "action": "assign to the right team member (Probe for code audit, Odin for research)",
             "can_route_down": True, "is_executor": False},
            {"level": "team_member", "agent": "Probe or Odin",
             "action": "DO THE WORK — audit codebase or research",
             "can_route_down": False, "is_executor": True},
        ],
        "report_up_chain": ["Team Member", "Athena", "Hermes", "CEO"],
    },
    "build": {
        "levels": [
            {"level": "coordinator", "agent": "Hermes",
             "action": "review and route to department head",
             "can_route_down": True, "is_executor": False},
            {"level": "director", "agent": "Hephaestus",
             "action": "determine which team (Aurora frontend, Titan backend, Zephyr database)",
             "can_route_down": True, "is_executor": False},
            {"level": "team_head", "agent": "Aurora/Titan/Zephyr",
             "action": "route to tech lead",
             "can_route_down": True, "is_executor": False},
            {"level": "tech_lead", "agent": "Lead-Faro/Terra/Zen",
             "action": "assign to senior dev",
             "can_route_down": True, "is_executor": False},
            {"level": "senior", "agent": "Senior Dev",
             "action": "review and assign to junior dev",
             "can_route_down": True, "is_executor": False},
            {"level": "junior", "agent": "Junior Dev",
             "action": "WRITE THE CODE — do the actual work",
             "can_route_down": False, "is_executor": True},
        ],
        "report_up_chain": ["Junior", "Senior", "Tech Lead", "Team Head", "Director", "Hermes", "CEO"],
    },
    "quality": {
        "levels": [
            {"level": "coordinator", "agent": "Hermes",
             "action": "review and route to department head",
             "can_route_down": True, "is_executor": False},
            {"level": "director", "agent": "Minos",
             "action": "assign to the right test team (Pixel, Scalpel, Janus, Pulse)",
             "can_route_down": True, "is_executor": False},
            {"level": "team", "agent": "Test Team",
             "action": "RUN TESTS — execute quality checks",
             "can_route_down": False, "is_executor": True},
        ],
        "report_up_chain": ["Test Team", "Minos", "Hermes", "CEO"],
    },
    "documentation": {
        "levels": [
            {"level": "coordinator", "agent": "Hermes",
             "action": "review and route to department head",
             "can_route_down": True, "is_executor": False},
            {"level": "director", "agent": "Thoth",
             "action": "assign to the right doc agent",
             "can_route_down": True, "is_executor": False},
            {"level": "writer", "agent": "Quill/Scroll/Ledger",
             "action": "WRITE DOCS — create the documentation",
             "can_route_down": False, "is_executor": True},
        ],
        "report_up_chain": ["Writer", "Thoth", "Hermes", "CEO"],
    },
}

TASK_TYPE_TO_DEPT = {
    "feature": "build", "bugfix": "build", "refactor": "build",
    "test": "quality", "docs": "documentation",
    "research": "intelligence", "architecture": "intelligence",
    "design": "intelligence", "security": "quality",
}


def load_task(task_id: str) -> dict:
    board_file = get_project_root() / ".webforge" / "tasks" / "board.json"
    if board_file.exists():
        board = json.loads(board_file.read_text())
        for t in board.get("tasks", []):
            if t["id"] == task_id:
                return t
    return None


def execute_chain(task_id: str, ceo_instructions: str = "") -> McpResult:
    """
    Execute the ENTIRE chain for a task without stopping.
    
    1. Load task and determine department
    2. Route down through EVERY level (Hermes → ... → Executor)
    3. At each level, assign the task and notify
    4. When executor level is reached, build the work prompt
    5. Return: chain is ready. Launch sub-agent for executor.
    
    Does NOT stop between levels. Routes through everything.
    Only stops if CEO decision needed.
    """
    task = load_task(task_id)
    if not task:
        return fail(f"Task not found: {task_id}")

    title = task.get("title", "Untitled")
    task_type = task.get("type", "feature")
    dept = TASK_TYPE_TO_DEPT.get(task_type, "build")

    if dept not in DEPT_CHAINS:
        return fail(f"Unknown department: {dept}")

    chain = DEPT_CHAINS[dept]
    levels = chain["levels"]

    # Execute each level in order
    execution_log = []
    current_owner = "System"
    needs_ceo = False
    ceo_question = ""
    executor_prompt = ""

    for i, level in enumerate(levels):
        agent = level["agent"]
        action = level["action"]
        is_executor = level["is_executor"]
        can_route = level["can_route_down"]

        # Route to this level
        if i == 0:
            # First level — task was already assigned to Hermes by auto-dispatch
            current_owner = "Hermes"
            execution_log.append(f"Step {i}: @{agent} — {action} (already in inbox)")
        else:
            # Route down to this level
            try:
                import subprocess
                route_cmd = [
                    "python3", str(Path(__file__).parent / "dispatch.py"),
                    "route-down", task_id, agent, current_owner
                ]
                env = os.environ.copy()
                env["WEBFORGE_PROJECT"] = os.environ.get("WEBFORGE_PROJECT", "")
                result = subprocess.run(route_cmd, capture_output=True, text=True, env=env)
                execution_log.append(f"Step {i}: @{current_owner} → @{agent} — {action}")
                current_owner = agent
            except Exception as e:
                execution_log.append(f"Step {i}: FAILED to route to @{agent}: {e}")
                return fail(f"Chain stopped at step {i}: could not route to @{agent}")

        # Move task to doing if it's the executor
        if is_executor:
            try:
                import subprocess
                move_cmd = [
                    "python3", str(Path(__file__).parent / "task.py"),
                    "move", task_id, "doing"
                ]
                env = os.environ.copy()
                env["WEBFORGE_PROJECT"] = os.environ.get("WEBFORGE_PROJECT", "")
                subprocess.run(move_cmd, capture_output=True, text=True, env=env)
            except Exception:
                pass

        # If this level is the executor, build the work prompt
        if is_executor:
            executor_prompt = build_executor_prompt(task_id, title, task_type, dept, agent, ceo_instructions)

        # If this level cannot route down but is NOT the executor, something is wrong
        if not can_route and not is_executor:
            needs_ceo = True
            ceo_question = f"@{agent} cannot route down and is not an executor. Chain broken at {task_id}."

    # Check if CEO decision needed (architecture/design tasks)
    if task_type in ("architecture", "design"):
        needs_ceo = True
        ceo_question = f"CEO decision needed for {task_id}: {title} — this is an architecture/design task."

    # Log the execution
    session_append(
        f"CHAIN EXECUTED → {task_id}: {title} ({dept}) — {len(levels)} steps",
        agent="Chain Executor", kind="note"
    )
    write_log("Executor", "Chain Executor", "execute",
              {"task_id": task_id, "department": dept, "steps": len(levels)})

    # Build the output
    result = {
        "task_id": task_id,
        "title": title,
        "type": task_type,
        "department": dept,
        "execution_log": execution_log,
        "current_owner": current_owner,
        "executor_level": levels[-1]["agent"] if levels else "unknown",
        "executor_prompt": executor_prompt,
        "report_up_chain": " → ".join(chain["report_up_chain"]),
        "needs_ceo": needs_ceo,
        "ceo_question": ceo_question,
        "chain_complete": not needs_ceo,
    }

    # Build display message
    lines = []
    lines.append("=" * 60)
    lines.append(f"🏃 CHAIN EXECUTED — {task_id}: {title}")
    lines.append("=" * 60)
    lines.append(f"  Department: {dept}")
    lines.append("")
    lines.append("  Execution log:")
    for log in execution_log:
        lines.append(f"    {log}")
    lines.append("")
    lines.append(f"  Current owner: @{current_owner}")
    lines.append(f"  Report up: {result['report_up_chain']}")
    lines.append("")

    if needs_ceo:
        lines.append(f"  ⚠️  STOPPED — CEO decision needed: {ceo_question}")
        lines.append(f"  Use: /answer <id> <your response>")
    else:
        lines.append(f"  ✅ Chain complete. Ready for executor to work.")
        lines.append(f"  I will now launch a sub-agent for @{current_owner}.")

    result["display"] = "\n".join(lines)

    return success(result)


def build_executor_prompt(task_id: str, title: str, task_type: str,
                          dept: str, agent: str, ceo_instructions: str) -> str:
    """Build the prompt that will be given to the sub-agent doing the work."""
    prompt_parts = [f"You are @{agent} in the {dept} department."]

    if dept == "intelligence":
        prompt_parts.append(f"Your task: {title}")
        prompt_parts.append("")
        prompt_parts.append("What to do:")
        prompt_parts.append("1. Audit the codebase thoroughly")
        prompt_parts.append("2. Check every file related to the task")
        prompt_parts.append("3. Report findings with file paths and line numbers")
        prompt_parts.append("4. Do NOT make changes — only report what you find")
        prompt_parts.append("5. If you need clarification, note it in your report")
    elif dept == "build":
        prompt_parts.append(f"Your task: {title}")
        prompt_parts.append("")
        prompt_parts.append("What to do:")
        prompt_parts.append("1. Read the task requirements carefully")
        prompt_parts.append("2. Implement the changes in the codebase")
        prompt_parts.append("3. Test your changes")
        prompt_parts.append("4. Report what you changed and why")
        prompt_parts.append("5. If blocked, say what's blocking you")
    elif dept == "quality":
        prompt_parts.append(f"Your task: {title}")
        prompt_parts.append("")
        prompt_parts.append("What to do:")
        prompt_parts.append("1. Run the relevant tests")
        prompt_parts.append("2. Check for security issues")
        prompt_parts.append("3. Report pass/fail with details")
        prompt_parts.append("4. If something fails, include the error")
    elif dept == "documentation":
        prompt_parts.append(f"Your task: {title}")
        prompt_parts.append("")
        prompt_parts.append("What to do:")
        prompt_parts.append("1. Read the codebase to understand what needs docs")
        prompt_parts.append("2. Write clear, concise documentation")
        prompt_parts.append("3. Report what you wrote and where")

    if ceo_instructions:
        prompt_parts.append("")
        prompt_parts.append("CEO's specific instructions:")
        prompt_parts.append(ceo_instructions)

    prompt_parts.append("")
    prompt_parts.append("When done, report your findings back to me.")
    prompt_parts.append("I will route them up the chain.")

    return "\n".join(prompt_parts)


# ── Sub-agent report handler ──
def report_up(task_id: str, from_agent: str, report: str = "") -> McpResult:
    """
    Called when a sub-agent finishes work.
    Routes the results back up the chain automatically.
    """
    task = load_task(task_id)
    if not task:
        return fail(f"Task not found: {task_id}")

    title = task.get("title", "Untitled")
    dept = TASK_TYPE_TO_DEPT.get(task.get("type", "feature"), "build")
    chain = DEPT_CHAINS.get(dept)
    if not chain:
        return fail(f"Unknown department: {dept}")

    report_up_chain = chain["report_up_chain"]
    route_steps = []

    # Move task to done
    try:
        import subprocess
        done_cmd = [
            "python3", str(Path(__file__).parent / "task.py"),
            "done", task_id, report[:100] if report else "Work completed"
        ]
        env = os.environ.copy()
        env["WEBFORGE_PROJECT"] = os.environ.get("WEBFORGE_PROJECT", "")
        subprocess.run(done_cmd, capture_output=True, text=True, env=env)
        route_steps.append(f"✅ Task {task_id} marked done")
    except Exception as e:
        route_steps.append(f"⚠️  Could not mark done: {e}")

    # Route up each level
    for i in range(len(report_up_chain) - 1):
        from_lvl = report_up_chain[i]
        to_lvl = report_up_chain[i + 1]
        try:
            import subprocess
            up_cmd = [
                "python3", str(Path(__file__).parent / "dispatch.py"),
                "route-up", task_id, from_lvl, to_lvl
            ]
            env = os.environ.copy()
            env["WEBFORGE_PROJECT"] = os.environ.get("WEBFORGE_PROJECT", "")
            subprocess.run(up_cmd, capture_output=True, text=True, env=env)
            route_steps.append(f"  ↑ @{from_lvl} → @{to_lvl}")
        except Exception:
            route_steps.append(f"  ↑ @{from_lvl} → @{to_lvl} (failed)")

    # Log
    session_append(
        f"REPORT UP → {task_id}: results routed up through {len(report_up_chain)} levels",
        agent=from_agent, kind="note"
    )

    # Build display
    lines = []
    lines.append("=" * 60)
    lines.append(f"📤 RESULTS REPORTED — {task_id}: {title}")
    lines.append("=" * 60)
    lines.append("")
    lines.append("  Route up:")
    for step in route_steps:
        lines.append(f"  {step}")
    lines.append("")
    if report:
        lines.append("  Report summary:")
        lines.append(f"  {report[:500]}")
    lines.append("")
    lines.append("  The report has been routed up the chain.")
    lines.append("  CEO, please review when ready.")

    return success({
        "task_id": task_id,
        "route_steps": route_steps,
        "report": report,
        "display": "\n".join(lines),
    })


# ── CLI ──
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Chain Executor — runs the entire chain automatically")
        print()
        print("Commands:")
        print("  run <task-id> [instructions]    Execute the full chain for a task")
        print("  report-up <id> <from> [report]  Route results back up the chain")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "info":
        print(json.dumps(info(), indent=2))
    elif cmd == "run":
        task_id = sys.argv[2] if len(sys.argv) > 2 else ""
        instructions = sys.argv[3] if len(sys.argv) > 3 else ""
        if task_id:
            result = execute_chain(task_id, instructions)
            data = result.data if hasattr(result, 'data') else result
            print(data.get("display", json.dumps(data, indent=2)))
        else:
            print("Usage: run <task-id> [instructions]")
    elif cmd == "report-up":
        task_id = sys.argv[2] if len(sys.argv) > 2 else ""
        from_agent = sys.argv[3] if len(sys.argv) > 3 else ""
        report = sys.argv[4] if len(sys.argv) > 4 else ""
        if task_id and from_agent:
            result = report_up(task_id, from_agent, report)
            data = result.data if hasattr(result, 'data') else result
            print(data.get("display", json.dumps(data, indent=2)))
        else:
            print("Usage: report-up <task-id> <from-agent> [report]")
    else:
        print(f"Unknown command: {cmd}")
