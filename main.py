import asyncio
import os
import signal
import threading

from web_app import app, set_bot
from xyrin_bot import DISCORD_TOKEN, bot


def start_web_server():
    port = int(os.environ.get("PORT") or os.environ.get("WEB_PORT") or 10000)
    print(f"[web] Flask sunucusu başlatılıyor: 0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False, threaded=True)


async def start_all():
    if not DISCORD_TOKEN:
        raise RuntimeError("DISCORD_TOKEN çevre değişkeni tanımlı değil.")

    set_bot(bot)
    threading.Thread(target=start_web_server, daemon=True, name="xyrin-web").start()

    loop = asyncio.get_running_loop()
    shutdown_requested = asyncio.Event()

    def request_shutdown():
        shutdown_requested.set()
        if not bot.is_closed():
            asyncio.create_task(bot.close())

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, request_shutdown)
        except (NotImplementedError, RuntimeError, ValueError):
            pass

    async with bot:
        await bot.start(DISCORD_TOKEN)

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(start_all()))
    except KeyboardInterrupt:
        pass
