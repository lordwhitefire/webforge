#!/usr/bin/env python3
"""
MCP 1 — Pipeline MCP (Hermes's main tool)
Tier 1 — Foundation

This is the most important MCP. It manages the trigger chain.
When an agent signals done, this MCP receives the signal, checks
what comes next in the pipeline, and wakes the next agent.

It also handles pausing — when a decision is needed from the developer,
this MCP halts the chain and flags the CEO.

Owner: Hermes (COO / Scheduler)
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))
from common import write_log, utc_now, notify_hermes, success, fail, McpResult

PIPELINE_FILE = Path("~/webforge/logs/pipeline-state.json").expanduser()

# Standard pipeline order
DEFAULT_PIPELINE = [
    "intelligence.probe",      # Probe team assesses
    "intelligence.odin",       # Odin team researches
    "intelligence.dorian",     # Dorian does UI research
    "ceo.review_intelligence", # CEO reviews with developer
    "build.frontend",          # Frontend builds
    "build.backend",           # Backend builds
    "build.database",          # Database/Infra builds
    "quality.verdict",         # Verdict checks standards
    "quality.nemesis",         # Nemesis tests
    "quality.janus",           # Janus security
    "quality.pulse",           # Pulse bug fixing
    "ceo.final_review",        # CEO final review
    "documentation.finalize",  # Docs finalize
]


def load_state():
    """Load current pipeline state from file."""
    if not PIPELINE_FILE.exists():
        return {
            "current_step": 0,
            "pipeline": DEFAULT_PIPELINE,
            "status": "idle",
            "history": [],
            "started_at": None,
        }
    with open(PIPELINE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state):
    """Save pipeline state to file."""
    PIPELINE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PIPELINE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def wake_agent(agent_name: str, task: str) -> McpResult:
    """Wake a specific agent with a task."""
    state = load_state()
    state["history"].append({
        "timestamp": utc_now(),
        "action": "wake",
        "agent": agent_name,
        "task": task,
    })
    save_state(state)
    write_log("Pipeline", "Hermes", "wake_agent",
              {"agent": agent_name, "task": task})
    print(f"[Pipeline] Waking {agent_name} for task: {task}")
    return success({"agent": agent_name, "task": task})


def signal_done(agent_name: str, report: str) -> McpResult:
    """An agent signals it is done. Move to next step in pipeline."""
    state = load_state()
    state["history"].append({
        "timestamp": utc_now(),
        "action": "done",
        "agent": agent_name,
        "report": report,
    })

    # Advance to next step
    state["current_step"] += 1

    if state["current_step"] >= len(state["pipeline"]):
        state["status"] = "complete"
        save_state(state)
        print("[Pipeline] Pipeline complete!")
        return success({"status": "complete"})

    next_step = state["pipeline"][state["current_step"]]
    state["status"] = f"running:{next_step}"
    save_state(state)

    print(f"[Pipeline] Agent {agent_name} done. Next: {next_step}")
    write_log("Pipeline", "Hermes", "advance_pipeline",
              {"from": agent_name, "to": next_step})
    return success({"next_step": next_step, "report": report})


def pause_for_developer(question: str, agent_name: str) -> McpResult:
    """Halt the pipeline and ask the developer a question (Law 5)."""
    state = load_state()
    state["status"] = "paused_for_developer"
    state["pending_question"] = {
        "from": agent_name,
        "question": question,
        "timestamp": utc_now(),
    }
    save_state(state)
    write_log("Pipeline", "Hermes", "pause_for_developer",
              {"from": agent_name, "question": question})
    print(f"\n[Pipeline] PAUSED — {agent_name} has a question for the developer:")
    print(f"  {question}\n")
    return success({"paused": True, "question": question})


def resume(answer: str) -> McpResult:
    """Developer answered the pending question. Resume pipeline."""
    state = load_state()
    if state.get("status") != "paused_for_developer":
        return fail("Pipeline is not paused")
    question = state.pop("pending_question")
    state["status"] = f"running:{state['pipeline'][state['current_step']]}"
    state["history"].append({
        "timestamp": utc_now(),
        "action": "resume",
        "question": question,
        "answer": answer,
    })
    save_state(state)
    write_log("Pipeline", "Hermes", "resume_after_answer",
              {"question": question, "answer": answer})
    print(f"[Pipeline] Resumed. Answer routed to {question['from']}.")
    return success({"resumed": True, "answer": answer})


def get_status() -> McpResult:
    """Get current pipeline status."""
    state = load_state()
    return success(state)


def reset_pipeline() -> McpResult:
    """Reset pipeline to idle state."""
    state = {
        "current_step": 0,
        "pipeline": DEFAULT_PIPELINE,
        "status": "idle",
        "history": [],
        "started_at": utc_now(),
    }
    save_state(state)
    write_log("Pipeline", "Hermes", "reset_pipeline", {})
    return success({"reset": True})


# CLI
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python pipeline.py <command> [args]")
        print("Commands: status, wake <agent> <task>, done <agent> <report>,")
        print("          pause <question> <agent>, resume <answer>, reset")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "status":
        print(json.dumps(get_status().to_dict(), indent=2))
    elif cmd == "wake":
        print(wake_agent(sys.argv[2], sys.argv[3]).to_dict())
    elif cmd == "done":
        print(signal_done(sys.argv[2], sys.argv[3]).to_dict())
    elif cmd == "pause":
        print(pause_for_developer(sys.argv[2], sys.argv[3]).to_dict())
    elif cmd == "resume":
        print(resume(sys.argv[2]).to_dict())
    elif cmd == "reset":
        print(reset_pipeline().to_dict())
    else:
        print(f"Unknown command: {cmd}")
