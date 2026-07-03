# /memory

Read or write to memory files.

## What this command does

Manages the project memory files in `~/webforge/memory/`.

## Subcommands

- `/memory status` — show current memory file size, generation, line count
- `/memory read` — read the current memory generation
- `/memory read <gen>` — read a specific generation (e.g. `/memory read 2`)
- `/memory search <query>` — search across all memory generations
- `/memory new-gen` — force create a new generation (Law 2)

## How to use

Memory updates automatically as agents work. You don't usually need to write to it manually.

But you can read it any time to see project state, decisions log, pending questions, build progress, and active agents.

## Law 2 — 300-Line Rule

- When a memory file reaches 300 lines, a new generation is created.
- The new file starts with a 20-30 line summary of the previous generation.
- The Memory MCP triggers this automatically at 80% (240 lines).
- You can force it with `/memory new-gen`.

## Example

```
> /memory status
[Quill] Current file: memory-gen-001.md
[Quill] Lines: 156 / 300
[Quill] At 52% capacity. No new generation needed.

> /memory read
[memory-gen-001.md contents displayed]

> /memory search "Payment Integration"
[Quill] Found 3 matches:
  - memory-gen-001.md:45 — "Payment Integration decided: Paystack"
  - memory-gen-001.md:78 — "Probe-Marsh: Paystack webhook setup needed"
  - memory-gen-001.md:120 — "Jr-Copper: Built Paystack integration"
```
