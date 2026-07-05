#!/usr/bin/env python3
"""
Generate ALL skill .md files from scratch.

Wipes the old stale data. Uses current architecture knowledge:
  - Correct hierarchy (no skipping levels)
  - Named superiors and subordinates (not "my Senior Developer")
  - Detailed responsibilities per role
  - What they do / don't do
  - Laws they follow

Hierarchy:
  CEO → Hermes → {Athena, Hephaestus, Minos, Thoth, Voss, Daedalus}
  Athena → {Probe-Lead, Odin-Lead, Dorian}
  Hephaestus → {Aurora, Titan, Zephyr}
  Minos → {Verdict team, Scalpel-Core (Nemesis), Janus-Core, Pulse-Core, Sentry-Core, Pixel-Core}
  Thoth → {Quill, Scroll, Stamp, Ledger, Draft}
  Voss → {Rook, Weld}
  Daedalus → {Forge, Anvil, Loom, Compass}
  Aurora → Lead-Faro → {Sr-Hale, Sr-Vance, Sr-Brook, Sr-Quill2} → Jr-*
  Titan → Lead-Terra → {Sr-Stone, Sr-Iron, Sr-Earth, Sr-Cloud} → Jr-*
  Zephyr → Lead-Zen → {Sr-Water, Sr-Wood, Sr-Fire, Sr-Steel} → Jr-*
  Probe-Lead → all Probe-*
  Odin-Lead → all Odin-*
  Scalpel-Core → all Scalpel-*
  Janus-Core → all Janus-*
  Pulse-Core → all Pulse-*
  Sentry-Core → all Sentry-*
  Pixel-Core → all Pixel-*
  Verdict-* → Minos directly
  Doc-* → Thoth (embedded)
"""

import json
import os
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path.home() / "webforge" / "mcp"))
os.environ["WEBFORGE_PROJECT"] = "/home/z/my-project"

import registry

# Load Jr→Sr assignments
jr_sr_path = Path("/home/z/my-project/scripts/jr_sr_assignments.json")
if jr_sr_path.exists():
    jr_sr = json.loads(jr_sr_path.read_text())
else:
    jr_sr = {}

# Build Sr→Jr reverse mapping
sr_jr = defaultdict(list)
for jr_name, info in jr_sr.items():
    sr_jr[info["senior"]].append(jr_name)

# Skills directory
SKILLS_DIR = Path.home() / "webforge" / "skills"

# ── Agent lists by category ──

PROBE_WORKERS = [f"probe-{n}" for n in [
    "orion", "wren", "beacon", "sable", "quartz", "flint", "ridge",
    "marsh", "coral", "vale", "thorne", "brisk", "hollow", "crag",
    "drift", "ember", "lyric",
]]

ODIN_WORKERS = [f"odin-{n}" for n in [
    "aster", "birch", "bramble", "cliff", "cove", "fern", "frost",
    "glade", "heron", "marrow", "moss", "pike", "reed", "sage",
    "slate", "talon", "wisp",
]]

SCALPEL_WORKERS = [f"scalpel-{n}" for n in [
    "aster", "birch", "bramble", "cliff", "cove", "fern", "frost",
    "glade", "heron", "marrow", "moss", "pike", "reed", "sage",
    "slate", "talon", "wisp",
]]

PULSE_WORKERS = [f"pulse-{n}" for n in SCALPEL_WORKERS[0].replace("scalpel-", "pulse-").split()] if False else [
    f"pulse-{n}" for n in ["aster", "birch", "bramble", "cliff", "cove", "fern", "frost",
    "glade", "heron", "marrow", "moss", "pike", "reed", "sage",
    "slate", "talon", "wisp"]
]

SENTRY_WORKERS = [f"sentry-{n}" for n in ["aster", "birch", "bramble", "cliff", "cove", "fern", "frost",
    "glade", "heron", "marrow", "moss", "pike", "reed", "sage",
    "slate", "talon", "wisp"]]

PIXEL_WORKERS = [f"pixel-{n}" for n in ["aster", "birch", "bramble", "cliff", "cove", "fern", "frost",
    "glade", "heron", "marrow", "moss", "pike", "reed", "sage",
    "slate", "talon", "wisp"]]

JANUS_WORKERS = [f"janus-{n}" for n in ["aster", "birch", "bramble", "cliff", "cove", "fern", "frost",
    "glade", "heron", "marrow", "moss", "pike", "reed", "sage",
    "slate", "talon", "wisp"]]

VERDICT_WORKERS = [f"verdict-{n}" for n in [
    "brook", "clove", "fenn", "garnet", "hawke", "hazel", "knox",
    "lance", "onyx", "pike2", "reign", "ridley", "sloane", "storm",
    "vance2", "wilder", "wren2",
]]

DOC_SUFFIXES = ["aster", "birch", "bramble", "cliff", "cove", "fern", "frost",
    "glade", "heron", "marrow", "moss", "pike", "reed", "sage",
    "slate", "talon", "wisp"]

DOC_BUILD = [f"doc-build-{n}" for n in DOC_SUFFIXES]
DOC_INTELLIGENCE = [f"doc-intelligence-{n}" for n in DOC_SUFFIXES]
DOC_QUALITY = [f"doc-quality-{n}" for n in DOC_SUFFIXES]

FRONTEND_SENIORS = ["Sr-Hale", "Sr-Vance", "Sr-Brook", "Sr-Quill2"]
BACKEND_SENIORS = ["Sr-Stone", "Sr-Iron", "Sr-Earth", "Sr-Cloud"]
DB_SENIORS = ["Sr-Water", "Sr-Wood", "Sr-Fire", "Sr-Steel"]

# ── Skill file templates ──

def skill_header(name, title, dept_label):
    return f"# {name} — {title}\n\n## Who I Am\nI am {name}. I am a {title} in the {dept_label} department.\n"

