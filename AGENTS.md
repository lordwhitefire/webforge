# WebForge

WebForge is an AI agent organization that builds websites, web apps, and mobile apps. It is run by 290 named agents across 5 departments, governed by 6 Laws, and connected by 46 MCPs (tools).

This file is the entry point. OpenCode reads this first.

---

## Quick Start

When you start a new project in OpenCode:

1. **Read the Laws** → `~/webforge/LAWS.md`
2. **Check the Registry** → `~/webforge/REGISTRY.md`
3. **Review the Areas** → `~/webforge/AREAS.md` (mark each as [D] Decided, [S] Skip, or [P] Pending)
4. **Use slash commands** to invoke agents (see `/cmd` folder)

---

## The Six Laws (Quick Reference)

Read the full Laws at `LAWS.md`. Short version:

1. **Law 1A — 5-Unit (Files):** Too many files? Ask HR for temporary workers. Never spawn alone.
2. **Law 1B — 5-Unit (Areas):** One named agent per 5 areas. HR recruits new ones.
3. **Law 2 — 300-Line:** Memory files split into new generations. Skill files split into smaller files. Records never compact.
4. **Law 3 — Common vs Proper Noun:** Named agents (permanent, own areas) vs Numbered agents (temporary, handle files).
5. **Law 4 — Skills Belong to Agents:** Every skill file has ONE owner agent.
6. **Law 5 — No Inference. Ever.** If something is not decided, STOP and ask the developer.
7. **Law 6 — Real-Time Documentation:** Embedded doc agents record everything as it happens.

---

## Organization Structure

```
CEO (you, the developer)
└── Hermes (COO/Scheduler — runs the pipeline)
    ├── Voss (HR Director)
    │   ├── Rook (Registry Manager)
    │   └── Weld (Assignment Officer)
    ├── Athena (Intelligence Director — 38 agents)
    │   ├── Probe Team (17 agents — assess readiness)
    │   ├── Odin Team (17 agents — research standards)
    │   └── Dorian (UI Researcher)
    ├── Hephaestus (Build Director — 69 agents)
    │   ├── Aurora (Frontend — 22 agents)
    │   ├── Titan (Backend — 22 agents)
    │   └── Zephyr (Database/Infra — 22 agents)
    ├── Minos (Quality Director — 108 agents)
    │   ├── Verdict Team (17 — standards compliance)
    │   ├── Nemesis Team (55 — testing)
    │   ├── Janus Team (18 — security)
    │   └── Pulse Team (18 — bug fixing)
    └── Thoth (Documentation Director — 60 agents)
        ├── Quill Team (5 — core docs)
        ├── Memory Team (3 — project memory)
        └── Embedded Docs (51 — one per area batch per dept)
```

---

## The 46 MCPs (Tools the Agents Use)

MCPs live in `~/webforge/mcp/`. Each is a Python script.

### Tier 1 — Foundation (must exist for anything to work)
| MCP | Owner | What it does |
|---|---|---|
| Pipeline MCP | Hermes | Wakes agents in sequence, passes info |
| Memory MCP | Quill | Read/write memory files, enforce 300-line rule |
| Skill Loader MCP | Hermes | Fetches the right skill files for an agent |
| File System MCP | Everyone | Read/write/delete files |
| Search MCP | Everyone | Search codebase (grep, glob, find) |

### Tier 2 — Core Ops
| MCP | Owner | What it does |
|---|---|---|
| Progress MCP | Hermes | Tracks what's built, crash recovery |
| Registry MCP | Rook | Create/activate/deactivate named agents |
| HR MCP | Voss | Spawn/terminate temporary numbered workers |
| Git MCP | Stamp | Stage, commit, generate commit messages |
| CEO Communication MCP | CEO | Bridge between you and the pipeline |
| Code Execution MCP | Build Team | Run code, scripts, builds |
| Linter MCP | Build Team | Run ESLint, Prettier, type-check |

### Tier 3 — Documentation
| MCP | Owner | What it does |
|---|---|---|
| Real-Time Doc Capture MCP | Embedded Docs | Records agent actions as they happen |
| Changelog MCP | Scroll | Auto-generates changelog from git diffs |
| README MCP | Scroll | Keeps README in sync with project |
| API Documentation MCP | Draft | Generates API docs from code |
| Component Documentation MCP | Draft | Generates component docs (Storybook) |
| Environment Docs MCP | Ledger | Maintains .env.example |
| Audit Log MCP | Janus-Core | Permanent append-only log |

### Tier 4 — Quality & Testing
| MCP | Owner | What it does |
|---|---|---|
| Test Runner MCP | Pixel-Core | Run unit/integration tests |
| E2E Browser MCP | Scalpel-Core | Run Playwright/Cypress tests |
| Test Review MCP | Sentry-Core | Review test coverage |
| Standards Compliance MCP | Verdict Team | Check code against standards |
| Security Scan MCP | Janus-Core | Scan for vulnerabilities |
| Accessibility MCP | Janus-Core | WCAG, ARIA, contrast checks |
| Performance MCP | Verdict Team | Lighthouse, Core Web Vitals |
| Error Monitoring MCP | Pulse-Core | Read Sentry logs |
| Bug Tracker MCP | Pulse-Core | Track bugs found, fixed, reopened |

