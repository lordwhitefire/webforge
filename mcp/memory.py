#!/usr/bin/env python3
"""
WebForge Memory MCP (v2)

The heart of WebForge. Handles 4 types of memory:

1. SESSION LOG — what we did today, where we stopped
   File: <project>/.webforge/memory/session-YYYY-MM.md (splits when hits 240 lines)

2. RULES — do's and don'ts the developer has set
   Folder: <project>/.webforge/rules/
   Each rule is one file: <timestamp>-<slug>.md
   Global rules: ~/.webforge/global-rules/ (travel with you across projects)

3. PREFERENCES — what the developer likes/dislikes
   File: <project>/.webforge/preferences.md
   Global: ~/.webforge/global-preferences.md

4. ADRs — Architecture Decision Records
   Folder: <project>/docs/adr/ (industry standard location)
   Format: NNNN-title.md (numbered)

Law 2 (300-line rule) applies to session log and preferences.
Rules and ADRs are RECORDS — never compacted.
"""

import os
import sys
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))
from common import write_log, success, fail, utc_now, McpResult, get_project_root


# ── Paths ──
def webforge_dir() -> Path:
    """The .webforge folder inside the project."""
    return get_project_root() / ".webforge"

def global_webforge_dir() -> Path:
    """The ~/.webforge folder — travels with you across projects."""
    return Path.home() / ".webforge"

def session_log_file() -> Path:
    """Current session log file. Splits by month to stay under 300 lines."""
    wf = webforge_dir() / "memory"
    wf.mkdir(parents=True, exist_ok=True)
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    return wf / f"session-{month}.md"

def rules_dir() -> Path:
    d = webforge_dir() / "rules"
    d.mkdir(parents=True, exist_ok=True)
    return d

def global_rules_dir() -> Path:
    d = global_webforge_dir() / "global-rules"
    d.mkdir(parents=True, exist_ok=True)
    return d

def preferences_file() -> Path:
    return webforge_dir() / "preferences.md"

def global_preferences_file() -> Path:
    return global_webforge_dir() / "global-preferences.md"

def corrections_file() -> Path:
    """Project-specific correction log."""
    d = webforge_dir() / "meta-memory"
    d.mkdir(parents=True, exist_ok=True)
    return d / "corrections.md"

def global_corrections_file() -> Path:
    """Global correction log — WebForge learns across all projects."""
    d = global_webforge_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d / "corrections.md"

def adr_dir() -> Path:
    """ADRs live in the project's docs/adr/ (industry standard)."""
    d = get_project_root() / "docs" / "adr"
    d.mkdir(parents=True, exist_ok=True)
    return d


def info() -> dict:
    return {
        "id": "m02",
        "name": "Memory MCP v2",
        "tier": 1,
        "owner": "Quill",
        "job": "Session log, rules, preferences, ADRs. The heart of WebForge memory.",
    }


# ── Session log ──
def session_append(entry: str, agent: str = "Unknown", kind: str = "note") -> McpResult:
    """Append an entry to today's session log."""
    log_file = session_log_file()

    lines = 0
    if log_file.exists():
        lines = sum(1 for _ in log_file.open())

    if lines >= 240:
        month = datetime.now(timezone.utc).strftime("%Y-%m")
        parts = list((webforge_dir() / "memory").glob(f"session-{month}-part-*.md"))
        next_part = len(parts) + 1
        new_name = log_file.parent / f"session-{month}-part-{next_part:02d}.md"
        log_file.rename(new_name)
        log_file = session_log_file()
        log_file.write_text(f"# Session log — {month} (part {next_part + 1})\n\nContinued from {new_name.name}.\n\n---\n\n")

    timestamp = utc_now()
    kind_emoji = {
        "note": "📝",
        "decision": "✅",
        "correction": "⚠️",
        "stop": "🛑",
        "resume": "▶️",
        "rule": "📏",
        "preference": "❤️",
    }.get(kind, "📝")

    line = f"- **[{timestamp}]** {kind_emoji} **{agent}**: {entry}\n"

    if not log_file.exists() or log_file.stat().st_size == 0:
        log_file.write_text(f"# Session log — {datetime.now(timezone.utc).strftime('%Y-%m')}\n\n---\n\n")

    with log_file.open("a", encoding="utf-8") as f:
        f.write(line)

    write_log("Memory", agent, "session_append",
              {"kind": kind, "chars": len(entry), "file": log_file.name})
    return success({"file": log_file.name, "kind": kind})