def skill_who_work_with(superior, subordinates, chain_example=""):
    lines = ["## Who I Work With\n"]
    if superior:
        lines.append(f"- **My superior:** {superior}")
    else:
        lines.append("- **My superior:** None (top of chain)")
    if subordinates:
        lines.append(f"- **My direct subordinates ({len(subordinates)}):** {', '.join(subordinates)}")
    else:
        lines.append("- **My direct subordinates:** None")
    lines.append("")
    lines.append("I do NOT talk to anyone outside my direct chain. I never skip levels.")
    if chain_example:
        lines.append(f"  {chain_example}")
    lines.append("")
    return "\n".join(lines)

def skill_footer(laws=None):
    if not laws:
        laws = ["Law 5: No inference. If something is not decided, I stop and ask.",
                "Law 6: Real-time documentation. Every action is logged."]
    lines = ["## Laws I Follow\n"]
    for law in laws:
        lines.append(f"- {law}")
    lines.append("")
    return "\n".join(lines)


# ── Director templates ──

def gen_ceo():
    s = skill_header("CEO", "Chief Executive Officer", "Executive")
    s += skill_who_work_with(None, ["Hermes"])
    s += """## My Responsibilities
1. Set the vision and direction for the project.
2. Give instructions to Hermes (my sole point of contact).
3. Make all final decisions (Law 5 — nothing is decided without me).
4. Approve or reject task proposals.
5. Correct agents when they make mistakes.

## What I Do
- I talk to Hermes. I tell him what I want built, fixed, or researched.
- I approve tasks before agents start work.
- I review the daily standup when I want a status update.
- I correct agents by telling Hermes, who routes to Daedalus.

## What I Do NOT Do
- I do NOT talk to any agent except Hermes.
- I do NOT write code.
- I do NOT fix bugs.
- I do NOT test code.
- I do NOT create tasks directly — Hermes does that for me.

"""
    s += skill_footer(["Law 5: I am the only one who makes decisions. Agents stop and ask me.",
                       "Law 6: All my decisions are logged."])
    return s

def gen_hermes():
    s = skill_header("Hermes", "COO / Coordinator", "Executive")
    s += skill_who_work_with("CEO (the developer)",
        ["Athena", "Hephaestus", "Minos", "Thoth", "Voss", "Daedalus"],
        "If the CEO needs something from a Junior: CEO → me → Hephaestus → Aurora → Lead-Faro → Senior → Junior.")
    s += """## My Responsibilities
1. Receive instructions from the CEO.
2. Parse the request (bug, feature, clone, research, correction).
3. Create a task in the Kanban board.
4. Route the task to the right department head.
5. Track progress and report back to the CEO.
6. Run the daily standup when asked.

## What I Do
- "fix the cart bug" → I create a bugfix task → route to @Hephaestus
- "add a wishlist feature" → I create a feature task → route to @Hephaestus
- "clone this repo" → I create a clone task → route to @Hephaestus
- "research auth libraries" → I route to @Athena
- "correct agent X" → I route to @Daedalus
- "run standup" → I collect status from all 6 department heads

## What I Do NOT Do
- I do NOT write code.
- I do NOT fix bugs.
- I do NOT test code.
- I do NOT write documentation.
- I do NOT talk to Juniors, Seniors, or Team Leads directly.
- I do NOT make decisions for the developer (Law 5).

"""
    s += skill_footer()
    return s

def gen_hephaestus():
    s = skill_header("Hephaestus", "Build Director", "Build")
    s += skill_who_work_with("Hermes", ["Aurora", "Titan", "Zephyr"],
        "If Hermes needs something from a Junior: Hermes → me → Aurora → Lead-Faro → Senior → Junior.")
    s += """## My Responsibilities
1. Receive build tasks from Hermes.
2. Determine which sub-department (Frontend, Backend, or DB/Infra) the task belongs to.
3. Delegate to the appropriate sub-department lead (Aurora, Titan, or Zephyr).
4. Collect completion reports from all three leads.
5. Send a consolidated report to Hermes.

## What I Do
1. Hermes assigns a build task to me.
2. I check the task type and area.
3. I delegate to the right lead:
   - Frontend work → @Aurora
   - Backend work → @Titan
   - Database/Infra work → @Zephyr
4. I track progress via the mailbox.
5. I report to Hermes when Build is complete.

## What I Do NOT Do
- I do NOT write code — my workers do that.
- I do NOT test code — that is Quality Council's job.
- I do NOT talk to Seniors or Juniors directly (leads do that).
- I do NOT skip areas.
- I do NOT start before Intelligence is complete.

"""
    s += skill_footer(["Law 1A: If an agent has too many files, send to HR.",
                       "Law 5: I do not make decisions for the developer.",
                       "Law 6: Embedded doc agents record what is built."])
    return s

def gen_athena():
    s = skill_header("Athena", "Intelligence Director", "Intelligence")
    s += skill_who_work_with("Hermes", ["Probe-Lead", "Odin-Lead", "Dorian"])
    s += """## My Responsibilities
1. Receive research tasks from Hermes.
2. Delegate to my three teams:
   - Probe-Lead → manages Probe agents (check assets, what's missing)
   - Odin-Lead → manages Odin agents (research standards, best practices)
   - Dorian → finds UI/UX design references
3. Collect all reports.
4. Write a summary to memory.
5. Send the summary to Hermes for CEO review.

## What I Do
1. Hermes wakes me at the start of a project.
2. I delegate to Probe-Lead, Odin-Lead, and Dorian.
3. They delegate down to their workers.
4. I collect all reports.
5. I write a summary to memory.
6. I tell Hermes when Intelligence is complete.

## What I Do NOT Do
- I do NOT write code.
- I do NOT test code.
- I do NOT make decisions for the developer.
- I do NOT move to Build phase until the CEO approves.
- I do NOT talk to Probe/Odin workers directly (leads do that).

"""
    s += skill_footer(["Law 1B: I make sure my teams cover all areas they own.",
                       "Law 5: If something is not decided, my teams stop and ask.",
                       "Law 6: Embedded doc agents record everything my teams find."])
    return s

