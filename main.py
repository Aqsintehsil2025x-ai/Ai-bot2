"""Render Web Service launcher: serve the website and Discord bot in one process."""
import asyncio
import os
import shutil
import subprocess
import threading

# xyrin_bot.py has an aiohttp health listener on PORT. The Flask app below owns
# Render's single public port, so disable that second listener before importing it.
os.environ["HEALTH_SERVER"] = "false"

from web_app import app, set_bot
from xyrin_bot import DISCORD_TOKEN, bot, main as run_bot


def start_web_server():
    port = int(os.environ.get("PORT") or os.environ.get("WEB_PORT") or "10000")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False, threaded=True)


def ensure_dashboard_built():
    dashboard_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard")
    built_index = os.path.join(dashboard_dir, "dist", "index.html")
    if os.path.isfile(built_index):
        return

    npm = shutil.which("npm")
    if not npm:
        raise RuntimeError("Dashboard build için npm bulunamadı. Replit nodejs-20 modülünü etkinleştir.")

    print("[dashboard] Frontend build bulunamadı; bağımlılıklar kuruluyor...", flush=True)
    lockfile = os.path.join(dashboard_dir, "package-lock.json")
    install = [npm, "ci", "--no-audit", "--no-fund"] if os.path.isfile(lockfile) else [npm, "install", "--no-audit", "--no-fund"]
    subprocess.run(install, cwd=dashboard_dir, check=True)
    subprocess.run([npm, "run", "build"], cwd=dashboard_dir, check=True)
    if not os.path.isfile(built_index):
        raise RuntimeError("Dashboard build tamamlandı ancak dashboard/dist/index.html oluşmadı.")
    print("[dashboard] Frontend hazır.", flush=True)


async def main():
    if not DISCORD_TOKEN:
        raise RuntimeError("DISCORD_TOKEN çevre değişkeni tanımlı değil.")

    ensure_dashboard_built()
    set_bot(bot)
    web_thread = threading.Thread(target=start_web_server, daemon=True, name="xyrin-web")
    web_thread.start()
    return await run_bot()


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except KeyboardInterrupt:
        pass
