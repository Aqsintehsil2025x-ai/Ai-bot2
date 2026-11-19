# Xyrin Flower AI — Cloudflare migration

This branch is a non-production migration workspace. The existing Replit/Render application remains unchanged.

## Current Cloudflare Pages preview project

- Pages project: `xyrin-flower-ai`
- GitHub repository: `Aqsintehsil2025x-ai/Ai-bot2`
- Build root: `dashboard/`
- Build command: `npm run build`
- Output directory: `dist`
- Preview branch: `feature/xfa-cloudflare-platform`
- Production deployments are intentionally disabled.

## Verified platform capability

Cloudflare Python Workers support WSGI frameworks including Flask through `workers.wsgi.entrypoint(app)`. A static frontend can be served alongside the Flask app using Workers Static Assets.

References:
- https://developers.cloudflare.com/workers/framework-guides/apis/flask/
- https://developers.cloudflare.com/workers/languages/python/packages/flask/

## Migration blockers to resolve before enabling the backend

1. **Account storage:** `xfa_agent/accounts.py` opens a local SQLite file under `instance/xfa.sqlite3`. A Worker local filesystem is not a durable account database. Move account, device, resource, audit, and memory operations to a Cloudflare-supported persistent store (D1 or Durable Objects) with explicit per-user ownership and migration tests.
2. **Session and CSRF:** retain signed, HttpOnly, Secure, SameSite cookies and CSRF checks. Verify cookie behavior on the Pages/Workers hostname and across preview/production origins.
3. **Runtime compatibility:** audit every imported dependency and runtime feature against Python Workers/Pyodide. In particular, test `google-genai`, `urllib`, `certifi`, document parsers, image handling, and any code that assumes sockets, subprocesses, threads, or a writable local filesystem.
4. **Discord bot separation:** `main.py` starts both Flask and the Discord bot in one process and uses a background thread. Do not port this launcher to Workers. Keep the Discord bot on a persistent process host or move it to a separately designed event-driven service.
5. **Secrets:** configure `FLASK_SECRET_KEY`, `GEMINI_API_KEY`, and `NVIDIA_API_KEY` as Cloudflare secrets only after the Worker is ready. Never commit secrets to Git.
6. **Safety and regression tests:** preserve XFA's read-only public-web browsing, workspace boundaries, approval gates, and no-self-modification policy. Run the existing test suite and add storage, authentication, provider, and deployment smoke tests before production.

## Deployment status

The Pages project is connected to GitHub. Path filters have been cleared and the build root is now the repository root, with the dashboard build invoked from `dashboard/`. A fresh preview build is pending; no successful Pages build or public production release has been verified yet.

## Rollout policy

- Keep production on its current host until preview tests pass.
- Do not change the production branch or enable production deployments as part of this migration branch.
- Do not migrate or delete existing user data without a tested export/import and rollback plan.