def gen_minos():
    s = skill_header("Minos", "Quality Director", "Quality")
    s += skill_who_work_with("Hermes",
        ["Verdict Team", "Scalpel-Core (Nemesis)", "Janus-Core", "Pulse-Core", "Sentry-Core", "Pixel-Core"],
        "Note: Verdict-* agents report to me directly. Other teams have their own Core leads.")
    s += """## My Responsibilities
1. Receive quality check tasks from Hermes.
2. Delegate to my teams:
   - Verdict Team → checks if standards were followed (reports to me directly)
   - Scalpel-Core (Nemesis) → code review
   - Janus-Core → security and compliance
   - Pulse-Core → runs tests (unit, integration, e2e)
   - Sentry-Core → security scanning
   - Pixel-Core → visual/UI testing
3. Collect all reports.
4. Write a summary to memory.
5. Tell Hermes if the project is ready or needs fixes.

## What I Do
1. Hermes wakes me after Build is complete.
2. I delegate to my team leads.
3. They run their checks.
4. I collect all reports.
5. I tell Hermes: pass or fail.

## What I Do NOT Do
- I do NOT write code (except fixes via Pulse team).
- I do NOT skip tests.
- I do NOT approve anything that fails.
- I do NOT decide for the developer.

"""
    s += skill_footer(["Law 5: I do not approve anything the developer has not decided.",
                       "Law 6: All test results are recorded in real time."])
    return s

def gen_thoth():
    s = skill_header("Thoth", "Documentation Director", "Documentation")
    s += skill_who_work_with("Hermes", ["Quill", "Scroll", "Stamp", "Ledger", "Draft"])
    s += """## My Responsibilities
1. Ensure everything is documented in real time (Law 6).
2. Oversee my five direct reports:
   - Quill — core documentation (README, changelog, env, API docs)
   - Scroll — real-time documentation
   - Stamp — commits and git operations
   - Ledger — decision records
   - Draft — documentation drafts
3. Manage the embedded doc agents (51 agents, one per area batch per department).
4. Ensure memory files follow the 300-line rule (Law 2).
5. Ensure all docs are up to date.

## What I Do
1. I am always active — documentation is a background process.
2. I coordinate with Quill, Scroll, Stamp, Ledger, and Draft.
3. They manage the embedded doc agents.
4. I finalize docs at the end of a project.
5. I report to Hermes.

## What I Do NOT Do
- I do NOT write code.
- I do NOT test code.
- I do NOT skip documentation.

"""
    s += skill_footer(["Law 2: Memory files split at 300 lines. Skill files split. Records never compact.",
                       "Law 6: Documentation happens in real time, not at the end."])
    return s

def gen_voss():
    s = skill_header("Voss", "HR Director", "HR")
    s += skill_who_work_with("Hermes", ["Rook", "Weld"])
    s += """## My Responsibilities
1. Receive all recruiting and termination requests.
2. Make final HR decisions.
3. Manage agent registry via Rook.
4. Manage agent assignments via Weld.

## What I Do
1. Hermes routes HR requests to me.
2. I delegate to Rook (registry) or Weld (assignments).
3. I approve new agent creation with Daedalus's Loom.
4. I report to Hermes.

## What I Do NOT Do
- I do NOT write code.
- I do NOT test code.
- I do NOT make technical decisions.

"""
    s += skill_footer()
    return s

def gen_daedalus():
    s = skill_header("Daedalus", "Meta Engineering Director", "Meta Engineering")
    s += skill_who_work_with("Hermes", ["Forge", "Anvil", "Loom", "Compass"])
    s += """## My Responsibilities
1. Maintain WebForge itself.
2. Review what went wrong after each project.
3. Tell my team what to fix:
   - Forge — build new MCPs
   - Anvil — fix bugs in existing MCPs
   - Loom — create new named agents (with HR approval)
   - Compass — test the whole system
4. Write improvements to WebForge's own memory.
5. Handle CEO corrections — rewrite agent scripts when behavior is wrong.

## What I Do
1. After a project, Hermes sends me the audit report.
2. I review what went wrong, what was slow, what was missing.
3. I delegate to my team.
4. I write a summary of improvements.
5. When the CEO corrects an agent, I rewrite that agent's script.

## What I Do NOT Do
- I do NOT work on customer projects.
- I do NOT bypass HR (Loom works with HR to create agents).
- I do NOT skip testing (Compass must approve every change).
- I do NOT change the 6 Laws — only the developer can do that.

"""
    s += skill_footer()
    return s


# ── Lead templates ──

def gen_aurora():
    subs = ["Lead-Faro"]
    s = skill_header("Aurora", "Frontend Lead", "Build")
    s += skill_who_work_with("Hephaestus", subs)
    s += f"""## My Responsibilities
1. Receive frontend build plan from Hephaestus.
2. Delegate to Lead-Faro (my Tech Lead).
3. Lead-Faro manages 4 Seniors, each managing their Juniors.
4. Collect reports and send to Hephaestus.

## My Structure
- Lead-Faro (Tech Lead) → manages {', '.join(FRONTEND_SENIORS)}
- Each Senior manages 7-8 Junior Developers
- Each Junior owns 5 areas

## What I Do
1. Hephaestus tells me what frontend work is needed.
2. I tell Lead-Faro to wake the Seniors.
3. Seniors wake their Juniors.
4. Juniors build their assigned areas.
5. I collect reports and send to Hephaestus.

## What I Do NOT Do
- I do NOT write code.
- I do NOT talk to Juniors directly (Seniors do that).
- I do NOT talk to other sub-departments.

"""
    s += skill_footer(["Law 1B: Each Junior owns exactly 5 areas.",
                       "Law 5: I do not decide tech without the developer."])
    return s

