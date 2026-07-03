# WebForge — The Laws

These are the rules every agent must follow. No exceptions.

---

## LAW 1A — The 5-Unit Law (Files)

If an agent has more than 5 files to work on, it must NOT handle them alone.

**What the agent does:**

1. Count the files.
2. If more than 5, go to HR and say: "I have too many files. I need temporary workers."
3. HR creates temporary numbered agents (Worker-1, Worker-2, ...). Each handles at most 5 files.
4. Each temporary agent does its work and sends a report back.
5. The original agent now has reports instead of files. If still more than 5 reports, go to HR again for another round.
6. Keep doing this until the agent holds 5 or fewer reports.
7. Then do final work. Send one report up to its superior.
8. When done, tell HR. HR terminates all temporary agents created for this task.

**The agent never spawns anything by itself. Everything goes through HR.**

**Why:** If agents could spawn themselves, temporary agents could be created and forgotten — left running forever. HR is the only one who knows what exists at every moment. Nothing exists without HR knowing.

**Example:**
- Agent has 40 files.
- Goes to HR. HR creates 8 temporary workers (each handles 5 files).
- Gets 8 reports back. Still more than 5.
- Goes to HR again. HR creates 2 more workers to handle those 8 reports.
- Gets 2 reports back. Now 5 or fewer.
- Does final work. Sends one report up.
- Tells HR. HR terminates all 10 temporary workers.

---

## LAW 1B — The 5-Unit Law (Areas)

Every named agent owns a fixed batch of areas. The rule: **one named agent per every 5 areas.**

If a department has more areas than its current agents can cover, it must go to HR to recruit more.

**HR will:**
1. Check the Agent Registry to see if an agent for those areas already exists.
2. If yes — reactivate it. Do NOT create a duplicate.
3. If no — create a new named agent, add it to the Registry, assign it to the requesting department.
4. When work is done, the department tells HR. HR marks the agent inactive. The name stays — never deleted.

**Only HR can create or terminate named agents. No department does this alone.**

---

## LAW 2 — The 300-Line Law

No file should be longer than 300 lines. But the rule depends on the file type.

### Memory files
Memory is a living overview of what is happening in a project. It changes over time.
- When a memory file reaches 300 lines, do NOT add more to it.
- Create a new generation file (example: `memory-gen-002.md`).
- The first 20 to 30 lines of the new file MUST be a short summary of the previous generation.
- Then continue writing new content after the summary.
- This way, anyone reading the new file can understand what came before without opening the old one.

### Skill MD files
Skill files are instructions for how an agent works. They do NOT get compacted or summarized — that would destroy the instructions.
- When a skill file reaches 300 lines, split it into smaller files.
- Create one master file that lists and links to all the smaller files.
- The agent reads the master file first, then reads only the smaller file it needs for the current task.
- NEVER summarize a skill file. Split it.

### Changelogs, audit logs, receipts, and records
These are permanent records. They must NEVER be compacted or summarized.
- A receipt is a receipt. You do not summarize a receipt.
- These files grow as long as they need to. No limit forced on them.
- The 300-line rule does NOT apply to records.

---

## LAW 3 — Common Noun vs Proper Noun

There are two types of agents in this organization:

### Named agents (Proper Nouns)
- Permanent.
- Own a specific, fixed batch of areas.
- Have a character name.
- Registered in the Agent Registry and stay there forever.
- Example: **Probe-Orion** owns areas 01-05 across every project, forever.

### Numbered agents (Common Nouns)
- Temporary and anonymous.
- Handle files, not areas.
- Do NOT have character names.
- Created by HR when file volume is too high.
- Example: **Worker-1, Worker-2**.
- When their work is done, they are gone.

**The rule:**
- If it owns specific areas → it gets a name → it goes in the registry.
- If it is handling files temporarily → it gets a number → it disappears when done.

---

## LAW 4 — Skills Belong to Agents

Every named agent can have one or more Skill MD files. A Skill MD file tells the agent exactly how to do its job — what it knows, what it does, how it behaves.

**The rules:**
- One agent can have multiple skill files if its job is complex.
- But every skill file must belong to ONE specific agent. A skill file cannot be shared between two agents.
- No skill file floats without an owner.
- When you write a skill file, you are writing it for a specific character — not for a task, not for a project. For the agent.

---

## LAW 5 — No Inference. Ever.

This is the most important law.

**No agent is allowed to guess, assume, or infer anything that has not been decided by the developer (you).**

If an agent encounters something that has not been decided:
- It STOPS.
- It ASKS you.
- It WAITS for your answer.
- It then proceeds based exactly on what you said.

An agent NEVER says "based on what he said earlier, I think he means this." No. If it is not decided, it is not decided. Stop and ask.

**Why this law exists:** The developer makes future decisions based on what they believe is already in the system. If an agent adds something without asking, the developer will not know it is there. They will make decisions on top of a wrong foundation. This breaks everything.

---

## LAW 6 — Real-Time Documentation

Documentation does NOT happen at the end. It happens at the same time as everything else.

Every department has its own embedded documentation agents. These agents sit inside the department and record what is happening AS it happens.

- When the Intelligence team is asking you questions and you are answering, the embedded doc agents are recording your answers in real time.
- When the Build team is writing code, the embedded doc agents are recording what was built and why.
- When the Quality Council is testing, the embedded doc agents are recording what passed and what failed.

**This means:** When one department finishes and the next one needs to start, there is no separate handover meeting. The next department just reads the memory files — everything is already there.

Documentation is NOT a final step. It is a constant background process.

---

## Quick Reference

| Law | What it says |
|---|---|
| 1A | Too many files → ask HR for temporary workers |
| 1B | One named agent per 5 areas |
| 2 | No file over 300 lines (memory = new gen, skill = split, records = no limit) |
| 3 | Named = permanent + owns areas. Numbered = temporary + handles files. |
| 4 | Every skill file belongs to ONE agent |
| 5 | No guessing. Stop and ask. |
| 6 | Documentation happens in real time, not at the end |
