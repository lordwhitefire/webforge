#!/usr/bin/env python3
"""
WebForge Registry MCP — CODE-ENFORCED agent roles + communication hierarchy.

NOT markdown. Markdown describes; code enforces.

This module:
  1. Auto-discovers all agents from ~/webforge/agents/*.py files
  2. Parses each agent's Role line to get title + reports_to
  3. Builds the full hierarchy (who reports to whom)
  4. Enforces role-based access (directors delegate, workers execute)
  5. Enforces chain-of-command communication (no skipping levels)

HIERARCHY LAW:
  An agent can only send messages to:
    - Its direct superior (reports_to)
    - Its direct subordinates
  Any message outside this chain is REJECTED at send time.

  Example: Hermes → Hephaestus → Aurora → Lead-Faro → Sr-Hale → Jr-Ash
  Hermes CANNOT message Jr-Ash directly. The message must go through
  the full chain.
"""

import os
import sys
import re
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))
from common import write_log, success, fail, McpResult


# ── Role tiers ──

ROLE_DIRECTOR = "director"
ROLE_LEAD = "lead"
ROLE_WORKER = "worker"
ROLE_EMBEDDED = "embedded"
ROLE_UTILITY = "utility"

# ── Departments ──

DEPT_EXECUTIVE = "executive"
DEPT_HR = "hr"
DEPT_META = "meta"
DEPT_INTELLIGENCE = "intelligence"
DEPT_BUILD = "build"
DEPT_QUALITY = "quality"
DEPT_DOCUMENTATION = "documentation"


# ── Actions ──

DIRECTOR_ONLY_ACTIONS = {"route", "delegate", "approve", "reject", "correct_agent"}
WORKER_ONLY_ACTIONS = {
    "write_code", "clone_repo", "fix_bug",
    "run_tests", "review_code", "write_docs",
    "research", "deploy",
}

_ACTION_ALIASES = {
    "clone_project": "clone_repo",
    "create_bugfix_task": "fix_bug",
    "create_feature_task": "write_code",
    "generate_docs": "write_docs",
    "run_standup": "run_standup",
    "answer_question": "answer_question",
    "correct_agent": "correct_agent",
    "research": "research",
    "write_code": "write_code",
    "route": "route",
    "delegate": "delegate",
}


def canonical_action(action: str) -> str:
    return _ACTION_ALIASES.get(action, action)


# ── Agent definition ──

class AgentDef:
    def __init__(self, name, role_tier, department, title,
                 reports_to=None, subordinates=None,
                 can_do=None, cannot_do=None, areas="", skill_file=""):
        self.name = name
        self.role_tier = role_tier
        self.department = department
        self.title = title
        self.reports_to = reports_to
        self.subordinates = subordinates or []
        self.can_do = can_do or []
        self.cannot_do = cannot_do or []
        self.areas = areas
        self.skill_file = skill_file

    def is_director(self): return self.role_tier == ROLE_DIRECTOR
    def is_lead(self): return self.role_tier == ROLE_LEAD
    def is_worker(self): return self.role_tier == ROLE_WORKER
    def is_embedded(self): return self.role_tier == ROLE_EMBEDDED

    def can_perform(self, action):
        if action in self.cannot_do:
            return False
        if self.is_director() and action in WORKER_ONLY_ACTIONS:
            return False
        if self.is_worker() and action in DIRECTOR_ONLY_ACTIONS:
            return False
        if self.can_do and action not in self.can_do:
            return False
        return True

    def must_delegate(self, action):
        if self.is_director() and action in WORKER_ONLY_ACTIONS:
            return True
        if self.is_lead() and action in WORKER_ONLY_ACTIONS and self.subordinates:
            return True
        return False

    def can_communicate_with(self, other_name):
        """True if this agent can send messages to other_name (direct superior or subordinate)."""
        other_lower = other_name.lower()
        # Can always talk to direct superior
        if self.reports_to and self.reports_to.lower() == other_lower:
            return True
        # Can always talk to direct subordinates
        for sub in self.subordinates:
            if sub.lower() == other_lower:
                return True
        # Can always talk to self (for self-messages)
        if self.name.lower() == other_lower:
            return True
        return False

    def to_dict(self):
        return {
            "name": self.name, "role_tier": self.role_tier,
            "department": self.department, "title": self.title,
            "reports_to": self.reports_to, "subordinates": self.subordinates,
            "can_do": self.can_do, "cannot_do": self.cannot_do,
            "areas": self.areas, "skill_file": self.skill_file,
        }


