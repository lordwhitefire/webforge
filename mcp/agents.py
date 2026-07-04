#!/usr/bin/env python3
"""
Agents MCP — list, talk to, and EXECUTE commands through agents.

Industry pattern: @mentions (Slack, GitHub, Discord).
When the developer types @Hermes or /talk Hermes, this MCP:
  1. Looks up the agent in the registry
  2. Returns their skill file path
  3. Returns their role, department, and capabilities
  4. The LLM reads the skill file and adopts that agent's persona
  5. The LLM EXECUTES the developer's request (not just talks about it)

Command execution: When a developer asks an agent to do something
(correction, rule, task, etc.), the agent runs the WebForge MCP
via bash instead of just explaining how it should be done.
"""

import os
import sys
import json
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import write_log, success, fail, utc_now, McpResult, SKILLS_DIR


def info() -> dict:
    return {
        "id": "m-agents",
        "name": "Agents MCP",
        "tier": 2,
        "owner": "Hermes",
        "job": "List and look up agents for @mention routing. Slack/GitHub @mention pattern.",
    }


# ── Agent registry (sourced from skills/ folder structure) ──
# Format: { "name": { "department": ..., "role": ..., "skill_file": ... } }

def scan_agents() -> dict:
    """Scan the skills/ folder and build an agent registry."""
    agents = {}

    if not SKILLS_DIR.exists():
        return agents

    for dept_dir in sorted(SKILLS_DIR.iterdir()):
        if not dept_dir.is_dir():
            continue
        dept = dept_dir.name

        for skill_file in sorted(dept_dir.glob("*.md")):
            name = skill_file.stem  # filename without .md

            # Try to extract role from the file (first "## Who I Am" or "# Name" line)
            role = ""
            content = skill_file.read_text(encoding="utf-8")
            for line in content.split("\n")[:20]:
                if line.startswith("# "):
                    # "# Hermes — COO / Coordinator" → "Hermes", "COO / Coordinator"
                    title = line.lstrip("# ").strip()
                    name_from_title = title.split("—")[0].split("-")[0].strip()
                    if "—" in title:
                        role = title.split("—", 1)[1].strip()
                    elif "-" in title and len(title.split("-")) > 1:
                        role = title.split("-", 1)[1].strip()
                    break
                elif line.startswith("## Who I Am"):
                    # Next non-empty line is the description
                    continue

            # Try to find role from "I am X. I am the Y" pattern
            if not role:
                for line in content.split("\n")[:30]:
                    line = line.strip()
                    if line.startswith("I am ") and ". I am" in line:
                        # "I am Hermes. I am the COO / Coordinator."
                        parts = line.split(". I am ")
                        if len(parts) > 1:
                            role = parts[1].rstrip(".").strip()
                            break
                    elif line.startswith("I am ") and "I am the" in line:
                        parts = line.split("I am the ")
                        if len(parts) > 1:
                            role = "the " + parts[1].rstrip(".").strip()
                            break

            agents[name.lower()] = {
                "name": name,
                "department": dept.capitalize(),
                "role": role or "(see skill file)",
                "skill_file": str(skill_file),
                "skill_file_relative": f"skills/{dept}/{skill_file.name}",
            }

    return agents


# ── List all agents ──
def list_agents() -> McpResult:
    """List all available agents, grouped by department."""
    agents = scan_agents()

    if not agents:
        return fail("No agents found. Skills directory may be missing.")

    # Group by department
    by_dept = {}
    for agent in agents.values():
        dept = agent["department"]
        if dept not in by_dept:
            by_dept[dept] = []
        by_dept[dept].append(agent)

    # Format output
    lines = []
    lines.append("=" * 60)
    lines.append("🤖 AVAILABLE AGENTS")
    lines.append("=" * 60)
    lines.append("")
    lines.append("Talk to any agent with:")
    lines.append("  /talk <agent-name> <your message>")
    lines.append("  Or just type @AgentName in your message")
    lines.append("")

    dept_order = ["Executive", "Hr", "Meta", "Intelligence", "Build", "Quality", "Documentation"]
    dept_labels = {
        "Executive": "EXECUTIVE",
        "Hr": "HR",
        "Meta": "META ENGINEERING",
        "Intelligence": "INTELLIGENCE",
        "Build": "BUILD",
        "Quality": "QUALITY",
        "Documentation": "DOCUMENTATION",
    }

    for dept in dept_order:
        if dept not in by_dept:
            continue
        lines.append(f"  {dept_labels.get(dept, dept.upper())}")
        lines.append("  " + "─" * 40)

        for agent in sorted(by_dept[dept], key=lambda a: a["name"]):
            name = agent["name"]
            role = agent["role"]
            lines.append(f"    @{name:<15s} — {role}")

        lines.append("")

    # Handle any departments not in the standard order
    for dept in sorted(by_dept.keys()):
        if dept not in dept_order:
            lines.append(f"  {dept.upper()}")
            lines.append("  " + "─" * 40)
            for agent in sorted(by_dept[dept], key=lambda a: a["name"]):
                name = agent["name"]
                role = agent["role"]
                lines.append(f"    @{name:<15s} — {role}")
            lines.append("")

    lines.append("=" * 60)
    lines.append(f"Total agents: {len(agents)}")
    lines.append("=" * 60)

    return success({
        "agents": agents,
        "count": len(agents),
        "output": "\n".join(lines),
    })


