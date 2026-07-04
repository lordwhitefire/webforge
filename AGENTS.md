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

### 📋 RFC — Design Review for One-Way Doors (Amazon pattern)

Not every task needs a design document. WebForge uses Amazon's "two-way door" rule:

- **One-way door** (irreversible) → RFC required before coding
  - Task types: `feature`, `refactor`, `architecture`
  - Effort: `L`
- **Two-way door** (easily reversible) → skip RFC, just code
  - Task types: `bugfix`, `test`, `docs`
  - Effort: `S`, `M`

**How it works:**

1. `/task-approve task-001` — you approve the task
2. If it's a one-way door → WebForge **auto-generates an RFC**
3. The RFC includes: summary, motivation, design, alternatives, risks, rules, ADRs
4. WebForge says: "⚠️ RFC REQUIRED. Review: /rfc task-001"
5. **Coding is BLOCKED until you approve the RFC**
6. `/rfc task-001` — you review the design
7. `/rfc-approve task-001` — unlock coding
   OR
   `/rfc-reject task-001 "use server-side instead"` — send back

**Why:** Big tech (Uber, Amazon, Rust, Meta) all use RFCs. They catch design
mistakes BEFORE code is written. Cheaper to fix a design on paper than in code.

### 📚 Knowledge Base (replaces rigid Odin team)

The old design had 17 Odin agents each researching 5 areas. That's not how
real teams work. Instead, knowledge is added **as needed** and **searched**
when relevant.

- `/knowledge-add "Next.js Server Components" | "Use by default..." standards`
- `/knowledge "server components"` — search when working on a related task

Categories: `standards`, `patterns`, `references`, `general`

### 🔍 Quality — Continuous, Not a Phase (Minos)

Quality is NOT a post-build audit. It's **continuous** — it happens DURING
and AFTER coding, not in a separate phase.

**The Quality Gate:**

When you type `/task-done`, WebForge automatically runs:
1. **Lint** (ESLint) — code style
2. **Type check** (tsc --noEmit) — TypeScript correctness
3. **Tests** (vitest/jest) — unit + integration
4. **Build** (next build) — does it compile?
5. **Security** (npm audit) — known vulnerabilities

If any check fails → **task-done is BLOCKED** (strict by default).