# ── Auto-discover agents from files ──

AGENTS: dict[str, AgentDef] = {}

AGENTS_DIR = Path.home() / "webforge" / "agents"

# Known directors and their EXACT hierarchy (from the user's spec)
# Level 1: CEO → Hermes only
# Level 2: Hermes → Athena, Hephaestus, Minos, Thoth, Voss, Daedalus
# Level 3: Department Heads → their direct subordinates only
_DIRECTOR_HIERARCHY = {
    "CEO": {
        "department": DEPT_EXECUTIVE,
        "title": "Chief Executive Officer",
        "reports_to": None,
        "subordinates": ["Hermes"],
        "can_do": ["approve", "reject", "answer_question", "correct_agent"],
        "cannot_do": list(WORKER_ONLY_ACTIONS),
    },
    "Hermes": {
        "department": DEPT_EXECUTIVE,
        "title": "COO / Coordinator — CEO's sole point of contact",
        "reports_to": "CEO",
        "subordinates": ["Athena", "Hephaestus", "Minos", "Thoth", "Voss", "Daedalus"],
        "can_do": ["route", "delegate", "answer_question", "run_standup", "correct_agent",
                   "create_bugfix_task", "create_feature_task", "clone_project"],
        "cannot_do": list(WORKER_ONLY_ACTIONS),
    },
    "Voss": {
        "department": DEPT_HR,
        "title": "HR Director",
        "reports_to": "Hermes",
        "subordinates": ["Rook", "Weld"],
        "can_do": ["route", "delegate", "manage_registry", "assign_agents"],
        "cannot_do": list(WORKER_ONLY_ACTIONS),
    },
    "Daedalus": {
        "department": DEPT_META,
        "title": "Meta Engineering Director",
        "reports_to": "Hermes",
        "subordinates": ["Forge", "Anvil", "Loom", "Compass"],
        "can_do": ["route", "delegate", "add_correction_rule", "learn"],
        "cannot_do": list(WORKER_ONLY_ACTIONS),
    },
    "Athena": {
        "department": DEPT_INTELLIGENCE,
        "title": "Intelligence Director",
        "reports_to": "Hermes",
        # Athena talks to Probe Team lead, Odin Team lead, and Dorian only
        # Since we don't have separate team lead agents, probe-*/odin-* report directly
        "subordinates": [],  # Will be filled by auto-discovery
        "can_do": ["route", "delegate", "research_topic", "investigate"],
        "cannot_do": ["write_code", "clone_repo", "fix_bug", "deploy"],
    },
    "Hephaestus": {
        "department": DEPT_BUILD,
        "title": "Build Director — DELEGATES, never codes",
        "reports_to": "Hermes",
        "subordinates": ["Aurora", "Titan", "Zephyr"],
        "can_do": ["route", "delegate", "answer_question", "report_status"],
        "cannot_do": list(WORKER_ONLY_ACTIONS),
    },
    "Minos": {
        "department": DEPT_QUALITY,
        "title": "Quality Director — DELEGATES, never tests",
        "reports_to": "Hermes",
        # Minos talks to Verdict team, Nemesis team, Janus, Pulse
        # Janus-Core and Pulse-Core are the team leads
        "subordinates": [],  # Will be filled by auto-discovery
        "can_do": ["route", "delegate", "approve_quality", "block_release"],
        "cannot_do": list(WORKER_ONLY_ACTIONS),
    },
    "Thoth": {
        "department": DEPT_DOCUMENTATION,
        "title": "Documentation Director — DELEGATES, never writes docs",
        "reports_to": "Hermes",
        "subordinates": ["Quill", "Scroll", "Stamp", "Ledger", "Draft"],
        "can_do": ["route", "delegate", "approve_docs"],
        "cannot_do": list(WORKER_ONLY_ACTIONS),
    },
}

