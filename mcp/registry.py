#!/usr/bin/env python3
"""
WebForge Registry MCP — CODE-ENFORCED agent roles.

NOT markdown. Markdown describes; code enforces.

This module defines every agent's:
  - role_tier:    director | lead | worker | embedded | utility
  - department:   executive | hr | meta | intelligence | build | quality | documentation
  - reports_to:   who they report to (None for CEO)
  - subordinates: list of agents they can delegate to
  - can_do:       actions they're allowed to perform
  - cannot_do:    actions explicitly forbidden
  - areas:        for workers, the area numbers they own

ENFORCEMENT (in base.py):
  - Directors (Hephaestus, Athena, Minos, Thoth, Daedalus, Voss) REFUSE
    to do worker actions (write_code, clone_repo, run_tests, etc.).
    They MUST delegate to a subordinate.
  - Workers REFUSE to do director actions (route, delegate, approve).
  - Leads (Aurora, Titan, Zephyr) can delegate within their sub-department
    but report up to their director.

This stops the recurring bug where Hephaestus (a director) was cloning
repos himself instead of delegating to jr-ash / jr-aster / etc.
"""

import os
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))
from common import write_log, success, fail, McpResult


# ── Role tiers ──

ROLE_DIRECTOR = "director"    # leads a department, delegates to leads/workers
ROLE_LEAD = "lead"            # leads a sub-department, delegates to workers
ROLE_WORKER = "worker"        # does the actual work
ROLE_EMBEDDED = "embedded"    # attached to another agent for docs/quality
ROLE_UTILITY = "utility"      # system tools (ai_client, base, etc.)


# ── Departments ──

DEPT_EXECUTIVE = "executive"
DEPT_HR = "hr"
DEPT_META = "meta"
DEPT_INTELLIGENCE = "intelligence"
DEPT_BUILD = "build"
DEPT_QUALITY = "quality"
DEPT_DOCUMENTATION = "documentation"


# ── Action types ──

# Director-only actions
ACTION_ROUTE = "route"
ACTION_DELEGATE = "delegate"
ACTION_APPROVE = "approve"
ACTION_REJECT = "reject"
ACTION_CORRECT_AGENT = "correct_agent"

# Worker actions
ACTION_WRITE_CODE = "write_code"
ACTION_CLONE_REPO = "clone_repo"
ACTION_FIX_BUG = "fix_bug"
ACTION_RUN_TESTS = "run_tests"
ACTION_REVIEW_CODE = "review_code"
ACTION_WRITE_DOCS = "write_docs"
ACTION_RESEARCH = "research"
ACTION_DEPLOY = "deploy"

# Shared actions
ACTION_ANSWER_QUESTION = "answer_question"
ACTION_RUN_STANDUP = "run_standup"
ACTION_REPORT_STATUS = "report_status"


# Actions that are DIRECTOR-ONLY — workers doing these must be refused
DIRECTOR_ONLY_ACTIONS = {
    ACTION_ROUTE, ACTION_DELEGATE, ACTION_APPROVE, ACTION_REJECT,
    ACTION_CORRECT_AGENT,
}

# Actions that are WORKER-ONLY — directors doing these must be refused
# (they should delegate instead)
WORKER_ONLY_ACTIONS = {
    ACTION_WRITE_CODE, ACTION_CLONE_REPO, ACTION_FIX_BUG,
    ACTION_RUN_TESTS, ACTION_REVIEW_CODE, ACTION_WRITE_DOCS,
    ACTION_RESEARCH, ACTION_DEPLOY,
}


# ── Agent definition ──

class AgentDef:
    """Definition of one agent. Code, not markdown."""

    def __init__(
        self,
        name: str,
        role_tier: str,
        department: str,
        title: str,
        reports_to: Optional[str] = None,
        subordinates: Optional[list] = None,
        can_do: Optional[list] = None,
        cannot_do: Optional[list] = None,
        areas: str = "",
        skill_file: str = "",
    ):
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

    def is_director(self) -> bool:
        return self.role_tier == ROLE_DIRECTOR

    def is_lead(self) -> bool:
        return self.role_tier == ROLE_LEAD

    def is_worker(self) -> bool:
        return self.role_tier == ROLE_WORKER

    def is_embedded(self) -> bool:
        return self.role_tier == ROLE_EMBEDDED

    def can_perform(self, action: str) -> bool:
        """Check if this agent can perform an action."""
        if action in self.cannot_do:
            return False
        # Directors can't do worker-only actions
        if self.is_director() and action in WORKER_ONLY_ACTIONS:
            return False
        # Workers can't do director-only actions
        if self.is_worker() and action in DIRECTOR_ONLY_ACTIONS:
            return False
        if self.can_do and action not in self.can_do:
            return False
        return True

    def must_delegate(self, action: str) -> bool:
        """True if this agent must delegate this action instead of doing it."""
        if self.is_director() and action in WORKER_ONLY_ACTIONS:
            return True
        if self.is_lead() and action in WORKER_ONLY_ACTIONS and self.subordinates:
            return True
        return False

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "role_tier": self.role_tier,
            "department": self.department,
            "title": self.title,
            "reports_to": self.reports_to,
            "subordinates": self.subordinates,
            "can_do": self.can_do,
            "cannot_do": self.cannot_do,
            "areas": self.areas,
            "skill_file": self.skill_file,
        }

    def __repr__(self):
        return f"AgentDef({self.name}, {self.role_tier}, {self.department})"


