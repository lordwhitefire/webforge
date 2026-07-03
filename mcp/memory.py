#!/usr/bin/env python3
"""
MCP 2 — Memory MCP
Tier 1 — Foundation

Reads and writes all memory files. Controls the 300-line rule (Law 2).
Checks if a memory file is at 80% (240 lines), triggers new generation.
This stops two agents writing to the same file at the same time.

Owner: Quill (Documentation Lead)
"""

import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import (write_log, count_lines, MEMORY_DIR, MEMORY_MAX_LINES,
                    MEMORY_SPLIT_THRESHOLD, success, fail, McpResult, utc_now)


def _lock_file(path: Path) -> Path:
    """Create a lock file to prevent concurrent writes."""
    return path.with_suffix(path.suffix + ".lock")


def _is_locked(path: Path) -> bool:
    return _lock_file(path).exists()


def _acquire_lock(path: Path, agent: str) -> bool:
    lock = _lock_file(path)
    if lock.exists():
        return False
    lock.write_text(f"{agent}\n{utc_now()}\n")
    return True


def _release_lock(path: Path):
    lock = _lock_file(path)
    if lock.exists():
        lock.unlink()


def get_current_generation() -> int:
    """Find the highest generation number in the memory folder."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    gens = []
    for f in MEMORY_DIR.glob("memory-gen-*.md"):
        m = re.match(r"memory-gen-(\d+)\.md", f.name)
        if m:
            gens.append(int(m.group(1)))
    return max(gens) if gens else 0


def get_current_file() -> Path:
    """Get the path of the current (latest) memory generation file."""
    gen = get_current_generation()
    if gen == 0:
        return MEMORY_DIR / "memory-gen-001.md"
    return MEMORY_DIR / f"memory-gen-{gen:03d}.md"


def create_new_generation(summary_lines: list = None) -> McpResult:
    """
    Law 2: When a memory file reaches 300 lines, create a new generation.
    First 20-30 lines of new file MUST be a summary of the previous.
    """
    current_gen = get_current_generation()
    new_gen = current_gen + 1
    new_file = MEMORY_DIR / f"memory-gen-{new_gen:03d}.md"

    # Auto-generate summary from previous generation if not provided
    if summary_lines is None:
        summary_lines = _summarize_generation(current_gen)

    header = f"""# WebForge Project Memory — Generation {new_gen:03d}

**Previous Generation:** {current_gen:03d}
**Created:** {utc_now()}

---

## Summary of Previous Generation

{chr(10).join(summary_lines)}

---

## New Content