# Build sub-department leads (Level 4)
_LEAD_HIERARCHY = {
    "Aurora": {"reports_to": "Hephaestus", "subordinates": ["Lead-Faro"],
               "title": "Frontend Lead", "department": DEPT_BUILD},
    "Titan": {"reports_to": "Hephaestus", "subordinates": ["Lead-Terra"],
              "title": "Backend Lead", "department": DEPT_BUILD},
    "Zephyr": {"reports_to": "Hephaestus", "subordinates": ["Lead-Zen"],
               "title": "Database/Infra Lead", "department": DEPT_BUILD},
    "Lead-Faro": {"reports_to": "Aurora",
                  "subordinates": ["Sr-Hale", "Sr-Vance", "Sr-Brook", "Sr-Quill2"],
                  "title": "Frontend Team Lead", "department": DEPT_BUILD},
    "Lead-Terra": {"reports_to": "Titan",
                   "subordinates": ["Sr-Stone", "Sr-Iron", "Sr-Earth", "Sr-Cloud"],
                   "title": "Backend Team Lead", "department": DEPT_BUILD},
    "Lead-Zen": {"reports_to": "Zephyr",
                 "subordinates": ["Sr-Water", "Sr-Wood", "Sr-Fire", "Sr-Steel"],
                 "title": "DB/Infra Team Lead", "department": DEPT_BUILD},
}

# Map file-name underscores to canonical hyphenated names
_NAME_NORMALIZE = {
    "lead_faro": "Lead-Faro",
    "lead_terra": "Lead-Terra",
    "lead_zen": "Lead-Zen",
    "sr_brook": "Sr-Brook",
    "sr_cloud": "Sr-Cloud",
    "sr_earth": "Sr-Earth",
    "sr_fire": "Sr-Fire",
    "sr_hale": "Sr-Hale",
    "sr_iron": "Sr-Iron",
    "sr_quill2": "Sr-Quill2",
    "sr_steel": "Sr-Steel",
    "sr_stone": "Sr-Stone",
    "sr_vance": "Sr-Vance",
    "sr_water": "Sr-Water",
    "sr_wood": "Sr-Wood",
    "memory_architecture": "Memory-Architecture",
    "memory_choices": "Memory-Choices",
    "memory_forgotten": "Memory-Forgotten",
    "patch_core": "Patch-Core",
    "pixel_core": "Pixel-Core",
    "scalpel_core": "Scalpel-Core",
    "sentry_core": "Sentry-Core",
}


def _parse_role_line(filepath: Path) -> tuple:
    """Parse the Role: line from an agent file.
    Returns (title, reports_to, areas).
    """
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception:
        return ("Unknown", None, "")

    # Match: Role: I am X. I am a Y. I report to Z. [I lead N agents.]
    # Or: Role: I am X. I lead the Y sub-department. I report to Z.
    role_match = re.search(
        r'^Role:\s*(.+?)(?:\n|$)', content, re.MULTILINE
    )
    if not role_match:
        return ("Unknown", None, "")

    role_text = role_match.group(1).strip()

    # Extract reports_to
    reports_to = None
    report_match = re.search(r'report to\s+(.+?)(?:\.|$)', role_text)
    if report_match:
        reports_to_raw = report_match.group(1).strip().rstrip('.')
        # Handle "Minos (and Hermes for critical security issues)"
        reports_to = reports_to_raw.split('(')[0].strip()
        # Normalize: "my Senior Developer" → None (will be set by hierarchy)
        if reports_to.lower().startswith("my "):
            reports_to = None

    # Extract title — text between "I am a/an " and ". I report"
    title = "Agent"
    title_match = re.search(
        r'I am (?:the )?(?:a |an )?(.+?)\.(?:\s+I (?:report|lead))',
        role_text
    )
    if title_match:
        title = title_match.group(1).strip()
        # Clean up: "Build Director" not "Build Director. I lead 69 agents"
        title = title.split('.')[0].strip()

    # Extract areas
    areas = ""
    areas_match = re.search(r'^Areas:\s*(.+?)(?:\n|$)', content, re.MULTILINE)
    if areas_match:
        areas = areas_match.group(1).strip()

    return (title, reports_to, areas)