def session_read(days: int = 7) -> McpResult:
    """Read the last N days of session logs."""
    wf = webforge_dir() / "memory"
    if not wf.exists():
        return success({"entries": [], "note": "No session logs yet."})

    files = sorted(wf.glob("session-*.md"), reverse=True)
    cutoff = datetime.now(timezone.utc).timestamp() - (days * 86400)
    entries = []

    for f in files:
        for line in f.read_text(encoding="utf-8").split("\n"):
            if line.startswith("- **["):
                ts_match = line.split("**[")[1].split("]")[0]
                try:
                    ts = datetime.fromisoformat(ts_match).timestamp()
                    if ts >= cutoff:
                        entries.append(line)
                except:
                    entries.append(line)

    return success({"entries": entries, "count": len(entries)})


def session_stop(summary: str = "") -> McpResult:
    """Mark the end of a session — where we stopped, what's next."""
    if not summary:
        summary = input("Where did you stop? What's next? > ")

    session_append(f"STOP — {summary}", agent="Developer", kind="stop")
    return success({"stopped": True, "summary": summary})


# ── Rules ──
def add_rule(rule_text: str, scope: str = "project", source: str = "developer") -> McpResult:
    """Add a new rule. Rules are RECORDS — never compacted."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    slug = hashlib.md5(rule_text.encode()).hexdigest()[:8]

    if scope == "global":
        target_dir = global_rules_dir()
    else:
        target_dir = rules_dir()

    filename = f"{timestamp}-{slug}.md"
    filepath = target_dir / filename

    content = f"""# Rule: {rule_text}

- **Added:** {utc_now()}
- **Scope:** {scope}
- **Source:** {source}
- **Status:** active

## Rule
{rule_text}

## Context
<!-- Why was this rule added? What happened that made it necessary? -->

## Enforcement
<!-- How is this rule enforced? Lint rule? Skill file? Manual review? -->
- [ ] Add to skill files (relevant agents)
- [ ] Add to lint rules (if automatable)
- [ ] Add to AGENTS.md (if universal)