# ── The registry — all 286 agents as code ──

# Build sub-department leads first (so we can reference their workers)
_AURORA_WORKERS = [f"jr-{n}" for n in [
    "aster", "cole", "finch", "hawk", "cliff", "fern", "cove", "bram",
    "lake", "ocean", "pine", "willow", "marsh", "drift", "ember",
]]  # 15 frontend workers

_TITAN_WORKERS = [f"jr-{n}" for n in [
    "granite", "copper", "bronze", "gold", "birch", "cedar", "chromium",
    "cobalt", "oak", "hill", "mountain", "marble", "pike", "talon",
]]  # 14 backend workers

_ZEPHYR_WORKERS = [f"jr-{n}" for n in [
    "ash", "flame", "coal", "ember", "nickel", "cobalt", "lake2",
]]  # 7 database/infra workers (ember may overlap — fixed below)

# All build workers (for Hephaestus's subordinates list)
_ALL_BUILD_WORKERS = sorted(set(_AURORA_WORKERS + _TITAN_WORKERS + _ZEPHYR_WORKERS))

# Intelligence workers (Probe + Odin teams — 17 each = 34)
_PROBE_WORKERS = [f"probe-{n}" for n in [
    "orion", "wren", "beacon", "sable", "quartz", "flint", "ridge",
    "marsh", "coral", "vale", "thorne", "brisk", "hollow", "crag",
    "drift", "ember", "lyric",
]]

_ODIN_WORKERS = [f"odin-{n}" for n in [
    "aster", "birch", "bramble", "cliff", "cove", "fern", "frost",
    "glade", "heron", "marrow", "moss", "pike", "reed", "sage",
    "slate", "talon", "wisp",
]]

_ALL_INTELLIGENCE_WORKERS = _PROBE_WORKERS + _ODIN_WORKERS

# Documentation embedded agents (17 per department × 3 = 51)
_DOC_BUILD = [f"doc-build-{n}" for n in [
    "aster", "birch", "bramble", "cliff", "cove", "fern", "frost",
    "glade", "heron", "marrow", "moss", "pike", "reed", "sage",
    "slate", "talon", "wisp",
]]

_DOC_INTELLIGENCE = [f"doc-intelligence-{n}" for n in _DOC_BUILD]
_DOC_QUALITY = [f"doc-quality-{n}" for n in _DOC_BUILD]

_ALL_DOC_EMBEDDED = _DOC_BUILD + _DOC_INTELLIGENCE + _DOC_QUALITY

# Quality sub-departments — Minos leads 108 agents across multiple cores
# (Scalpel, Pulse, Sentry, Pixel, Janus — each is a lead with workers)
_QUALITY_LEADS = ["Scalpel-Core", "Pulse-Core", "Sentry-Core", "Pixel-Core", "Janus-Core"]


# ── THE REGISTRY ──

AGENTS: dict[str, AgentDef] = {}


def _register(agent: AgentDef):
    AGENTS[agent.name.lower()] = agent


# ── Executive ──

_register(AgentDef(
    name="CEO",
    role_tier=ROLE_DIRECTOR,
    department=DEPT_EXECUTIVE,
    title="Chief Executive Officer (the developer)",
    reports_to=None,
    subordinates=["Hermes"],
    can_do=[ACTION_APPROVE, ACTION_REJECT, ACTION_ANSWER_QUESTION, ACTION_CORRECT_AGENT],
    cannot_do=[ACTION_WRITE_CODE, ACTION_CLONE_REPO, ACTION_RUN_TESTS],
))

_register(AgentDef(
    name="Hermes",
    role_tier=ROLE_DIRECTOR,
    department=DEPT_EXECUTIVE,
    title="COO / Coordinator — the CEO's sole point of contact",
    reports_to="CEO",
    subordinates=["Voss", "Daedalus", "Athena", "Hephaestus", "Minos", "Thoth"],
    can_do=[
        ACTION_ROUTE, ACTION_DELEGATE, ACTION_ANSWER_QUESTION,
        ACTION_RUN_STANDUP, ACTION_CORRECT_AGENT,
        "create_bugfix_task", "create_feature_task", "clone_project",
    ],
    cannot_do=[
        ACTION_WRITE_CODE, ACTION_CLONE_REPO, ACTION_FIX_BUG,
        ACTION_RUN_TESTS, ACTION_REVIEW_CODE, ACTION_WRITE_DOCS,
        ACTION_RESEARCH, ACTION_DEPLOY,
    ],
))


