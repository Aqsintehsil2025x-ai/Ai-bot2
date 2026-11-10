# Live panel URL configuration

The authenticated panel API and `!panel` command run inside this bot's existing Flask web server and Discord process. Do not launch another bot process for the panel.

Set `PANEL_PUBLIC_URL` in the Ai-bot2 deployment environment to the public HTTPS origin of the **Discord-Bot-Site** app, for example `https://your-discord-bot-site.example`. Use only the scheme and host; the command appends `/panel`.

The Discord-Bot-Site deployment must separately define `AI_BOT2_API_ORIGIN` as this bot service's public HTTPS origin. Configure both values in deployment secrets/environment settings, not in committed source files.

After both apps are deployed, run `!panel` in a server where the user has permission, open the sent link, and enter the one-time six-character code. The site forwards authenticated panel requests to this existing bot process.