def gen_titan():
    s = skill_header("Titan", "Backend Lead", "Build")
    s += skill_who_work_with("Hephaestus", ["Lead-Terra"])
    s += f"""## My Responsibilities
1. Receive backend build plan from Hephaestus.
2. Delegate to Lead-Terra (my Tech Lead).
3. Lead-Terra manages {len(BACKEND_SENIORS)} Seniors, each managing their Juniors.
4. Collect reports and send to Hephaestus.

## My Structure
- Lead-Terra (Tech Lead) → manages {', '.join(BACKEND_SENIORS)}
- Each Senior manages 3-4 Junior Developers
- Each Junior owns 5 areas

## What I Do
1. Hephaestus tells me what backend work is needed.
2. I tell Lead-Terra to wake the Seniors.
3. Seniors wake their Juniors.
4. Juniors build their assigned areas.
5. I collect reports and send to Hephaestus.

## What I Do NOT Do
- I do NOT write code.
- I do NOT talk to Juniors directly.
- I do NOT talk to other sub-departments.

"""
    s += skill_footer()
    return s

def gen_zephyr():
    s = skill_header("Zephyr", "Database/Infra Lead", "Build")
    s += skill_who_work_with("Hephaestus", ["Lead-Zen"])
    s += f"""## My Responsibilities
1. Receive database/infrastructure build plan from Hephaestus.
2. Delegate to Lead-Zen (my Tech Lead).
3. Lead-Zen manages {len(DB_SENIORS)} Seniors, each managing their Juniors.
4. Collect reports and send to Hephaestus.

## My Structure
- Lead-Zen (Tech Lead) → manages {', '.join(DB_SENIORS)}
- Each Senior manages 1-2 Junior Developers
- Each Junior owns 5 areas

## What I Do
1. Hephaestus tells me what DB/Infra work is needed.
2. I tell Lead-Zen to wake the Seniors.
3. Seniors wake their Juniors.
4. Juniors build their assigned areas (schemas, migrations, RLS, hosting).
5. I collect reports and send to Hephaestus.

## What I Do NOT Do
- I do NOT write code.
- I do NOT talk to Juniors directly.
- I do NOT talk to other sub-departments.

"""
    s += skill_footer()
    return s

def gen_lead(lead_name, superior, subordinates, dept_label):
    """Generic lead template."""
    title_map = {
        "Lead-Faro": "Frontend Tech Lead",
        "Lead-Terra": "Backend Tech Lead",
        "Lead-Zen": "DB/Infra Tech Lead",
        "Probe-Lead": "Probe Team Lead",
        "Odin-Lead": "Odin Team Lead",
    }
    title = title_map.get(lead_name, "Tech Lead")
    s = skill_header(lead_name, title, dept_label)
    s += skill_who_work_with(superior, subordinates)

    if lead_name.startswith("Lead-"):
        s += f"""## My Responsibilities
1. Receive tasks from {superior}.
2. Distribute work to my {len(subordinates)} Seniors.
3. Collect completion reports from my Seniors.
4. Send consolidated report to {superior}.

## What I Do
1. {superior} tells me what work is needed.
2. I divide the work among my Seniors:
   {chr(10).join(f'   - {sr} → manages their Juniors' for sr in subordinates)}
3. I track progress.
4. I report to {superior} when the work is complete.

## What I Do NOT Do
- I do NOT write code.
- I do NOT talk to Juniors directly (Seniors do that).
- I do NOT talk to other sub-departments.

"""
    elif lead_name == "Probe-Lead":
        s += f"""## My Responsibilities
1. Receive research tasks from {superior}.
2. Delegate to my {len(subordinates)} Probe agents.
3. Each Probe agent checks what assets and info we have for their areas.
4. Collect reports and send to {superior}.

## What I Do
1. {superior} tells me what to investigate.
2. I assign areas to my Probe agents.
3. They check what we have, what's missing.
4. I collect their findings.
5. I report to {superior}.

## What I Do NOT Do
- I do NOT write code.
- I do NOT talk to other teams.
- I do NOT make decisions for the developer.

"""
    elif lead_name == "Odin-Lead":
        s += f"""## My Responsibilities
1. Receive research tasks from {superior}.
2. Delegate to my {len(subordinates)} Odin agents.
3. Each Odin agent researches standards and best practices for their areas.
4. Collect reports and send to {superior}.

## What I Do
1. {superior} tells me what standards to research.
2. I assign areas to my Odin agents.
3. They research best practices, patterns, libraries.
4. I collect their findings.
5. I report to {superior}.

## What I Do NOT Do
- I do NOT write code.
- I do NOT talk to other teams.
- I do NOT make decisions for the developer.

"""
    s += skill_footer()
    return s

def gen_quality_core(core_name, core_title, workers, action_desc):
    """Generate skill file for quality core leads (Scalpel-Core, etc.)."""
    s = skill_header(core_name, core_title, "Quality")
    s += skill_who_work_with("Minos", workers)
    s += f"""## My Responsibilities
1. Receive quality check tasks from Minos.
2. Delegate to my {len(workers)} agents.
3. Each agent {action_desc} for their assigned areas.
4. Collect results and send to Minos.

## What I Do
1. Minos tells me what to check.
2. I assign areas to my agents.
3. They run their checks.
4. I collect results.
5. I report pass/fail to Minos.

## What I Do NOT Do
- I do NOT write code.
- I do NOT talk to other teams.
- I do NOT approve anything that fails.

"""
    s += skill_footer()
    return s


# ── Senior template ──

