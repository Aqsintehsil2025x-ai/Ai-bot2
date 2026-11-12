# XFA account and local storage setup

## Required server secrets

Add these values in the Replit Secrets panel. Never put them in browser code or commit them to Git.

- `FLASK_SECRET_KEY`: generate with `python -c "import secrets; print(secrets.token_hex(32))"`.
- `XFA_PUBLIC_BASE_URL`: the public origin of this deployment, with no trailing slash. Example: `https://ai-bot-2--aqsintehsil2025.replit.app`.
- `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`: from the Google OAuth web application.
- `DISCORD_CLIENT_ID` and `DISCORD_CLIENT_SECRET`: from the Discord Developer Portal OAuth2 application.
- `DISCORD_TOKEN`: the existing Discord bot token, used only by the bot process.

Optional:
- `XFA_DATA_DIR`: writable persistent directory for the minimal account database and server-side sessions. Default: `data/xfa`.
- `XFA_COOKIE_SECURE`: defaults to `true`. Set to `false` only for local HTTP development; keep it enabled on the public site.

## OAuth callback URLs

Register these exact redirect URLs in both provider dashboards:

- Google: `https://ai-bot-2--aqsintehsil2025.replit.app/auth/callback/google`
- Discord: `https://ai-bot-2--aqsintehsil2025.replit.app/auth/callback/discord`

The callback host must match the deployment's public domain. If the Replit deployment domain changes, update `XFA_PUBLIC_BASE_URL` and both provider callback allowlists.

Google OAuth:
1. Create an OAuth client of type Web application in Google Cloud Console.
2. Add the Google callback above under Authorized redirect URIs.
3. Copy the client ID and client secret into the two Google Replit Secrets.

Discord OAuth:
1. Open the XFA application in Discord Developer Portal.
2. In OAuth2, add the Discord callback above as a Redirect.
3. Copy the Client ID and Client Secret into the two Discord Replit Secrets.
4. OAuth scopes requested are `identify` and `email`; XFA does not request a user's Discord password.

## How account and file storage works

- The browser receives a Secure, HttpOnly, SameSite=Lax cookie containing only a signed random session identifier.
- Session contents, minimal provider identity records, and notification preferences are stored server-side in SQLite.
- Provider access tokens are exchanged server-side and discarded. They are not kept in the database.
- Users can sign in with Google or Discord. To use both on one XFA profile, sign in with the first provider and explicitly link the second from **Ayarlar → Hesabım**. Matching email addresses are not silently merged.
- User workspace files are stored in browser IndexedDB, partitioned by XFA account ID. File contents are not uploaded to the XFA server by the workspace UI.
- Local files are available only in the same browser profile and device. Clearing site/browser data can delete them; use **İndir** to keep an external backup. Cloud sync is not enabled.
- If a user deliberately attaches a text file to a chat message, its selected text is included in that message sent to the AI service. The local workspace is not automatically attached to agent or chat requests.
- Discord DMs are disabled by default. A user must link Discord and enable the explicit notification consent in **Ayarlar → Discord Bildirimleri**. Discord privacy settings may still prevent delivery.

## Removed legacy access token

The XFA dashboard and `/xfa/api` no longer use `XFA_ACCESS_TOKEN` or Bearer-token entry. Remove the old `XFA_ACCESS_TOKEN` secret from Replit after deploying this branch. Keep `FLASK_SECRET_KEY` and all provider secrets server-side.

## Email

Gmail SMTP is intentionally not part of this stage. XFA login uses Google OAuth; notifications currently use Discord DMs only.
