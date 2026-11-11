# XFA — Xyrin Flower Agent

XFA is being introduced as a separate, resource-conscious agent module inside Ai-bot2. It does not replace the Discord bot, Flask server, or dashboard.

## Phase 1

- Authenticated API under `/xfa/api` using the `XFA_ACCESS_TOKEN` environment secret.
- Gemini-backed task planning using the existing `GEMINI_API_KEY` / `GOOGLE_API_KEY` configuration.
- Optional remote browser connection through a trusted Playwright-compatible CDP endpoint (`XFA_BROWSER_CDP_URL`). The Replit process does not download or run a local Chromium binary.
- Browser navigation is read-only in this phase. Private/local network targets are blocked. No form submission, purchases, messages, publishing, account changes, shell commands, deletion, or deployment are automated.
- Health endpoint reports whether planner and remote browser configuration are present.

## Replit secrets

- `XFA_ACCESS_TOKEN`: generate a long random secret and keep it in Replit Secrets; never commit it.
- `GEMINI_API_KEY`: existing model key used by the bot.
- `XFA_MODEL`: optional model override.
- `XFA_BROWSER_CDP_URL`: optional trusted remote browser CDP endpoint. Leave unset until a provider is selected.

## API

All endpoints require `Authorization: Bearer <XFA_ACCESS_TOKEN>`.

- `GET /xfa` — XFA dashboard (enter the access token in the page; it is kept in memory only).
- `GET /xfa/api/health`
- `POST /xfa/api/tasks/plan` with JSON `{"task":"..."}`
- `POST /xfa/api/browser/open` with JSON `{"url":"https://example.com"}`

The browser dependency is optional and remote-only. Never expose the CDP endpoint or access token to the browser frontend. Before enabling write actions, add per-action approval, domain restrictions, audit logs, timeouts, and an isolated browser profile.