# ── HR ──

_register(AgentDef(
    name="Voss",
    role_tier=ROLE_DIRECTOR,
    department=DEPT_HR,
    title="HR Director",
    reports_to="Hermes",
    subordinates=["Rook", "Weld"],
    can_do=[ACTION_ROUTE, ACTION_DELEGATE, "manage_registry", "assign_agents"],
    cannot_do=WORKER_ONLY_ACTIONS,
))

_register(AgentDef(
    name="Rook",
    role_tier=ROLE_WORKER,
    department=DEPT_HR,
    title="Registry Manager",
    reports_to="Voss",
    can_do=["manage_registry", ACTION_ANSWER_QUESTION],
))

_register(AgentDef(
    name="Weld",
    role_tier=ROLE_WORKER,
    department=DEPT_HR,
    title="Assignment Officer",
    reports_to="Voss",
    can_do=["assign_agents", ACTION_ANSWER_QUESTION],
))


# ── Meta Engineering ──

_register(AgentDef(
    name="Daedalus",
    role_tier=ROLE_DIRECTOR,
    department=DEPT_META,
    title="Meta Engineering Director — maintains WebForge itself",
    reports_to="Hermes",
    subordinates=["Forge", "Anvil", "Loom", "Compass"],
    can_do=[ACTION_ROUTE, ACTION_DELEGATE, "add_correction_rule", "learn"],
    cannot_do=WORKER_ONLY_ACTIONS,
))

_register(AgentDef(
    name="Forge",
    role_tier=ROLE_WORKER,
    department=DEPT_META,
    title="MCP Builder — builds new MCPs",
    reports_to="Daedalus",
    can_do=["build_mcp", ACTION_WRITE_CODE],
))

_register(AgentDef(
    name="Anvil",
    role_tier=ROLE_WORKER,
    department=DEPT_META,
    title="MCP Fixer — fixes bugs in existing MCPs",
    reports_to="Daedalus",
    can_do=["fix_mcp", ACTION_FIX_BUG],
))

_register(AgentDef(
    name="Loom",
    role_tier=ROLE_WORKER,
    department=DEPT_META,
    title="Agent Creator — creates new agents",
    reports_to="Daedalus",
    can_do=["create_agent"],
))

_register(AgentDef(
    name="Compass",
    role_tier=ROLE_WORKER,
    department=DEPT_META,
    title="System Tester — tests the WebForge system",
    reports_to="Daedalus",
    can_do=[ACTION_RUN_TESTS, "test_system"],
))


# ── Intelligence ──

_register(AgentDef(
    name="Athena",
    role_tier=ROLE_DIRECTOR,
    department=DEPT_INTELLIGENCE,
    title="Intelligence Director — leads 38 research agents",
    reports_to="Hermes",
    subordinates=_ALL_INTELLIGENCE_WORKERS,
    can_do=[ACTION_ROUTE, ACTION_DELEGATE, "research_topic", "investigate"],
    cannot_do=[ACTION_WRITE_CODE, ACTION_CLONE_REPO, ACTION_FIX_BUG, ACTION_DEPLOY],
))

# Register all probe-* and odin-* workers
for name in _PROBE_WORKERS + _ODIN_WORKERS:
    _register(AgentDef(
        name=name,
        role_tier=ROLE_WORKER,
        department=DEPT_INTELLIGENCE,
        title=f"Intelligence Researcher ({name})",
        reports_to="Athena",
        can_do=[ACTION_RESEARCH, "investigate_area", ACTION_ANSWER_QUESTION],
        areas="varies",
    ))


# ── Build ──

_register(AgentDef(
    name="Hephaestus",
    role_tier=ROLE_DIRECTOR,
    department=DEPT_BUILD,
    title="Build Director — leads 69 build agents. DELEGATES, never codes.",
    reports_to="Hermes",
    subordinates=["Aurora", "Titan", "Zephyr"] + _ALL_BUILD_WORKERS,
    can_do=[
        ACTION_ROUTE, ACTION_DELEGATE, "assign_to_subordinate",
        ACTION_ANSWER_QUESTION, "report_build_status",
    ],
    cannot_do=[
        ACTION_WRITE_CODE, ACTION_CLONE_REPO, ACTION_FIX_BUG,
        ACTION_RUN_TESTS, ACTION_REVIEW_CODE, ACTION_WRITE_DOCS,
        ACTION_RESEARCH, ACTION_DEPLOY,
    ],
    skill_file="build/hephaestus.md",
))

