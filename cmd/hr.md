# /hr

Talk to the HR Department.

## What this command does

Opens a direct line to Voss (HR Director), Rook (Registry Manager), and Weld (Assignment Officer).

## Subcommands

- `/hr status` — show all active and inactive agents
- `/hr recruit <name> <areas>` — recruit a new named agent (Law 1B)
- `/hr spawn <count>` — spawn temporary workers (Law 1A)
- `/hr terminate <worker-id>` — terminate a temporary worker
- `/hr deactivate <name>` — mark a named agent inactive

## How to use

You usually don't call `/hr` directly. Agents call HR through the HR MCP when they need workers.

But you can use `/hr status` to see who's active, or `/hr recruit` to add a new agent for new areas.

## Law 1A — 5-Unit Law (Files)

If an agent has more than 5 files:
1. Agent tells HR.
2. HR creates temporary workers (Worker-1, Worker-2, ...).
3. Each handles at most 5 files.
4. When done, HR terminates them.

## Law 1B — 5-Unit Law (Areas)

One named agent per 5 areas. If you add new areas (e.g. areas 89-93):
1. Department tells HR.
2. HR (Rook) checks the registry.
3. If an agent for those areas exists, reactivate.
4. If not, create a new named agent.

## Example

```
> /hr status
[Voss] Active agents: 280
[Voss] Inactive agents: 0
[Voss] Temporary workers: 0

> /hr recruit Probe-Stream 89-93
[Voss] Checking registry...
[Rook] No existing agent for areas 89-93.
[Rook] Creating Probe-Stream...
[Weld] Assigned to Intelligence department.
[Voss] Done. Probe-Stream is now Active.
```
