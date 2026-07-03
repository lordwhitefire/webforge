# /areas

Show the 88 areas checklist.

## What this command does

Reads `~/webforge/AREAS.md` and shows:
- All 88 areas
- Their status: [D] Decided, [S] Skip, [P] Pending
- Which areas are owned by which agents

## Subcommands

- `/areas` — show all 88 areas
- `/areas <section>` — show areas in a section (A, B, C, D, E, F)
- `/areas <number>` — show details for a specific area (e.g. `/areas 34`)
- `/areas pending` — show only pending areas
- `/areas decided` — show only decided areas

## The 6 Sections

- **A** (01-33): Applies to all projects
- **B** (34-42): E-commerce specific
- **C** (43-64): Web app specific
- **D** (65-72): Mobile/desktop specific
- **E** (73-82): Universal advanced
- **F** (83-88): Modern (NEW — AI, realtime, observability, edge, types, privacy)

## How to use

Type `/areas` to see the full checklist. Use `/areas pending` to see what still needs decisions.

## Example

```
> /areas pending
[CEO] Pending areas (need decisions):
[CEO] 02. Stack Decisions — frontend framework? CSS approach? TypeScript?
[CEO] 14. Environment & Configuration — which vars in dev vs prod?
[CEO] 34. Payment Integration — Paystack or Stripe or both?
[CEO] 49. Multi-tenancy — is this multi-tenant?
[CEO] 83. AI Features — any LLM integration needed?
[CEO] ---
[CEO] 5 of 88 areas pending. Answer these before /build.
```
