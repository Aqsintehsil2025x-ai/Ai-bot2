# ==============================================================================
# XYRIN BOT — LAUNCHER (tek komutla çalıştırıcı)
# ==============================================================================
import asyncio
from xyrin_bot import main

if __name__ == "__main__":
    try:
        sys_exit_code = asyncio.run(main())
        raise SystemExit(sys_exit_code)
    except KeyboardInterrupt:
        pass