def _infer_department(name: str) -> str:
    """Infer department from agent name prefix."""
    name_lower = name.lower()
    # Check if it's a known director
    for dir_name, dir_info in _DIRECTOR_HIERARCHY.items():
        if name_lower == dir_name.lower():
            return dir_info["department"]
    if name_lower == "ceo":
        return DEPT_EXECUTIVE
    if name_lower in ("aurora", "titan", "zephyr"):
        return DEPT_BUILD
    if name_lower.startswith(("jr-", "sr-")):
        return DEPT_BUILD
    if name_lower.startswith(("lead-",)):
        return DEPT_BUILD
    if name_lower.startswith("probe-") or name_lower.startswith("odin-"):
        return DEPT_INTELLIGENCE
    if name_lower in ("dorian", "draft", "scroll", "ledger"):
        return DEPT_INTELLIGENCE
    if name_lower.startswith("memory-"):
        return DEPT_INTELLIGENCE
    if name_lower.startswith(("scalpel-", "pulse-", "sentry-", "pixel-", "janus-", "verdict-")):
        return DEPT_QUALITY
    if name_lower.endswith("-core"):
        return DEPT_QUALITY
    if name_lower in ("patch-core",):
        return DEPT_META
    if name_lower.startswith("doc-"):
        return DEPT_DOCUMENTATION
    if name_lower in ("quill", "stamp"):
        return DEPT_DOCUMENTATION
    if name_lower in ("forge", "anvil", "loom", "compass"):
        return DEPT_META
    if name_lower in ("rook", "weld"):
        return DEPT_HR
    return DEPT_BUILD  # default


def _infer_role_tier(name: str, title: str, reports_to: str) -> str:
    """Infer role tier from name/title."""
    name_lower = name.lower()
    title_lower = title.lower()

    # Check if it's a known director
    if name_lower in [d.lower() for d in _DIRECTOR_HIERARCHY]:
        return ROLE_DIRECTOR
    if "director" in title_lower:
        return ROLE_DIRECTOR
    if name_lower.startswith("lead-"):
        return ROLE_LEAD
    if "lead" in title_lower and "sub-department" in title_lower:
        return ROLE_LEAD
    if name_lower.startswith("sr-"):
        return ROLE_LEAD  # Seniors are leads — can delegate to juniors
    if name_lower in ("aurora", "titan", "zephyr"):
        return ROLE_LEAD
    if name_lower.endswith("-core"):
        return ROLE_LEAD
    if name_lower.startswith("doc-"):
        return ROLE_EMBEDDED
    return ROLE_WORKER


def _infer_can_do(name: str, role_tier: str, department: str) -> list:
    """Infer can_do actions from role/department."""
    if role_tier == ROLE_DIRECTOR:
        return ["route", "delegate", "answer_question", "correct_agent"]
    if role_tier == ROLE_LEAD:
        return ["delegate", "answer_question", "review_code"]
    # Workers
    if department == DEPT_BUILD:
        return ["write_code", "fix_bug", "clone_repo", "answer_question"]
    if department == DEPT_QUALITY:
        return ["run_tests", "review_code", "answer_question"]
    if department == DEPT_INTELLIGENCE:
        return ["research", "answer_question"]
    if department == DEPT_DOCUMENTATION:
        return ["write_docs", "answer_question"]
    if department == DEPT_META:
        return ["fix_bug", "patch_system", "answer_question"]
    return ["answer_question"]


def _register(agent: AgentDef):
    AGENTS[agent.name.lower()] = agent


