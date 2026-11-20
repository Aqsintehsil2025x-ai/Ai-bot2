"""Restricted, token-authenticated MCP endpoint for Replit workspace maintenance.

This intentionally exposes a small allowlist of operations, never an arbitrary shell.
Set REMOTE_DEV_TOKEN in Replit Secrets before enabling the endpoint.
"""
from __future__ import annotations

import hmac
import json
import os
import subprocess
from pathlib import Path
from typing import Any

from flask import Blueprint, Response, current_app, jsonify, request

ROOT = Path(__file__).resolve().parent
BLUEPRINT = Blueprint("remote_dev_mcp", __name__)
MAX_WRITE_BYTES = 256 * 1024
MAX_READ_BYTES = 128 * 1024
BLOCKED_NAMES = {
    ".env", ".env.local", ".env.production", ".git", ".ssh",
    "secrets", "secrets.json", "credentials.json", "cookies.txt",
}
READ_EXTENSIONS = {
    ".py", ".md", ".txt", ".toml", ".yaml", ".yml", ".json",
    ".html", ".css", ".js", ".ts", ".tsx", ".jsx", ".svg",
}
WRITE_EXTENSIONS = READ_EXTENSIONS - {".svg"}
BLOCKED_TOP_LEVEL = {".git", ".venv", "venv", "node_modules", "__pycache__"}
TOOLS = [
    {
        "name": "workspace_status",
        "description": "Read Git status and current branch in the Replit workspace.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "read_file",
        "description": "Read a non-secret text file inside the project. Hidden paths and credential files are blocked.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string", "minLength": 1, "maxLength": 240}},
            "required": ["path"], "additionalProperties": False,
        },
    },
    {
        "name": "write_file",
        "description": "Write a project text file. Credential files, hidden paths, dependency folders, and deployment secrets are blocked.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "minLength": 1, "maxLength": 240},
                "content": {"type": "string", "maxLength": MAX_WRITE_BYTES},
            },
            "required": ["path", "content"], "additionalProperties": False,
        },
    },
    {
        "name": "run_check",
        "description": "Run one fixed, safe project check. No arbitrary command or shell arguments are accepted.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "check": {"type": "string", "enum": ["compile", "tests", "dashboard_build", "git_diff"]},
            },
            "required": ["check"], "additionalProperties": False,
        },
    },
]


def _safe_path(raw: str, writing: bool = False) -> Path:
    if not isinstance(raw, str) or not raw or "\x00" in raw or "\\" in raw:
        raise ValueError("Invalid project path.")
    rel = Path(raw)
    if rel.is_absolute() or any(part in {"", ".", ".."} for part in rel.parts):
        raise ValueError("Path must be a clean relative path inside the project.")
    if any(part.startswith(".") or part.lower() in BLOCKED_TOP_LEVEL for part in rel.parts):
        raise ValueError("Hidden, internal, and dependency paths are blocked.")
    if any(part.lower() in BLOCKED_NAMES or "secret" in part.lower() or "credential" in part.lower() for part in rel.parts):
        raise ValueError("Credential-related paths are blocked.")
    suffix = rel.suffix.lower()
    allowed = WRITE_EXTENSIONS if writing else READ_EXTENSIONS
    if suffix not in allowed:
        raise ValueError("This file type is not enabled.")
    target = ROOT / rel
    resolved_parent = target.parent.resolve()
    if resolved_parent != ROOT and ROOT not in resolved_parent.parents:
        raise ValueError("Path escapes the project directory.")
    if target.exists() and target.is_symlink():
        raise ValueError("Symbolic links are blocked.")
    if writing and target.exists() and not target.is_file():
        raise ValueError("Only regular files can be written.")
    return target


def _run(args: list[str], timeout: int = 120) -> dict[str, Any]:
    result = subprocess.run(
        args, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, text=True, timeout=timeout, check=False,
        env={**os.environ, "CI": "1", "GIT_TERMINAL_PROMPT": "0"},
    )
    output = (result.stdout or "")[-16000:]
    return {"exit_code": result.returncode, "output": output}


