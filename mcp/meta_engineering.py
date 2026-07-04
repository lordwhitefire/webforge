#!/usr/bin/env python3
"""
Meta Engineering MCP — the learning loop.

When the developer corrects WebForge, this MCP:
1. Detects the correction
2. Proposes it as a rule
3. Records it in system-memory for future learning

Commands:
  review    — Scan session log for corrections, propose rules
  learn     — Review all corrections and update skill files (future)
  status    — Show what Meta Engineering has learned
"""

import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))
from common import write_log, success, fail, utc_now, McpResult, get_project_root
from memory import (
    webforge_dir, session_append, add_correction, add_rule,
    read_rules, list_rules, session_read
)


def info() -> dict:
    return {
        "id": "m-meta",
        "name": "Meta Engineering MCP",
        "tier": 8,
        "owner": "Daedalus",
        "job": "Learn from corrections. Turn developer feedback into permanent rules.",
    }


# ── Correction detection patterns ──
# These are phrases that indicate the developer is correcting the AI
CORRECTION_PATTERNS = [
    r"\bno[,\s]+(don't|do not|not)\b",
    r"\bdon't\b",
    r"\bdo not\b",
    r"\bstop\b",
    r"\bnever\b",
    r"\bwrong\b",
    r"\bshould have\b",
    r"\bshouldn't\b",
    r"\binstead\b",
    r"\bI prefer\b",
    r"\bI don't (like|want)\b",
    r"\bnot like that\b",
    r"\bI said\b",
    r"\bI told you\b",
    r"\bthat's not\b",
    r"\bthat is not\b",
    r"\byou (made|did) (a |an )?(mistake|error)\b",
    r"\bfix this\b",
    r"\bthat's wrong\b",
]


def find_corrections_in_session(days: int = 7) -> list:
    """
    Scan session log entries for correction patterns.
    Returns list of entries that look like corrections.
    """
    result = session_read(days)
    entries = result.data.get("entries", [])

    corrections = []
    for entry in entries:
        # Skip entries that are rules or rule-related (they contain "never" but aren't corrections)
        if "📏" in entry or "NEW RULE" in entry.upper():
            continue
        # Skip entries that are resume/stop/notes
        if "▶️" in entry or "🛑" in entry:
            continue

        # Check if entry already has correction kind marker (the ⚠️ emoji)
        if "⚠️" in entry:
            corrections.append({
                "entry": entry,
                "type": "explicit_correction",
                "already_processed": True,
            })
            continue

        # Check for correction patterns in the text
        entry_lower = entry.lower()
        for pattern in CORRECTION_PATTERNS:
            if re.search(pattern, entry_lower, re.IGNORECASE):
                corrections.append({
                    "entry": entry,
                    "type": "detected_pattern",
                    "pattern": pattern,
                    "already_processed": False,
                })
                break

    return corrections


