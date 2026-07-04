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
    Auto-learn from corrections: detect correction → write check file → register it.
    
    This is the REAL Meta Engineering loop:
    1. Scan session log for corrections (wrong → right patterns)
    2. For each unprocessed correction:
       a. Generate a Python check file in .webforge/checks/
       b. The check file has a check(project_root) function
       c. The check runs automatically on every /task-done
       d. If it fails, the task is ACTUALLY blocked (lock file)
    3. Report what was learned
    """
    corrections = find_corrections_in_session(30)
    # DON'T filter by already_processed — we want to generate check files
    # for ALL corrections, even ones that already have .md rule files.
    # The check file is DIFFERENT from the rule file.
    all_corrections = corrections  # Use all, not just "new"

    print("=" * 60)
    print("META ENGINEERING — LEARN MODE (auto-generating check files)")
    print("=" * 60)
    print()

    if not all_corrections:
        print("✅ No corrections found. Nothing to learn from.")
        return success({"corrections": 0, "auto_learn": True, "checks_generated": 0})

    # Import the enforcement engine
    try:
        from enforce import generate_check_file, discover_checks
    except ImportError:
        print("❌ enforce.py not available. Cannot auto-generate check files.")
        return fail("Enforcement engine not available")

    # Get existing checks to avoid duplicates
    existing_checks = discover_checks()
    existing_hashes = set(c["name"].replace("check_", "") for c in existing_checks)

    checks_generated = 0
    import hashlib

    for c in all_corrections:
        entry = c["entry"]
        # Parse the correction from the session log entry
        # Format: CORRECTION — Wrong: X → Right: Y → Rule: Z
        import re
        wrong_match = re.search(r'Wrong:\s*(.+?)\s*→', entry)
        right_match = re.search(r'Right:\s*(.+?)\s*→', entry)
        rule_match = re.search(r'Rule:\s*(.+?)(?:\s*$)', entry)

        if not wrong_match or not right_match:
            continue

        wrong = wrong_match.group(1).strip()
        right = right_match.group(1).strip()
        rule = rule_match.group(1).strip() if rule_match else f"Never {wrong}. {right}."

        # Check if we already have a check for this rule
        rule_hash = hashlib.md5(rule.encode()).hexdigest()[:8]
        if rule_hash in existing_hashes:
            print(f"  ⏭️  Check already exists for: {rule[:60]}")
            continue

        # Generate the check file
        result = generate_check_file(rule, wrong, right)
        if result.ok:
            checks_generated += 1
            print(f"  ✅ Generated: {result.data.get('file', 'unknown')}")
            print(f"     Rule: {rule[:80]}")
            print(f"     Searches for: {', '.join(result.data.get('search_terms', []))}")
            print()

    # Log what we learned
    session_append(
        f"META ENGINEERING LEARNED — Generated {checks_generated} enforcement check file(s) from corrections.",
        agent="Daedalus", kind="decision"
    )

    print(f"📊 Summary: {checks_generated} enforcement check file(s) generated.")
    print(f"   These will run automatically on every /task-done.")
    print(f"   If a check fails, the task is ACTUALLY blocked (lock file).")

    return success({
        "corrections": len(all_corrections),
        "auto_learn": True,
        "checks_generated": checks_generated,
    })


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