def _discover_all_agents():
    """Auto-discover all agents: directors from hardcoded hierarchy, others from files."""
    # 1. Register directors from hardcoded hierarchy
    for name, info in _DIRECTOR_HIERARCHY.items():
        _register(AgentDef(
            name=name,
            role_tier=ROLE_DIRECTOR,
            department=info["department"],
            title=info["title"],
            reports_to=info["reports_to"],
            subordinates=info["subordinates"],
            can_do=info["can_do"],
            cannot_do=info["cannot_do"],
        ))

    # 2. Register leads from hardcoded hierarchy
    for name, info in _LEAD_HIERARCHY.items():
        _register(AgentDef(
            name=name,
            role_tier=ROLE_LEAD,
            department=info["department"],
            title=info["title"],
            reports_to=info["reports_to"],
            subordinates=info["subordinates"],
            can_do=["delegate", "review_code", "answer_question"],
            cannot_do=[],
        ))

    # 3. Scan all .py files for remaining agents
    if not AGENTS_DIR.exists():
        return

    for filepath in sorted(AGENTS_DIR.glob("*.py")):
        file_name = filepath.stem  # e.g. "jr-ash" or "sr_brook"

        # Skip utility files
        if file_name in ("__init__", "base", "ai_client"):
            continue

        # Normalize name (underscores → hyphens for sr_*, lead_*, etc.)
        canonical_name = _NAME_NORMALIZE.get(file_name, file_name)

        # Skip if already registered (directors, leads)
        if canonical_name.lower() in AGENTS:
            continue

        title, reports_to, areas = _parse_role_line(filepath)
        department = _infer_department(canonical_name)
        role_tier = _infer_role_tier(canonical_name, title, reports_to)
        can_do = _infer_can_do(canonical_name, role_tier, department)

        cannot_do = []
        if role_tier == ROLE_DIRECTOR:
            cannot_do = list(WORKER_ONLY_ACTIONS)
        elif role_tier == ROLE_WORKER:
            cannot_do = list(DIRECTOR_ONLY_ACTIONS)

        # Normalize reports_to — handle "my Senior Developer" etc.
        if reports_to and reports_to.lower().startswith("my "):
            # Will be assigned to a senior based on sub-department later
            reports_to = None

        # If reports_to is a director name, make sure casing matches
        if reports_to:
            for dir_name in _DIRECTOR_HIERARCHY:
                if reports_to.lower() == dir_name.lower():
                    reports_to = dir_name
                    break
            for lead_name in _LEAD_HIERARCHY:
                if reports_to.lower() == lead_name.lower():
                    reports_to = lead_name
                    break

        _register(AgentDef(
            name=canonical_name,
            role_tier=role_tier,
            department=department,
            title=title,
            reports_to=reports_to,
            can_do=can_do,
            cannot_do=cannot_do,
            areas=areas,
        ))


def _assign_jr_to_seniors():
    """
    Assign jr-* workers to the right senior based on their sub-department.

    jr-* agents with reports_to=None or reports_to=Hephaestus should be
    assigned to a senior in their sub-department (Frontend/Backend/DB).
    """
    # Build senior → sub-department mapping
    senior_depts = {}
    for sr_name in ["Sr-Brook", "Sr-Hale", "Sr-Vance", "Sr-Quill2"]:
        senior_depts[sr_name] = "Frontend"
    for sr_name in ["Sr-Stone", "Sr-Iron", "Sr-Earth", "Sr-Cloud"]:
        senior_depts[sr_name] = "Backend"
    for sr_name in ["Sr-Water", "Sr-Wood", "Sr-Fire", "Sr-Steel"]:
        senior_depts[sr_name] = "Database/Infra"

    # For each jr-* agent, determine sub-department from title
    for agent in list(AGENTS.values()):
        if not agent.name.lower().startswith("jr-"):
            continue
        if agent.reports_to and agent.reports_to not in ("Hephaestus", None):
            continue  # Already has a proper superior

        title_lower = agent.title.lower()
        if "frontend" in title_lower:
            sub_dept = "Frontend"
        elif "backend" in title_lower:
            sub_dept = "Backend"
        elif "database" in title_lower or "infra" in title_lower:
            sub_dept = "Database/Infra"
        else:
            sub_dept = "Frontend"  # default

        # Find a senior in this sub-department
        for sr_name, sr_dept in senior_depts.items():
            if sr_dept == sub_dept:
                agent.reports_to = sr_name
                # Add to senior's subordinates
                sr_agent = AGENTS.get(sr_name.lower())
                if sr_agent and agent.name not in sr_agent.subordinates:
                    sr_agent.subordinates.append(agent.name)
                break


