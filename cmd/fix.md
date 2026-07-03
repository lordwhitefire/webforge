# /fix

Wake the Pulse team to fix bugs.

## What this command does

1. Wakes Pulse-Core (Bug Fixer Lead).
2. Pulse-Core wakes the 17 Pulse batch agents.
3. Each Pulse agent checks error logs for their 5 areas.
4. Bugs found get fixed.
5. Fixes are committed via the Git MCP (Stamp).

## How to use

Type `/fix` when:
- The audit (`/audit`) found bugs
- Production errors are reported
- You want a fresh check of error logs

## What happens next

- Pulse agents read error logs (Sentry, console, server logs).
- For each bug, they:
  - Identify the root cause
  - Fix it (or ask you per Law 5 if the fix is complex)
  - Commit the fix
  - Update memory
- Pulse-Core sends a summary to Minos.

## If a bug needs a decision

Per Law 5, the Pulse agent stops and asks you. Example:

```
[Pulse-Sage] Found bug in area 03: form validation failing on Safari.
[Pulse-Sage] Question: Should I add a Safari-specific polyfill, or rewrite the validation logic?
> Add polyfill
[Pulse-Sage] Adding polyfill...
[Stamp] Committing fix...
```

## Files this command reads

- `~/webforge/logs/bugs.jsonl` — bug reports
- Production error logs (via Error Monitoring MCP)

## Files this command writes

- Code fixes in your project folder
- `~/webforge/memory/memory-gen-XXX.md` — what was fixed
- `~/webforge/logs/audit-YYYY-MM-DD.log` — all actions logged
