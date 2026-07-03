# /build

Wake the Build Team to start building.

## What this command does

1. Wakes Hephaestus (Build Director).
2. Hephaestus wakes Aurora (Frontend), Titan (Backend), Zephyr (Database/Infra).
3. Each sub-head wakes their Tech Lead.
4. Tech Leads wake Senior Developers.
5. Senior Developers wake Junior Developers.
6. Each Junior builds their assigned 5 areas.
7. Stamp commits each completed area via Git MCP.

## How to use

Type `/build` AFTER:
- The Probe team has finished (`/probe`)
- The Odin team has finished (`/odin`)
- The CEO has approved the Intelligence phase

## What happens next

- Junior Developers will ask you questions (Law 5) about anything not decided.
- Each commit is automatic (Stamp handles it).
- Progress is tracked in real time by the Progress MCP.
- Memory is updated in real time by embedded doc agents.

## Files this command reads

- `~/webforge/AREAS.md` — to know what to build
- `~/webforge/memory/memory-gen-XXX.md` — to read Intelligence findings
- `~/webforge/REGISTRY.md` — to find active Build agents

## Files this command writes

- Code in your project folder
- `~/webforge/memory/memory-gen-XXX.md` — what was built
- `~/webforge/logs/audit-YYYY-MM-DD.log` — all actions logged

## If a Junior has too many files

Per Law 1A, the Junior tells their Senior, who tells HR (Voss).
Voss creates temporary numbered workers (Worker-1, Worker-2, ...).
Each worker handles at most 5 files.
When done, Voss terminates the workers.

## Example

```
> /build
[Hephaestus] Waking Build Team...
[Aurora] Waking Frontend sub-department...
[Lead-Faro] Waking Senior Developers...
[Sr-Hale] Waking Junior Developers...
[Jr-Hawk] Building areas 01-05...
[Jr-Hawk] Question: Which CSS framework? (Tailwind / CSS Modules / other)
> Tailwind
[Jr-Hawk] Recorded. Building...
[Stamp] Committing area 01...
[Jr-Hawk] Done. Reporting to Sr-Hale.
...
```
