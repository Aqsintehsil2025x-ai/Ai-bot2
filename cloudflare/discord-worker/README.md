# XFA / Discord Cloudflare test worker

This is an isolated, free-tier-oriented interaction-endpoint prototype. It does not alter the Python bot, Flask app, or repository `main` branch.

## What works in this first slice

- `GET /health` returns a non-sensitive health response.
- `POST /discord/interactions` verifies Discord Ed25519 request signatures.
- Handles Discord's PING handshake.
- Handles test slash commands `/ping` and `/xfa`.
- Writes a minimal interaction audit record to D1.

## Important scope boundary

This is **not** a full port of the existing `discord.py` bot. It uses Discord's HTTP Interactions model, not the long-lived Discord Gateway connection. Gateway-driven features (message listeners, member join events, voice state / temporary voice channels, and other event-driven cogs) are not migrated by this prototype. Each existing command must be ported and tested individually. The Python bot remains the production implementation on Replit.

## Setup

1. Create a D1 database named `xfa-discord-test` in the Cloudflare dashboard.
2. Replace `REPLACE_WITH_D1_DATABASE_ID` in `wrangler.jsonc` with that database's ID.
3. From this directory run `npm install`, then `npm run db:remote`.
4. Add Worker-scoped secrets with `npx wrangler secret put DISCORD_PUBLIC_KEY`. Add any provider keys only when the relevant feature is implemented.
5. Deploy with `npm run deploy`.
6. In the Discord Developer Portal, configure the Interactions Endpoint URL as `https://<worker-domain>/discord/interactions`. Discord's endpoint verification sends a PING which this Worker answers.
7. Register the `ping` and `xfa` application commands using Discord's application-commands API. Do not point the production bot at this test endpoint.

## Secrets Store note

Account-level Secrets Store entries are not automatically exposed as Worker environment variables. This first prototype expects Worker-scoped secrets/bindings. Bind the central Secrets Store only after following Cloudflare's current Workers integration instructions and confirming the required plan/permissions. Never commit secret values.

## Security and rollout

- Do not log request bodies, signatures, tokens, or provider credentials.
- Use a separate Discord test application and test server.
- Keep the production bot token and endpoint unchanged.
- Do not merge this branch into `main` until all checks and manual Discord tests pass.
