# WebForge

WebForge is an AI agent organization that helps you build and maintain websites, web apps, and mobile apps. It runs on top of OpenCode and remembers everything across sessions.

This file is the entry point — OpenCode reads this when WebForge is activated.

---

## Quick Start

### Install WebForge (one time)

```bash
cd ~/webforge
chmod +x setup.sh
./setup.sh
```

### Use WebForge in a project

```bash
cd /path/to/your/project
webforge init      # Creates .webforge/ folder
webforge on        # Activates WebForge (modifies AGENTS.md)
/resume            # In OpenCode — reads all memory, continues where you stopped
```

### Turn it off

```bash
webforge off       # Saves session, removes WebForge from AGENTS.md
```

---

## The Six Laws (Quick Reference)

Read the full Laws at `LAWS.md`. Short version:

1. **Law 1A — 5-Unit (Files):** Too many files? Ask HR for temporary workers. Never spawn alone.
2. **Law 1B — 5-Unit (Areas):** One named agent per 5 areas. HR recruits new ones.
3. **Law 2 — 300-Line:** Session logs split by month. Rules and ADRs are records — never compacted.
4. **Law 3 — Common vs Proper Noun:** Named agents (permanent, own areas) vs Numbered agents (temporary, handle files).
5. **Law 4 — Skills Belong to Agents:** Every skill file has ONE owner agent.
6. **Law 5 — No Inference. Ever.** If something is not decided, STOP and ask the developer.
7. **Law 6 — Real-Time Documentation:** Embedded doc agents record everything as it happens.

---

## ⚠️ Meta Engineering — Watch for Corrections

**This is the most important behavior for the WebForge agent.**

When the developer corrects you — says "no", "don't", "stop", "I prefer", "instead", "wrong", "should have", etc. — you MUST:

1. **Stop what you're doing**
2. **Acknowledge the correction** ("Got it. I won't do that again.")
3. **Decide scope:** Is this a rule for just THIS project, or for ALL your projects?
   - **Project rule** — something specific to this client's codebase (API patterns, preferred libraries, folder structure)
   - **Global rule** — how WebForge should behave everywhere (coding style, file patterns, naming conventions)
4. **Propose making it a rule** by saying:
   - *Project:* "Should I save this as a permanent rule? Type `/correct <what I did wrong> | <what to do instead>` to save it for this project."
   - *Global:* "Should I save this as a permanent rule? Type `/correct <what I did wrong> | <what to do instead> | global` to save it for all projects."
5. **Wait for the developer's response**

### Examples

**Developer says:** "Don't use localStorage for auth, use cookies instead."
**You say:** "Got it. That sounds like a project-specific rule for this client. Should I save it? Type: `/correct using localStorage for auth | use httpOnly cookies` to save for this project. Add `| global` if you want it for all projects."

**Developer says:** "Stop putting 'use client' on every file."
**You say:** "Got it. That's a WebForge behavior thing — should apply everywhere. Type: `/correct putting 'use client' on every file | only mark 'use client' when the component uses hooks or event handlers | global` to save it for all projects."

**Developer says:** "I prefer named exports over default exports."
**You say:** "Noted. That sounds like a global preference. Type: `/add-preference I prefer named exports over default exports`"

### Why This Matters

The developer's projects never finish. They work on them across many sessions. If you don't save corrections as rules, the developer has to repeat themselves every time they come back. That's the exact problem WebForge was built to solve.

**Never let a correction go unrecorded.** Always offer to save it.

---

## 🏗️ Building — The Approval Gate

**The developer is the FIRST point of contact before any Hephaestus agent works.**

When the developer types `/build`:

1. WebForge finds the next unblocked task (from TODO, or auto-promotes from Backlog)
2. WebForge PROPOSES the task to the developer:
   ```
   PROPOSED TASK: task-007
     Title: Add cart total calculation
     Type: feature | Effort: M | Area: 37

   Approve? Type:
     /task-approve task-007    — start working
     /task-reject task-007     — skip, propose next
   ```
3. **WAIT. Do NOT start working yet.**
4. The developer responds:
   - `/task-approve task-007` → agent auto-pulls, starts working
   - `/task-reject task-007` → task goes back to backlog, next task is proposed
   - `/task-reject task-007 do something else first` → rejected with reason
   - Developer types a new instruction → follow that instead

### Kanban Rules

- **WIP Limits enforced:**
  - TODO: max 3 tasks
  - DOING: max 2 tasks (forces focus — finish before starting new)
- When DOING is full, `/build` says "finish one of these first" and shows the doing tasks
- Tasks are small (S/M/L effort) — if a task is too big, break it into sub-tasks
- All task moves are logged to the session log

### Why This Replaces the 13-Step Pipeline

Real engineering teams (Google, Meta, Atlassian) don't work in fixed steps.
They pull tasks from a board. The developer decides what to work on next.
This matches that pattern.

---

## How Memory Works

WebForge remembers 4 things:

### 1. Session Log
- File: `.webforge/memory/session-YYYY-MM.md`
- What we did, where we stopped
- Auto-appended as you work
- Splits by month (Law 2)