## Origin
<!-- The session log entry or conversation that triggered this rule -->
"""

    filepath.write_text(content, encoding="utf-8")
    session_append(f"NEW RULE ({scope}): {rule_text}", agent="Quill", kind="rule")
    write_log("Memory", "Quill", "add_rule",
              {"rule": rule_text, "scope": scope, "file": filepath.name})
    return success({"file": filepath.name, "scope": scope, "rule": rule_text})


def add_correction(wrong: str, right: str, scope: str = "project") -> McpResult:
    """
    Meta Engineering: Turn a correction into a permanent rule.

    When the developer says "don't do X, do Y instead", this function:
    1. Generates a rule from the correction
    2. Saves it to rules/
    3. Logs the correction to session log
    4. Records it in system-memory for Meta Engineering to learn from

    Args:
        wrong: What the AI did wrong (e.g. "using localStorage for auth tokens")
        right: What it should do instead (e.g. "use httpOnly cookies")
        scope: 'project' or 'global'
    """
    # Generate the rule text — always include both what's wrong and what's right
    right_cap = right[0].upper() + right[1:] if right else ""
    rule_text = f"Never {wrong}. {right_cap}."

    # Add the rule
    result = add_rule(rule_text, scope=scope, source="correction")

    # Log the correction specifically
    session_append(
        f"CORRECTION — Wrong: {wrong} → Right: {right} → Rule: {rule_text}",
        agent="Meta-Engineering",
        kind="correction"
    )

    # Write to correction log (scope-aware)
    try:
        if scope == "global":
            log_file = global_corrections_file()
        else:
            log_file = corrections_file()
        if not log_file.exists():
            log_file.write_text("# Meta Engineering — Corrections Log\n\nRules learned from developer corrections.\n\n---\n\n")
        with log_file.open("a", encoding="utf-8") as f:
            f.write(f"- **[{utc_now()}]** Wrong: {wrong} → Right: {right} → Rule: {rule_text}\n")
    except:
        pass

    return success({
        "rule": rule_text,
        "wrong": wrong,
        "right": right,
        "scope": scope,
        "rule_file": result.data.get("file"),
    })


def list_rules(scope: str = "all") -> McpResult:
    """List all rules."""
    rules = []
    if scope in ("project", "all"):
        for f in sorted(rules_dir().glob("*.md")):
            rules.append({"scope": "project", "file": f.name, "path": str(f)})
    if scope in ("global", "all"):
        for f in sorted(global_rules_dir().glob("*.md")):
            rules.append({"scope": "global", "file": f.name, "path": str(f)})
    return success({"rules": rules, "count": len(rules)})


def read_rules() -> str:
    """Read all active rules and return as a single text block (for LLM context)."""
    parts = []

    global_dir = global_rules_dir()
    if global_dir.exists():
        global_rules = sorted(global_dir.glob("*.md"))
        if global_rules:
            parts.append("## GLOBAL RULES (apply to all projects)\n")
            for f in global_rules:
                content = f.read_text(encoding="utf-8")
                try:
                    rule_section = content.split("## Rule")[1].split("## Context")[0].strip()
                    parts.append(f"- {rule_section}")
                except IndexError:
                    parts.append(f"- (malformed rule file: {f.name})")

    proj_dir = rules_dir()
    if proj_dir.exists():
        proj_rules = sorted(proj_dir.glob("*.md"))
        if proj_rules:
            parts.append("\n## PROJECT RULES (this project only)\n")
            for f in proj_rules:
                content = f.read_text(encoding="utf-8")
                try:
                    rule_section = content.split("## Rule")[1].split("## Context")[0].strip()
                    parts.append(f"- {rule_section}")
                except IndexError:
                    parts.append(f"- (malformed rule file: {f.name})")

    return "\n".join(parts) if parts else "(no rules set)"


# ── Preferences ──
def add_preference(pref_text: str, scope: str = "project") -> McpResult:
    """Add a preference. Preferences are softer than rules."""
    target = global_preferences_file() if scope == "global" else preferences_file()
    target.parent.mkdir(parents=True, exist_ok=True)

    if not target.exists():
        target.write_text(f"# Preferences\n\nWhat the developer likes and dislikes.\n\n---\n\n")

    with target.open("a", encoding="utf-8") as f:
        f.write(f"- {pref_text}\n")

    session_append(f"NEW PREFERENCE ({scope}): {pref_text}", agent="Quill", kind="preference")
    return success({"file": target.name, "preference": pref_text})


def read_preferences() -> str:
    """Read all preferences as text for LLM context."""
    parts = []
    g = global_preferences_file()
    if g.exists():
        parts.append("## GLOBAL PREFERENCES\n")
        parts.append(g.read_text(encoding="utf-8"))
    p = preferences_file()
    if p.exists():
        parts.append("\n## PROJECT PREFERENCES\n")
        parts.append(p.read_text(encoding="utf-8"))
    return "\n".join(parts) if parts else "(no preferences set)"


# ── ADRs ──
def add_adr(title: str, context: str, decision: str, consequences: str = "") -> McpResult:
    """Add an ADR. Industry-standard Michael Nygard template."""
    d = adr_dir()
    existing = sorted(d.glob("[0-9][0-9][0-9][0-9]-*.md"))
    if existing:
        last_num = int(existing[-1].name[:4])
        next_num = last_num + 1
    else:
        next_num = 1

    slug = title.lower().replace(" ", "-").replace(":", "")[:50]
    slug = "".join(c for c in slug if c.isalnum() or c == "-")

    filename = f"{next_num:04d}-{slug}.md"
    filepath = d / filename

    content = f"""# {next_num:04d}. {title}

Date: {datetime.now(timezone.utc).strftime("%Y-%m-%d")}

## Status

Accepted

## Context

{context}

## Decision

{decision}

## Consequences

{consequences or '(to be filled as consequences emerge)'}