# Sub-department leads
_register(AgentDef(
    name="Aurora",
    role_tier=ROLE_LEAD,
    department=DEPT_BUILD,
    title="Frontend Lead — leads frontend workers",
    reports_to="Hephaestus",
    subordinates=_AURORA_WORKERS,
    can_do=[ACTION_DELEGATE, "review_frontend", ACTION_ANSWER_QUESTION],
    cannot_do=[ACTION_WRITE_CODE, ACTION_CLONE_REPO],
))

_register(AgentDef(
    name="Titan",
    role_tier=ROLE_LEAD,
    department=DEPT_BUILD,
    title="Backend Lead — leads backend workers",
    reports_to="Hephaestus",
    subordinates=_TITAN_WORKERS,
    can_do=[ACTION_DELEGATE, "review_backend", ACTION_ANSWER_QUESTION],
    cannot_do=[ACTION_WRITE_CODE, ACTION_CLONE_REPO],
))

_register(AgentDef(
    name="Zephyr",
    role_tier=ROLE_LEAD,
    department=DEPT_BUILD,
    title="Database/Infra Lead — leads DB/infra workers",
    reports_to="Hephaestus",
    subordinates=_ZEPHYR_WORKERS,
    can_do=[ACTION_DELEGATE, "review_database", ACTION_ANSWER_QUESTION],
    cannot_do=[ACTION_WRITE_CODE, ACTION_CLONE_REPO],
))

# All jr-* build workers
_JR_ROLES = {
    "ash": ("Junior Database/Infra Developer", "51-55", "zephyr"),
    "aster": ("Junior Frontend Developer", "81-82", "aurora"),
    "birch": ("Junior Backend Developer", "56-60", "titan"),
    "bram": ("Junior Frontend Developer", "71-75", "aurora"),
    "bronze": ("Junior Backend Developer", "26-30", "titan"),
    "cedar": ("Junior Backend Developer", "51-55", "titan"),
    "chromium": ("Junior Backend Developer", "71-75", "titan"),
    "cliff": ("Junior Frontend Developer", "46-50", "aurora"),
    "coal": ("Junior Database/Infra Developer", "56-60", "zephyr"),
    "cobalt": ("Junior Backend Developer", "81-82", "titan"),
    "cole": ("Junior Frontend Developer", "16-20", "aurora"),
    "copper": ("Junior Backend Developer", "21-25", "titan"),
    "cove": ("Junior Frontend Developer", "66-70", "aurora"),
    "ember": ("Junior Database/Infra Developer", "46-50", "zephyr"),
    "fern": ("Junior Frontend Developer", "51-55", "aurora"),
    "finch": ("Junior Frontend Developer", "06-10", "aurora"),
    "flame": ("Junior Database/Infra Developer", "41-45", "zephyr"),
    "gold": ("Junior Backend Developer", "36-40", "titan"),
    "granite": ("Junior Backend Developer", "01-05", "titan"),
    "hawk": ("Junior Frontend Developer", "01-05", "aurora"),
    "hill": ("Junior Backend Developer", "61-65", "titan"),
    "lake": ("Junior Frontend Developer", "11-15", "aurora"),
    "lake2": ("Junior Frontend Developer", "76-80", "aurora"),
    "marble": ("Junior Backend Developer", "31-35", "titan"),
    "moss": ("Junior Frontend Developer", "61-65", "aurora"),
    "mountain": ("Junior Backend Developer", "41-45", "titan"),
    "nickel": ("Junior Database/Infra Developer", "21-25", "zephyr"),
    "oak": ("Junior Backend Developer", "11-15", "titan"),
    "ocean": ("Junior Frontend Developer", "26-30", "aurora"),
    "pike": ("Junior Backend Developer", "21-25", "titan"),
    "pine": ("Junior Frontend Developer", "21-25", "aurora"),
    "talon": ("Junior Backend Developer", "16-20", "titan"),
    "willow": ("Junior Frontend Developer", "31-35", "aurora"),
    # Fill in the rest generically
}

# Generic roles for any jr-* not in the dict above
for f in Path(Path.home() / "webforge" / "agents").glob("jr-*.py"):
    name = f.stem  # jr-ash
    suffix = name.replace("jr-", "")
    if suffix not in _JR_ROLES:
        _JR_ROLES[suffix] = ("Junior Build Developer", "varies", "hephaestus")

for suffix, (title, areas, lead) in _JR_ROLES.items():
    name = f"jr-{suffix}"
    _register(AgentDef(
        name=name,
        role_tier=ROLE_WORKER,
        department=DEPT_BUILD,
        title=title,
        reports_to=lead.capitalize() if lead != "hephaestus" else "Hephaestus",
        can_do=[
            ACTION_WRITE_CODE, ACTION_FIX_BUG, ACTION_CLONE_REPO,
            ACTION_ANSWER_QUESTION, ACTION_REPORT_STATUS,
        ],
        areas=areas,
    ))


