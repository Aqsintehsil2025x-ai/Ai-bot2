# XFA account and local storage setup

## Required server secrets

Add these values in the Replit Secrets panel. Never put them in browser code or commit them to Git.

- `FLASK_SECRET_KEY`: generate with `python -c "import secrets; print(secrets.token_hex(32))"`.
- `XFA_PUBLIC_BASE_URL`: the public origin of this deployment, with no trailing slash. Example: `https://ai-bot-2--aqsintehsil2025.replit.app`.
- `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`: from the Google OAuth web application.
- `DISCORD_TOKEN`: the existing Discord bot token, used by the separate Discord bot and its Tickets support system.

Optional:
- `XFA_DATABASE_PATH`: writable persistent SQLite database path shared with the existing XFA account and integration tables. Default: `instance/xfa.sqlite3`.
- `XFA_COOKIE_SECURE`: defaults to `true`. Set to `false` only for local HTTP development; keep it enabled on the public site.

## OAuth callback URLs

Register this exact redirect URL in Google Cloud Console:

- Google: `https://ai-bot-2--aqsintehsil2025.replit.app/auth/callback/google`

The callback host must match the deployment's public domain. If the Replit deployment domain changes, update `XFA_PUBLIC_BASE_URL` and the Google OAuth callback allowlist.

Google OAuth:
1. Create an OAuth client of type Web application in Google Cloud Console.
2. Add the Google callback above under Authorized redirect URIs.
3. Copy the client ID and client secret into the two Google Replit Secrets.

## How account and file storage works

- The browser receives a Secure, HttpOnly, SameSite=Lax cookie containing only a signed random session identifier.
- Session contents and Google identity records are stored server-side in the shared XFA SQLite database (`xfa_sessions` and `xfa_oauth_accounts`).
- Provider access tokens are exchanged server-side and discarded. They are not kept in the database.
- Google is the only XFA sign-in provider. Discord OAuth and account linking are disabled. Discord remains a separate community and Tickets support channel for account-access problems.
- User workspace files are stored in browser IndexedDB, partitioned by XFA account ID. File contents are not uploaded to the XFA server by the workspace UI.
- Local files are available only in the same browser profile and device. Clearing site/browser data can delete them; use **İndir** to keep an external backup. Cloud sync is not enabled.
- If a user deliberately attaches a text file to a chat message, its selected text is included in that message sent to the AI service. The local workspace is not automatically attached to agent or chat requests.
- Account recovery requests are handled manually by the project owner through the Discord server's **Tickets** section. Users should provide their account email and a description of the issue, never passwords or verification codes.

## Removed legacy access token

The XFA dashboard and `/xfa/api` no longer use `XFA_ACCESS_TOKEN` or Bearer-token entry. Remove the old `XFA_ACCESS_TOKEN` secret from Replit after deploying this branch. Keep `FLASK_SECRET_KEY` and Google OAuth secrets server-side.

## Email

Gmail SMTP is intentionally not part of this stage. Google OAuth is used only for sign-in; Discord is used separately for Tickets-based support.
