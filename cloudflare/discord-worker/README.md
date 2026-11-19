# XFA Discord Worker + Gateway

This branch contains an isolated Cloudflare test deployment for the Xyrin Discord bot. It does not modify `main` or the Replit project.

## Runtime architecture

- **Worker HTTP endpoint**: verifies Discord Ed25519 signatures and handles HTTP-delivered slash-command interactions.
- **Durable Object `DiscordGateway`**: opens the outbound Discord Gateway WebSocket, identifies/resumes the bot session, heartbeats, and handles Gateway-delivered interactions and selected message/member events.
- **D1**: stores FAQ entries, interaction audit records, per-server provider/configuration values, suggestions, and member-join event timestamps.
- **Secrets Store**: `DISCORD_TOKEN`, `DISCORD_CLIENT_ID`, `GEMINI_API_KEY`, and `NVIDIA_API_KEY` are bound at runtime; secret values are not stored in Git.

The Worker is configured with a one-minute Cron Trigger to ensure the Gateway Durable Object starts or reconnects. Manual endpoints:
- Health: `/health`
- Gateway state: `/gateway/status`
- Start/reconnect Gateway: `/gateway/start`

## Implemented interaction handlers

- `/ping`, `/yardim`, `/kimlik`
- `/sor`, `/xfa` (Gemini and NVIDIA)
- `/zar`, `/yazitura`, `/kahve`, `/secim`, `/sekiztop`, `/ship`
- `/kb add|ask|list|remove` with D1 and `MANAGE_GUILD` checks
- `/kullanici`, `/avatar`, `/sunucu`, `/rapor`
- `/oneri`, `/analytics`, `/gemini`, `/nvidia`
- Moderation and channel/role command handlers are present in the TypeScript source branch; test them before relying on them in a live server.

The Gateway also handles selected prefix commands (`!ping`, `!yardim`, `!kimlik`, `!zar`, `!yazitura`, `!kahve`, `!secim`, `!sekiztop`), welcome-channel messages, anti-raid warning events, and AFK mention notices.

## Slash command registration

Run `node scripts/register-commands.mjs` with `DISCORD_APPLICATION_ID`, `DISCORD_TOKEN`, and optionally `DISCORD_TEST_GUILD_ID`. The script reads the existing command list and creates/updates only the listed command names; it does not bulk-replace unrelated application commands.

The Discord Developer Portal Interactions Endpoint URL has **not** been changed. To route slash commands over HTTP, set it to:

`https://xfa-discord-test.aqsin-tehsil2025x.workers.dev/discord/interactions`

If that URL is not set, Discord delivers slash interactions through the Gateway; the Durable Object handles the implemented subset. Do not switch production routing until the commands you rely on have been tested.

## Deployment and limits

The test Worker currently receives 100% of traffic for its own `workers.dev` hostname. It is not a replacement for every Python bot feature yet. Voice-channel joining/voice playback, all original prefix commands, every cog, and full feature parity still need implementation. Cloudflare Workers do not run the original `discord.py` process.

A continuously connected outbound Gateway WebSocket keeps the Durable Object active and is billable duration. Cloudflare's Free allowance currently includes 13,000 GB-s/day; one 128 MB object running continuously is approximately 10,800 GB-s/day before other account usage. If the account exceeds a Free limit, further operations can fail. Monitor usage before relying on this as a permanent always-on host.

Replit and the production Discord Interactions Endpoint were not changed by this deployment.