# ── Quality ──

_register(AgentDef(
    name="Minos",
    role_tier=ROLE_DIRECTOR,
    department=DEPT_QUALITY,
    title="Quality Director — leads 108 quality agents. DELEGATES, never tests.",
    reports_to="Hermes",
    subordinates=_QUALITY_LEADS,
    can_do=[ACTION_ROUTE, ACTION_DELEGATE, "approve_quality", "block_release"],
    cannot_do=[ACTION_WRITE_CODE, ACTION_CLONE_REPO, ACTION_FIX_BUG, ACTION_RUN_TESTS],
))

for lead_name in _QUALITY_LEADS:
    _register(AgentDef(
        name=lead_name,
        role_tier=ROLE_LEAD,
        department=DEPT_QUALITY,
        title=f"Quality Lead ({lead_name})",
        reports_to="Minos",
        can_do=[ACTION_DELEGATE, ACTION_RUN_TESTS, ACTION_REVIEW_CODE],
    ))


# ── Documentation ──

_register(AgentDef(
    name="Thoth",
    role_tier=ROLE_DIRECTOR,
    department=DEPT_DOCUMENTATION,
    title="Documentation Director — leads 60 doc agents. DELEGATES, never writes docs.",
    reports_to="Hermes",
    subordinates=_ALL_DOC_EMBEDDED + ["Quill"],
    can_do=[ACTION_ROUTE, ACTION_DELEGATE, "approve_docs"],
    cannot_do=[ACTION_WRITE_CODE, ACTION_CLONE_REPO, ACTION_WRITE_DOCS],
))

_register(AgentDef(
    name="Quill",
    role_tier=ROLE_WORKER,
    department=DEPT_DOCUMENTATION,
    title="Documentation Writer",
    reports_to="Thoth",
    can_do=[ACTION_WRITE_DOCS],
))

# Register all doc-* embedded agents
for name in _ALL_DOC_EMBEDDED:
    dept = name.split("-")[1]  # "build", "intelligence", "quality"
    _register(AgentDef(
        name=name,
        role_tier=ROLE_EMBEDDED,
        department=DEPT_DOCUMENTATION,
        title=f"Embedded Documentation Agent ({dept})",
        reports_to="Thoth",
        can_do=[ACTION_WRITE_DOCS],
        areas=dept,
    ))


# ── Additional agent data (registered after public API is defined) ──

# Quality sub-departments (5 cores × 17 workers each = 85)
_QUALITY_CORE_NAMES = {
    "Scalpel-Core": ("Code Review Lead", "scalpel"),
    "Pulse-Core": ("Testing Lead", "pulse"),
    "Sentry-Core": ("Security Lead", "sentry"),
    "Pixel-Core": ("Visual/UI Testing Lead", "pixel"),
    "Janus-Core": ("Standards/Compliance Lead", "janus"),
}

_QUALITY_WORKER_SUFFIXES = [
    "aster", "birch", "bramble", "cliff", "cove", "fern", "frost",
    "glade", "heron", "marrow", "moss", "pike", "reed", "sage",
    "slate", "talon", "wisp",
]

_VERDICT_NAMES = [
    "verdict-brook", "verdict-clove", "verdict-fenn", "verdict-garnet",
    "verdict-hawke", "verdict-iris", "verdict-jade", "verdict-kite",
    "verdict-lark", "verdict-mint", "verdict-nova", "verdict-onyx",
    "verdict-prism", "verdict-quill", "verdict-rowan", "verdict-sage",
    "verdict-thorn",
]

_SR_BUILD_AGENTS = [
    ("sr_brook", "Senior Frontend Developer", "Aurora"),
    ("sr_cloud", "Senior Frontend Developer", "Aurora"),
    ("sr_earth", "Senior Backend Developer", "Titan"),
    ("sr_fire", "Senior Backend Developer", "Titan"),
    ("sr_hale", "Senior Database/Infra Developer", "Zephyr"),
    ("sr_iron", "Senior Backend Developer", "Titan"),
    ("sr_quill2", "Senior Frontend Developer", "Aurora"),
    ("sr_steel", "Senior Backend Developer", "Titan"),
    ("sr_stone", "Senior Database/Infra Developer", "Zephyr"),
    ("sr_vance", "Senior Frontend Developer", "Aurora"),
    ("sr_water", "Senior Backend Developer", "Titan"),
    ("sr_wood", "Senior Database/Infra Developer", "Zephyr"),
]

_INTEL_LEADS = [
    ("lead_faro", "Intelligence Lead", "Athena"),
    ("lead_terra", "Intelligence Lead", "Athena"),
    ("lead_zen", "Intelligence Lead", "Athena"),
]

