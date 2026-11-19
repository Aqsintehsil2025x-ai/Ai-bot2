# XFA Discord Worker + Gateway

This is an isolated Cloudflare test runtime for the Xyrin Discord bot. It does not modify the Replit project or the production Discord Interactions Endpoint.

## Runtime architecture

- **Worker**: Discord HTTP Interactions endpoint, timestamp-bounded Ed25519 signature verification, D1 access, and Cron processing.
- **Shared dispatcher**: HTTP Interactions and Gateway-delivered slash commands use the same command handler and provider selection.
- **AI provider layer**: Gemini 3.8 Flash → Gemini 3.5 Flash-Lite model fallback, NVIDIA Nemotron model support, bounded retries for temporary errors, and cross-provider fallback. NVIDIA HTTP 410 is treated as an account/endpoint access issue rather than blindly retrying model names. The bot reports which provider actually answered.
- **Durable Object — DiscordGateway**: persistent outbound Discord Gateway WebSocket, Identify/Resume, heartbeat ACK checks, reconnects, selected message/member events, and Gateway-delivered slash interactions.
- **D1**: FAQ, audit logs, server settings, suggestions, join events, virtual economy/XP, and scheduled reminders.
- **Secrets Store**: bot token and AI provider keys are bound at runtime; secret values are not in Git.

The Worker has a one-minute Cron Trigger to start/reconnect the Gateway and deliver due reminders. Endpoints:
- Health: https://xfa-discord-test.aqsin-tehsil2025x.workers.dev/health
- Gateway state: https://xfa-discord-test.aqsin-tehsil2025x.workers.dev/gateway/status
- Start/reconnect: https://xfa-discord-test.aqsin-tehsil2025x.workers.dev/gateway/start

## Implemented commands

- General/AI: /ping, /yardim, /kimlik, /sor, /xfa
- Utilities: /zar, /yazitura, /kahve, /secim, /sekiztop, /ship, /anket
- FAQ: /kb add, /kb ask, /kb list, /kb remove
- User/server: /kullanici, /avatar, /sunucu, /rapor, /analytics
- Moderation: /kick, /ban, /unban, /mute, /unmute, /temizle, /slowmode, /rolver, /rolal, /nick, /duyuru, /kilitle, /kilita, /kanalolustur, /rololustur
- Server settings/events: /gemini, /nvidia, /hosgeldin, /modlog, /afk, /antiraid
- Virtual economy (no betting): /bakiye, /gunluk, /transfer, /market, /satinal, /calis, /seviye, /siralama
- Scheduling: /hatirlat, /etkinlik, /hatirlatmalar, /hatirlatsil
- Prefix subset: !ping, !yardim, !kimlik, !zar, !yazitura, !kahve, !secim, !sekiztop

D1 stores the economy, reminders, suggestions, and server settings. Message XP has a per-user cooldown. AFK is cleared when a member returns to chat and mentioned AFK members are announced. Anti-raid only sends warnings; it does not automatically punish members. Gateway heartbeat startup timers are cancelled on disconnect, reconnect uses bounded exponential backoff, and invalid session sequence codes clear stale resume state.

## Validation

From this directory run `npm run check` for TypeScript checks, AI provider regression tests, and command registration syntax. CI also runs `wrangler deploy --dry-run` to validate the Cloudflare bundle. The tests mock provider responses; they do not claim that external Gemini/NVIDIA accounts are currently entitled or available.

## Slash command registration

Run node scripts/register-commands.mjs with DISCORD_APPLICATION_ID, DISCORD_TOKEN, and optionally DISCORD_TEST_GUILD_ID. The script upserts only the listed command names and preserves unrelated existing application commands.

The Discord Developer Portal Interactions Endpoint URL has not been changed. To route slash commands over HTTP, set it to:

https://xfa-discord-test.aqsin-tehsil2025x.workers.dev/discord/interactions

If that URL is not set, Discord sends slash interactions through the Gateway; the Durable Object handles the supported commands directly. Existing Replit deployment and production routing remain untouched.

## Remaining gaps

This is a broad Worker migration, not yet byte-for-byte feature parity with the Python bot. Voice-channel joining/playback, every original command/cog, and some background automations are not ported. Discord voice requires a separate voice transport and is not provided by this Worker.

## Free-plan usage

A continuously connected outbound Gateway WebSocket keeps one 128 MB Durable Object active. At 24/7 uptime this is approximately 10,800 GB-s/day, against Cloudflare's 13,000 GB-s/day Free allowance before other account usage. Exceeding a Free limit can cause further operations to fail. Monitor usage; this is not a guarantee of unlimited free hosting.
