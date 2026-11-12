# ==============================================================================
# XYRIN BOT — WEB SUNUCUSU (Flask)
# Botun sitesi: https://sunucu-adi.onrender.com
# ==============================================================================
from flask import Flask, render_template_string, jsonify, request, send_from_directory
import os

app = Flask(__name__)
DASHBOARD_DIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard", "dist")


def _serve_dashboard_index():
    if not os.path.isfile(os.path.join(DASHBOARD_DIST, "index.html")):
        return "Dashboard build bulunamadı. dashboard/ klasöründe npm install ve npm run build çalıştır.", 503
    return send_from_directory(DASHBOARD_DIST, "index.html")


@app.get("/panel")
def dashboard_panel():
    return _serve_dashboard_index()


@app.get("/assets/<path:filename>")
def dashboard_assets(filename):
    return send_from_directory(os.path.join(DASHBOARD_DIST, "assets"), filename)


@app.get("/images/<path:filename>")
def dashboard_images(filename):
    return send_from_directory(os.path.join(DASHBOARD_DIST, "images"), filename)


@app.get("/favicon.svg")
def dashboard_favicon():
    return send_from_directory(DASHBOARD_DIST, "favicon.svg")



# --- Bot referansı (main.py'den atanacak) ---
_bot = None
_dashboard_state = {
    "guilds": 0,
    "members": 0,
    "latency": 0,
    "status": "offline",
    "modules": {
        "ai": True,
        "economy": True,
        "moderation": True,
        "utility": True,
    },
    "dashboard": {
        "command": "!yardim",
        "language": "Türkçe",
        "welcome_message": "Aramıza hoş geldin, {kullanıcı}!",
    },
}

SERVER_INVITE = "https://discord.gg/Dkj8VFnga"
BOT_INVITE = "https://discord.com/oauth2/authorize?client_id=1555918878268456970&permissions=8&integration_type=0&scope=bot"


def set_bot(bot):
    global _bot
    _bot = bot
    try:
        from panel_wire import wire_panel
        wire_panel(app, bot)
    except Exception as exc:
        print(f"[web_app] panel_wire failed: {exc}", flush=True)
    try:
        from xfa_agent.auth import register_auth
        register_auth(app)
        app.config["XFA_DISCORD_BOT"] = bot
    except Exception as exc:
        print(f"[web_app] XFA authentication registration failed: {exc}", flush=True)
    try:
        from xfa_agent.routes import register_xfa
        register_xfa(app)
    except Exception as exc:
        print(f"[web_app] XFA registration failed: {exc}", flush=True)


@app.route("/health")
def health():
    ready = bool(_bot and getattr(_bot, "is_ready", lambda: False)())
    latency = 0
    try:
        if ready:
            latency = round(_bot.latency * 1000)
    except Exception:
        pass
    return jsonify({
        "status": "ok",
        "ready": ready,
        "guilds": len(_bot.guilds) if _bot else 0,
        "latency_ms": latency,
    })


