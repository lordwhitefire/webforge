"""
WebForge Agent Registry — maps agent names to their script modules.

When /talk Hermes is called, this registry finds hermes.py and runs it.
When Daedalus needs to patch an agent, this registry finds the file path.

To add a new agent:
  1. Create agents/<name>.py with a class inheriting from base.Agent
  2. Add it to AGENT_REGISTRY below
  3. Loom can do this automatically (future)
"""

import importlib
from pathlib import Path

AGENTS_DIR = Path(__file__).parent

# Registry: agent name (lowercase) → module name
AGENT_REGISTRY = {
    "hermes": "hermes",
    "hephaestus": "hephaestus",
    "athena": "athena",
    "minos": "minos",
    "thoth": "thoth",
    "daedalus": "daedalus",
    "voss": "voss",
    "dorian": "dorian",
    "forge": "forge",
    "anvil": "anvil",
    "compass": "compass",
    "loom": "loom",
}


def get_agent_script(agent_name: str) -> Path:
    """Get the .py file path for an agent."""
    return AGENTS_DIR / f"{agent_name.lower()}.py"


def run_agent(agent_name: str, message: str, context: dict = None) -> dict:
    """
    Run an agent's script with a message.
    This is THE function that activates an agent.
    """
    agent_name = agent_name.lower().strip().replace("@", "")
    module_name = AGENT_REGISTRY.get(agent_name)

    if not module_name:
        # Check if the file exists even if not in registry
        script = get_agent_script(agent_name)
        if script.exists():
            module_name = agent_name
        else:
            return {
                "agent": "System",
                "action": "error",
                "message": f"Agent not found: @{agent_name}. Use /agents to see available agents.",
                "next_step": None,
            }

    # Import the agent module
    try:
        module = importlib.import_module(module_name)
    except ImportError as e:
        return {
            "agent": "System",
            "action": "error",
            "message": f"Failed to import agent {agent_name}: {e}",
            "next_step": None,
        }

    # Call the agent's run() function
    if hasattr(module, "run"):
        return module.run(message, context)
    else:
        return {
            "agent": "System",
            "action": "error",
            "message": f"Agent {agent_name} has no run() function.",
            "next_step": None,
        }


def list_available_agents() -> list:
    """List all available agent scripts."""
    agents = []
    for f in sorted(AGENTS_DIR.glob("*.py")):
        if f.name in ("base.py", "__init__.py"):
            continue
        agents.append(f.stem)
    return agents
