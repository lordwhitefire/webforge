# /registry

Show the Agent Registry.

## What this command does

Reads `~/webforge/REGISTRY.md` and shows:
- Total active agents
- Total inactive agents
- Agents by department
- Status of each agent

## Subcommands

- `/registry` — show summary
- `/registry <department>` — show agents in a department (executive, hr, intelligence, build, quality, documentation)
- `/registry <agent-name>` — show details for a specific agent
- `/registry active` — show only active agents
- `/registry inactive` — show only inactive agents

## How to use

Type `/registry` to see everyone. Type `/registry build` to see just the Build team.

## Law 1B — Registry Rules

- Only HR (Rook) can modify the registry.
- Names are never deleted — only marked inactive.
- The registry is the single source of truth for who exists.

## Example

```
> /registry
[Rook] WebForge Agent Registry:
[Rook] Executive: 2 active
[Rook] HR: 3 active
[Rook] Intelligence: 38 active
[Rook] Build: 69 active
[Rook] Quality Council: 108 active
[Rook] Documentation: 60 active
[Rook] ---
[Rook] Total: 280 active, 0 inactive

> /registry Probe-Orion
[Rook] Agent: Probe-Orion
[Rook] Department: Intelligence
[Rook] Role: Probe Agent
[Rook] Areas: 01-05
[Rook] Status: Active
[Rook] Reports to: Athena
[Rook] Skill file: ~/webforge/skills/intelligence/probe-orion.md
```