_INTEL_SPECIALISTS = [
    ("dorian", "Intelligence Specialist", "Athena"),
    ("draft", "Intelligence Specialist", "Athena"),
    ("scroll", "Intelligence Specialist", "Athena"),
    ("ledger", "Intelligence Specialist", "Athena"),
    ("memory_architecture", "Architecture Memory Specialist", "Athena"),
    ("memory_choices", "Decision Memory Specialist", "Athena"),
    ("memory_forgotten", "Legacy Memory Specialist", "Athena"),
]

_META_SPECIALISTS = [
    ("patch_core", "Patch Core Specialist", "Daedalus"),
    ("pixel_core", "Pixel Core Specialist", "Daedalus"),
    ("scalpel_core", "Scalpel Core Specialist", "Daedalus"),
    ("sentry_core", "Sentry Core Specialist", "Daedalus"),
]

_DOC_SPECIALISTS = [
    ("stamp", "Documentation Stamper", "Thoth"),
]


# ── Public API ──

def get_agent(name: str) -> AgentDef | None:
    """Look up an agent by name (case-insensitive)."""
    return AGENTS.get(name.lower())


# Action name mapping — parse_message returns these names, registry uses canonical names
_ACTION_ALIASES = {
    "clone_project": ACTION_CLONE_REPO,
    "create_bugfix_task": ACTION_FIX_BUG,  # creating a bugfix task = fixing a bug
    "create_feature_task": ACTION_WRITE_CODE,  # creating a feature = writing code
    "generate_docs": ACTION_WRITE_DOCS,
    "run_standup": ACTION_RUN_STANDUP,
    "answer_question": ACTION_ANSWER_QUESTION,
    "correct_agent": ACTION_CORRECT_AGENT,
    "research": ACTION_RESEARCH,
    "write_code": ACTION_WRITE_CODE,
    "route": ACTION_ROUTE,
    "delegate": ACTION_DELEGATE,
}


def canonical_action(action: str) -> str:
    """Convert a parse_message action name to the canonical registry action name."""
    return _ACTION_ALIASES.get(action, action)


def get_director(department: str) -> AgentDef | None:
    """Get the director of a department."""
    for agent in AGENTS.values():
        if agent.department == department and agent.is_director():
            return agent
    return None


def get_subordinates(name: str) -> list:
    """Get all direct subordinates of an agent."""
    agent = get_agent(name)
    if not agent:
        return []
    return [get_agent(s) for s in agent.subordinates if get_agent(s)]


def get_workers_in_department(department: str) -> list:
    """Get all workers (not directors/leads) in a department."""
    return [a for a in AGENTS.values()
            if a.department == department and a.is_worker()]


def get_all_directors() -> list:
    return [a for a in AGENTS.values() if a.is_director()]


def get_all_leads() -> list:
    return [a for a in AGENTS.values() if a.is_lead()]


def get_all_workers() -> list:
    return [a for a in AGENTS.values() if a.is_worker()]


def can_perform(name: str, action: str) -> bool:
    """Check if an agent can perform an action."""
    agent = get_agent(name)
    if not agent:
        return False
    return agent.can_perform(action)


def must_delegate(name: str, action: str) -> bool:
    """Check if an agent MUST delegate this action (instead of doing it)."""
    agent = get_agent(name)
    if not agent:
        return False
    return agent.must_delegate(action)


def pick_worker(department: str, action: str = None, areas: str = None) -> AgentDef | None:
    """
    Pick a worker in a department to perform an action.

    Selection criteria:
      1. Worker can perform the action
      2. Worker's areas match (if areas specified)
      3. Round-robin (pick the first one that's not busy)

    For now, simple: pick the first worker who can do the action.
    """
    workers = get_workers_in_department(department)
    if not workers:
        return None

    # Filter by action capability
    if action:
        workers = [w for w in workers if w.can_perform(action)]

    if not workers:
        return None

    # TODO: check round-robin / load via SQLite runs table
    # For now, pick the first
    return workers[0]


def pick_worker_for_task(task: dict) -> AgentDef | None:
    """
    Pick the right worker for a task based on task type and area.

    Task type → department mapping:
      feature, bugfix, refactor → build
      test → quality
      docs → documentation
      architecture → intelligence
    """
    task_type = task.get("type", "feature")
    area = task.get("area", "")

    TYPE_TO_DEPT = {
        "feature": DEPT_BUILD,
        "bugfix": DEPT_BUILD,
        "refactor": DEPT_BUILD,
        "test": DEPT_QUALITY,
        "docs": DEPT_DOCUMENTATION,
        "architecture": DEPT_INTELLIGENCE,
    }

    dept = TYPE_TO_DEPT.get(task_type, DEPT_BUILD)

    # Determine action based on task type
    action_map = {
        "feature": ACTION_WRITE_CODE,
        "bugfix": ACTION_FIX_BUG,
        "refactor": ACTION_WRITE_CODE,
        "test": ACTION_RUN_TESTS,
        "docs": ACTION_WRITE_DOCS,
        "architecture": ACTION_RESEARCH,
    }
    action = action_map.get(task_type, ACTION_WRITE_CODE)

    return pick_worker(dept, action, areas=area)