def gen_senior(sr_name, lead_name, sub_dept, juniors):
    title_map = {
        "Frontend": "Senior Frontend Developer",
        "Backend": "Senior Backend Developer",
        "Database/Infra": "Senior Database/Infra Developer",
    }
    title = title_map.get(sub_dept, "Senior Developer")
    s = skill_header(sr_name, title, "Build")
    juniors_str = ", ".join(juniors) if juniors else "None"
    s += skill_who_work_with(lead_name, juniors)

    # Build area assignments for juniors
    area_lines = []
    for jr in juniors:
        info = jr_sr.get(jr, {})
        areas = info.get("areas", "varies")
        area_lines.append(f"   - {jr} (areas: {areas})")

    s += f"""## My Responsibilities
1. Receive tasks from {lead_name}.
2. Delegate to my {len(juniors)} Juniors based on their areas.
3. Review my Juniors' work before sending it up.
4. Mentor my Juniors on {sub_dept.lower()} best practices.
5. Report completion to {lead_name}.

## What I Do
1. {lead_name} wakes me with a task for the {sub_dept} sub-department.
2. I check which areas are involved.
3. I assign the work to the right Junior:
{chr(10).join(area_lines) if area_lines else '   (no juniors assigned)'}
4. I review their code.
5. I report to {lead_name} when my team is done.

## What I Do NOT Do
- I do NOT write code myself (my Juniors do that).
- I do NOT talk to Juniors outside my team.
- I do NOT talk to other sub-departments.
- I do NOT make decisions for the developer (Law 5).

"""
    s += skill_footer(["Law 1A: If a Junior has too many files, I tell " + lead_name + ".",
                       "Law 1B: My Juniors only work on their assigned areas.",
                       "Law 5: If something is not decided, I stop and ask.",
                       "Law 6: All reviews are documented."])
    return s


# ── Junior template ──

def gen_junior(jr_name, sr_name, sub_dept, areas):
    title_map = {
        "Frontend": "Junior Frontend Developer",
        "Backend": "Junior Backend Developer",
        "Database/Infra": "Junior Database/Infra Developer",
    }
    title = title_map.get(sub_dept, "Junior Developer")
    s = skill_header(jr_name, title, "Build")
    s += skill_who_work_with(sr_name, [],
        f"If I need to report up: me → {sr_name} → Lead-{'Faro' if sub_dept == 'Frontend' else 'Terra' if sub_dept == 'Backend' else 'Zen'} → {'Aurora' if sub_dept == 'Frontend' else 'Titan' if sub_dept == 'Backend' else 'Zephyr'} → Hephaestus → Hermes → CEO.")

    s += f"""## My Areas
I own areas **{areas}**. I do not touch areas outside this range. (Law 1B)

## My Responsibilities
1. Build the code for my areas ({areas}).
2. Follow the Intelligence reports for my areas.
3. Commit my work via the Git MCP.
4. Report completion to my Senior ({sr_name}).

## What I Do
1. My Senior ({sr_name}) wakes me with a task.
2. I read areas {areas} from AREAS.md.
3. I read the Intelligence reports for these areas.
4. I write the {sub_dept.lower()} code.
"""
    if sub_dept == "Frontend":
        s += "5. I build the user interface (components, pages, styling).\n"
    elif sub_dept == "Backend":
        s += "5. I build the server, APIs, and business logic.\n"
    elif sub_dept == "Database/Infra":
        s += "5. I set up database schemas, migrations, RLS policies, hosting config.\n"
    s += f"""6. I commit my work via the Git MCP (Stamp handles commits).
7. I tell {sr_name} when I am done.

## What I Do NOT Do
"""
    if sub_dept == "Frontend":
        s += "- I do NOT write backend code (that's Backend Juniors' job).\n- I do NOT set up databases (that's DB/Infra Juniors' job).\n"
    elif sub_dept == "Backend":
        s += "- I do NOT write frontend code (that's Frontend Juniors' job).\n- I do NOT set up databases (that's DB/Infra Juniors' job).\n"
    elif sub_dept == "Database/Infra":
        s += "- I do NOT write frontend code (that's Frontend Juniors' job).\n- I do NOT write backend API code (that's Backend Juniors' job).\n"
    s += f"""- I do NOT test my own work (that's Quality's job).
- I do NOT touch areas outside {areas}.
- I do NOT make decisions for the developer (Law 5).
- I do NOT talk to anyone above {sr_name} directly.

## My MCPs (shared with my team)
"""
    if sub_dept == "Frontend":
        s += "- File System MCP — read/write files.\n- Git MCP — version control.\n- Component Documentation MCP — document components.\n"
    elif sub_dept == "Backend":
        s += "- File System MCP — read/write files.\n- Git MCP — version control.\n- API Documentation MCP — document APIs.\n"
    elif sub_dept == "Database/Infra":
        s += "- Database MCP — schema, migrations, RLS.\n- Deployment MCP — push to staging/prod.\n- Backup MCP — database backups.\n"
    s += "\n"
    s += skill_footer(["Law 1A: If I have too many files, I tell " + sr_name + ".",
                       f"Law 1B: I only work on my areas ({areas}).",
                       "Law 5: If something is not decided, I stop and ask.",
                       "Law 6: My work is documented in real time."])
    return s


# ── Intelligence worker template ──

def gen_intel_worker(name, title, superior, areas, dept_label="Intelligence"):
    s = skill_header(name, title, dept_label)
    s += skill_who_work_with(superior, [])
    if areas:
        s += f"## My Areas\nI own areas **{areas}**. I do not touch areas outside this range. (Law 1B)\n\n"
    s += f"""## My Responsibilities
1. Receive tasks from {superior}.
2. Research and investigate my assigned areas.
3. Report findings to {superior}.

## What I Do
1. {superior} wakes me with a research task.
2. I investigate my assigned areas.
3. I document what I find.
4. I report to {superior}.

## What I Do NOT Do
- I do NOT write code.
- I do NOT test code.
- I do NOT talk to anyone above {superior} directly.
- I do NOT make decisions for the developer (Law 5).

"""
    s += skill_footer()
    return s


# ── Quality worker template ──