"""
    new_file.write_text(header)
    write_log("Memory", "Quill", "new_generation",
              {"new_gen": new_gen, "previous_gen": current_gen,
               "summary_lines": len(summary_lines)})
    print(f"[Memory] Created new generation: {new_file.name}")
    return success({"new_file": str(new_file), "generation": new_gen})


def _summarize_generation(gen: int) -> list:
    """
    Law 2: Auto-generate a 20-30 line summary of the previous generation.
    Extracts key info: decisions, build progress, active agents, pending questions.
    """
    if gen == 0:
        return ["(No previous generation — this is the first memory file.)"]

    prev_file = MEMORY_DIR / f"memory-gen-{gen:03d}.md"
    if not prev_file.exists():
        return [f"(Previous generation file not found: {prev_file.name})"]

    content = prev_file.read_text(encoding="utf-8")
    lines = content.split("\n")

    summary = []
    summary.append(f"**Previous file:** `{prev_file.name}` ({len(lines)} lines)")
    summary.append("")

    # Extract decisions (look for | date | area | patterns or "Decision:" lines)
    decisions = []
    for line in lines:
        if "DECIDED" in line.upper() or "Decision:" in line:
            decisions.append(line.strip())
        elif line.startswith("| ") and "|" in line[2:]:
            # Table row — include if it has content
            if any(kw in line.lower() for kw in ["decided", "skip", "pending", "done", "completed", "started"]):
                decisions.append(line.strip())

    summary.append("**Key decisions / progress from previous gen:**")
    if decisions:
        # Take up to 15 most important
        seen = set()
        unique = []
        for d in decisions:
            if d not in seen and len(unique) < 15:
                seen.add(d)
                unique.append(d)
        for d in unique:
            summary.append(f"- {d[:200]}")
    else:
        summary.append("- (No structured decisions found — read previous file for context.)")

    summary.append("")
    summary.append(f"**Total lines in previous:** {len(lines)}")
    summary.append(f"**Generated:** {utc_now()}")
    return summary



def append(content: str, agent: str, section: str = "") -> McpResult:
    """
    Append content to the current memory file.
    Checks 300-line rule. If at threshold, creates new generation.
    Acquires lock to prevent concurrent writes.
    """
    memory_file = get_current_file()

    if not memory_file.exists():
        memory_file.write_text("# WebForge Project Memory — Generation 001\n\n")

    if _is_locked(memory_file):
        return fail(f"Memory file is locked by another agent. Try again later.")

    if not _acquire_lock(memory_file, agent):
        return fail(f"Could not acquire lock on {memory_file}")

    try:
        # Check line count
        line_count = count_lines(memory_file)
        if line_count >= MEMORY_SPLIT_THRESHOLD:
            # Need new generation
            _release_lock(memory_file)
            new_gen_result = create_new_generation()
            if not new_gen_result.ok:
                return new_gen_result
            memory_file = get_current_file()
            if not _acquire_lock(memory_file, agent):
                return fail("Could not acquire lock on new generation file")

        # Append content
        timestamp = utc_now()
        section_header = f"\n## [{timestamp}] {agent}" + (f" — {section}\n" if section else "\n")
        with open(memory_file, "a", encoding="utf-8") as f:
            f.write(section_header + content + "\n")

        write_log("Memory", agent, "append",
                  {"file": memory_file.name, "section": section, "chars": len(content)})
        return success({"file": memory_file.name, "appended": True})

    finally:
        _release_lock(memory_file)


def read(generation: int = None) -> McpResult:
    """Read a memory file. If no generation given, read current."""
    if generation is None:
        memory_file = get_current_file()
    else:
        memory_file = MEMORY_DIR / f"memory-gen-{generation:03d}.md"

    if not memory_file.exists():
        return fail(f"Memory file not found: {memory_file.name}")

    content = memory_file.read_text(encoding="utf-8")
    return success({"file": memory_file.name, "content": content})


def search(query: str) -> McpResult:
    """Search across all memory generations."""
    results = []
    for f in sorted(MEMORY_DIR.glob("memory-gen-*.md")):
        content = f.read_text(encoding="utf-8")
        for i, line in enumerate(content.split("\n"), 1):
            if query.lower() in line.lower():
                results.append({
                    "file": f.name,
                    "line": i,
                    "text": line.strip(),
                })
    return success({"query": query, "matches": results})


def status() -> McpResult:
    """Show current memory status."""
    current = get_current_file()
    lines = count_lines(current) if current.exists() else 0
    return success({
        "current_file": current.name,
        "current_generation": get_current_generation(),
        "lines": lines,
        "max_lines": MEMORY_MAX_LINES,
        "split_threshold": MEMORY_SPLIT_THRESHOLD,
        "needs_new_generation": lines >= MEMORY_SPLIT_THRESHOLD,
    })


# CLI
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python memory.py <command> [args]")
        print("Commands: status, read [gen], append <content> <agent> [section],")
        print("          search <query>, new-gen [summary]")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "status":
        print(status().to_dict())
    elif cmd == "read":
        gen = int(sys.argv[2]) if len(sys.argv) > 2 else None
        result = read(gen)
        if result.ok:
            print(result.data["content"])
        else:
            print(result.error)
    elif cmd == "append":
        content = sys.argv[2]
        agent = sys.argv[3] if len(sys.argv) > 3 else "Unknown"
        section = sys.argv[4] if len(sys.argv) > 4 else ""
        print(append(content, agent, section).to_dict())
    elif cmd == "search":
        print(search(sys.argv[2]).to_dict())
    elif cmd == "new-gen":
        print(create_new_generation().to_dict())
    else:
        print(f"Unknown command: {cmd}")