**Your options when checks fail:**
- Fix the issues, re-run `/check <task-id>`, then `/task-done`
- Override: `/check-approve <task-id> "I know about the warning"` (you're the boss)

**Bug Tracking (replaces Pulse team):**
- `/bug "cart shows NaN when quantity is 0" high` → creates bugfix task
- Bugs are two-way doors → no RFC needed → fast fix
- When fixed, write a regression test so it never comes back

**Code Review (Google/Meta pattern):**
- `/review <task-id>` → generates a checklist:
  - PR size (should be < 400 lines — Meta standard)
  - Test coverage (tests written?)
  - RFC compliance (code follows approved design?)
  - Project rules compliance
  - General checks (no console.log, error handling, etc.)

**Industry patterns used:**
- Testing Pyramid (Martin Fowler): unit > integration > e2e
- Shift Left: test during coding, not after
- CI/CD: lint → type-check → test → build → security
- Code Review: no merge without review (Google Engineering Practices)

### 📝 Documentation — Docs as Code (Thoth)

Documentation is NOT manually written. It's **generated from the project**
and reviewed before merging (Google's "Docs as Code" pattern).

**5 types of generated docs:**

1. **README** (`/readme`) — project overview, stack, scripts, structure, ADRs, rules
   Auto-detected from package.json, file scan, ADRs, and rules.

2. **Changelog** (`/changelog`) — from git history using Keep a Changelog format
   Categorizes commits: Added, Changed, Deprecated, Removed, Fixed, Security

3. **API Docs** (`/api-docs`) — from scanning `src/app/api/**/route.ts`
   Lists all routes with HTTP methods and JSDoc descriptions

4. **Env Docs** (`/env-docs`) — from scanning `.env.example`
   Documents each variable: required, public, description

5. **Onboarding** (`/onboard`) — pulls from ALL sources
   Quick start, stack, ADRs, rules, current tasks, recent commits, WebForge commands

**Where generated docs go:**
- `.webforge/docs/` (not tracked by git — you review and merge manually)
- Generate all at once: `/docs`

**What's already handled (not by Thoth):**
- Session logs → Memory MCP (real-time, Law 6)
- Architecture decisions → ADRs
- Rules/corrections → Rules system
- Research findings → Knowledge base

### 🏢 Executive — Hermes (COO) + CEO (You)

**CEO = you (the developer). Always.** You set priorities, make decisions, decide what to build and what NOT to build.

**Hermes = COO.** Coordinates work, tracks progress, surfaces blockers, escalates decisions to you.

**⚠️ CRITICAL: Hermes does NOT do the work.** Hermes is the bridge between you and the departments. When you talk to Hermes:
- Hermes LISTENS
- Hermes CREATES a task and ROUTES it to the right department
- Hermes does NOT write code, fix bugs, or build features
- That's Hephaestus's job (Build), Minos's job (Quality), Athena's job (Intelligence), etc.

**Routing table:**
| You tell Hermes... | Hermes creates... | Routes to... |
|---|---|---|
| "Add a feature" | task (feature) | @Hephaestus via /build |
| "There's a bug" | task (bugfix) | @Hephaestus via /build |
| "Research this" | knowledge entry | @Athena |
| "Document this" | doc generation | @Thoth |
| "WebForge has a bug" | task (bugfix) | @Daedalus (Meta Engineering) |
| "I need a decision" | escalation | You (CEO) answer via /answer |

**The 13-step rigid pipeline is RETIRED.** Replaced by:
- Kanban board (task.py) — for tracking what to work on
- Standup — for tracking status and blockers
- Approval gate (/build) — for deciding what to do next
- Escalation (/escalate) — for when the AI needs your decision

**Daily Flow:**
```
/resume     ← Load memory + run standup (one command, start of every session)
/build      ← See proposed task, approve or reject
            ← AI works
/check      ← Run quality checks
/task-done  ← Mark done (blocked if checks fail)
/stop       ← Save where you stopped, end session
```

**When AI needs a decision (Law 5: No Inference):**
```
/escalate "Should we use Paystack or Stripe?"
/answer esc-001 "Use Paystack for Nigeria, Stripe for international"
```

**When AI does something wrong:**
```
/correct "using localStorage for auth | use httpOnly cookies"
→ becomes a permanent rule, never happens again
```

### 💬 Talking to Agents Directly (@mentions)

**Industry pattern: @mentions (Slack, GitHub, Discord)**

You can talk to any agent directly. The AI reads that agent's skill file
and responds as that agent.

**Method 1: /talk command**
```
/talk Hermes what should I work on next?
/talk Hephaestus why is task-003 blocked?
/talk Minos run a security scan
/talk Daedalus the memory MCP has a bug
/talk Athena research best practices for Supabase RLS
```

**Method 2: @mention in your message**
```
@Hermes what's the status of the board?
@Minos what's the test coverage?
@Thoth generate the README
```

**How it works (LLM instruction):**
When you type @AgentName or /talk AgentName:
1. WebForge looks up the agent in the skills/ folder
2. The LLM reads that agent's skill file
3. The LLM adopts that agent's persona and capabilities
4. The LLM responds as that agent would
5. **If you ask the agent to DO something (correction, rule, task, etc.), the agent:**
   - **Explains** what they understood in simple terms
   - **Suggests** alternatives if there's a better way
   - **Waits** for your approval
   - **Then executes** the command via bash
6. The conversation is logged to the session log

**Available agents:**
- Type `/agents` to see the full list
- Key agents: @Hermes (COO), @Hephaestus (Build), @Athena (Intelligence),
  @Minos (Quality), @Thoth (Docs), @Daedalus (Meta Engineering),
  @Voss (HR), @Dorian (UI Research)

### 📬 Notifications — The Phone System

**Problem solved:** Nobody gets a ping when something happens.

**How it works now:**
Every task event automatically sends a notification to the relevant agent's inbox:

| Event | Who gets notified |
|---|---|
| Task created | Department director (e.g. @Hephaestus for build tasks) |
| Task assigned | The agent who was assigned |
| Task done | Developer (you) + @Minos (Quality — review needed) |
| Task blocked | @Hermes (COO) + Developer (you) |

**Commands:**
- `/notifications` — show ALL unread notifications across all agents
- `/inbox <agent-name>` — show one agent's inbox
- `/read-notifications <agent-name>` — mark their notifications as read

**Where notifications show up:**
- `/standup` — includes a "📬 NOTIFICATIONS" section showing all unread
- `/resume` — runs standup at the end, so you see notifications automatically
- `/inbox <agent-name>` — check a specific agent's inbox

**The notification chain (solves all 3 breakdowns):**
```
1. Hermes creates task → 📝 notifies @Hephaestus "new task on the board"
2. /task-approve → 📤 notifies assigned agent "task assigned to you"
3. /task-done → ✅ notifies Developer + @Minos "task done, review needed"
4. /task-block → 🚫 notifies @Hermes + Developer "task blocked, needs attention"
```

Nobody is left in the dark. Every event pings the right people.

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

### Design Review (RFC — for one-way door tasks)
- `/rfc <task-id>` — Show the RFC (design proposal) for a task
- `/rfc-approve <task-id>` — Approve the RFC, unlock coding
- `/rfc-reject <task-id> [reason]` — Reject RFC, send back to backlog
- `/rfcs` — List all RFCs

### Knowledge Base (replaces rigid Odin team)
- `/knowledge <query>` — Search the knowledge base
- `/knowledge-add <topic> | <content> [category]` — Add a research finding
- `/knowledge-list [category]` — List all knowledge entries

### Quality (replaces rigid 108-agent audit)
- `/check [task-id]` — Run quality checks (lint, type-check, tests, build, security)
- `/check-approve <task-id> [reason]` — Override failed checks (you're the boss)
- `/bug <description> [severity]` — Report a bug (creates bugfix task)
- `/bugs` — List all open bugs
- `/review <task-id>` — Generate code review checklist

### Dispatch & Routing (Chain of Command)
- `/dispatch <task-id>` — Show routing status for a task (who it went to, who has it now)
- `/dispatch-route <task-id>` — Route a task to its department head (auto-detected from task type)
- `/dispatch-down <task-id> <agent>` — Route a task DOWN to a specific agent (e.g., head → senior → junior)
- `/dispatch-up <task-id> <from-agent>` — Route results UP the chain (junior → senior → head → CEO)
- `/dispatch-chain [agent]` — Show chain of command for an agent or full org chart
- `/dispatch-pending` — Show all tasks that haven't been routed yet

**Auto-routing:** When a task is created with `/task`, it's automatically dispatched to the right department head:
- feature/bugfix/refactor → @Hephaestus (Build)
- research/architecture → @Athena (Intelligence)
- test/security → @Minos (Quality)
- docs/content → @Thoth (Documentation)

### Notifications (The Phone System)
- `/notifications` — Show all unread notifications across all agents
- `/inbox <agent-name>` — Show one agent's inbox
- `/read-notifications <agent-name>` — Mark notifications as read

### Documentation (Docs as Code — replaces 60-agent Thoth)
- `/readme` — Generate README from project state → `.webforge/docs/`
- `/changelog` — Generate changelog from git history (Keep a Changelog format)
- `/api-docs` — Generate API documentation from route files
- `/env-docs` — Document environment variables from .env.example
- `/onboard` — Generate onboarding doc (pulls from ALL sources)
- `/docs` — Generate ALL 5 at once

### Executive (Hermes + CEO)
- `/resume` — Load all memory + run standup automatically (start of every session)
- `/standup` — Daily sync: what we did, what we're doing, what's blocked
- `/escalate <question>` — AI asks you a question (Law 5: No Inference)
- `/answer <id> <answer>` — You answer an escalation
- `/escalations` — List open escalations (questions waiting for you)

### Agent Communication
- `/agents` — List all available agents you can talk to
- `/talk <agent-name> <message>` — Talk directly to a specific agent
- `@AgentName` in your message — Mention an agent inline (LLM adopts their persona)
- `/notifications` — Show all unread notifications (the phone system)
- `/inbox <agent-name>` — Show an agent's notification inbox
- `/read-notifications <agent-name>` — Mark an agent's notifications as read

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