def enforce_role(name: str, action: str) -> McpResult:
    """
    Enforce role-based access control.
    Returns success() if allowed, fail() with explanation if not.

    Directors attempting worker actions get a DELEGATE message.
    Workers attempting director actions get a REFUSE message.
    """
    agent = get_agent(name)
    if not agent:
        return fail(f"Unknown agent: {name}")

    if agent.can_perform(action):
        return success()

    if agent.must_delegate(action):
        # Find a subordinate who can do this
        subordinates = get_subordinates(name)
        capable = [s for s in subordinates if s.can_perform(action)]
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
                f"but no subordinate can perform '{action}'. "
                f"Escalate to Hermes."
            )

    return fail(
        f"ROLE VIOLATION — {name} ({agent.role_tier}) cannot perform '{action}'.\n"
        f"Allowed: {agent.can_do}\n"
        f"Forbidden: {agent.cannot_do}"
    )


def delegate_to(director_name: str, task: dict, action: str = None) -> dict:
    """
    A director delegates a task to a subordinate worker.

    Picks the right worker based on task type and area.
    Returns dict with: worker_name, task_id, message
    """
    director = get_agent(director_name)
    if not director:
        return {"error": f"Unknown director: {director_name}"}

    if not director.is_director() and not director.is_lead():
        return {"error": f"{director_name} is not a director or lead — cannot delegate"}

    # Pick the worker
    worker = pick_worker_for_task(task)
    if not worker:
        return {"error": f"No worker available for task type {task.get('type')}"}

    return {
        "director": director_name,
        "worker": worker.name,
        "worker_title": worker.title,
        "worker_areas": worker.areas,
        "task_id": task.get("id"),
        "message": (
            f"@{director_name} delegated task {task.get('id')} to @{worker.name} "
            f"({worker.title}, areas {worker.areas})"
        ),
    }


def info() -> dict:
    return {
        "id": "m-registry",
        "name": "Registry MCP (code-enforced)",
        "tier": 1,
        "owner": "HR",
        "job": "Code-enforced agent roles. Directors delegate, workers execute. Stops Hephaestus from cloning repos himself.",
        "total_agents": len(AGENTS),
        "directors": len(get_all_directors()),
        "leads": len(get_all_leads()),
        "workers": len(get_all_workers()),
    }


# ── Register additional agents (after public API is defined) ──

def _register_additional():
    """Register quality workers, seniors, specialists, etc."""
    # Quality sub-department workers
    for core_name, (core_title, prefix) in _QUALITY_CORE_NAMES.items():
        core_agent = get_agent(core_name)
        if core_agent:
            workers = [f"{prefix}-{s}" for s in _QUALITY_WORKER_SUFFIXES]
            core_agent.subordinates = workers

            for suffix in _QUALITY_WORKER_SUFFIXES:
                worker_name = f"{prefix}-{suffix}"
                action = ACTION_RUN_TESTS
                if prefix == "scalpel":
                    action = ACTION_REVIEW_CODE
                elif prefix == "sentry":
                    action = "security_scan"
                elif prefix == "pixel":
                    action = "visual_test"
                elif prefix == "janus":
                    action = "compliance_check"

                _register(AgentDef(
                    name=worker_name,
                    role_tier=ROLE_WORKER,
                    department=DEPT_QUALITY,
                    title=f"{core_title} Worker",
                    reports_to=core_name,
                    can_do=[action, ACTION_ANSWER_QUESTION],
                ))

    # Update Minos's subordinates
    minos = get_agent("Minos")
    if minos:
        all_q_workers = []
        for _, (_, prefix) in _QUALITY_CORE_NAMES.items():
            all_q_workers.extend([f"{prefix}-{s}" for s in _QUALITY_WORKER_SUFFIXES])
        minos.subordinates = list(_QUALITY_CORE_NAMES.keys()) + all_q_workers + _VERDICT_NAMES

    # Verdict agents
    for name in _VERDICT_NAMES:
        _register(AgentDef(
            name=name,
            role_tier=ROLE_WORKER,
            department=DEPT_QUALITY,
            title="Standards Compliance Agent",
            reports_to="Minos",
            can_do=["compliance_check", ACTION_REVIEW_CODE],
        ))

    # Build seniors
    for name, title, lead in _SR_BUILD_AGENTS:
        _register(AgentDef(
            name=name,
            role_tier=ROLE_LEAD,
            department=DEPT_BUILD,
            title=title,
            reports_to=lead,
            subordinates=[],
            can_do=[ACTION_DELEGATE, ACTION_REVIEW_CODE, ACTION_WRITE_CODE],
            cannot_do=[],
        ))
        lead_agent = get_agent(lead)
        if lead_agent and name not in lead_agent.subordinates:
            lead_agent.subordinates.append(name)

    # Intelligence leads
    for name, title, director in _INTEL_LEADS:
        _register(AgentDef(
            name=name,
            role_tier=ROLE_LEAD,
            department=DEPT_INTELLIGENCE,
            title=title,
            reports_to=director,
            can_do=[ACTION_DELEGATE, ACTION_RESEARCH],
        ))
        d = get_agent(director)
        if d and name not in d.subordinates:
            d.subordinates.append(name)

    # Intelligence specialists
    for name, title, director in _INTEL_SPECIALISTS:
        _register(AgentDef(
            name=name,
            role_tier=ROLE_WORKER,
            department=DEPT_INTELLIGENCE,
            title=title,
            reports_to=director,
            can_do=[ACTION_RESEARCH, "investigate_area"],
        ))
        d = get_agent(director)
        if d and name not in d.subordinates:
            d.subordinates.append(name)

    # Meta specialists
    for name, title, director in _META_SPECIALISTS:
        _register(AgentDef(
            name=name,
            role_tier=ROLE_WORKER,
            department=DEPT_META,
            title=title,
            reports_to=director,
            can_do=[ACTION_FIX_BUG, "patch_system"],
        ))
        d = get_agent(director)
        if d and name not in d.subordinates:
            d.subordinates.append(name)

    # Doc specialists
    for name, title, director in _DOC_SPECIALISTS:
        _register(AgentDef(
            name=name,
            role_tier=ROLE_WORKER,
            department=DEPT_DOCUMENTATION,
            title=title,
            reports_to=director,
            can_do=[ACTION_WRITE_DOCS],
        ))
        d = get_agent(director)
        if d and name not in d.subordinates:
            d.subordinates.append(name)