def _build_hierarchy():
    """Build subordinates lists from reports_to relationships."""
    # Clear existing subordinates
    for agent in AGENTS.values():
        agent.subordinates = []

    # For each agent, add it to its superior's subordinates
    for agent in AGENTS.values():
        if agent.reports_to:
            superior = AGENTS.get(agent.reports_to.lower())
            if superior:
                if agent.name not in superior.subordinates:
                    superior.subordinates.append(agent.name)
            else:
                # Superior not found — try to find by partial match
                for sup_name, sup_agent in AGENTS.items():
                    if sup_agent.name.lower() == agent.reports_to.lower():
                        if agent.name not in sup_agent.subordinates:
                            sup_agent.subordinates.append(agent.name)
                        break


def _link_skill_files():
    """
    Link each agent to its skill .md file in ~/webforge/skills/<dept>/<name>.md.

    Skill files use the agent name (lowercase). Some older files use
    underscores (sr_brook.md) instead of hyphens (sr-brook.md) — we
    normalize for matching.
    """
    skills_dir = Path.home() / "webforge" / "skills"
    if not skills_dir.exists():
        return

    # Build a map of skill file paths, indexed by normalized name
    all_skills = {}
    for dept_dir in skills_dir.iterdir():
        if not dept_dir.is_dir():
            continue
        for skill_file in dept_dir.glob("*.md"):
            name = skill_file.stem.lower()
            rel_path = str(skill_file.relative_to(skills_dir))
            all_skills[name] = rel_path
            # Also index under hyphen-normalized name
            normalized = name.replace("_", "-")
            all_skills[normalized] = rel_path

    # Link each agent to its skill file
    for agent in AGENTS.values():
        name_lower = agent.name.lower()
        if name_lower in all_skills:
            agent.skill_file = all_skills[name_lower]


# Discover, assign juniors, and build hierarchy
_discover_all_agents()
_assign_jr_to_seniors()
_build_hierarchy()
_link_skill_files()


# ── Public API ──

def get_agent(name: str) -> AgentDef | None:
    return AGENTS.get(name.lower())


def get_director(department: str) -> AgentDef | None:
    for agent in AGENTS.values():
        if agent.department == department and agent.is_director():
            return agent
    return None


def get_subordinates(name: str) -> list:
    agent = get_agent(name)
    if not agent:
        return []
    return [get_agent(s) for s in agent.subordinates if get_agent(s)]


def get_workers_in_department(department: str) -> list:
    return [a for a in AGENTS.values()
            if a.department == department and a.is_worker()]


def get_all_directors():
    return [a for a in AGENTS.values() if a.is_director()]


def get_all_leads():
    return [a for a in AGENTS.values() if a.is_lead()]


def get_all_workers():
    return [a for a in AGENTS.values() if a.is_worker()]


def can_perform(name: str, action: str) -> bool:
    agent = get_agent(name)
    if not agent:
        return False
    return agent.can_perform(action)


def must_delegate(name: str, action: str) -> bool:
    agent = get_agent(name)
    if not agent:
        return False
    return agent.must_delegate(action)


def can_communicate(from_agent: str, to_agent: str) -> bool:
    """Check if from_agent can send messages to to_agent (chain-of-command)."""
    agent = get_agent(from_agent)
    if not agent:
        return False
    return agent.can_communicate_with(to_agent)


