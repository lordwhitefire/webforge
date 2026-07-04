#!/usr/bin/env python3
"""
Knowledge MCP — Research findings storage + search

Replaces the rigid Odin team (17 agents). Instead of 17 agents
researching 5 areas each, knowledge is added as needed and searched
when relevant.

Industry pattern: Knowledge Base (Confluence, Atlassian)
- Central wiki for standards, decisions, patterns
- Searchable
- Grows organically as the team learns

Files live in: <project>/.webforge/knowledge/
  - standards/   ← best practices (Odin's old job)
  - patterns/    ← code patterns used in this project
  - references/  ← external links, docs
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))
from common import write_log, success, fail, utc_now, McpResult, get_project_root
from memory import session_append


# ── Paths ──
def knowledge_dir() -> Path:
    d = get_project_root() / ".webforge" / "knowledge"
    d.mkdir(parents=True, exist_ok=True)
    return d

def category_dir(category: str) -> Path:
    d = knowledge_dir() / category
    d.mkdir(parents=True, exist_ok=True)
    return d

VALID_CATEGORIES = ["standards", "patterns", "references", "general"]


def info() -> dict:
    return {
        "id": "m-knowledge",
        "name": "Knowledge MCP",
        "tier": 1,
        "owner": "Athena",
        "job": "Store and search research findings. Replaces rigid Odin team with searchable knowledge base.",
    }


# ── Add knowledge ──
def knowledge_add(topic: str, content: str, category: str = "general",
                  source: str = "") -> McpResult:
    """
    Add a research finding to the knowledge base.

    Args:
        topic: Short title (e.g. "Next.js Server Components")
        content: The research content (markdown)
        category: standards, patterns, references, general
        source: URL or reference where this was found
    """
    if category not in VALID_CATEGORIES:
        category = "general"

    # Slugify topic for filename
    slug = "".join(c if c.isalnum() or c == "-" else "-" for c in topic.lower().replace(" ", "-"))
    slug = slug.strip("-")[:50]

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    filename = f"{timestamp}-{slug}.md"
    filepath = category_dir(category) / filename

    file_content = f"""# {topic}

- **Category:** {category}
- **Added:** {utc_now()}
- **Source:** {source or "(none)"}

## Content

{content}

---
*Added via WebForge Knowledge MCP*
"""

    filepath.write_text(file_content, encoding="utf-8")

    session_append(f"KNOWLEDGE ADDED — [{category}] {topic}", agent="Athena", kind="note")
    write_log("Knowledge", "Athena", "knowledge_add",
              {"topic": topic, "category": category, "file": filepath.name})

    return success({
        "file": filepath.name,
        "category": category,
        "topic": topic,
        "message": f"Knowledge added: [{category}] {topic} → {filepath.name}",
    })


# ── Search knowledge ──
def knowledge_search(query: str) -> McpResult:
    """Search the knowledge base for a query."""
    results = []
    query_lower = query.lower()

    for category in VALID_CATEGORIES:
        cat_dir = knowledge_dir() / category
        if not cat_dir.exists():
            continue

        for f in cat_dir.glob("*.md"):
            content = f.read_text(encoding="utf-8")
            # Search in title and content
            if query_lower in content.lower():
                # Extract title (first line)
                title = content.split("\n")[0].lstrip("# ").strip()
                # Extract first 200 chars of content as preview
                preview_match = content.split("## Content")
                preview = preview_match[1].strip()[:200] if len(preview_match) > 1 else ""
                results.append({
                    "file": f.name,
                    "category": category,
                    "title": title,
                    "preview": preview,
                    "path": str(f),
                })

    return success({"query": query, "results": results, "count": len(results)})


# ── List all knowledge ──
def knowledge_list(category: str = "all") -> McpResult:
    """List all knowledge entries."""
    entries = []

    categories = [category] if category != "all" else VALID_CATEGORIES
    for cat in categories:
        cat_dir = knowledge_dir() / cat
        if not cat_dir.exists():
            continue
        for f in sorted(cat_dir.glob("*.md")):
            content = f.read_text(encoding="utf-8")
            title = content.split("\n")[0].lstrip("# ").strip()
            entries.append({
                "file": f.name,
                "category": cat,
                "title": title,
            })

    return success({"entries": entries, "count": len(entries)})


# ── Read a specific knowledge entry ──
def knowledge_read(filepath: str) -> McpResult:
    """Read a specific knowledge entry."""
    p = Path(filepath)
    if not p.exists():
        return fail(f"File not found: {filepath}")
    content = p.read_text(encoding="utf-8")
    return success({"content": content, "file": p.name})


# ── CLI ──
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Knowledge MCP — Research findings storage + search")
        print("Usage: python knowledge.py <command> [args]")
        print()
        print("Commands:")
        print("  add <topic> | <content> [category] [source]  Add knowledge")
        print("  search <query>                              Search knowledge")
        print("  list [category]                             List all entries")
        print("  read <filepath>                             Read an entry")
        print()
        print("Categories: standards, patterns, references, general")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "info":
        print(json.dumps(info(), indent=2))
    elif cmd == "add":
        # Format: add <topic> | <content> [category] [source]
        raw = sys.argv[2] if len(sys.argv) > 2 else ""
        parts = raw.split("|")
        if len(parts) >= 2:
            topic = parts[0].strip()
            content = parts[1].strip()
            category = parts[2].strip() if len(parts) > 2 else "general"
            source = parts[3].strip() if len(parts) > 3 else ""
            result = knowledge_add(topic, content, category, source)
            print(result.data.get("message", result.to_dict()))
        else:
            print("Usage: add <topic> | <content> [category] [source]")
    elif cmd == "search":
        query = sys.argv[2] if len(sys.argv) > 2 else ""
        result = knowledge_search(query)
        if result.ok:
            data = result.data
            print(f"Search: '{query}' — {data['count']} results\n")
            for r in data["results"]:
                print(f"  [{r['category']}] {r['title']}")
                print(f"    File: {r['file']}")
                print(f"    Preview: {r['preview'][:100]}...")
                print()
        else:
            print(result.error)
    elif cmd == "list":
        category = sys.argv[2] if len(sys.argv) > 2 else "all"
        result = knowledge_list(category)
        if result.ok:
            data = result.data
            print(f"Knowledge entries ({data['count']}):\n")
            for e in data["entries"]:
                print(f"  [{e['category']}] {e['title']} ({e['file']})")
        else:
            print(result.error)
    elif cmd == "read":
        result = knowledge_read(sys.argv[2])
        if result.ok:
            print(result.data["content"])
        else:
            print(result.error)
    else:
        print(f"Unknown command: {cmd}")