# Run the additional registration
_register_additional()


# ── CLI ──

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Registry MCP — code-enforced agent roles")
        print("Usage: python registry.py <command>")
        print()
        print("Commands:")
        print("  info                          Show registry stats")
        print("  show <name>                   Show agent definition")
        print("  directors                     List all directors")
        print("  workers [dept]                List workers (optionally by dept)")
        print("  can <name> <action>           Check if agent can perform action")
        print("  delegate <name> <action>      Check if agent must delegate")
        print("  pick <dept> [action]          Pick a worker in a department")
        print("  pick-for-task <task_id>       Pick the right worker for a task")
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

    elif cmd == "workers":
        dept = sys.argv[2] if len(sys.argv) > 2 else None
        for w in get_all_workers():
            if dept and w.department != dept:
                continue
            print(f"  {w.name:20s} {w.department:15s} {w.title[:50]:50s} areas={w.areas}")

    elif cmd == "can":
        if len(sys.argv) < 4:
            print("Usage: can <name> <action>")
            sys.exit(1)
        name, action = sys.argv[2], sys.argv[3]
        result = enforce_role(name, action)
        if result.ok:
            print(f"✅ {name} can perform '{action}'")
        else:
            print(f"❌ {name} cannot perform '{action}':")
            print(f"   {result.error}")

    elif cmd == "delegate":
        if len(sys.argv) < 4:
            print("Usage: delegate <name> <action>")
            sys.exit(1)
        name, action = sys.argv[2], sys.argv[3]
        if must_delegate(name, action):
            print(f"✅ {name} MUST delegate '{action}' to a subordinate")
            subs = get_subordinates(name)
            capable = [s for s in subs if s.can_perform(action)]
            print(f"   Capable subordinates: {', '.join(s.name for s in capable[:5])}")
        else:
            print(f"ℹ️  {name} does not need to delegate '{action}'")

    elif cmd == "pick":
        if len(sys.argv) < 3:
            print("Usage: pick <dept> [action]")
            sys.exit(1)
        dept = sys.argv[2]
        action = sys.argv[3] if len(sys.argv) > 3 else None
        worker = pick_worker(dept, action)
        if worker:
            print(f"Picked: {worker.name} ({worker.title})")
        else:
            print(f"No worker available in {dept} for action {action}")

    elif cmd == "pick-for-task":
        if len(sys.argv) < 3:
            print("Usage: pick-for-task <task_id>")
            sys.exit(1)
        import state
        state.init_schema()
        task = state.query_one("SELECT * FROM tasks WHERE id=?", (sys.argv[2],))
        if not task:
            print(f"Task not found: {sys.argv[2]}")
            sys.exit(1)
        worker = pick_worker_for_task(task)
        if worker:
            print(f"Picked: {worker.name} ({worker.title})")
        else:
            print("No worker available for this task type")

    else:
        print(f"Unknown command: {cmd}")