### Tier 5 — Research & External
| MCP | Owner | What it does |
|---|---|---|
| Standards MCP | Odin Team | Fetch live docs (Vercel, Supabase, Next.js) |
| Web Search MCP | Dorian | Search the internet |
| Image Search MCP | Dorian | Find UI/UX design references |
| SEO MCP | SEO Agent | Generate robots.txt, sitemap.xml, schema.org, llms.txt |

### Tier 6 — Runtime & Infra
| MCP | Owner | What it does |
|---|---|---|
| Database MCP | Zephyr | Migrations, RLS, indexes |
| Deployment MCP | Zephyr | Push to staging/prod, rollback |
| Backup MCP | Zephyr | Database backups, restore |
| Asset Storage MCP | Build Team | Upload to Supabase/S3/Cloudinary |
| Notification MCP | Build Team | Email (Resend), SMS (Termii), push |
| Webhook MCP | Build Team | Send/receive webhooks |
| Analytics MCP | Build Team | Posthog, GA4 |
| Auth MCP | Build Team | Auth flows, sessions, roles |
| Cache MCP | Build Team | Redis, browser cache |
| Rate Limit MCP | Build Team | Upstash, throttling, bot protection |

### Tier 7 — Specialized
| MCP | Owner | What it does |
|---|---|---|
| Payment MCP | Build Team | Paystack, Stripe, refunds |
| Form MCP | Build Team | Form handling, validation, uploads |
| i18n MCP | Build Team | Translations, locale formatting |
| Feature Flag MCP | Build Team | Toggle features without deploying |

---

## Slash Commands (for OpenCode)

Slash commands live in `~/webforge/cmd/`. Use them in OpenCode to invoke agents.

| Command | What it does |
|---|---|
| `/probe` | Wake the Probe team to assess a project |
| `/odin` | Wake the Odin team to research standards |
| `/build` | Wake the Build team to start building |
| `/audit` | Wake the Quality Council to test |
| `/fix` | Wake the Pulse team to fix bugs |
| `/hr` | Talk to HR (Voss, Rook, Weld) |
| `/memory` | Read or write to memory files |
| `/progress` | Show current build progress |
| `/laws` | Show the 6 Laws |
| `/registry` | Show the Agent Registry |
| `/areas` | Show the 88 areas checklist |
| `/pipeline` | Show the current pipeline state |

---

## Folder Structure

```
~/webforge/                      ← The SYSTEM (not project data)
├── AGENTS.md                    ← Entry point
├── LAWS.md                      ← The 6 Laws
├── REGISTRY.md                  ← All 295 agents (290 + 5 Meta)
├── AREAS.md                     ← 88 areas checklist
├── README.md                    ← Quick start
├── system-memory/               ← Meta department's memory (about WebForge itself)
├── skills/                      ← Skill MD files (one per agent)
│   ├── executive/               ← CEO, Hermes
│   ├── hr/                      ← Voss, Rook, Weld
│   ├── intelligence/            ← Athena, Probe-*, Odin-*, Dorian
│   ├── build/                   ← Hephaestus, Aurora, Titan, Zephyr, leads, seniors, juniors
│   ├── quality/                 ← Minos, Verdict-*, Nemesis leads, Janus-*, Pulse-*
│   ├── documentation/           ← Thoth, Quill, Scroll, Stamp, Ledger, Draft, Memory-*, Doc-*
│   └── meta/                    ← Daedalus, Forge, Anvil, Loom, Compass
├── mcp/                         ← 46 Python scripts (the MCPs)
├── cmd/                         ← Slash commands for OpenCode
└── scripts/                     ← Helper scripts

~/your-project/                  ← THE PROJECT (owns its own data)
├── memory/                      ← Project memory (gen-001, gen-002, ...)
├── .webforge/
│   ├── logs/                    ← Audit logs, bug reports
│   ├── pipeline-state.json      ← Current pipeline state
│   └── active-workers.json      ← Active temporary workers (Law 1A)
└── (your project files)
```

**Important:** WebForge does NOT own project memory. Each project has its own `memory/` folder. WebForge is just the system that manages it.

---

## How to Use WebForge in OpenCode

1. **Open your project** in OpenCode.
2. **Create a symlink or copy** `~/webforge/AGENTS.md` to your project root, OR set `~/webforge` as your OpenCode working directory.
3. **Use slash commands** like `/probe`, `/build`, `/audit` to wake agents.
4. **When an agent asks you a question** (per Law 5), answer directly in chat. The CEO Communication MCP routes your answer back to the agent.
5. **Memory updates automatically** as agents work — read `~/webforge/memory/memory-gen-001.md` any time to see project state.

---

## Important Notes

- **No agent infers anything.** If something is not decided, the agent stops and asks you. (Law 5)
- **Nothing happens without HR knowing.** Temporary agents are tracked by HR and terminated when done. (Law 1A)
- **Memory files split at 300 lines.** A new generation file is created with a 20-30 line summary of the old one. (Law 2)
- **Skill files split at 300 lines too.** But they are never summarized — they are split into smaller files. (Law 2)
- **Documentation happens in real time.** Every department has embedded doc agents recording as work happens. (Law 6)

---

*Last updated: July 2026*
*WebForge — Victor Makuo*
