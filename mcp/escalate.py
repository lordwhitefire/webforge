#!/usr/bin/env python3
"""
Escalation MCP — CEO Communication (finally implemented)

Industry pattern: Escalation paths in engineering teams.
When an engineer (or AI) can't make a decision, they escalate to
the decision-maker (CEO/tech lead/developer).

This is the bridge between the AI and the developer (Law 5: No Inference).

How it works:
  1. AI encounters something it can't decide → /escalate "question"
  2. Question is recorded with a unique ID
  3. Developer sees the question and answers
  4. Answer is logged to session log
  5. If answer is a decision → suggest /add-adr
  6. If answer is a correction → suggest /correct
"""

import os
import sys
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))
from common import write_log, success, fail, utc_now, McpResult, get_project_root
from memory import session_append


def info() -> dict:
    return {
        "id": "m-escalate",
        "name": "Escalation MCP (CEO Communication)",
        "tier": 2,
        "owner": "Hermes",
        "job": "Bridge between AI and developer. Law 5: No Inference. When AI can't decide, it asks you.",
    }


# ── Paths ──
def escalations_dir() -> Path:
    d = get_project_root() / ".webforge" / "escalations"
    d.mkdir(parents=True, exist_ok=True)
    return d

def escalations_file() -> Path:
    return escalations_dir() / "open.json"


def load_escalations() -> dict:
    f = escalations_file()
    if not f.exists():
        return {"escalations": [], "next_id": 1}
    return json.loads(f.read_text())

def save_escalations(data: dict):
    escalations_file().write_text(json.dumps(data, indent=2, ensure_ascii=False))


# ── Ask a question (AI → Developer) ──
def escalate_ask(question: str, context: str = "", task_id: str = "") -> McpResult:
    """
    AI escalates a question to the developer (CEO).
    Law 5: No Inference. Ever. If something is not decided, STOP and ask.
    """
    data = load_escalations()
    esc_id = f"esc-{data['next_id']:03d}"
    data["next_id"] += 1

    escalation = {
        "id": esc_id,
        "question": question,
        "context": context,
        "task_id": task_id,
        "status": "open",
        "asked_at": utc_now(),
        "answered_at": None,
        "answer": None,
    }
    data["escalations"].append(escalation)
    save_escalations(data)

    session_append(f"ESCALATION — {esc_id}: {question}", agent="Hermes", kind="note")
    write_log("Escalation", "Hermes", "escalate_ask",
              {"id": esc_id, "question": question})

    return success({
        "id": esc_id,
        "question": question,
        "message": (
            f"📤 ESCALATION {esc_id}\n\n"
            f"  Question: {question}\n"
            f"  Context: {context or '(none)'}\n"
            f"  Task: {task_id or '(none)'}\n\n"
            f"  This needs YOUR decision (Law 5: No Inference).\n"
            f"  Answer: /answer {esc_id} <your answer>\n"
            f"  Or defer: /answer {esc_id} skip"
        ),
    })


# ── Answer a question (Developer → AI) ──
def escalate_answer(esc_id: str, answer: str) -> McpResult:
    """
    Developer answers an escalated question.
    The answer is logged and the AI proceeds based on it.
    """
    data = load_escalations()
    esc = None
    for e in data["escalations"]:
        if e["id"] == esc_id:
            esc = e
            break

    if not esc:
        return fail(f"Escalation not found: {esc_id}")

    esc["status"] = "answered"
    esc["answer"] = answer
    esc["answered_at"] = utc_now()
    save_escalations(data)

    session_append(
        f"ESCALATION ANSWERED — {esc_id}: Q: {esc['question']} → A: {answer}",
        agent="Developer", kind="decision"
    )
    write_log("Escalation", "Developer", "escalate_answer",
              {"id": esc_id, "answer": answer})

    # Suggest follow-up actions based on the answer
    suggestions = []
    if answer.lower() not in ("skip", "defer", "later"):
        # If the answer looks like a decision, suggest ADR
        if any(word in answer.lower() for word in ["use", "should", "because", "decided"]):
            suggestions.append(f"  → Save as ADR: /add-adr {esc['question'][:50]} | {esc.get('context','')} | {answer}")

        # If the answer corrects something, suggest /correct
        if any(word in answer.lower() for word in ["no", "don't", "never", "instead", "wrong"]):
            suggestions.append(f"  → Save as rule: /correct <what was wrong> | <what to do instead>")

    suggestion_text = "\n".join(suggestions) if suggestions else "  (no follow-up suggested)"

    return success({
        "id": esc_id,
        "question": esc["question"],
        "answer": answer,
        "message": (
            f"✅ ESCALATION ANSWERED — {esc_id}\n\n"
            f"  Question: {esc['question']}\n"
            f"  Answer: {answer}\n\n"
            f"  The AI will now proceed based on your answer.\n"
            f"{suggestion_text}"
        ),
    })


# ── List open escalations ──
def escalate_list() -> McpResult:
    """List all open escalations (questions waiting for developer answer)."""
    data = load_escalations()
    open_esc = [e for e in data["escalations"] if e["status"] == "open"]

    if not open_esc:
        return success({"open_count": 0, "message": "✅ No open escalations. AI is not blocked."})

    lines = []
    lines.append(f"📤 OPEN ESCALATIONS ({len(open_esc)})")
    lines.append("=" * 50)
    lines.append("")
    for e in open_esc:
        lines.append(f"  {e['id']}: {e['question']}")
        if e.get("context"):
            lines.append(f"     Context: {e['context']}")
        if e.get("task_id"):
            lines.append(f"     Task: {e['task_id']}")
        lines.append(f"     Asked: {e['asked_at'][:19]}")
        lines.append(f"     → Answer: /answer {e['id']} <your answer>")
        lines.append("")

    return success({"open_count": len(open_esc), "output": "\n".join(lines)})


# ── CLI ──
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Escalation MCP — CEO Communication")
        print("Usage: python escalate.py <command> [args]")
        print()
        print("Commands:")
        print("  ask <question> [context] [task_id]  Escalate a question to the developer")
        print("  answer <id> <answer>                Answer an escalation")
        print("  list                                List open escalations")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "info":
        print(json.dumps(info(), indent=2))
    elif cmd == "ask":
        question = sys.argv[2] if len(sys.argv) > 2 else ""
        context = sys.argv[3] if len(sys.argv) > 3 else ""
        task_id = sys.argv[4] if len(sys.argv) > 4 else ""
        if question:
            result = escalate_ask(question, context, task_id)
            print(result.data.get("message", result.to_dict()))
        else:
            print("Usage: ask <question> [context] [task_id]")
    elif cmd == "answer":
        esc_id = sys.argv[2] if len(sys.argv) > 2 else ""
        answer = sys.argv[3] if len(sys.argv) > 3 else ""
        if esc_id and answer:
            result = escalate_answer(esc_id, answer)
            print(result.data.get("message", result.to_dict()))
        else:
            print("Usage: answer <id> <answer>")
    elif cmd == "list":
        result = escalate_list()
        print(result.data.get("output", result.data.get("message", "")))
    else:
        print(f"Unknown command: {cmd}")
