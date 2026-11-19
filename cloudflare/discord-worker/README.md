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
npx wrangler secret put DISCORD_TOKEN
npx wrangler secret put DISCORD_APPLICATION_ID
npm run deploy
```

Set Discord Developer Portal > General Information > Interactions Endpoint URL to:
`https://xfa-discord-test.<your-workers-subdomain>.workers.dev/discord/interactions`

Register slash commands using the command definitions in `scripts/register-commands.ts`. Use a dedicated test Discord application and test server; do not point the production application at this endpoint.

## Not yet ported
Gateway event features (message tracking, member-join anti-raid detection, voice-state/tempvoice, welcome events, prefix commands, and continuous background tasks) are not HTTP interactions. They need a separate persistent Gateway runtime or a deliberate redesign. This Worker does not claim those features are available.