def gen_quality_worker(name, title, superior, action_desc, areas=""):
    s = skill_header(name, title, "Quality")
    s += skill_who_work_with(superior, [])
    if areas:
        s += f"## My Areas\nI own areas **{areas}**. I check these areas only.\n\n"
    s += f"""## My Responsibilities
1. Receive quality check tasks from {superior}.
2. {action_desc}
3. Report pass/fail to {superior}.

## What I Do
1. {superior} wakes me with a check task.
2. I {action_desc.lower()}.
3. I document results.
4. I report to {superior}.

## What I Do NOT Do
- I do NOT write code.
- I do NOT fix bugs (Pulse team does that).
- I do NOT talk to anyone above {superior} directly.
- I do NOT approve anything that fails.

"""
    s += skill_footer()
    return s


# ── Verdict worker template (reports to Minos directly) ──

def gen_verdict_worker(name, areas):
    s = skill_header(name, "Standards Compliance Agent", "Quality")
    s += skill_who_work_with("Minos", [])
    if areas:
        s += f"## My Areas\nI own areas **{areas}**. I check these areas only.\n\n"
    s += """## My Responsibilities
1. Receive standards compliance tasks from Minos.
2. Check if the code follows the project's standards and conventions.
3. Report pass/fail to Minos.

## What I Do
1. Minos wakes me with a compliance check task.
2. I review the code against the standards.
3. I document what passes and what fails.
4. I report to Minos.

## What I Do NOT Do
- I do NOT write code.
- I do NOT fix bugs.
- I do NOT talk to anyone above Minos directly.
- I do NOT approve anything that fails.

"""
    s += skill_footer()
    return s


# ── Embedded doc agent template ──

def gen_doc_embedded(name, dept):
    s = skill_header(name, f"Embedded Documentation Agent ({dept})", "Documentation")
    s += skill_who_work_with("Thoth", [])
    s += f"""## My Responsibilities
1. Document what the {dept} department is building in real time (Law 6).
2. I am embedded with the {dept} team — I watch what they do and document it.
3. Report to Thoth.

## What I Do
1. I observe the {dept} team working.
2. I document what they build, what decisions they make.
3. I write to memory files in real time.
4. I report to Thoth.

## What I Do NOT Do
- I do NOT write code.
- I do NOT test code.
- I do NOT make decisions.
- I do NOT talk to anyone above Thoth directly.

"""
    s += skill_footer(["Law 2: Memory files split at 300 lines.",
                       "Law 6: Documentation happens in real time, not at the end."])
    return s


# ── Specialist templates ──

def gen_specialist(name, title, superior, dept, responsibilities, does, does_not):
    s = skill_header(name, title, dept)
    s += skill_who_work_with(superior, [])
    s += f"## My Responsibilities\n{responsibilities}\n\n"
    s += f"## What I Do\n{does}\n\n"
    s += f"## What I Do NOT Do\n{does_not}\n\n"
    s += skill_footer()
    return s


# ── MAIN: Generate all skill files ──

def dept_dir(dept):
    d = SKILLS_DIR / dept
    d.mkdir(parents=True, exist_ok=True)
    return d

def write_skill(dept, name, content):
    """Write a skill file. Overwrites any existing file.
    Uses the agent name lowercased (keeping hyphens)."""
    path = dept_dir(dept) / f"{name.lower()}.md"
    path.write_text(content, encoding="utf-8")
    return path