@app.route("/")
def index():
    guild_count = len(_bot.guilds) if _bot else _dashboard_state["guilds"]
    member_count = sum(g.member_count or 0 for g in _bot.guilds) if _bot else _dashboard_state["members"]
    latency = round(_bot.latency * 1000) if _bot and _bot.is_ready() else _dashboard_state["latency"]
    status = "online" if (_bot and _bot.is_ready()) else "offline"

    _dashboard_state["guilds"] = guild_count
    _dashboard_state["members"] = member_count
    _dashboard_state["latency"] = latency
    _dashboard_state["status"] = status

    # Serve the React website from this same Flask process.
    if os.path.isfile(os.path.join(DASHBOARD_DIST, "index.html")):
        return send_from_directory(DASHBOARD_DIST, "index.html")

    html = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Xyrin Flower</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;500;600;700&family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-dark: #020b17;
            --bg-mid: #071527;
            --bg-blue: #0a1d31;
            --panel: rgba(18, 28, 42, 0.8);
            --line: rgba(155, 176, 224, 0.25);
            --text: #edf3ff;
            --muted: #a7b8d6;
            --soft: #c7d8f8;
            --blue-1: #8fa9ff;
            --blue-2: #b6ccff;
            --blue-3: #dfe9ff;
            --shadow: 0 0 40px rgba(128, 153, 255, 0.2);
        }

        * { box-sizing: border-box; }
        html, body {
            margin: 0;
            min-height: 100%;
            background: var(--bg-dark);
            color: var(--text);
            font-family: 'Inter', sans-serif;
        }
        body {
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            background:
                radial-gradient(circle at 50% 28%, rgba(68, 88, 142, 0.18), transparent 20%),
                radial-gradient(circle at 15% 20%, rgba(68, 88, 142, 0.12), transparent 18%),
                radial-gradient(circle at 85% 20%, rgba(68, 88, 142, 0.12), transparent 18%),
                linear-gradient(180deg, #010812 0%, #020d1d 32%, #010b15 100%);
        }

        .page {
            width: 100%;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }

        .topbar {
            width: 100%;
            padding: 20px 30px 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
            z-index: 5;
        }

        .brand-mini {
            display: inline-flex;
            align-items: center;
            gap: 10px;
            font-size: 12px;
            letter-spacing: 0.18em;
            text-transform: uppercase;
            color: var(--soft);
            opacity: 0.9;
        }

        .brand-mini .dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: linear-gradient(135deg, var(--blue-1), var(--blue-3));
            box-shadow: 0 0 16px rgba(143,169,255,0.9);
        }

        .nav-links {
            display: flex;
            gap: 18px;
            align-items: center;
            flex-wrap: wrap;
        }

        .nav-links a {
            color: var(--muted);
            text-decoration: none;
            font-size: 12px;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            transition: 0.2s ease;
        }

        .nav-links a:hover { color: var(--text); }

        .hero {
            position: relative;
            flex: 1;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 36px 22px 60px;
            overflow: hidden;
        }

        .hero::before,
        .hero::after {
            content: "";
            position: absolute;
            inset: 0;
            pointer-events: none;
        }

        .hero::before {
            background:
                radial-gradient(circle at 50% 22%, rgba(100, 127, 255, 0.12), transparent 19%),
                radial-gradient(circle at 20% 72%, rgba(53, 79, 136, 0.14), transparent 18%),
                radial-gradient(circle at 80% 72%, rgba(53, 79, 136, 0.14), transparent 18%);
        }

        .hero-inner {
            position: relative;
            z-index: 1;
            width: min(1500px, 100%);
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 500px;
        }

        .banner-wrap {
            position: relative;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            width: 100%;
            padding: 20px 14px;
        }

        .banner-line {
            width: min(26vw, 360px);
            height: 2px;
            background: linear-gradient(90deg, transparent, rgba(194, 205, 248, 0.5), transparent);
            opacity: 0.75;
        }

        .brand-row {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: clamp(10px, 2vw, 28px);
            margin: 12px 0 8px;
        }

        .brand-mark {
            position: relative;
            width: clamp(90px, 9vw, 180px);
            height: clamp(90px, 9vw, 180px);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            filter: drop-shadow(0 0 20px rgba(134,157,255,0.6));
        }

        .brand-mark::before {
            content: "";
            position: absolute;
            inset: 0;
            background: linear-gradient(135deg, rgba(158,174,255,0.18), rgba(166,190,255,0.04));
            border-radius: 50%;
            transform: scale(1.05);
        }

        .flower {
            position: relative;
            width: 100%;
            height: 100%;
            display: block;
        }

        .flower .petal {
            position: absolute;
            left: 50%;
            top: 50%;
            width: 26%;
            height: 44%;
            background: linear-gradient(180deg, rgba(176,198,255,0.98), rgba(118,142,255,0.82));
            border-radius: 55% 55% 60% 60%;
            transform-origin: center bottom;
            box-shadow: 0 0 18px rgba(122, 146, 255, 0.35);
        }

        .flower .petal:nth-child(1) { transform: translate(-50%, -70%) rotate(0deg); }
        .flower .petal:nth-child(2) { transform: translate(-50%, -70%) rotate(45deg); }
        .flower .petal:nth-child(3) { transform: translate(-50%, -70%) rotate(90deg); }
        .flower .petal:nth-child(4) { transform: translate(-50%, -70%) rotate(135deg); }
        .flower .petal:nth-child(5) { transform: translate(-50%, -70%) rotate(180deg); }
        .flower .petal:nth-child(6) { transform: translate(-50%, -70%) rotate(225deg); }
        .flower .petal:nth-child(7) { transform: translate(-50%, -70%) rotate(270deg); }
        .flower .petal:nth-child(8) { transform: translate(-50%, -70%) rotate(315deg); }

        .flower .core {
            position: absolute;
            left: 50%;
            top: 50%;
            width: 18%;
            height: 18%;
            transform: translate(-50%, -50%);
            background: linear-gradient(135deg, #eaf0ff, #8aa3ff);
            border-radius: 50%;
            box-shadow: 0 0 18px rgba(146,168,255,0.8);
        }

        .brand-title {
            position: relative;
            font-family: 'Cormorant Garamond', serif;
            font-size: clamp(4.5rem, 11vw, 17rem);
            line-height: 0.8;
            letter-spacing: -0.04em;
            color: rgba(233, 238, 255, 0.96);
            text-shadow: 0 0 26px rgba(174, 188, 255, 0.18), 0 0 18px rgba(146, 168, 255, 0.12);
            font-weight: 700;
        }

        .brand-sub {
            margin-top: 10px;
            font-family: 'Cormorant Garamond', serif;
            font-size: clamp(1.6rem, 2.8vw, 3rem);
            font-style: italic;
            letter-spacing: 0.12em;
            color: rgba(183, 199, 255, 0.82);
            text-transform: none;
            text-shadow: 0 0 18px rgba(140, 160, 255, 0.18);
        }

        .cta-row {
            margin-top: 28px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 20px;
            flex-wrap: wrap;
        }

        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-width: 200px;
            padding: 16px 26px;
            border-radius: 999px;
            text-decoration: none;
            font-weight: 700;
            transition: 0.2s ease;
            letter-spacing: 0.04em;
        }

        .btn.primary {
            background: linear-gradient(135deg, #8fa9ff, #bfd4ff);
            color: #08131d;
            box-shadow: 0 16px 26px rgba(134, 156, 255, 0.35);
        }

        .btn.primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 20px 32px rgba(134, 156, 255, 0.45);
        }

        .btn.secondary {
            background: rgba(255,255,255,0.02);
            border: 1px solid rgba(179, 196, 255, 0.3);
            color: var(--text);
            backdrop-filter: blur(2px);
        }

        .btn.secondary:hover {
            background: rgba(255,255,255,0.04);
            transform: translateY(-2px);
        }

        .leaf {
            position: absolute;
            width: 18px;
            height: 52px;
            background: linear-gradient(180deg, rgba(124,145,236,0.38), rgba(18,30,52,0.08));
            border-radius: 60% 40% 60% 40%;
            transform-origin: center bottom;
            opacity: 0.7;
            filter: blur(0.2px);
            box-shadow: inset 0 0 14px rgba(255,255,255,0.08);
        }

        .leaf.l1 { left: 12%; top: 52%; transform: rotate(-24deg); }
        .leaf.l2 { right: 10%; top: 50%; transform: rotate(22deg); }
        .leaf.l3 { left: 18%; bottom: 6%; transform: rotate(24deg); }
        .leaf.l4 { right: 18%; bottom: 8%; transform: rotate(-18deg); }
        .leaf.l5 { left: 52%; top: 18%; transform: rotate(26deg); }

        @media (max-width: 860px) {
            .topbar {
                padding: 18px 16px 0;
                align-items: flex-start;
                gap: 10px;
                flex-direction: column;
            }
            .nav-links {
                gap: 10px 14px;
            }
            .brand-row {
                flex-direction: column;
            }
            .banner-line {
                width: 18vw;
            }
            .btn {
                width: 100%;
                min-width: 0;
            }
            .cta-row {
                width: 100%;
                flex-direction: column;
            }
        }
    </style>
