# /audit

Wake the Quality Council to test the build.

## What this command does

1. Wakes Minos (Quality Director).
2. Minos wakes all four teams:
   - Verdict Team — checks if standards were followed.
   - Nemesis Team — runs tests (Pixel=unit, Sentry=review, Scalpel=E2E).
   - Janus Team — checks security and compliance.
   - Pulse Team — fixes bugs found by other teams.
3. All results go to memory.
4. Minos sends a pass/fail report to the CEO.

## How to use

Type `/audit` AFTER:
- Build is complete (`/build`)
- You want to test what was built

## What happens next

- Verdict agents will flag standards violations.
- Nemesis agents will run tests and report failures.
- Janus agents will report security issues.
- Pulse agents will fix bugs automatically (and ask you for decisions per Law 5).
- Minos sends a final pass/fail report.

## If bugs are found

- Pulse team fixes them automatically when possible.
- Pulse team asks you (Law 5) for decisions on complex bugs.
- After fixes, Verdict re-checks the fixed areas.

## Files this command reads

- Code in your project folder
- `~/webforge/AREAS.md` — to know what to test
- `~/webforge/REGISTRY.md` — to find active Quality agents

## Files this command writes

- Test results in `~/webforge/memory/memory-gen-XXX.md`
- Audit log in `~/webforge/logs/audit-YYYY-MM-DD.log`
- Bug reports in `~/webforge/logs/bugs.jsonl`

## Example

```
> /audit
[Minos] Waking Quality Council...
[Verdict-Lance] Checking areas 01-05 against standards...
[Pixel-Sage] Running unit tests for areas 01-05...
[Scalpel-Sage] Running E2E tests for areas 01-05...
[Janus-Sage] Scanning security for areas 01-05...
[Verdict-Lance] FAIL: Area 02 — TypeScript strict mode not enabled.
[Pulse-Sage] Fixing area 02...
[Stamp] Committing fix...
[Verdict-Lance] Re-checking area 02... PASS.
[Minos] All checks complete. Report sent to CEO.
```