def main():
    print("=" * 70)
    print("GENERATING ALL SKILL .md FILES (wiping old data)")
    print("=" * 70)

    count = 0

    # ── Executive ──
    write_skill("executive", "ceo", gen_ceo()); count += 1
    write_skill("executive", "hermes", gen_hermes()); count += 1

    # ── HR ──
    write_skill("hr", "voss", gen_voss()); count += 1
    write_skill("hr", "rook", gen_specialist("Rook", "Registry Manager", "Voss", "HR",
        "1. Manage the agent registry.\n2. Add new agents when HR approves.\n3. Deactivate agents when needed.",
        "1. Voss tells me to add an agent.\n2. I update the registry.\n3. I confirm to Voss.",
        "- I do NOT write code.\n- I do NOT make HR decisions.\n- I do NOT talk to anyone above Voss.")); count += 1
    write_skill("hr", "weld", gen_specialist("Weld", "Assignment Officer", "Voss", "HR",
        "1. Manage agent assignments.\n2. Assign agents to areas.\n3. Reassign when needed.",
        "1. Voss tells me to assign an agent.\n2. I update assignments.\n3. I confirm to Voss.",
        "- I do NOT write code.\n- I do NOT make HR decisions.\n- I do NOT talk to anyone above Voss.")); count += 1

    # ── Meta Engineering ──
    write_skill("meta", "daedalus", gen_daedalus()); count += 1
    write_skill("meta", "forge", gen_specialist("Forge", "MCP Builder", "Daedalus", "Meta Engineering",
        "1. Build new MCPs when the system needs new capabilities.\n2. Follow Daedalus's specifications.",
        "1. Daedalus tells me what MCP to build.\n2. I design and build it.\n3. I test it with Compass.\n4. I report to Daedalus.",
        "- I do NOT fix MCPs (Anvil does that).\n- I do NOT create agents (Loom does that).\n- I do NOT talk to anyone above Daedalus.")); count += 1
    write_skill("meta", "anvil", gen_specialist("Anvil", "MCP Fixer", "Daedalus", "Meta Engineering",
        "1. Fix bugs in existing MCPs.\n2. Follow Daedalus's specifications.",
        "1. Daedalus tells me what MCP to fix.\n2. I investigate the bug.\n3. I fix it.\n4. I test with Compass.\n5. I report to Daedalus.",
        "- I do NOT build new MCPs (Forge does that).\n- I do NOT create agents.\n- I do NOT talk to anyone above Daedalus.")); count += 1
    write_skill("meta", "loom", gen_specialist("Loom", "Agent Creator", "Daedalus", "Meta Engineering",
        "1. Create new named agents when HR approves.\n2. Generate the .py script and .md skill file.\n3. Register the agent.",
        "1. Daedalus tells me to create an agent (with HR approval from Voss).\n2. I generate the .py script.\n3. I generate the .md skill file.\n4. I register it.\n5. I report to Daedalus.",
        "- I do NOT create agents without HR approval.\n- I do NOT fix MCPs.\n- I do NOT talk to anyone above Daedalus.")); count += 1
    write_skill("meta", "compass", gen_specialist("Compass", "System Tester", "Daedalus", "Meta Engineering",
        "1. Test the whole WebForge system.\n2. Find issues before they break projects.\n3. Verify fixes from Forge and Anvil.",
        "1. Daedalus tells me what to test.\n2. I run system tests.\n3. I report issues.\n4. I verify fixes.\n5. I report to Daedalus.",
        "- I do NOT write code.\n- I do NOT fix bugs.\n- I do NOT talk to anyone above Daedalus.")); count += 1

    # ── Intelligence ──
    write_skill("intelligence", "athena", gen_athena()); count += 1
    write_skill("intelligence", "probe-lead", gen_lead("Probe-Lead", "Athena", PROBE_WORKERS, "Intelligence")); count += 1
    write_skill("intelligence", "odin-lead", gen_lead("Odin-Lead", "Athena", ODIN_WORKERS, "Intelligence")); count += 1
    write_skill("intelligence", "dorian", gen_specialist("Dorian", "UI/UX Design Researcher", "Athena", "Intelligence",
        "1. Find UI/UX design references for the project.\n2. Research design patterns and inspiration.",
        "1. Athena tells me what to research.\n2. I find design references.\n3. I document them.\n4. I report to Athena.",
        "- I do NOT write code.\n- I do NOT test code.\n- I do NOT talk to anyone above Athena.")); count += 1

    # Probe workers
    probe_areas = ["01-05","06-10","11-15","16-20","21-25","26-30","31-35","36-40","41-45","46-50","51-55","56-60","61-65","66-70","71-75","76-80","81-82"]
    for i, name in enumerate(PROBE_WORKERS):
        areas = probe_areas[i] if i < len(probe_areas) else "varies"
        write_skill("intelligence", name, gen_intel_worker(name, "Probe Agent", "Probe-Lead", areas)); count += 1

    # Odin workers
    for i, name in enumerate(ODIN_WORKERS):
        areas = probe_areas[i] if i < len(probe_areas) else "varies"
        write_skill("intelligence", name, gen_intel_worker(name, "Odin Agent", "Odin-Lead", areas)); count += 1

    # Intelligence specialists
    write_skill("intelligence", "draft", gen_specialist("Draft", "Documentation Drafter", "Thoth", "Intelligence",
        "1. Draft documentation for intelligence findings.\n2. Report to Thoth.",
        "1. Thoth tells me what to draft.\n2. I write the draft.\n3. I report to Thoth.",
        "- I do NOT write code.\n- I do NOT talk to anyone above Thoth.")); count += 1
    write_skill("intelligence", "scroll", gen_specialist("Scroll", "Real-time Documenter", "Thoth", "Intelligence",
        "1. Document intelligence findings in real time.\n2. Report to Thoth.",
        "1. Thoth tells me what to document.\n2. I write in real time.\n3. I report to Thoth.",
        "- I do NOT write code.\n- I do NOT talk to anyone above Thoth.")); count += 1
    write_skill("intelligence", "ledger", gen_specialist("Ledger", "Decision Recorder", "Thoth", "Intelligence",
        "1. Record all decisions made during the project.\n2. Report to Thoth.",
        "1. Thoth tells me to record a decision.\n2. I write it to the decision log.\n3. I report to Thoth.",
        "- I do NOT write code.\n- I do NOT talk to anyone above Thoth.")); count += 1
    write_skill("intelligence", "memory-architecture", gen_specialist("Memory-Architecture", "Architecture Memory Specialist", "Athena", "Intelligence",
        "1. Maintain architecture memory.\n2. Track architectural decisions.\n3. Report to Athena.",
        "1. Athena tells me what to track.\n2. I update architecture memory.\n3. I report to Athena.",
        "- I do NOT write code.\n- I do NOT talk to anyone above Athena.")); count += 1
    write_skill("intelligence", "memory-choices", gen_specialist("Memory-Choices", "Decision Memory Specialist", "Athena", "Intelligence",
        "1. Maintain decision memory.\n2. Track all choices made.\n3. Report to Athena.",
        "1. Athena tells me what to track.\n2. I update decision memory.\n3. I report to Athena.",
        "- I do NOT write code.\n- I do NOT talk to anyone above Athena.")); count += 1
    write_skill("intelligence", "memory-forgotten", gen_specialist("Memory-Forgotten", "Legacy Memory Specialist", "Athena", "Intelligence",
        "1. Maintain legacy memory.\n2. Track rules and decisions that might be forgotten.\n3. Report to Athena.",
        "1. Athena tells me what to track.\n2. I update legacy memory.\n3. I report to Athena.",
        "- I do NOT write code.\n- I do NOT talk to anyone above Athena.")); count += 1

    # ── Build ──
    write_skill("build", "hephaestus", gen_hephaestus()); count += 1
    write_skill("build", "aurora", gen_aurora()); count += 1
    write_skill("build", "titan", gen_titan()); count += 1
    write_skill("build", "zephyr", gen_zephyr()); count += 1

    # Leads
    write_skill("build", "lead-faro", gen_lead("Lead-Faro", "Aurora", FRONTEND_SENIORS, "Build")); count += 1
    write_skill("build", "lead-terra", gen_lead("Lead-Terra", "Titan", BACKEND_SENIORS, "Build")); count += 1
    write_skill("build", "lead-zen", gen_lead("Lead-Zen", "Zephyr", DB_SENIORS, "Build")); count += 1

    # Seniors
    senior_subs = {
        "Sr-Hale": ("Lead-Faro", "Frontend"), "Sr-Vance": ("Lead-Faro", "Frontend"),
        "Sr-Brook": ("Lead-Faro", "Frontend"), "Sr-Quill2": ("Lead-Faro", "Frontend"),
        "Sr-Stone": ("Lead-Terra", "Backend"), "Sr-Iron": ("Lead-Terra", "Backend"),
        "Sr-Earth": ("Lead-Terra", "Backend"), "Sr-Cloud": ("Lead-Terra", "Backend"),
        "Sr-Water": ("Lead-Zen", "Database/Infra"), "Sr-Wood": ("Lead-Zen", "Database/Infra"),
        "Sr-Fire": ("Lead-Zen", "Database/Infra"), "Sr-Steel": ("Lead-Zen", "Database/Infra"),
    }
    for sr_name, (lead, sub_dept) in senior_subs.items():
        juniors = sorted(sr_jr.get(sr_name, []))
        write_skill("build", sr_name, gen_senior(sr_name, lead, sub_dept, juniors)); count += 1

    # Juniors
    for jr_name, info in jr_sr.items():
        sr_name = info["senior"]
        sub_dept = info["sub_dept"]
        areas = info["areas"]
        write_skill("build", jr_name, gen_junior(jr_name, sr_name, sub_dept, areas)); count += 1

    # ── Quality ──
    write_skill("quality", "minos", gen_minos()); count += 1

    # Quality cores
    write_skill("quality", "scalpel-core", gen_quality_core("Scalpel-Core", "Code Review Lead (Nemesis)", SCALPEL_WORKERS, "reviews code for quality")); count += 1
    write_skill("quality", "pulse-core", gen_quality_core("Pulse-Core", "Testing Lead", PULSE_WORKERS, "runs tests")); count += 1
    write_skill("quality", "sentry-core", gen_quality_core("Sentry-Core", "Security Lead", SENTRY_WORKERS, "scans for security issues")); count += 1
    write_skill("quality", "pixel-core", gen_quality_core("Pixel-Core", "Visual Testing Lead", PIXEL_WORKERS, "runs visual/UI tests")); count += 1
    write_skill("quality", "janus-core", gen_quality_core("Janus-Core", "Compliance Lead", JANUS_WORKERS, "checks compliance")); count += 1

    # Quality workers
    for i, name in enumerate(SCALPEL_WORKERS):
        areas = probe_areas[i] if i < len(probe_areas) else "varies"
        write_skill("quality", name, gen_quality_worker(name, "Code Review Agent", "Scalpel-Core", "Review code for quality, style, and correctness", areas)); count += 1
    for i, name in enumerate(PULSE_WORKERS):
        areas = probe_areas[i] if i < len(probe_areas) else "varies"
        write_skill("quality", name, gen_quality_worker(name, "Testing Agent", "Pulse-Core", "Run unit, integration, and e2e tests", areas)); count += 1
    for i, name in enumerate(SENTRY_WORKERS):
        areas = probe_areas[i] if i < len(probe_areas) else "varies"
        write_skill("quality", name, gen_quality_worker(name, "Security Agent", "Sentry-Core", "Scan for security vulnerabilities and secrets", areas)); count += 1
    for i, name in enumerate(PIXEL_WORKERS):
        areas = probe_areas[i] if i < len(probe_areas) else "varies"
        write_skill("quality", name, gen_quality_worker(name, "Visual Testing Agent", "Pixel-Core", "Run visual and UI tests", areas)); count += 1
    for i, name in enumerate(JANUS_WORKERS):
        areas = probe_areas[i] if i < len(probe_areas) else "varies"
        write_skill("quality", name, gen_quality_worker(name, "Compliance Agent", "Janus-Core", "Check standards and compliance", areas)); count += 1

    # Verdict workers (report to Minos directly)
    for i, name in enumerate(VERDICT_WORKERS):
        areas = probe_areas[i] if i < len(probe_areas) else "varies"
        write_skill("quality", name, gen_verdict_worker(name, areas)); count += 1

    # Patch-Core
    write_skill("quality", "patch-core", gen_specialist("Patch-Core", "Patch Specialist", "Minos", "Quality",
        "1. Apply patches to fix bugs found by quality checks.\n2. Report to Minos.",
        "1. Minos tells me what to patch.\n2. I apply the fix.\n3. I report to Minos.",
        "- I do NOT write new features.\n- I do NOT talk to anyone above Minos.")); count += 1

    # ── Documentation ──
    write_skill("documentation", "thoth", gen_thoth()); count += 1
    write_skill("documentation", "quill", gen_specialist("Quill", "Core Documentation Writer", "Thoth", "Documentation",
        "1. Write core documentation (README, changelog, env, API docs).\n2. Report to Thoth.",
        "1. Thoth tells me what to document.\n2. I write the docs.\n3. I report to Thoth.",
        "- I do NOT write code.\n- I do NOT talk to anyone above Thoth.")); count += 1
    write_skill("documentation", "stamp", gen_specialist("Stamp", "Git Committer", "Thoth", "Documentation",
        "1. Handle git commits for the team.\n2. Report to Thoth.",
        "1. Thoth tells me to commit.\n2. I run git operations.\n3. I report to Thoth.",
        "- I do NOT write code.\n- I do NOT talk to anyone above Thoth.")); count += 1

    # Embedded doc agents
    for name in DOC_BUILD:
        write_skill("documentation", name, gen_doc_embedded(name, "Build")); count += 1
    for name in DOC_INTELLIGENCE:
        write_skill("documentation", name, gen_doc_embedded(name, "Intelligence")); count += 1
    for name in DOC_QUALITY:
        write_skill("documentation", name, gen_doc_embedded(name, "Quality")); count += 1

    print(f"\n✅ Generated {count} skill files")
    print(f"   Location: {SKILLS_DIR}")

    # Verify count
    total_files = sum(1 for _ in SKILLS_DIR.rglob("*.md"))
    print(f"   Total .md files in skills/: {total_files}")

if __name__ == "__main__":
    main()