def review() -> McpResult:
    """
    Meta Engineering review — scan session for corrections, propose rules.

    This is what /review runs.
    """
    print("=" * 60)
    print("META ENGINEERING REVIEW")
    print(f"Date: {utc_now()}")
    print("=" * 60)

    # 1. Find corrections in session log
    corrections = find_corrections_in_session(7)

    print(f"\n## CORRECTIONS FOUND: {len(corrections)}\n")

    new_corrections = [c for c in corrections if not c["already_processed"]]
    processed = [c for c in corrections if c["already_processed"]]

    if processed:
        print(f"Already processed (rules created): {len(processed)}")
        for c in processed:
            print(f"  ✓ {c['entry'][:100]}")

    if new_corrections:
        print(f"\nNew corrections detected (not yet rules): {len(new_corrections)}")
        print()
        for i, c in enumerate(new_corrections, 1):
            print(f"  {i}. {c['entry'][:150]}")
            print(f"     Pattern: {c.get('pattern', 'unknown')}")
            print()

        print("## PROPOSED ACTIONS")
        print()
        print("To turn any of these into a permanent rule, use:")
        print("  /correct <what was wrong> | <what to do instead>")
        print("    → saves for this project only")
        print("  /correct <what was wrong> | <what to do instead> | global")
        print("    → saves for ALL your projects (WebForge learns forever)")
        print()
        print("Examples:")
        print("  /correct using localStorage for auth | use httpOnly cookies")
        print("  /correct putting 'use client' on every file | only mark when hooks or events | global")
        print()
        print("Or add a rule directly:")
        print("  /add-rule Never use localStorage for auth tokens")
    else:
        print("No new corrections detected. Good session!")

    # 2. Show current rules count
    rules_result = list_rules("all")
    total_rules = rules_result.data.get("count", 0)
    print(f"\n## CURRENT RULES: {total_rules}")

    # 3. Show correction logs
    from memory import global_corrections_file, corrections_file as project_corrections_file
    gc = global_corrections_file()
    pc = project_corrections_file()
    total = 0
    for log_file in [gc, pc]:
        if log_file.exists():
            lines = log_file.read_text().strip().split("\n")
            count = sum(1 for l in lines if l.startswith("- **["))
            total += count
            label = "GLOBAL" if log_file == gc else "PROJECT"
            print(f"## {label} CORRECTIONS: {count}")
            print(f"   Log: {log_file}")
    print(f"## TOTAL CORRECTIONS: {total}")

    # 4. Log the review
    session_append(
        f"Meta Engineering review: {len(corrections)} corrections found ({len(new_corrections)} new, {len(processed)} processed). {total_rules} rules total.",
        agent="Daedalus",
        kind="note"
    )

    print("\n" + "=" * 60)
    print("REVIEW COMPLETE")
    print("=" * 60)

    return success({
        "corrections_found": len(corrections),
        "new_corrections": len(new_corrections),
        "processed_corrections": len(processed),
        "total_rules": total_rules,
    })


def learn() -> McpResult:
    """
    Future: Review all corrections and update skill files automatically.
    For now, just reports what would be done.
    """
    corrections = find_corrections_in_session(30)  # Last 30 days
    new = [c for c in corrections if not c["already_processed"]]

    print("=" * 60)
    print("META ENGINEERING — LEARN MODE")
    print("=" * 60)
    print()
    print(f"Found {len(new)} unprocessed corrections in last 30 days.")
    print()
    if new:
        print("These would be turned into rules and added to skill files:")
        for c in new:
            print(f"  - {c['entry'][:100]}")
    else:
        print("No unprocessed corrections. All corrections have been turned into rules.")
    print()
    print("NOTE: Auto-learning is not implemented yet.")
    print("Use /review to see corrections, then /correct to create rules manually.")

    return success({"unprocessed": len(new), "auto_learn": False})


def status() -> McpResult:
    """Show Meta Engineering status."""
    from memory import global_corrections_file, corrections_file as project_corrections_file
    gc = global_corrections_file()
    pc = project_corrections_file()

    corrections_count = 0
    for log_file in [gc, pc]:
        if log_file.exists():
            corrections_count += sum(1 for l in log_file.read_text().split("\n")
                                     if l.startswith("- **["))

    rules_result = list_rules("all")

    return success({
        "total_rules": rules_result.data.get("count", 0),
        "corrections_learned": corrections_count,
        "global_corrections": gc.exists(),
        "project_corrections": pc.exists(),
        "auto_learn_enabled": False,
    })


# CLI
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Meta Engineering MCP")
        print("Usage: python meta_engineering.py <command>")
        print()
        print("Commands:")
        print("  review    Scan session for corrections, propose rules")
        print("  learn     Review corrections and update skills (future)")
        print("  status    Show what Meta Engineering has learned")
        print("  info      Show MCP info")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "info":
        print(json.dumps(info(), indent=2))
    elif cmd == "review":
        review()
    elif cmd == "learn":
        learn()
    elif cmd == "status":
        print(json.dumps(status().to_dict(), indent=2))
    else:
        print(f"Unknown command: {cmd}")