def enforce_communication(from_agent: str, to_agent: str) -> McpResult:
    """
    Enforce chain-of-command communication.
    Returns success() if allowed, fail() with explanation if not.

    An agent can only message:
      - Its direct superior (reports_to)
      - Its direct subordinates
    """
    agent = get_agent(from_agent)
    if not agent:
        return fail(f"Unknown agent: {from_agent}")

    target = get_agent(to_agent)
    if not target:
        return fail(f"Unknown agent: {to_agent}")

    if agent.can_communicate_with(to_agent):
        return success()

    # Build the correct chain
    chain = _find_chain(from_agent, to_agent)
    if chain:
        chain_str = " → ".join(chain)
        return fail(
            f"CHAIN-OF-COMMAND VIOLATION — @{from_agent} cannot message @{to_agent} directly.\n"
            f"  {from_agent} can only talk to: {agent.reports_to or '(no superior)'}"
            f"{', ' + ', '.join(agent.subordinates) if agent.subordinates else ''}\n"
            f"  Correct chain: {chain_str}"
        )

    return fail(
        f"CHAIN-OF-COMMAND VIOLATION — @{from_agent} cannot message @{to_agent}.\n"
        f"  No communication path exists between these agents.\n"
        f"  {from_agent} can only talk to: {agent.reports_to or '(no superior)'}"
        f"{', ' + ', '.join(agent.subordinates) if agent.subordinates else ''}"
    )


def _find_chain(from_agent: str, to_agent: str) -> list:
    """Find the communication chain from one agent to another (BFS)."""
    from_lower = from_agent.lower()
    to_lower = to_agent.lower()

    if from_lower == to_lower:
        return [from_agent]

    # BFS up and down the tree
    visited = {from_lower}
    queue = [(from_agent, [from_agent])]

    while queue:
        current, path = queue.pop(0)
        current_lower = current.lower()

        # Check subordinates
        agent = get_agent(current)
        if agent:
            for sub in agent.subordinates:
                if sub.lower() == to_lower:
                    return path + [sub]
                if sub.lower() not in visited:
                    visited.add(sub.lower())
                    queue.append((sub, path + [sub]))

            # Check superior
            if agent.reports_to:
                sup_lower = agent.reports_to.lower()
                if sup_lower == to_lower:
                    return path + [agent.reports_to]
                if sup_lower not in visited:
                    visited.add(sup_lower)
                    queue.append((agent.reports_to, path + [agent.reports_to]))

    return []


def enforce_role(name: str, action: str) -> McpResult:
    """Enforce role-based access control."""
    agent = get_agent(name)
    if not agent:
        return fail(f"Unknown agent: {name}")

    if agent.can_perform(action):
        return success()

    if agent.must_delegate(action):
        subs = get_subordinates(name)
        capable = [s for s in subs if s.can_perform(action)]
        if capable:
            names = ", ".join(s.name for s in capable[:5])
            return fail(
                f"DELEGATE REQUIRED — {name} is a {agent.role_tier} "
                f"({agent.title}) and must delegate '{action}' to a subordinate.\n"
                f"Capable subordinates: {names}\n"
                f"Use delegate_to() to assign this work."
            )
        else:
            return fail(
                f"DELEGATE REQUIRED — {name} is a {agent.role_tier} "
                f"but no subordinate can perform '{action}'."
            )

    return fail(
        f"ROLE VIOLATION — {name} ({agent.role_tier}) cannot perform '{action}'.\n"
        f"Allowed: {agent.can_do}\n"
        f"Forbidden: {agent.cannot_do}"
    )


def pick_worker(department: str, action: str = None) -> AgentDef | None:
    workers = get_workers_in_department(department)
    if not workers:
        return None
    if action:
        workers = [w for w in workers if w.can_perform(action)]
    return workers[0] if workers else None


def pick_worker_for_task(task: dict) -> AgentDef | None:
    task_type = task.get("type", "feature")
    TYPE_TO_DEPT = {
        "feature": DEPT_BUILD, "bugfix": DEPT_BUILD, "refactor": DEPT_BUILD,
        "test": DEPT_QUALITY, "docs": DEPT_DOCUMENTATION,
        "architecture": DEPT_INTELLIGENCE,
    }
    dept = TYPE_TO_DEPT.get(task_type, DEPT_BUILD)
    action_map = {
        "feature": "write_code", "bugfix": "fix_bug", "refactor": "write_code",
        "test": "run_tests", "docs": "write_docs", "architecture": "research",
    }
    action = action_map.get(task_type, "write_code")
    return pick_worker(dept, action)


