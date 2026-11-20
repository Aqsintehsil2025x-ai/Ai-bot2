# Replit Remote Development MCP (restricted)

This adds an authenticated, stateless JSON-RPC/MCP endpoint to the existing Flask process.
It does **not** expose a general shell, arbitrary command execution, deployment controls, or secret-file access.

## Enable it in Replit

1. Open the existing Ai-bot2 Repl and add a Replit Secret named `REMOTE_DEV_TOKEN`.
2. Generate a random token with at least 32 characters in your own password manager or trusted local generator. Never paste it into chat or commit it.
3. Restart the Repl. The endpoint is `https://YOUR-REPL-DOMAIN/remote-dev/mcp`.
4. Connect that URL from an MCP client that supports remote HTTP MCP and configure the same bearer token in that client's secret/authorization settings.

## Exposed tools

- `workspace_status`: Git status and branch.
- `read_file`: reads allowlisted text files in the project; hidden paths and credentials are blocked.
- `write_file`: writes allowlisted text files; hidden paths, credentials, dependencies, and symlinks are blocked.
- `run_check`: only fixed checks: Python compile, unit tests, dashboard build (no dependency installation), and diff summary.

There is deliberately no arbitrary shell tool, no Git push/merge, no deploy tool, and no ability to read environment variables. A failed or missing token disables the endpoint.

## Security notes

- Keep the token only in Replit Secrets and the MCP client's secret store.
- If the token is exposed, rotate it immediately.
- Use HTTPS only. Do not add CORS wildcard access.
- The endpoint shares the Replit app's runtime and resource limits.
- Review every code change before merging to `main`.
