#!/usr/bin/env python3
"""
MCP 8 — HR MCP
Tier 2 — Core Ops

Spawns and terminates temporary numbered workers (Law 1A).
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))
from common import write_log, success, fail, utc_now, LOGS_DIR, make_id

WORKERS_FILE = LOGS_DIR / "active-workers.json"


def info() -> dict:
    return {
        "id": "m08",
        "name": "HR MCP",
        "tier": 2,
        "owner": "Voss",
        "job": "Spawn and terminate temporary numbered workers (Law 1A).",
    }


def _load_workers():
    if not WORKERS_FILE.exists():
        return {"workers": [], "next_id": 1}
    return json.loads(WORKERS_FILE.read_text())


def _save_workers(data):
    WORKERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    WORKERS_FILE.write_text(json.dumps(data, indent=2))


def spawn_workers(parent_agent: str, files: list, max_files_per_worker: int = 5) -> dict:
    """
    Law 1A: An agent has too many files. Spawn temporary workers.
    Each worker handles at most max_files_per_worker files.
    Returns list of worker IDs.
    """
    data = _load_workers()
    workers_created = []

    # Split files into chunks
    for i in range(0, len(files), max_files_per_worker):
        chunk = files[i:i + max_files_per_worker]
        worker_id = f"Worker-{data['next_id']}"
        data["next_id"] += 1
        worker = {
            "id": worker_id,
            "parent": parent_agent,
            "files_assigned": chunk,
            "status": "active",
            "spawned_at": utc_now(),
        }
        data["workers"].append(worker)
        workers_created.append(worker)

    _save_workers(data)
    write_log("HR", "Voss", "spawn_workers",
              {"parent": parent_agent, "count": len(workers_created),
               "files_total": len(files)})
    return {"workers": workers_created, "count": len(workers_created)}


def terminate_worker(worker_id: str) -> dict:
    """Terminate a temporary worker by ID."""
    data = _load_workers()
    for w in data["workers"]:
        if w["id"] == worker_id and w["status"] == "active":
            w["status"] = "terminated"
            w["terminated_at"] = utc_now()
            _save_workers(data)
            write_log("HR", "Voss", "terminate_worker", {"worker_id": worker_id})
            return {"terminated": worker_id}
    return {"error": f"Worker not found or already terminated: {worker_id}"}


def terminate_all_for_agent(parent_agent: str) -> dict:
    """Terminate all workers spawned by a specific agent."""
    data = _load_workers()
    terminated = []
    for w in data["workers"]:
        if w["parent"] == parent_agent and w["status"] == "active":
            w["status"] = "terminated"
            w["terminated_at"] = utc_now()
            terminated.append(w["id"])
    _save_workers(data)
    if terminated:
        write_log("HR", "Voss", "terminate_all_for_agent",
                  {"parent": parent_agent, "count": len(terminated)})
    return {"terminated": terminated, "count": len(terminated)}


def list_active() -> dict:
    """List all active temporary workers."""
    data = _load_workers()
    active = [w for w in data["workers"] if w["status"] == "active"]
    return {"active_workers": active, "count": len(active)}


def worker_report(worker_id: str, report: str) -> dict:
    """A worker submits a report back to its parent agent."""
    data = _load_workers()
    for w in data["workers"]:
        if w["id"] == worker_id:
            w["report"] = report
            w["report_at"] = utc_now()
            _save_workers(data)
            write_log("HR", worker_id, "worker_report",
                      {"parent": w["parent"], "report_chars": len(report)})
            return {"recorded": worker_id}
    return {"error": f"Worker not found: {worker_id}"}


def run(action: str = "default", **kwargs) -> dict:
    if action == "info":
        return info()
    elif action == "spawn":
        return spawn_workers(kwargs.get("parent_agent", "Unknown"),
                             kwargs.get("files", []),
                             kwargs.get("max_per_worker", 5))
    elif action == "terminate":
        return terminate_worker(kwargs.get("worker_id", ""))
    elif action == "terminate_all":
        return terminate_all_for_agent(kwargs.get("parent_agent", ""))
    elif action == "list":
        return list_active()
    elif action == "report":
        return worker_report(kwargs.get("worker_id", ""), kwargs.get("report", ""))
    else:
        return {"error": f"Unknown action: {action}"}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("HR MCP — Law 1A enforcement")
        print("Usage: python hr.py <command> [args]")
        print("Commands: info, list, spawn <parent> <file1,file2,...> [max],")
        print("          terminate <worker_id>, terminate_all <parent>")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "info":
        print(json.dumps(info(), indent=2))
    elif cmd == "list":
        print(json.dumps(list_active(), indent=2))
    elif cmd == "spawn":
        parent = sys.argv[2]
        files = sys.argv[3].split(",") if len(sys.argv) > 3 else []
        max_per = int(sys.argv[4]) if len(sys.argv) > 4 else 5
        print(json.dumps(spawn_workers(parent, files, max_per), indent=2))
    elif cmd == "terminate":
        print(json.dumps(terminate_worker(sys.argv[2]), indent=2))
    elif cmd == "terminate_all":
        print(json.dumps(terminate_all_for_agent(sys.argv[2]), indent=2))
    else:
        print(f"Unknown command: {cmd}")
