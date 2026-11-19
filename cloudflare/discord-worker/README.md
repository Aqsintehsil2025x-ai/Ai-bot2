# XFA Discord Worker (TypeScript test port)

This is an isolated Cloudflare Workers implementation. It does not replace the Python bot on Replit and does not modify `main`.

## Included
- TypeScript HTTP Interaction endpoint with Ed25519 signature verification.
- Discord PING handshake, `/ping`, and `/xfa`.
- D1-backed per-server FAQ commands: `/kb add`, `/kb ask`, `/kb list`, `/kb remove`.
- Permission checks for FAQ administration (`MANAGE_GUILD`).
- Interaction audit log.

## Deploy
```bash
npm ci
npm run typecheck
npm run db:remote
npx wrangler secret put DISCORD_PUBLIC_KEY
npm run deploy
```

Set Discord Developer Portal > General Information > Interactions Endpoint URL to:
`https://xfa-discord-test.aqsin-tehsil2025x.workers.dev/discord/interactions`

Worker health endpoint: `https://xfa-discord-test.aqsin-tehsil2025x.workers.dev/health`. The existing account-level Secrets Store is bound with least privilege: `DISCORD_CLIENT_ID`, `GEMINI_API_KEY`, and `NVIDIA_API_KEY`. Values remain encrypted and are never copied into this repository. The production `DISCORD_TOKEN`, `DISCORD_CLIENT_SECRET`, and XFA account tokens are intentionally not bound to this test Worker, so the Replit bot credentials are not exposed to the test runtime. The store does not contain `DISCORD_PUBLIC_KEY`; add the public key for a dedicated test Discord application as a Worker secret with `npx wrangler secret put DISCORD_PUBLIC_KEY` before configuring the Discord Interactions URL. Do not point the production application at this test endpoint.

Register slash commands using `node scripts/register-commands.mjs` with `DISCORD_APPLICATION_ID`, `DISCORD_TOKEN`, and optionally `DISCORD_TEST_GUILD_ID` set locally. Use a dedicated test Discord application and test server; do not point the production application at this endpoint. Use a dedicated test Discord application and test server; do not point the production application at this endpoint.

## Not yet ported
Gateway event features (message tracking, member-join anti-raid detection, voice-state/tempvoice, welcome events, prefix commands, and continuous background tasks) are not HTTP interactions. They need a separate persistent Gateway runtime or a deliberate redesign. This Worker does not claim those features are available.
