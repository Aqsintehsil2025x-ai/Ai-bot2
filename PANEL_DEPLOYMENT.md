# Ai-bot2 — single-server deployment

The Discord bot, Flask API, public website and React management panel run from **one Replit deployment** and one Python process.

## Deploy

1. Import this Ai-bot2 repository into Replit.
2. Add the bot's existing environment secrets, including `DISCORD_TOKEN` and the required AI provider keys.
3. Deploy this project once. The existing `.replit` config provides Python 3.12 and Node.js 20.
4. GitHub Actions builds and commits `dashboard/dist` after pushes. If the build is not present, `main.py` installs the dashboard dependencies and builds it at startup.
5. Set `PANEL_PUBLIC_URL` to this same deployment's public HTTPS URL if Replit does not expose `REPLIT_DOMAINS`.

## Panel login

Run `!panel` in a Discord server where you have management permission. Open the link sent by the bot and enter the one-time six-character code. The React panel calls the existing Flask API and uses its session cookie directly. There is no second API server, proxy, Render origin, or second bot process.

## Local frontend build

```bash
cd dashboard
npm install
npm run build
```

Flask serves the website at `/`, the management panel at `/panel`, and built assets at `/assets/`.