def delegate_to(director_name: str, task: dict, action: str = None) -> dict:
    director = get_agent(director_name)
    if not director:
        return {"error": f"Unknown director: {director_name}"}

    worker = pick_worker_for_task(task)
    if not worker:
        return {"error": f"No worker available for task type {task.get('type')}"}

    return {
        "director": director_name,
        "worker": worker.name,
        "worker_title": worker.title,
        "worker_areas": worker.areas,
        "task_id": task.get("id"),
        "message": f"@{director_name} delegated task {task.get('id')} to @{worker.name}",
    }


def info() -> dict:
    return {
        "id": "m-registry",
        "name": "Registry MCP (auto-discovered + chain-enforced)",
        "tier": 1,
        "owner": "HR",
        "job": "Code-enforced agent roles + chain-of-command communication. Directors delegate, workers execute. No skipping levels.",
        "total_agents": len(AGENTS),
        "directors": len(get_all_directors()),
        "leads": len(get_all_leads()),
        "workers": len(get_all_workers()),
    }


# ── CLI ──

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Registry MCP — auto-discovered + chain-enforced")
        print("Usage: python registry.py <command>")
        print()
        print("Commands:")
        print("  info                          Show registry stats")
        print("  show <name>                   Show agent definition")
        print("  directors                     List all directors")
        print("  can-comm <from> <to>          Check if from can message to")
        print("  chain <from> <to>             Show communication chain")
        print("  subordinates <name>           List direct subordinates")
        print("  hierarchy <name>              Show full up/down chain")
        sys.exit(1)

    import json
    cmd = sys.argv[1]

    if cmd == "info":
        print(json.dumps(info(), indent=2))

    elif cmd == "show":
        if len(sys.argv) < 3:
            print("Usage: show <name>")
            sys.exit(1)
        agent = get_agent(sys.argv[2])
        if not agent:
            print(f"Agent not found: {sys.argv[2]}")
            sys.exit(1)
        print(json.dumps(agent.to_dict(), indent=2))

    elif cmd == "directors":
        for d in get_all_directors():
            subs = len(d.subordinates)
            print(f"  {d.name:20s} {d.department:15s} {d.title[:40]:40s} ({subs} subs)")

    elif cmd == "can-comm":
        if len(sys.argv) < 4:
            print("Usage: can-comm <from> <to>")
            sys.exit(1)
        r = enforce_communication(sys.argv[2], sys.argv[3])
        if r.ok:
            print(f"✅ @{sys.argv[2]} CAN message @{sys.argv[3]}")
        else:
            print(f"❌ @{sys.argv[2]} CANNOT message @{sys.argv[3]}:")
            print(f"   {r.error}")

    elif cmd == "chain":
        if len(sys.argv) < 4:
            print("Usage: chain <from> <to>")
            sys.exit(1)
        chain = _find_chain(sys.argv[2], sys.argv[3])
        if chain:
            print(" → ".join(chain))
        else:
            print(f"No chain found from {sys.argv[2]} to {sys.argv[3]}")

    elif cmd == "subordinates":
        if len(sys.argv) < 3:
            print("Usage: subordinates <name>")
            sys.exit(1)
        subs = get_subordinates(sys.argv[2])
        if not subs:
            print(f"No subordinates for {sys.argv[2]}")
        for s in subs:
            print(f"  {s.name:20s} {s.title[:50]:50s}")

    elif cmd == "hierarchy":
        if len(sys.argv) < 3:
            print("Usage: hierarchy <name>")
            sys.exit(1)
        agent = get_agent(sys.argv[2])
        if not agent:
            print(f"Agent not found: {sys.argv[2]}")
            sys.exit(1)
        print(f"Agent: {agent.name} ({agent.title})")
        print(f"Department: {agent.department}")
        print(f"Role tier: {agent.role_tier}")
        print(f"Reports to: {agent.reports_to or '(top of chain)'}")
        print(f"Subordinates ({len(agent.subordinates)}):")
        for sub in agent.subordinates:
            sub_agent = get_agent(sub)
            if sub_agent:
                print(f"  - {sub_agent.name} ({sub_agent.title})")

    else:
        print(f"Unknown command: {cmd}")