# ── Look up a single agent ──
def lookup_agent(name: str) -> McpResult:
    """Look up an agent by name. Returns their skill file path and info."""
    agents = scan_agents()
    name_lower = name.lower().strip()

    if name_lower not in agents:
        # Try partial match
        matches = [k for k in agents.keys() if name_lower in k]
        if len(matches) == 1:
            agent = agents[matches[0]]
        elif len(matches) > 1:
            return fail(f"Multiple agents match '{name}': {', '.join(agents[m]['name'] for m in matches)}. Be more specific.")
        else:
            return fail(f"Agent not found: @{name}. Use /agents to see available agents.")
    else:
        agent = agents[name_lower]

    return success({
        "agent": agent,
        "message": (
            f"🤖 AGENT LOOKUP — @{agent['name']}\n"
            f"  Department: {agent['department']}\n"
            f"  Role: {agent['role']}\n"
            f"  Skill file: {agent['skill_file_relative']}\n\n"
            f"The LLM should read this skill file and respond as @{agent['name']}.\n"
            f"Use /talk {agent['name']} <message> to address them directly."
        ),
    })


# ── Talk to an agent ──
def talk_to(agent_name: str, message: str) -> McpResult:
    """
    Route a message to a specific agent.
    Returns the agent's skill file path so the LLM can adopt their persona.
    """
    lookup = lookup_agent(agent_name)
    if not lookup.ok:
        return lookup

    agent = lookup.data["agent"]

    # Log the conversation
    from memory import session_append
    session_append(
        f"TALK TO @{agent['name']} — {message}",
        agent="Developer", kind="note"
    )

    write_log("Agents", "Developer", "talk_to",
              {"agent": agent["name"], "message": message})

    # Check if the message contains a command request
    command_map = {
        "correct": f"WEBFORGE_PROJECT=\"$OPENCODE_CWD\" python3 $HOME/webforge/mcp/memory.py add-correction \"$1\"",
        "add-rule": f"WEBFORGE_PROJECT=\"$OPENCODE_CWD\" python3 $HOME/webforge/mcp/memory.py add-rule \"$1\" project developer",
        "add-preference": f"WEBFORGE_PROJECT=\"$OPENCODE_CWD\" python3 $HOME/webforge/mcp/memory.py add-preference \"$1\" project",
        "add-adr": f"WEBFORGE_PROJECT=\"$OPENCODE_CWD\" python3 $HOME/webforge/mcp/memory.py add-adr",
        "task": f"WEBFORGE_PROJECT=\"$OPENCODE_CWD\" python3 $HOME/webforge/mcp/task.py create \"$1\" \"$2\" \"$3\" \"$4\"",
        "rfc": f"WEBFORGE_PROJECT=\"$OPENCODE_CWD\" python3 $HOME/webforge/mcp/rfc.py",
    }
    has_command = any(cmd in message.lower() for cmd in command_map.keys())

    return success({
        "agent": agent,
        "message_to_agent": message,
        "instruction": (
            f"READ THIS SKILL FILE: {agent['skill_file']}\n"
            f"Then respond AS @{agent['name']} ({agent['role']}).\n"
            f"The developer's message: {message}\n\n"
            f"Adopt the agent's persona. Use their tools. Answer as they would.\n\n"
            f"=== CHAIN EXECUTOR — ONE CALL, FULL CHAIN ===\n"
            f"When a task needs to be worked on, use the Chain Executor. "
            f"It routes through ALL levels in one call. Do NOT route manually.\n\n"
            f"1. RUN THE CHAIN — Execute the full chain in one command:\n"
            f"   bash> WEBFORGE_PROJECT=\"$OPENCODE_CWD\" python3 $HOME/webforge/mcp/executor.py run <task-id>\n"
            f"   This routes through EVERY level: Hermes → Dept Head → Lead → Senior → Junior\n"
            f"   It does NOT stop at each level. One command. Full chain.\n\n"
            f"2. REPORT UP — When work is complete, route results back up:\n"
            f"   bash> WEBFORGE_PROJECT=\"$OPENCODE_CWD\" python3 $HOME/webforge/mcp/executor.py report-up <task-id> <your-name> [report]\n"
            f"   This routes results up through every level: Junior → Senior → Lead → Head → Hermes → CEO\n\n"
            f"3. STOP ONLY IF — You need the CEO to make a decision. Then escalate.\n\n"
            f"DO NOT manually route-down or route-up. The executor does it all at once.\n"
            f"DO NOT stop after one level. The executor handles all levels.\n\n"
            f"=== ANY AGENT CAN CREATE TASKS ===\n"
            f"When the developer or another agent asks you to do something — create a task for it.\n"
            f"You do NOT need Hermes to create tasks. ANY agent can create a task:\n"
            f"  bash> WEBFORGE_PROJECT=\"$OPENCODE_CWD\" python3 $HOME/webforge/mcp/task.py create \"<title>\" \"<type>\"\n"
            f"The task goes to the board. Hermes gets pinged automatically and routes it.\n"
            f"Examples:\n"
            f"  Developer: '@Jr-Hawk add a login button'\n"
            f"  You: Create task, post it to the board. Hermes will route it.\n"
            f"  Developer: '@Probe-Wren audit the api folder'\n"
            f"  You: Create task, post it to the board. Hermes will route it.\n\n"
            f"=== COMMAND EXECUTION RULE ===\n"
            f"When the developer asks you to make a correction, save a rule, add a preference, "
            f"or execute ANY WebForge command — follow this process:\n\n"
            f"1. UNDERSTAND — If confused, ask. Don't guess.\n"
            f"2. EXPLAIN — Tell the developer what you understood in simple terms.\n"
            f"3. SUGGEST — Offer alternatives if there's a better way.\n"
            f"4. WAIT — DO NOT run anything until the developer says 'go ahead' or 'do it'.\n"
            f"5. EXECUTE — Only after approval, run the command.\n\n"
            f"You have bash access. Use it to run the appropriate WebForge MCP command.\n"
            f"For example:\n"
            f"  Developer: 'make a correction about X'\n"
            f"  You: 'Here's what I understood — X should Y instead of Z. "
            f"Command will be: /correct \"Z | Y | global\". Shall I run it?'\n"
            f"  Developer: 'yes'\n"
            f"  You: bash> WEBFORGE_PROJECT=\"$OPENCODE_CWD\" python3 $HOME/webforge/mcp/memory.py add-correction \"Z | Y | global\"\n\n"
            f"Available command mappings:\n"
            f"  - correction → memory.py add-correction\n"
            f"  - rule → memory.py add-rule\n"
            f"  - preference → memory.py add-preference\n"
            f"  - task → task.py create\n"
            f"  - adr → memory.py add-adr\n"
            f"  - dispatch route-down → dispatch.py route-down\n"
            f"  - dispatch route-up → dispatch.py route-up\n\n"
            f"Never run without approval. Never guess. Always explain first.\n"
            f"Never stop after one response. Keep the chain moving."
        ),
        "display": (
            f"📤 MESSAGE ROUTED TO @{agent['name']}\n"
            f"  Department: {agent['department']}\n"
            f"  Role: {agent['role']}\n"
            f"  Message: {message}\n\n"
            f"  Loading {agent['name']}'s skill file..."
        ),
    })


