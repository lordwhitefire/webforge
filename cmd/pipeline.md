# /pipeline

Show the current pipeline state.

## What this command does

Calls the Pipeline MCP and shows:
- Current step in the pipeline
- What has been completed
- What's running now
- What's next
- Any paused questions waiting for the developer

## How to use

Type `/pipeline` any time to see where the project is.

## The Pipeline Order

```
1. intelligence.probe       — Probe team assesses
2. intelligence.odin        — Odin team researches standards
3. intelligence.dorian      — Dorian does UI research
4. ceo.review_intelligence  — CEO reviews with developer
5. build.frontend           — Aurora's team builds UI
6. build.backend            — Titan's team builds server
7. build.database           — Zephyr's team builds DB/infra
8. quality.verdict          — Verdict checks standards
9. quality.nemesis          — Nemesis runs tests
10. quality.janus           — Janus checks security
11. quality.pulse           — Pulse fixes bugs
12. ceo.final_review        — CEO final review
13. documentation.finalize  — Docs finalize
```

## Example

```
> /pipeline
[Hermes] Pipeline Status: running:build.frontend
[Hermes] Current step: 5 of 13 (build.frontend)
[Hermes] Completed: intelligence.probe, intelligence.odin, intelligence.dorian, ceo.review_intelligence
[Hermes] Running: Aurora's Frontend team (Jr-Hawk working on areas 01-05)
[Hermes] Next: build.backend (Titan's team)
[Hermes] No pending questions.
```

## If paused

```
> /pipeline
[Hermes] Pipeline Status: paused_for_developer
[Hermes] Question from Jr-Hawk:
  "Which CSS framework? (Tailwind / CSS Modules / other)"
[Hermes] Type your answer to resume:
> Tailwind
[Hermes] Resumed. Answer routed to Jr-Hawk.
```