</head>
<body>
    <div class="page">
        <header class="topbar">
            <div class="brand-mini"><span class="dot"></span> Xyrin</div>
            <nav class="nav-links">
                <a href="{{ server_invite }}" target="_blank">Sunucu</a>
                <a href="{{ bot_invite }}" target="_blank">Bot</a>
                <a href="/panel">Panel</a>
            </nav>
        </header>

        <main class="hero">
            <div class="hero-inner">
                <div class="banner-wrap">
                    <div class="brand-row">
                        <div class="banner-line"></div>
                        <div class="brand-mark" aria-hidden="true">
                            <div class="flower">
                                <span class="petal"></span>
                                <span class="petal"></span>
                                <span class="petal"></span>
                                <span class="petal"></span>
                                <span class="petal"></span>
                                <span class="petal"></span>
                                <span class="petal"></span>
                                <span class="petal"></span>
                                <span class="core"></span>
                            </div>
                        </div>
                        <div class="banner-line"></div>
                    </div>

                    <div class="brand-title">Xyrin</div>
                    <div class="brand-sub">Flower</div>

                    <div class="cta-row">
                        <a class="btn primary" href="{{ server_invite }}" target="_blank">Sunucuya Katıl</a>
                        <a class="btn secondary" href="{{ bot_invite }}" target="_blank">Botu Davet Et</a>
                    </div>
                </div>
            </div>

            <div class="leaf l1"></div>
            <div class="leaf l2"></div>
            <div class="leaf l3"></div>
            <div class="leaf l4"></div>
            <div class="leaf l5"></div>
        </main>
    </div>
</body>
</html>
    """
    return render_template_string(
        html,
        guild_count=guild_count,
        member_count=member_count,
        latency=latency,
        status=status,
        dashboard=_dashboard_state["dashboard"],
        server_invite=SERVER_INVITE,
        bot_invite=BOT_INVITE,
    )


@app.route("/api/stats")
def api_stats():
    if _bot is None:
        return jsonify({"guilds": 0, "members": 0, "latency": 0, "ready": False, "status": "offline"})
    return jsonify({
        "guilds": len(_bot.guilds),
        "members": sum(g.member_count or 0 for g in _bot.guilds),
        "latency": round(_bot.latency * 1000) if _bot.is_ready() else 0,
        "ready": _bot.is_ready(),
        "status": "online" if _bot.is_ready() else "offline",
    })


@app.route("/api/moderation", methods=["POST"])
def api_moderation():
    payload = request.get_json(silent=True) or {}
    _dashboard_state["dashboard"]["command"] = payload.get("command", _dashboard_state["dashboard"]["command"])
    _dashboard_state["dashboard"]["language"] = payload.get("language", _dashboard_state["dashboard"]["language"])
    _dashboard_state["dashboard"]["welcome_message"] = payload.get("welcome_message", _dashboard_state["dashboard"]["welcome_message"])

    modules = payload.get("modules", {})
    if isinstance(modules, dict):
        for key, value in modules.items():
            _dashboard_state["modules"][key] = bool(value)

    return jsonify({"success": True, "status": "saved", "data": _dashboard_state})


def run_web_server(port: int):
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
