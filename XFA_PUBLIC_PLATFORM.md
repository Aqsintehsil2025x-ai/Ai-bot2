# XFA Public Platform — Architecture

This document is the implementation contract for a multi-user desktop/mobile agent with a chat-only web client.

## Product surfaces
- Web: Google/Discord sign-in and chat, plus an optional browser-local text workspace stored in IndexedDB. It has no access to the operating-system filesystem, shell, command runner, or device-control API.
- Desktop: account and chat plus an opt-in local agent. Capabilities stay unavailable until installation, device pairing, and explicit permission.
- Mobile: same account and chat plus explicitly granted mobile capabilities. Android permissions remain revocable in system settings.
- Cloud: authentication, chat orchestration, encrypted integration credentials, device pairing, approvals, audit events, and sync. It never executes commands on a user's computer.

## Account model
- Independent account, session, integration list, resource list, device list, and audit history for every user.
- Current web sign-in methods: Google OAuth and Discord OAuth. The existing account module also provides password-hash primitives, but password login is not exposed in the web UI.
- OAuth client secrets and AI provider keys remain server-side; never ship them in app binaries or browser JavaScript.
- Passwords use a strong one-way hash (Argon2id preferred; scrypt acceptable fallback), never reversible encryption.
- Sessions use Secure, HttpOnly, SameSite cookies, server-side session records, OAuth state/PKCE checks, and CSRF protection. Add login/OAuth rate limiting before broad public release.
- Every user-owned database query includes the authenticated user ID. Never trust a client-supplied user ID.

## Extensions and Resources
- Extensions: provider integrations such as GitHub, Discord, Google Drive, GitLab, and Notion.
- Resources: user-selected repositories, folders, documents, URLs, and API documentation.
- Use OAuth where available. Encrypt access/refresh tokens at rest with authenticated encryption (AES-256-GCM); keep the encryption key outside the database in deployment secrets or a KMS.
- Never log tokens, authorization headers, OAuth codes, passwords, or encryption keys.
- Users can disconnect extensions and revoke provider grants.
- Account-level integrations/resources sync across Desktop and Mobile. Device-local folders and permissions remain device-specific.

## GitHub authorization and approvals
- XFA can enumerate all repositories visible to the GitHub OAuth grant, including private repositories only when GitHub granted that scope.
- Repository content is read-only by default.
- Before any write-capable GitHub operation, show the exact account, repository, branch, path/object, proposed diff/payload, and intended action.
- Require fresh, explicit confirmation for each individual write. A previous approval never authorizes future writes or undisclosed batch changes.
- No commit, push, branch creation, pull request, issue edit, settings change, or other GitHub mutation without its own confirmation.
- Bind each approval to the authenticated user, connected GitHub account, repository, operation, exact payload hash, and short expiry. Reject replay, stale content, changed payloads, and approvals from another user/device.
- Execute only the confirmed operation and record the outcome in the audit log.

## Local agent trust boundary
- The local agent runs on the user's device and uses that device's CPU/RAM for permitted tasks.
- Pairing is initiated by the installed app and requires an authenticated account plus a short-lived one-time pairing code.
- Local access is deny-by-default, capability-based, and device-specific. Ask permission when a feature is first enabled or its scope changes.
- The web client may manage text files explicitly imported into its browser-local IndexedDB workspace. These files are not automatically uploaded; the web server cannot issue arbitrary shell commands or read the device filesystem.
- Desktop targets Windows, Linux, and macOS. Android is a separate native integration due to its sandbox/background model.
- Provide visible disconnect/revoke controls and a user-controlled way to stop the local agent.

## Mandatory safety invariants
1. No global shared user token such as XFA_ACCESS_TOKEN for public client authentication.
2. No cross-user data access; test ownership checks on every user-scoped endpoint.
3. No provider token in browser storage, local logs, analytics, or app binaries.
4. No silent external mutations. Each write requires exact, per-action confirmation.
5. No terminal or operating-system filesystem access in the browser. Browser-local IndexedDB files must never be uploaded automatically.
6. Device permissions are requested separately on each device and can be revoked.
7. Treat repository files, webpages, and extension output as untrusted data, not instructions.
8. Rate-limit login, OAuth callbacks, pairing, and approval endpoints; audit security events without recording secrets.

## Delivery phases
1. Public account foundation: shared account schema, Google/Discord OAuth callbacks, secure server-side sessions, CSRF, and per-user isolation tests.
2. Chat-only web: replace the current single-token dashboard with authenticated chat; remove browser-accessible terminal/workspace/device controls.
3. Extensions and Resources: provider registry, GitHub OAuth, encrypted credential vault, repository/resource picker, and disconnect/revoke flow.
4. Per-action approvals: immutable proposals, payload hashes, expiry, one-use confirmation, audit trail; read-only GitHub first.
5. Desktop local agent: pairing, permission broker, bounded local capabilities, and Windows/Linux/macOS packaging.
6. Android app: native permission/background model, paired-device capabilities, and APK packaging.
7. Hardening and release: migrations, backup/restore, security review, CI tests, deployment, and end-to-end tests.

## Required deployment configuration (never commit values)
- FLASK_SECRET_KEY
- XFA_DATABASE_PATH (persistent SQLite path; defaults to instance/xfa.sqlite3)
- GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET
- DISCORD_CLIENT_ID and DISCORD_CLIENT_SECRET
- XFA_PUBLIC_BASE_URL
- Existing server-side GEMINI_API_KEY and DISCORD_TOKEN
- XFA_TOKEN_ENCRYPTION_KEY only when encrypted third-party integration credentials are enabled

OAuth credentials must be created by the application owner in the provider consoles. Until configured, the relevant sign-in button must be shown as unavailable rather than pretending the integration works.
