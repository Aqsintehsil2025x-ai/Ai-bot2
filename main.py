"""Render Web Service launcher: serve the website and Discord bot in one process."""
import asyncio
import os
import threading

# xyrin_bot.py has an aiohttp health listener on PORT. The Flask app below owns
# Render's single public port, so disable that second listener before importing it.
os.environ["HEALTH_SERVER"] = "false"

# Make !panel give users this service's URL on Render, when the platform exposes it.
_render_host = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "").strip()
if _render_host:
    os.environ.setdefault("PANEL_PUBLIC_URL", f"https://{_render_host}")

from web_app import app, set_bot
from xyrin_bot import DISCORD_TOKEN, bot, is_sovereign_member, main as run_bot, panel_settings
from panel_routes import register_panel_routes


def start_web_server():
    port = int(os.environ.get("PORT") or os.environ.get("WEB_PORT") or "10000")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False, threaded=True)


async def main():
    if not DISCORD_TOKEN:
        raise RuntimeError("DISCORD_TOKEN çevre değişkeni tanımlı değil.")

    set_bot(bot)
    register_panel_routes(bot, panel_settings, is_sovereign_member)
    web_thread = threading.Thread(target=start_web_server, daemon=True, name="xyrin-web")
    web_thread.start()
    return await run_bot()


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except KeyboardInterrupt:
        pass
