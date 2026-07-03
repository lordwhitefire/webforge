# /progress

Show what has been built and what hasn't.

## What this command does

Calls the Progress MCP and shows:
- How many of the 88 areas are done
- How many are in progress
- How many are not started
- Which agents are currently working
- Last checkpoint (for crash recovery)

## How to use

Type `/progress` any time to see where the build stands.

## Crash Recovery

If your session crashes:
1. Open OpenCode again.
2. Type `/progress`.
3. Hermes reads the Progress MCP and resumes from the last checkpoint.
4. Nothing is lost.

## Example

```
> /progress
[Hermes] Build Progress:
[Hermes] Done: 45 / 88 areas (51%)
[Hermes] In progress: 3 areas
[Hermes] Not started: 40 areas
[Hermes] ---
[Hermes] Currently working:
  - Jr-Hawk (areas 01-05) — area 03 in progress
  - Jr-Granite (areas 01-05) — area 02 in progress
  - Jr-Sky (areas 01-05) — area 01 in progress
[Hermes] ---
[Hermes] Last checkpoint: 2026-07-02 14:23:01 UTC
[Hermes] Session is resumable.
```
