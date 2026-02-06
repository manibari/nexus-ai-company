#!/usr/bin/env python3
"""
Agent Status Bridge for Apple Intelligence

This script acts as a bridge between Claude Code output and the Agent Dashboard.
It can be called by Apple Intelligence Shortcuts to parse task descriptions
and update the appropriate agent status.

Usage:
    python3 agent_status_bridge.py --parse "SWE Agent 正在實作 StockPulse 後端模組"
    python3 agent_status_bridge.py --update BUILDER working "Implementing StockPulse"
    python3 agent_status_bridge.py --idle BUILDER
"""

import argparse
import json
import re
import subprocess
import sys
from typing import Optional, Tuple

API_URL = "http://localhost:8000"

# Agent name mappings
AGENT_MAPPINGS = {
    "swe": "BUILDER",
    "engineer": "BUILDER",
    "developer": "BUILDER",
    "工程師": "BUILDER",
    "pm": "ORCHESTRATOR",
    "product": "ORCHESTRATOR",
    "專案經理": "ORCHESTRATOR",
    "qa": "INSPECTOR",
    "test": "INSPECTOR",
    "測試": "INSPECTOR",
    "sales": "HUNTER",
    "業務": "HUNTER",
    "finance": "LEDGER",
    "財務": "LEDGER",
    "admin": "GATEKEEPER",
    "行政": "GATEKEEPER",
}

# Status keywords
STATUS_KEYWORDS = {
    "working": ["正在", "開始", "執行", "實作", "processing", "working", "implementing"],
    "idle": ["完成", "結束", "done", "finished", "completed", "idle"],
    "blocked_internal": ["等待", "阻塞", "blocked", "waiting"],
    "blocked_user": ["需要確認", "請審查", "pending approval", "needs review"],
}


def parse_task_description(description: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Parse a task description to extract agent, status, and task.

    Returns: (agent_id, status, task_description)
    """
    description_lower = description.lower()

    # Find agent
    agent_id = None
    for keyword, agent in AGENT_MAPPINGS.items():
        if keyword in description_lower:
            agent_id = agent
            break

    # Find status
    status = "working"  # default
    for stat, keywords in STATUS_KEYWORDS.items():
        for kw in keywords:
            if kw in description_lower:
                status = stat
                break

    return agent_id, status, description


def update_agent_status(agent_id: str, status: str, task: Optional[str] = None) -> dict:
    """Update agent status via API."""
    payload = {"status": status}
    if task:
        payload["current_task"] = task

    cmd = [
        "curl", "-s", "-X", "PUT",
        f"{API_URL}/api/v1/agents/{agent_id}/status",
        "-H", "Content-Type: application/json",
        "-d", json.dumps(payload)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return {"error": result.stdout}
    else:
        return {"error": result.stderr}


def main():
    parser = argparse.ArgumentParser(description="Agent Status Bridge for Apple Intelligence")

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Parse command
    parse_parser = subparsers.add_parser("parse", help="Parse task description")
    parse_parser.add_argument("description", help="Task description to parse")

    # Update command
    update_parser = subparsers.add_parser("update", help="Update agent status")
    update_parser.add_argument("agent_id", help="Agent ID")
    update_parser.add_argument("status", help="Status: idle, working, blocked_internal, blocked_user")
    update_parser.add_argument("task", nargs="?", help="Task description")

    # Idle command (shortcut)
    idle_parser = subparsers.add_parser("idle", help="Set agent to idle")
    idle_parser.add_argument("agent_id", help="Agent ID")

    # Auto command (parse and update)
    auto_parser = subparsers.add_parser("auto", help="Auto-parse and update")
    auto_parser.add_argument("description", help="Task description")

    args = parser.parse_args()

    if args.command == "parse":
        agent_id, status, task = parse_task_description(args.description)
        print(json.dumps({
            "agent_id": agent_id,
            "status": status,
            "task": task
        }, indent=2, ensure_ascii=False))

    elif args.command == "update":
        result = update_agent_status(args.agent_id, args.status, args.task)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.command == "idle":
        result = update_agent_status(args.agent_id, "idle", None)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.command == "auto":
        agent_id, status, task = parse_task_description(args.description)
        if agent_id:
            result = update_agent_status(agent_id, status, task)
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(json.dumps({"error": "Could not identify agent from description"}, indent=2))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
