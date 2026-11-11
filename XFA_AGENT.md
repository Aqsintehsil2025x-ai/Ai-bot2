# XFA — Xyrin Flower Agent

XFA is a separate, resource-conscious agent module inside Ai-bot2. It runs in the existing Flask process and does not replace the Discord bot, website, or dashboard.

## Current capabilities

- Gemini plans a task and runs a bounded agent loop (up to five reasoning steps).
- The agent can choose between reading public web pages and inspecting project files.
- Public web browsing is limited to four distinct pages per run and uses an optional remote Playwright/CDP browser. No local Chromium binary is installed.
- Project inspection is confined to the configured workspace root, skips hidden/dependency/internal paths, and limits individual reads to 64 KiB.
- The dashboard can propose creating a new project file or updating an existing text/code file. Both require separate explicit approval, expire after ten minutes, and are limited to selected formats and 32 KiB. Updates are rejected if the original file changed after the proposal; new-file creation never overwrites.
- A small in-memory audit log records workspace listing, reads, proposals, and approved file creation.

## Deliberate safety limits

- XFA does not execute arbitrary shell commands, install packages, read hidden files or secrets, overwrite project files, log in to websites, submit forms, send messages, publish content, purchase items, delete data, change accounts, or deploy.
- Page and repository contents are untrusted data, never instructions.
- Browser requests and redirects are checked for public HTTP(S) destinations; local/private network destinations are blocked.
- The remote browser uses a fresh isolated context and does not reuse provider default cookies/session.
- Any future write, external side effect, or privileged operation must have a narrowly scoped tool, an explicit per-action approval, audit trail, limits, and verification.

## Replit secrets

- `XFA_ACCESS_TOKEN`: generate a long random secret and store it in Replit Secrets; never commit it.
- `GEMINI_API_KEY`: existing Gemini key used by the bot.
- `XFA_MODEL`: optional model override; defaults to the bot's existing `GEMINI_MODEL`.
- `XFA_BROWSER_CDP_URL`: optional trusted remote browser CDP endpoint. Leave unset until a provider is selected.
- `XFA_WORKSPACE_ROOT`: optional absolute workspace root; defaults to the Ai-bot2 repository directory.

## API

All API endpoints require `Authorization: Bearer <XFA_ACCESS_TOKEN>`.

- `GET /xfa` — XFA dashboard; token remains in page memory only.
- `GET /xfa/api/health`
- `POST /xfa/api/tasks/plan` with `{"task":"..."}`
- `POST /xfa/api/tasks/run` with `{"task":"..."}` — bounded read-only web and workspace research.
- `POST /xfa/api/browser/open` with `{"url":"https://example.com"}`
- `GET /xfa/api/workspace/list?path=.`
- `POST /xfa/api/workspace/read` with `{"path":"README.md"}`
- `POST /xfa/api/workspace/propose-create` with `{"path":"notes/new.md","content":"..."}`
- `POST /xfa/api/workspace/propose-update` with `{"path":"README.md","content":"new full content"}`
- `POST /xfa/api/workspace/approve-create` with `{"approval_id":"..." }` (also approves pending updates)
- `GET /xfa/api/audit`

## Resource notes

- Gemini is API-hosted; no local model is loaded.
- Browser mode is optional and remote-only.
- Agent steps, page count, file count, file size, and proposed write size are bounded.
- Keep the XFA module inside the existing Ai-bot2 deployment; do not create a second web server.
- The project must be deployed and runtime-tested in Replit before relying on these features.
