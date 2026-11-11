"""Strict allowlist of read-only diagnostic commands for XFA.

No shell parsing, user arguments, pipelines, redirects, scripts, or arbitrary
process execution are accepted. Commands are fixed server-side.
"""
from __future__ import annotations

import subprocess
import sys

from xfa_agent.workspace import ROOT, list_files

_COMMANDS = {
    "pwd": "Show the configured XFA workspace directory",
    "ls": "List safe, visible workspace entries",
    "python --version": "Show the Python interpreter version",
    "git status --short": "Show concise repository status",
    "git log -5 --oneline": "Show the latest five commit summaries",
    "git diff --stat": "Show changed-file statistics only",
}


def available_commands() -> list[dict]:
    return [{"command": command, "description": description}
            for command, description in _COMMANDS.items()]


def run_command(command: str) -> dict:
    """Run one exact allowlisted diagnostic; never pass user input to a shell."""
    command = str(command or "").strip()
    if command not in _COMMANDS:
        raise ValueError(
            "Command blocked. Only the listed read-only diagnostics are allowed; "
            "process control (/stop, /kill), deletion, scripts, installs, and arbitrary shell are disabled."
        )

    if command == "pwd":
        output = str(ROOT) + "\n"
        return {"command": command, "output": output, "exit_code": 0}
    if command == "ls":
        entries = list_files(".")
        output = "\n".join(
            ("[dir] " if item["type"] == "directory" else "[file] ") + item["name"]
            for item in entries
        ) or "(empty)"
        return {"command": command, "output": output[:4000], "exit_code": 0}
    if command == "python --version":
        return {"command": command, "output": sys.version.splitlines()[0] + "\n", "exit_code": 0}

    argv = {
        "git status --short": ["git", "-c", "core.fsmonitor=false", "status", "--short"],
        "git log -5 --oneline": ["git", "-c", "core.fsmonitor=false", "-c", "core.pager=cat", "log", "-5", "--oneline"],
        "git diff --stat": ["git", "-c", "core.fsmonitor=false", "-c", "diff.external=", "diff", "--stat"],
    }[command]
    completed = subprocess.run(
        argv,
        cwd=ROOT,
        shell=False,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
        env={
            "PATH": "/usr/bin:/bin",
            "HOME": str(ROOT),
            "GIT_PAGER": "cat",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_CONFIG_NOSYSTEM": "1",
        },
    )
    output = (completed.stdout or "") + (completed.stderr or "")
    return {
        "command": command,
        "output": output[:4000] or "(no output)",
        "exit_code": completed.returncode,
    }