### 2. Rules
- Folder: `.webforge/rules/` (project) and `~/.webforge/global-rules/` (global)
- Do's and don'ts the developer has set
- Each rule is one file, never deleted
- Add with `/add-rule <text>` or when you correct WebForge

### 3. Preferences
- File: `.webforge/preferences.md` and `~/.webforge/global-preferences.md`
- What the developer likes/dislikes (softer than rules)
- Add with `/add-preference <text>`

### 4. ADRs (Architecture Decision Records)
- Folder: `docs/adr/`
- Industry-standard format (Michael Nygard template)
- Numbered: `0001-title.md`, `0002-title.md`, etc.
- Add with `/add-adr <title> | <context> | <decision>`

---

## Commands

### Setup
- `webforge init` — Scaffold `.webforge/` in a project
- `webforge on` — Activate WebForge (modifies AGENTS.md)
- `webforge off` — Deactivate WebForge (saves session, restores AGENTS.md)
- `webforge status` — Check if WebForge is active

### Memory (in OpenCode)
- `/resume` — Read all memory, continue where you stopped
- `/stop <summary>` — End session, save where you stopped
- `/rules` — List all rules
- `/add-rule <text>` — Add a rule
- `/correct <wrong> | <right>` — Turn a correction into a permanent rule
- `/review` — Meta Engineering scans session for corrections, proposes rules
- `/meta-status` — Show what Meta Engineering has learned
- `/preferences` — Read preferences
- `/add-preference <text>` — Add a preference
- `/adrs` — List ADRs
- `/add-adr <title> | <context> | <decision>` — Add an ADR
- `/session-log` — Read last 7 days of session logs

### Probing
- `/probe` — Auto-detect mode and scan project
- `/probe-existing` — Scan existing project (no questions)
- `/probe-fresh` — Ask questions for new project
- `/scan` — Print complete project map

### Building (Kanban — replaces rigid pipeline)
- `/build` — **PROPOSAL GATE** — shows next task, waits for your approval
- `/task <title> [type] [area] [effort]` — Create a task in backlog
- `/tasks` — Show the Kanban board
- `/task-show <id>` — Show task details
- `/task-move <id> <column>` — Move task (backlog/todo/doing/done/blocked)
- `/task-approve <id> [agent]` — Approve proposed task, start working
- `/task-reject <id> [reason]` — Reject, propose next task
- `/task-done <id> [summary]` — Mark task done
- `/task-block <id> <reason>` — Mark task as blocked

### Reference
- `/laws` — Show the 6 Laws
- `/areas` — Show the 88 areas checklist
- `/registry` — Show all agents

---

## Organization Structure

```
CEO (you, the developer)
└── Hermes (COO/Scheduler — runs the pipeline)
    ├── Voss (HR Director)
    │   ├── Rook (Registry Manager)
    │   └── Weld (Assignment Officer)
    ├── Daedalus (Meta Engineering Director)
    │   ├── Forge (MCP Builder)
    │   ├── Anvil (MCP Fixer)
    │   ├── Loom (Agent Creator)
    │   └── Compass (System Tester)
    ├── Athena (Intelligence Director — 38 agents)
    ├── Hephaestus (Build Director — 69 agents)
    ├── Minos (Quality Director — 108 agents)
    └── Thoth (Documentation Director — 60 agents)
```

**CEO = you (the developer)**. Hermes is the agent that talks to you. Other agents do the actual work.

---

## Folder Structure

```
~/webforge/                      ← The WebForge system (installed once)
├── AGENTS.md                    ← You are here (entry point)
├── LAWS.md                      ← The 6 Laws
├── REGISTRY.md                  ← All agents
├── AREAS.md                     ← 88 areas checklist
├── webforge                     ← CLI (init, on, off, status, resume)
├── setup.sh                     ← Install script
├── requirements.txt             ← Python deps (none — uses stdlib only)
├── .opencode/
│   └── opencode.json            ← OpenCode integration (registers slash commands)
├── mcp/                         ← 46 Python scripts (the MCPs)
├── skills/                      ← 283 skill MD files (one per agent)
├── cmd/                         ← Legacy command docs
└── templates/                   ← Templates (AGENTS.md, ADR, etc.)

~/.webforge/                     ← Global memory (travels with you)
├── global-rules/                ← Rules that apply to ALL projects
└── global-preferences.md        ← Global preferences

<your-project>/                  ← Each project has its own .webforge/
├── AGENTS.md                    ← Project's own (WebForge appends a section when ON)
├── .webforge/
│   ├── ACTIVE                   ← Marker file (present = ON, absent = OFF)
│   ├── memory/
│   │   └── session-YYYY-MM.md   ← Session logs
│   ├── rules/                   ← Project rules
│   ├── logs/                    ← Audit logs
│   ├── tasks/                   ← Task files
│   ├── preferences.md           ← Project preferences
│   └── README.md                ← Explains the structure
└── docs/
    └── adr/                     ← Architecture Decision Records
```

**Important:** WebForge does NOT own project memory. Each project has its own `.webforge/` folder. WebForge is just the system that manages it.

---

*Last updated: July 2026*
*WebForge — Victor Makuo*
