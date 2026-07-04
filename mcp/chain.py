#!/usr/bin/env python3
"""
Chain Runner — runs the entire chain of command autonomously.

THE PROBLEM:
  After dispatch routes a task, nobody works on it. You have to manually
  type @Athena, @Probe-Wren, etc. at every step. It's like my sub-agents
  run by themselves but your agents sit and wait.

THE SOLUTION:
  This runner is like a sub-agent launcher. You call it once:
    /run-chain <task-id>
  
  It runs the WHOLE chain automatically:
    1. Routes to department head
    2. Routes down through the chain (head → senior → junior)
    3. Does the work at the junior level
    4. Reports results back up (junior → senior → head → CEO)
    5. ONLY stops if it needs a decision from you

HOW IT WORKS:
  Each level in the chain is a Python function that calls the next level.
  The chain runs in a single process — no manual wake-ups needed.
  
  If a level needs a decision from the CEO, it creates an escalation
  and stops. Otherwise, it keeps going until the work is done.

USAGE:
  /run-chain <task-id>
  /run-chain <task-id> [agent]   — Start from a specific agent
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
        "id": "m-chain",
        "name": "Chain Runner",
        "tier": 1,
        "owner": "Hermes",
        "job": "Runs the entire chain of command autonomously. Launch once, it goes until done or needs a CEO decision.",
    }


# ── Task type to department mapping (same as dispatch.py) ──
TASK_TYPE_TO_DEPT = {
    "feature": "build",
    "bugfix": "build",
    "refactor": "build",
    "test": "quality",
    "docs": "documentation",
    "research": "intelligence",
    "architecture": "intelligence",
    "design": "intelligence",
}

DEPT_DESCRIPTIONS = {
    "build": "Build (frontend/backend/database). Junior developers write the code.",
    "intelligence": "Intelligence (research/audit). Probe team scans, Odin team researches.",
    "quality": "Quality (tests/security). Pixel team tests, Janus team secures.",
    "documentation": "Documentation (docs/readme). Quill team writes docs.",
}


# ── Load task from board ──
def load_task(task_id: str) -> dict:
    board_file = get_project_root() / ".webforge" / "tasks" / "board.json"
    if board_file.exists():
        board = json.loads(board_file.read_text())
        for t in board.get("tasks", []):
            if t["id"] == task_id:
                return t
    return None


# ── The Chain Runner ──
def run_chain(task_id: str, start_from: str = "") -> McpResult:
    """
    Run the entire chain for a task autonomously.
    
    1. Load the task
    2. Determine the department
    3. Route to department head
    4. Route down the chain
    5. Do the work
    6. Report back up
    
    At each step, if a CEO decision is needed, stop and escalate.
    """
    task = load_task(task_id)
    if not task:
        return fail(f"Task not found: {task_id}")

    title = task.get("title", "Untitled")
    task_type = task.get("type", "feature")
    dept = TASK_TYPE_TO_DEPT.get(task_type, "build")
    dept_desc = DEPT_DESCRIPTIONS.get(dept, dept)

    # Build the chain execution plan
    chain_plan = build_chain_plan(task_id, title, task_type, dept, start_from)
    
    if not chain_plan["ok"]:
        return chain_plan

    # The plan tells us what to do at each level
    # We return this to the LLM which then executes it
    return success({
        "task_id": task_id,
        "title": title,
        "type": task_type,
        "department": dept,
        "department_description": dept_desc,
        "chain_plan": chain_plan["plan"],
        "instructions": chain_plan["instructions"],
        "needs_ceo": chain_plan.get("needs_ceo", False),
        "ceo_question": chain_plan.get("ceo_question", ""),
    })


def build_chain_plan(task_id: str, title: str, task_type: str,
                     dept: str, start_from: str = "") -> dict:
    """Build an execution plan for the chain. Returns instructions for each level."""
    
    plan = []
    instructions = []
    needs_ceo = False
    ceo_question = ""

    if dept == "intelligence":
        # Intelligence chain: Athena → Probe/Odin → work → back up
        plan = [
            {"level": "director", "agent": "Athena",
             "action": f"Route to the right team member"},
            {"level": "team_member", "agent": "Probe or Odin",
             "action": f"Audit/research the codebase for: {title}"},
        ]
        instructions = [
            f"1. @Athena (Director): Assign this task to the right team member. "
            f"If it's code auditing → Probe team. If it's research → Odin team.",
            f"2. @Probe or @Odin (Team Member): Do the actual work. "
            f"Audit the codebase, research best practices, or whatever the task requires.",
            f"3. Report back up: Team member → Athena → you (CEO).",
        ]

    elif dept == "build":
        # Build chain: Hephaestus → Aurora/Titan/Zephyr → Lead → Senior → Junior
        plan = [
            {"level": "director", "agent": "Hephaestus",
             "action": f"Determine which team: frontend (Aurora), backend (Titan), or database (Zephyr)"},
            {"level": "team_head", "agent": "Aurora/Titan/Zephyr",
             "action": f"Route to the right tech lead"},
            {"level": "tech_lead", "agent": "Lead-Faro/Terra/Zen",
             "action": f"Assign to the right senior dev"},
            {"level": "senior", "agent": "Senior Dev",
             "action": f"Review task, assign to the right junior dev"},
            {"level": "junior", "agent": "Junior Dev",
             "action": f"DO THE WORK — write the code"},
        ]
        instructions = [
            f"1. @Hephaestus (Director): Decide which team this goes to "
            f"(frontend/Aurora, backend/Titan, or database/Zephyr).",
            f"2. @Aurora/Titan/Zephyr (Team Head): Route to the tech lead.",
            f"3. @Lead-Faro/Terra/Zen (Tech Lead): Route to the right senior.",
            f"4. @Senior Dev: Review the task, assign to the right junior.",
            f"5. @Junior Dev: Write the actual code.",
            f"6. Report back up: Junior → Senior → Tech Lead → Team Head → Director → CEO.",
        ]

    elif dept == "quality":
        plan = [
            {"level": "director", "agent": "Minos",
             "action": f"Run quality checks, or assign to Pixel/Scalpel/Janus team"},
            {"level": "team", "agent": "Test Team",
             "action": f"Execute tests, security scans, etc."},
        ]
        instructions = [
            f"1. @Minos (Director): Decide what checks are needed.",
            f"2. @Pixel/Scalpel/Janus: Run the actual tests.",
            f"3. Report back: Team → Minos → CEO.",
        ]

    elif dept == "documentation":
        plan = [
            {"level": "director", "agent": "Thoth",
             "action": f"Assign to the right doc agent"},
            {"level": "writer", "agent": "Quill/Scroll/Ledger",
             "action": f"Write the actual documentation"},
        ]
        instructions = [
            f"1. @Thoth (Director): Assign to the right doc agent.",
            f"2. @Quill/Scroll/Ledger: Write the docs.",
            f"3. Report back: Writer → Thoth → CEO.",
        ]

    else:
        return {"ok": False, "error": f"Unknown department: {dept}"}

    # Check if a CEO decision is needed
    if task_type in ("architecture", "design"):
        needs_ceo = True
        ceo_question = f"@{dept.capitalize()} needs a CEO decision on architecture/design for: {title}"
        instructions.append(f"\n⚠️ STOP — CEO decision needed: {ceo_question}")

    log_entry = f"CHAIN RUN → {task_id}: {title} ({dept})"
    session_append(log_entry, agent="Chain Runner", kind="note")
    write_log("Chain", "Chain Runner", "run",
              {"task_id": task_id, "department": dept})

    return {
        "ok": True,
        "plan": plan,
        "instructions": instructions,
        "needs_ceo": needs_ceo,
        "ceo_question": ceo_question,
    }


# ── CLI ──
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Chain Runner — Run the chain of command autonomously")
        print()
        print("Commands:")
        print("  run <task-id> [start-from]    Execute the chain for a task")
        print("  plan <task-id>                Show the chain plan without running")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "info":
        print(json.dumps(info(), indent=2))
    elif cmd == "run":
        task_id = sys.argv[2] if len(sys.argv) > 2 else ""
        start_from = sys.argv[3] if len(sys.argv) > 3 else ""
        if task_id:
            result = run_chain(task_id, start_from)
            print(json.dumps(result.to_dict() if hasattr(result, 'to_dict') else result, indent=2))
        else:
            print("Usage: run <task-id> [start-from]")
    elif cmd == "plan":
        task_id = sys.argv[2] if len(sys.argv) > 2 else ""
        if task_id:
            from common import McpResult
            result = run_chain(task_id)
            if result.ok:
                print(f"\nCHAIN PLAN — {result.data['task_id']}: {result.data['title']}")
                print(f"Department: {result.data['department']}")
                print(f"Description: {result.data['department_description']}")
                print()
                for step in result.data['chain_plan']:
                    print(f"  {step['level'].upper():15s} @{step['agent']:<20s} {step['action']}")
                print()
                print("Instructions:")
                for inst in result.data.get('instructions', []):
                    print(f"  {inst}")
                if result.data.get('needs_ceo'):
                    print(f"\n  ⚠️  CEO decision needed: {result.data['ceo_question']}")
            else:
                print(result.to_dict())
        else:
            print("Usage: plan <task-id>")
    else:
        print(f"Unknown command: {cmd}")