def _call_tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
    if name == "workspace_status":
        return _run(["git", "status", "--short", "--branch"])
    if name == "read_file":
        target = _safe_path(args.get("path", ""))
        if not target.is_file():
            raise ValueError("File not found.")
        if target.stat().st_size > MAX_READ_BYTES:
            raise ValueError("File is larger than the read limit.")
        return {"path": str(target.relative_to(ROOT)), "content": target.read_text(encoding="utf-8")}
    if name == "write_file":
        target = _safe_path(args.get("path", ""), writing=True)
        content = args.get("content")
        if not isinstance(content, str) or len(content.encode("utf-8")) > MAX_WRITE_BYTES:
            raise ValueError("Content exceeds the write limit.")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return {"written": str(target.relative_to(ROOT)), "bytes": len(content.encode("utf-8"))}
    if name == "run_check":
        check = args.get("check")
        if check == "compile":
            return _run(["python", "-m", "compileall", "-q", "main.py", "web_app.py", "xfa_agent"], 120)
        if check == "tests":
            return _run(["python", "-m", "unittest", "discover", "-s", "tests", "-v"], 180)
        if check == "dashboard_build":
            dashboard = ROOT / "dashboard"
            if not (dashboard / "package.json").is_file():
                raise ValueError("Dashboard package.json was not found.")
            npm = "npm.cmd" if os.name == "nt" else "npm"
            return _run([npm, "run", "build"], 240) if (dashboard / "node_modules").is_dir() else {
                "exit_code": 2, "output": "Dependencies are not installed; this check will not install packages automatically."
            }
        if check == "git_diff":
            return _run(["git", "diff", "--stat"])
        raise ValueError("Unsupported check.")
    raise ValueError("Unknown tool.")


def _rpc(payload: dict[str, Any]):
    method = payload.get("method")
    request_id = payload.get("id")
    params = payload.get("params") or {}
    if method == "notifications/initialized":
        return None
    if method == "initialize":
        return {
            "jsonrpc": "2.0", "id": request_id,
            "result": {
                "protocolVersion": "2025-03-26",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "xfa-replit-remote-dev", "version": "0.1.0"},
            },
        }
    if method == "ping":
        return {"jsonrpc": "2.0", "id": request_id, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": TOOLS}}
    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments") or {}
        try:
            result = _call_tool(name, arguments)
            content = json.dumps(result, ensure_ascii=False)
            return {"jsonrpc": "2.0", "id": request_id, "result": {
                "content": [{"type": "text", "text": content}],
                "isError": bool(result.get("exit_code", 0) != 0),
            }}
        except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
            return {"jsonrpc": "2.0", "id": request_id, "result": {
                "content": [{"type": "text", "text": str(exc)}], "isError": True,
            }}
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": "Method not found"}}


@BLUEPRINT.route("/remote-dev/mcp", methods=["POST"])
def mcp_endpoint():
    expected = os.environ.get("REMOTE_DEV_TOKEN", "")
    if len(expected) < 32:
        return jsonify({"error": "Remote development endpoint is not configured."}), 503
    supplied = request.headers.get("Authorization", "")
    if not hmac.compare_digest(supplied, "Bearer " + expected):
        return jsonify({"error": "Unauthorized"}), 401
    if not request.is_json:
        return jsonify({"error": "Expected application/json"}), 415
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or payload.get("jsonrpc") != "2.0":
        return jsonify({"error": "Invalid JSON-RPC request"}), 400
    response = _rpc(payload)
    if response is None:
        return Response(status=202)
    return jsonify(response)


def register_remote_dev(app):
    if not app.extensions.get("remote_dev_mcp_registered"):
        app.register_blueprint(BLUEPRINT)
        app.extensions["remote_dev_mcp_registered"] = True