---
*ADR created via WebForge Memory MCP*
"""
    filepath.write_text(content, encoding="utf-8")
    session_append(f"NEW ADR #{next_num:04d}: {title}", agent="Quill", kind="decision")
    write_log("Memory", "Quill", "add_adr",
              {"number": next_num, "title": title, "file": filepath.name})
    return success({"file": filepath.name, "number": next_num})


def list_adrs() -> McpResult:
    """List all ADRs."""
    d = adr_dir()
    if not d.exists():
        return success({"adrs": [], "count": 0})
    adrs = []
    for f in sorted(d.glob("*.md")):
        first_line = f.read_text(encoding="utf-8").split("\n")[0]
        title = first_line.lstrip("# ").strip()
        adrs.append({"file": f.name, "title": title})
    return success({"adrs": adrs, "count": len(adrs)})


# ── Full context ──
def get_full_context() -> dict:
    """Get EVERYTHING WebForge knows about this project. Used by /resume."""
    return {
        "project_root": str(get_project_root()),
        "session_logs": [str(f) for f in (webforge_dir() / "memory").glob("session-*.md")] if (webforge_dir() / "memory").exists() else [],
        "rules": {
            "project": [str(f) for f in rules_dir().glob("*.md")] if rules_dir().exists() else [],
            "global": [str(f) for f in global_rules_dir().glob("*.md")] if global_rules_dir().exists() else [],
        },
        "preferences": {
            "project": str(preferences_file()) if preferences_file().exists() else None,
            "global": str(global_preferences_file()) if global_preferences_file().exists() else None,
        },
        "adrs": [str(f) for f in adr_dir().glob("*.md")] if adr_dir().exists() else [],
    }


# ── CLI ──
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Memory MCP v2")
        print("Usage: python memory.py <command> [args]")
        print()
        print("Session log:")
        print("  session-append <entry> [agent] [kind]")
        print("  session-read [days]")
        print("  session-stop [summary]")
        print()
        print("Rules:")
        print("  add-rule <rule> [scope] [source]")
        print("  add-correction <wrong> | <right> [scope]  — turn a correction into a rule")
        print("  list-rules [scope]")
        print("  read-rules")
        print()
        print("Preferences:")
        print("  add-preference <pref> [scope]")
        print("  read-preferences")
        print()
        print("ADRs:")
        print("  add-adr <title> <context> <decision> [consequences]")
        print("  list-adrs")
        print()
        print("Context:")
        print("  get-context")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "info":
        print(json.dumps(info(), indent=2))
    elif cmd == "session-append":
        entry = sys.argv[2]
        agent = sys.argv[3] if len(sys.argv) > 3 else "Unknown"
        kind = sys.argv[4] if len(sys.argv) > 4 else "note"
        print(session_append(entry, agent, kind).to_dict())
    elif cmd == "session-read":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
        print(session_read(days).to_dict())
    elif cmd == "session-stop":
        summary = sys.argv[2] if len(sys.argv) > 2 else ""
        print(session_stop(summary).to_dict())
    elif cmd == "add-rule":
        rule = sys.argv[2]
        scope = sys.argv[3] if len(sys.argv) > 3 else "project"
        source = sys.argv[4] if len(sys.argv) > 4 else "developer"
        print(add_rule(rule, scope, source).to_dict())
    elif cmd == "add-correction":
        # Usage: add-correction <wrong> | <right> [scope]
        # The | splits wrong from right
        raw = sys.argv[2] if len(sys.argv) > 2 else ""
        parts = raw.split("|")
        if len(parts) >= 2:
            wrong = parts[0].strip()
            right = parts[1].strip()
            scope = parts[2].strip() if len(parts) > 2 else "project"
            print(add_correction(wrong, right, scope).to_dict())
        else:
            print("Usage: add-correction <wrong> | <right> [scope]")
    elif cmd == "list-rules":
        scope = sys.argv[2] if len(sys.argv) > 2 else "all"
        print(list_rules(scope).to_dict())
    elif cmd == "read-rules":
        print(read_rules())
    elif cmd == "add-preference":
        pref = sys.argv[2]
        scope = sys.argv[3] if len(sys.argv) > 3 else "project"
        print(add_preference(pref, scope).to_dict())
    elif cmd == "read-preferences":
        print(read_preferences())
    elif cmd == "add-adr":
        title = sys.argv[2]
        context = sys.argv[3]
        decision = sys.argv[4]
        consequences = sys.argv[5] if len(sys.argv) > 5 else ""
        print(add_adr(title, context, decision, consequences).to_dict())
    elif cmd == "list-adrs":
        print(list_adrs().to_dict())
    elif cmd == "get-context":
        print(json.dumps(get_full_context(), indent=2))
    else:
        print(f"Unknown command: {cmd}")
