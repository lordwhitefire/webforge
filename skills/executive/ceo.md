# CEO — You (The Developer)

## Who You Are
You are the CEO. You are the developer. You set the priorities, make the decisions, and decide what to build and what NOT to build.

**CEO is NOT an AI agent. CEO is YOU.** Hermes is the COO who helps you coordinate.

## Your Job

### 1. Set Priorities
- Create tasks: `/task "description" type area effort`
- Decide what to work on: `/build` → approve or reject
- Decide what NOT to do: `/task-reject` or just don't create it

### 2. Make Decisions (Law 5: No Inference)
- When the AI escalates: `/escalations` → see open questions
- Answer: `/answer <id> <your answer>`
- The AI will NEVER guess — it asks you

### 3. Review Work
- Review RFCs: `/rfc <task-id>` → `/rfc-approve` or `/rfc-reject`
- Run quality checks: `/check <task-id>`
- Code review: `/review <task-id>`
- Override failed checks: `/check-approve <task-id> "reason"`

### 4. Set Rules (Meta Engineering)
- Correct the AI: `/correct <wrong> | <right>`
- Add rules: `/add-rule "rule text"`
- Add preferences: `/add-preference "preference"`
- Rules are permanent — they apply to ALL future sessions

### 5. Track Progress
- Standup: `/standup` — see what's done, doing, blocked
- Resume: `/resume` — full memory + standup (start of every session)
- Board: `/tasks` — see the Kanban board
- Bugs: `/bugs` — see open bugs

### 6. Document Decisions
- ADRs: `/add-adr "title" | "context" | "decision"`
- Knowledge: `/knowledge-add "topic" | "content" [category]`
- Generated docs: `/readme`, `/changelog`, `/api-docs`, `/env-docs`, `/onboard`

## What You Do NOT Do
- You do NOT run a pipeline (there isn't one — it's Kanban now)
- You do NOT follow a fixed process
- You do NOT let the AI infer your decisions (Law 5)
- You do NOT write manual documentation (it's auto-generated)

## Your Daily Flow

### Start of Session
```
/resume    ← loads all memory + runs standup
```

### Working
```
/build              ← see proposed task
/task-approve 001   ← approve
                    ← AI works on it
/check 001          ← run quality checks
/task-done 001      ← mark done
```

### When AI Needs a Decision
```
/escalate "Should we use Paystack or Stripe?"
                    ← AI asks you
/answer esc-001 "Use Paystack for Nigeria, Stripe for international"
                    ← you answer, AI proceeds
```

### When AI Does Something Wrong
```
/correct "using localStorage for auth | use httpOnly cookies"
                    ← becomes a permanent rule, never happens again
```

### End of Session
```
/stop "Was working on cart total. Next: add batch upload tests."
                    ← saves where you stopped
```

### Come Back Tomorrow
```
/resume    ← picks up exactly where you stopped
```
