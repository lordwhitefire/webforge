# WebForge

An AI agent organization that builds websites, web apps, and mobile apps.

## What's Inside

- **290 named agents** across 5 departments (Executive, HR, Intelligence, Build, Quality, Documentation)
- **6 Laws** that govern how every agent behaves
- **46 MCPs** (tools) that agents call to do their work
- **88 areas** that every project must consider
- **Slash commands** for OpenCode integration

## Quick Start

1. Read `AGENTS.md` — the entry point
2. Read `LAWS.md` — the rules every agent follows
3. Read `REGISTRY.md` — all named agents
4. Read `AREAS.md` — the 88-area project checklist
5. Use slash commands in `cmd/` to invoke agents from OpenCode

## Folder Structure

```
~/webforge/
├── AGENTS.md       ← Start here
├── LAWS.md         ← The 6 Laws
├── REGISTRY.md     ← All 290 agents
├── AREAS.md        ← 88-area checklist
├── README.md       ← This file
├── memory/         ← Project memory (gen-001, gen-002, ...)
├── skills/         ← Skill MD files (one per agent)
├── mcp/            ← 46 Python scripts (the MCPs)
├── cmd/            ← Slash commands for OpenCode
├── scripts/        ← Helper scripts
└── logs/           ← Audit logs, session logs
```

## Using in OpenCode

1. Open your project in OpenCode.
2. Symlink `~/webforge/AGENTS.md` to your project root:
   ```bash
   ln -s ~/webforge/AGENTS.md /path/to/your/project/AGENTS.md
   ```
3. Use slash commands like `/probe`, `/build`, `/audit` to wake agents.
4. Answer questions when agents ask (per Law 5).

## The Six Laws (Quick Reference)

1. **5-Unit (Files)** — Too many files? Ask HR for temporary workers.
2. **5-Unit (Areas)** — One named agent per 5 areas.
3. **300-Line** — Memory files split into generations. Skill files split into smaller files. Records never compact.
4. **Common vs Proper Noun** — Named agents (permanent) vs Numbered agents (temporary).
5. **No Inference. Ever.** — If not decided, stop and ask.
6. **Real-Time Documentation** — Doc agents record everything as it happens.

## Authors

- **Victor Makuo** — system design
- **WebForge** — built July 2026
