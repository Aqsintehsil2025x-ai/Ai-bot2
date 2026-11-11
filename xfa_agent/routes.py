"""Authenticated, resource-light XFA API.

Phase 1 provides task planning and an optional remote-browser connection.
It deliberately does not execute shell commands or submit external forms.
"""
from __future__ import annotations

import hmac
import ipaddress
import os
import socket
from urllib.parse import urlparse
from flask import Blueprint, jsonify, request, send_from_directory

xfa = Blueprint("xfa", __name__, url_prefix="/xfa/api")


def _authorized() -> bool:
    expected = os.getenv("XFA_ACCESS_TOKEN", "").strip()
    supplied = request.headers.get("Authorization", "")
    if supplied.lower().startswith("bearer "):
        supplied = supplied[7:].strip()
    return bool(expected) and hmac.compare_digest(expected, supplied)


@xfa.before_request
def require_agent_token():
    if not _authorized():
        return jsonify({"error": "Unauthorized. Configure XFA_ACCESS_TOKEN and send it as a Bearer token."}), 401


@xfa.get("/health")
def health():
    return jsonify({
        "ok": True,
        "agent": "XFA",
        "planner_ready": bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")),
        "remote_browser_ready": bool(os.getenv("XFA_BROWSER_CDP_URL")),
        "execution_mode": "approval_required",
    })


@xfa.post("/tasks/plan")
def plan_task():
    body = request.get_json(silent=True) or {}
    task = str(body.get("task", "")).strip()
    if not task or len(task) > 2000:
        return jsonify({"error": "task must contain 1-2000 characters"}), 400

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return jsonify({"error": "GEMINI_API_KEY is not configured"}), 503

    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=api_key)
        model = os.getenv("XFA_MODEL", os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"))
        response = client.models.generate_content(
            model=model,
            contents=task,
            config=types.GenerateContentConfig(
                system_instruction=(
                    "You are XFA, a careful autonomous assistant for the user's own projects. "
                    "Return a concise, practical plan in plain text. Identify which steps are read-only "
                    "and which could change accounts, publish content, spend money, delete data, deploy, "
                    "or expose private information. Never claim an action has been performed. "
                    "Require explicit user approval before any consequential external action. "
                    "Do not request passwords, one-time codes, or secret tokens in chat."
                ),
                max_output_tokens=700,
                temperature=0.2,
            ),
        )
        return jsonify({"ok": True, "task": task, "plan": response.text or "No plan returned.", "status": "planned"})
    except Exception as exc:
        return jsonify({"error": "Planner request failed", "detail": str(exc)[:300]}), 502


@xfa.post("/browser/open")
def browser_open():
    body = request.get_json(silent=True) or {}
    url = str(body.get("url", "")).strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        return jsonify({"error": "Only public http:// and https:// URLs are allowed"}), 400
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)}
        if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
            return jsonify({"error": "Private, local, and non-public network addresses are blocked"}), 400
    except (OSError, ValueError):
        return jsonify({"error": "Could not resolve a public hostname"}), 400
    endpoint = os.getenv("XFA_BROWSER_CDP_URL", "").strip()
    if not endpoint:
        return jsonify({"error": "Remote browser is not configured. Set XFA_BROWSER_CDP_URL to a trusted remote Playwright/CDP endpoint."}), 503
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as playwright:
            browser = playwright.chromium.connect_over_cdp(endpoint, timeout=12000)
            context = browser.contexts[0] if browser.contexts else browser.new_context()
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            result = {"ok": True, "url": page.url, "title": page.title(), "text": page.locator("body").inner_text(timeout=5000)[:5000]}
            page.close()
            return jsonify(result)
    except ImportError:
        return jsonify({"error": "Playwright package is missing; install the optional browser dependency."}), 503
    except Exception as exc:
        return jsonify({"error": "Browser operation failed", "detail": str(exc)[:300]}), 502


def register_xfa(app):
    if "xfa" not in app.blueprints:
        app.register_blueprint(xfa)
    if "xfa_dashboard" not in app.view_functions:
        app.add_url_rule(
            "/xfa",
            endpoint="xfa_dashboard",
            view_func=lambda: send_from_directory(os.path.dirname(__file__), "dashboard.html"),
            methods=["GET"],
        )