# ── CLI ──
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Agents MCP — @mention routing")
        print("Usage: python agents.py <command> [args]")
        print()
        print("Commands:")
        print("  list                 List all available agents")
        print("  lookup <name>        Look up an agent by name")
        print("  talk <name> <msg>    Route a message to an agent")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "info":
        print(json.dumps(info(), indent=2))
    elif cmd == "list":
        result = list_agents()
        print(result.data.get("output", result.to_dict()))
    elif cmd == "lookup":
        result = lookup_agent(sys.argv[2] if len(sys.argv) > 2 else "")
        print(result.data.get("message", result.to_dict()))
    elif cmd == "talk":
        agent_name = sys.argv[2] if len(sys.argv) > 2 else ""
        message = sys.argv[3] if len(sys.argv) > 3 else ""
        if agent_name and message:
            # Redirect to pipeline — the hook system
            print(f"  ▶️  Routing @{agent_name} through pipeline...")
            sys.stdout.flush()
            pipeline_script = Path(__file__).parent / "pipeline.py"
            cmd_list = [sys.executable, str(pipeline_script), "trigger", agent_name, message]
            env = os.environ.copy()
            env["WEBFORGE_PROJECT"] = os.environ.get("WEBFORGE_PROJECT", str(Path.cwd()))
            subprocess.run(cmd_list, env=env)
        else:
            print("Usage: talk <agent-name> <message>")
    else:
        print(f"Unknown command: {cmd}")
