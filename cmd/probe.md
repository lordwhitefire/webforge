# /probe

Wake the Probe Team to assess a project's readiness.

## What this command does

1. Wakes Athena (Intelligence Director).
2. Athena wakes all 17 Probe agents (Probe-Orion through Probe-Lyric).
3. Each Probe agent checks their assigned 5 areas.
4. Each writes findings to memory.
5. Athena sends a summary to the CEO.

## How to use

Type `/probe` in OpenCode when you want to start assessing a new project.

## What happens next

- Probe agents will ask you questions (per Law 5) about anything not decided.
- Answer the questions in chat.
- The CEO Communication MCP routes your answers back to the agents.
- When all 17 Probe agents finish, Athena sends a readiness report.

## Files this command reads

- `~/webforge/AREAS.md` — the 88 areas checklist
- `~/webforge/REGISTRY.md` — to find active Probe agents

## Files this command writes

- `~/webforge/memory/memory-gen-XXX.md` — findings go into memory
- `~/webforge/logs/audit-YYYY-MM-DD.log` — all actions logged

## Example

```
> /probe
[Athena] Waking Probe Team...
[Probe-Orion] Reading areas 01-05...
[Probe-Orion] Question for developer: What is the project name?
> My Project
[Probe-Orion] Recorded. Continuing...
[Probe-Wren] Reading areas 06-10...
...
[Athena] All 17 Probe agents done. Summary sent to CEO.
```
