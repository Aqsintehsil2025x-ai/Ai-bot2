# ==============================================================================
# XYRIN BOT — WEB SUNUCUSU (Flask)
# Botun sitesi: https://sunucu-adi.onrender.com
# ==============================================================================
from flask import Flask, render_template_string, jsonify, request
import os

app = Flask(__name__)

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


def set_bot(bot):
    global _bot
    _bot = bot


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

    html = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Xyrin Flow AI — Control Panel</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #070b17;
            --bg-2: #0e1629;
            --panel: rgba(19, 29, 49, 0.92);
            --panel-strong: rgba(21, 33, 56, 0.98);
            --panel-soft: rgba(22, 36, 58, 0.8);
            --line: rgba(113, 143, 188, 0.18);
            --line-strong: rgba(129, 151, 201, 0.28);
            --text: #edf4ff;
            --muted: #a9b7d0;
            --muted-2: #7f8ca8;
            --blue: #7fa1ff;
            --blue-2: #8ee7ff;
            --purple: #7d85f8;
            --orange: #ffb45d;
            --green: #5ee0ad;
            --red: #ff6c7d;
            --shadow: 0 20px 50px rgba(5, 10, 22, 0.6);
        }
        * { box-sizing: border-box; }
        html, body {
            margin: 0;
            height: 100%;
            background:
                radial-gradient(circle at top left, rgba(127, 161, 255, 0.12), transparent 26%),
                radial-gradient(circle at top right, rgba(130, 123, 255, 0.12), transparent 18%),
                linear-gradient(180deg, #040915, #0a1221 32%, #070d18 100%);
            color: var(--text);
            font-family: 'Inter', sans-serif;
        }
        body { min-height: 100vh; display: flex; flex-direction: column; }
        .shell { display: flex; width: 100%; min-height: 100vh; }
        .sidebar {
            width: 78px; background: rgba(10, 15, 28, 0.9); border-right: 1px solid var(--line);
            display: flex; flex-direction: column; align-items: center; padding: 18px 0 16px; gap: 12px;
        }
        .brand {
            width: 32px; height: 32px; border-radius: 10px; background: linear-gradient(135deg, var(--blue), var(--purple));
            display: flex; align-items: center; justify-content: center; color: white; font-weight: 700; font-size: 12px;
            box-shadow: 0 14px 26px rgba(127, 161, 255, 0.38); margin-bottom: 12px;
        }
        .nav-icon {
            width: 42px; height: 42px; border-radius: 12px; background: rgba(255,255,255,0.02);
            border: 1px solid transparent; display: flex; align-items: center; justify-content: center;
            color: var(--muted); font-size: 18px; cursor: pointer; transition: 0.2s ease;
        }
        .nav-icon.active {
            background: linear-gradient(180deg, rgba(127,161,255,0.14), rgba(127,161,255,0.04));
            border-color: rgba(127,161,255,0.4); color: white;
        }
        .nav-icon:hover { border-color: rgba(127,161,255,0.25); color: white; }
        .nav-spacer { flex: 1; }
        .main { flex: 1; display: flex; flex-direction: column; }
        .topbar {
            height: 64px; display: flex; align-items: center; justify-content: space-between; padding: 0 22px 0 18px;
            border-bottom: 1px solid var(--line); background: rgba(7, 11, 23, 0.32); backdrop-filter: blur(18px);
        }
        .topbar-left { display: flex; align-items: center; gap: 10px; color: var(--muted); min-width: 0; }
        .topbar-title { font-size: 13px; color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .topbar-right { display: flex; align-items: center; gap: 14px; }
        .chip {
            display: inline-flex; align-items: center; gap: 8px; padding: 7px 12px; border-radius: 10px;
            border: 1px solid var(--line); background: rgba(255,255,255,0.02); color: var(--muted); font-size: 12px;
        }
        .chip .dot { width: 7px; height: 7px; border-radius: 50%; background: var(--green); box-shadow: 0 0 10px rgba(94,224,173,0.8); }
        .notif {
            width: 34px; height: 34px; border-radius: 10px; border: 1px solid var(--line);
            display: flex; align-items: center; justify-content: center; background: rgba(255,255,255,0.02); color: var(--muted);
        }
        .content { padding: 24px 26px 28px; }
        .page-banner {
            display: flex; align-items: center; justify-content: space-between; gap: 18px; padding: 10px 0 16px;
        }
        .breadcrumb { color: var(--muted-2); font-size: 12px; display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
        .breadcrumb span:last-child { color: var(--text); font-weight: 600; }
        .status-pill {
            display: inline-flex; align-items: center; gap: 8px; padding: 8px 12px; background: rgba(94,224,173,0.08);
            border: 1px solid rgba(94,224,173,0.2); border-radius: 10px; color: #c8f9df; font-size: 12px; font-weight: 600;
        }
        .status-pill .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--green); box-shadow: 0 0 12px rgba(94,224,173,0.8); }
        .hero {
            background: linear-gradient(180deg, rgba(17, 24, 39, 0.88), rgba(15, 23, 39, 0.78));
            border: 1px solid var(--line); border-radius: 18px; box-shadow: var(--shadow); overflow: hidden;
        }
        .hero-inner {
            display: flex; justify-content: space-between; align-items: flex-start; gap: 20px; padding: 34px 28px 26px;
        }
        .hero-title { font-size: 20px; font-weight: 800; margin: 0 0 8px; letter-spacing: 0.04em; text-transform: uppercase; }
        .hero-sub { color: var(--muted); font-size: 13px; margin: 0; max-width: 620px; line-height: 1.7; }
        .hero-toggle {
            display: inline-flex; align-items: center; gap: 10px; background: rgba(255,255,255,0.02); border: 1px solid var(--line);
            border-radius: 10px; padding: 8px 12px; color: var(--muted); font-size: 12px;
        }
        .toggle {
            width: 42px; height: 22px; border-radius: 999px; background: rgba(255,255,255,0.08);
            border: 1px solid rgba(255,255,255,0.15); position: relative; display: inline-block;
        }
        .toggle::after {
            content: ""; position: absolute; width: 14px; height: 14px; border-radius: 50%; background: white;
            top: 3px; left: 4px; transition: 0.2s ease; box-shadow: 0 2px 10px rgba(0,0,0,0.25);
        }
        .toggle.on { background: linear-gradient(90deg, rgba(125,133,248,0.9), rgba(142,231,255,0.9)); border-color: rgba(125,133,248,0.8); }
        .toggle.on::after { left: 23px; }
        .info-bar {
            display: flex; align-items: center; justify-content: space-between; background: rgba(14, 21, 34, 0.84);
            border-top: 1px solid var(--line); border-bottom: 1px solid var(--line); color: var(--muted);
            padding: 14px 20px; font-size: 12px;
        }
        .info-left { display: flex; align-items: center; gap: 10px; }
        .info-left .icon {
            width: 28px; height: 28px; border-radius: 8px; background: rgba(127,161,255,0.14);
            display: flex; align-items: center; justify-content: center; color: var(--blue-2); font-size: 14px;
        }
        .grid { display: grid; grid-template-columns: 1.65fr 0.9fr; gap: 22px; margin-top: 22px; }
        .card { background: rgba(14, 22, 37, 0.9); border: 1px solid var(--line); border-radius: 18px; box-shadow: var(--shadow); }
        .card-header {
            display: flex; align-items: center; justify-content: space-between; padding: 18px 18px 12px; color: var(--muted);
            font-size: 12px; letter-spacing: 0.12em; text-transform: uppercase;
        }
        .card-header .left { display: flex; align-items: center; gap: 10px; }
        .badge { width: 8px; height: 8px; border-radius: 50%; background: var(--orange); box-shadow: 0 0 12px rgba(255,180,93,0.8); }
        .mod-panel { padding: 0 18px 18px; }
        .module-list { display: flex; flex-direction: column; gap: 12px; }
        .module-row {
            display: flex; align-items: center; justify-content: space-between; gap: 16px; min-height: 54px;
            padding: 8px 10px; background: rgba(255,255,255,0.015); border: 1px solid rgba(255,255,255,0.02); border-radius: 12px;
        }
        .module-name { display: flex; align-items: center; gap: 12px; color: var(--text); font-weight: 600; }
        .module-icon {
            width: 30px; height: 30px; border-radius: 8px; display: flex; align-items: center; justify-content: center;
            background: rgba(127,161,255,0.08); color: var(--blue-2); font-size: 14px; border: 1px solid rgba(127,161,255,0.18);
        }
        .module-meta { color: var(--muted-2); font-size: 11px; line-height: 1.5; }
        .switch {
            position: relative; width: 44px; height: 24px; border-radius: 999px; border: 1px solid rgba(255,255,255,0.15);
            background: rgba(255,255,255,0.06); transition: 0.2s ease; cursor: pointer;
        }
        .switch::after {
            content: ""; position: absolute; width: 16px; height: 16px; left: 4px; top: 3px; border-radius: 50%; background: #f4f7ff;
            box-shadow: 0 2px 8px rgba(0,0,0,0.26); transition: 0.2s ease;
        }
        .switch.on { background: linear-gradient(90deg, rgba(125,133,248,0.85), rgba(142,231,255,0.85)); border-color: rgba(125,133,248,0.7); }
        .switch.on::after { left: 23px; }
        .side-stack { display: flex; flex-direction: column; gap: 22px; }
        .mini-panel { padding: 18px 18px 16px; }
        .mini-panel .title { margin: 0 0 16px; color: var(--muted); font-size: 12px; letter-spacing: 0.12em; text-transform: uppercase; }
        .server-box { display: flex; flex-direction: column; gap: 12px; }
        .server-box .stat {
            display: flex; align-items: center; justify-content: space-between; border-radius: 12px; padding: 12px 10px;
            background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.03); color: var(--muted); font-size: 12px;
        }
        .server-box .stat strong { color: var(--text); font-size: 15px; font-weight: 700; }
        .server-box .state { color: var(--green); font-weight: 700; }
        .config-form { display: grid; gap: 14px; }
        .field { display: grid; gap: 7px; }
        .field label { color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: 0.12em; }
        .field input, .field select, .field textarea {
            width: 100%; border: 1px solid var(--line); background: rgba(255,255,255,0.02); color: var(--text);
            border-radius: 10px; padding: 12px 12px; outline: none; font: inherit;
        }
        .field textarea { min-height: 72px; resize: vertical; }
        .primary {
            width: 100%; border: none; border-radius: 10px; background: linear-gradient(90deg, var(--orange), #ff8d52);
            color: #1c1209; font-weight: 800; padding: 12px 14px; cursor: pointer; box-shadow: 0 12px 28px rgba(255, 154, 85, 0.33);
        }
        .bottom-row { display: grid; grid-template-columns: 1.2fr 1fr; gap: 22px; margin-top: 22px; }
        .action-box { padding: 18px; display: flex; flex-direction: column; gap: 16px; }
        .action-box .row {
            display: flex; align-items: center; justify-content: space-between; gap: 10px; border: 1px solid var(--line);
            border-radius: 12px; background: rgba(255,255,255,0.02); padding: 12px 14px; color: var(--muted); font-size: 13px;
        }
        .pill-btn {
            border: none; background: linear-gradient(90deg, rgba(127,161,255,0.12), rgba(125,133,248,0.18));
            border: 1px solid rgba(127,161,255,0.2); color: var(--text); border-radius: 10px; padding: 8px 12px; font-weight: 700; cursor: pointer;
        }
        .footer-bar {
            margin-top: auto; border-top: 1px solid var(--line); display: flex; align-items: center; justify-content: space-between;
            padding: 12px 18px 14px; color: var(--muted-2); font-size: 12px; background: rgba(7, 11, 23, 0.24);
        }
        @media (max-width: 980px) {
            .grid, .bottom-row { grid-template-columns: 1fr; }
            .shell { flex-direction: column; }
            .sidebar {
                width: 100%; height: auto; flex-direction: row; padding: 12px 14px; justify-content: space-between;
            }
            .nav-spacer { display: none; }
            .page-banner, .hero-inner, .topbar { flex-wrap: wrap; }
        }
    </style>
</head>
<body>
<div class="shell">
    <aside class="sidebar">
        <div class="brand">X</div>
        <div class="nav-icon active">◈</div>
        <div class="nav-icon">⊞</div>
        <div class="nav-icon">✦</div>
        <div class="nav-icon">☆</div>
        <div class="nav-spacer"></div>
        <div class="nav-icon">⚙</div>
        <div class="nav-icon">⎋</div>
    </aside>

    <main class="main">
        <header class="topbar">
            <div class="topbar-left">
                <div class="chip"><span class="dot"></span> Online</div>
                <div class="topbar-title">discord-bot-site--aqsintehsil2025.replit.app/panel</div>
            </div>
            <div class="topbar-right">
                <div class="chip">👥 {{ guild_count }} Sunucu</div>
                <div class="chip">👤 {{ member_count }} Üye</div>
                <div class="chip">⚡ {{ latency }}ms</div>
                <div class="notif">🔔</div>
            </div>
        </header>

        <div class="content">
            <div class="page-banner">
                <div class="breadcrumb"><span>Yönetim</span> / <span>Panel</span> / <span>Kontrol Merkezi</span></div>
                <div class="status-pill"><span class="dot"></span>{{ status.upper() }}</div>
            </div>

            <section class="hero">
                <div class="hero-inner">
                    <div>
                        <h1 class="hero-title">BOTUNU TANI.</h1>
                        <p class="hero-sub">Tercihini düzenle. Bu ayarlar her biri Discord topluluğun için görünür ve kolayca değiştirilir.</p>
                    </div>
                    <div class="hero-toggle">
                        <span>Önizleme modu</span>
                        <span class="toggle on" aria-label="Önizleme modu açık"></span>
                    </div>
                </div>

                <div class="info-bar">
                    <div class="info-left">
                        <div class="icon">i</div>
                        <span>Yalnızca bu ayarları değiştirmek için izin verildi, görev dağılımını etkinleştir.</span>
                    </div>
                    <button class="pill-btn" type="button">Yenile</button>
                </div>
            </section>

            <div class="grid">
                <section class="card">
                    <div class="card-header">
                        <div class="left"><span class="badge"></span> Modüller</div>
                        <span>Aktif</span>
                    </div>
                    <div class="mod-panel">
                        <div class="module-list">
                            <div class="module-row">
                                <div class="module-name">
                                    <div class="module-icon">AI</div>
                                    <div>
                                        <div>Yapay zeka sohbet</div>
                                        <div class="module-meta">Gemini ve web tabanlı cevap üretimi</div>
                                    </div>
                                </div>
                                <div class="switch on" data-module="ai"></div>
                            </div>

                            <div class="module-row">
                                <div class="module-name">
                                    <div class="module-icon">💰</div>
                                    <div>
                                        <div>Ekonomi modu</div>
                                        <div class="module-meta">Bakiye, günlük, market ve bahis</div>
                                    </div>
                                </div>
                                <div class="switch on" data-module="economy"></div>
                            </div>

                            <div class="module-row">
                                <div class="module-name">
                                    <div class="module-icon">🛡</div>
                                    <div>
                                        <div>Moderasyon modu</div>
                                        <div class="module-meta">Ban, mute, kick, küfür ve otomatik filtre</div>
                                    </div>
                                </div>
                                <div class="switch on" data-module="moderation"></div>
                            </div>

                            <div class="module-row">
                                <div class="module-name">
                                    <div class="module-icon">⚙</div>
                                    <div>
                                        <div>Yardımcı araçlar</div>
                                        <div class="module-meta">Rol, anket, hatırlatıcı ve yardım</div>
                                    </div>
                                </div>
                                <div class="switch on" data-module="utility"></div>
                            </div>
                        </div>
                    </div>
                </section>

                <aside class="side-stack">
                    <section class="card mini-panel">
                        <h2 class="title">Sunucu Başlığı</h2>
                        <div class="server-box">
                            <div class="stat"><span>Toplam sunucu</span><strong>{{ guild_count }}</strong></div>
                            <div class="stat"><span>Üye sayısı</span><strong>{{ member_count }}</strong></div>
                            <div class="stat"><span>Ping</span><strong>{{ latency }}ms</strong></div>
                            <div class="stat"><span>Durum</span><span class="state">{{ status }}</span></div>
                        </div>
                    </section>

                    <section class="card mini-panel">
                        <h2 class="title">Ayarlar</h2>
                        <form id="panel-form" class="config-form">
                            <div class="field">
                                <label>Komut ön eki</label>
                                <input id="command-name" value="{{ dashboard.command }}" />
                            </div>
                            <div class="field">
                                <label>Dil</label>
                                <select id="language">
                                    <option selected>Türkçe</option>
                                    <option>English</option>
                                    <option>Deutsch</option>
                                </select>
                            </div>
                            <div class="field">
                                <label>Hoş geldin mesajı</label>
                                <textarea id="welcome-message">{{ dashboard.welcome_message }}</textarea>
                            </div>
                            <button type="submit" class="primary">Ayarları Kaydet</button>
                        </form>
                    </section>
                </aside>
            </div>

            <div class="bottom-row">
                <section class="card">
                    <div class="card-header">
                        <div class="left"><span class="badge"></span> Moderasyon</div>
                        <span>Hızlı işlem</span>
                    </div>
                    <div class="action-box">
                        <div class="row"><span>Sunucuya katılanları otomatik karşıla</span><button class="pill-btn" type="button">Etkin</button></div>
                        <div class="row"><span>Spam / küfür filtresi</span><button class="pill-btn" type="button">Açık</button></div>
                        <div class="row"><span>Otomatik ban eşiği</span><button class="pill-btn" type="button">25</button></div>
                    </div>
                </section>

                <section class="card">
                    <div class="card-header">
                        <div class="left"><span class="badge"></span> Sinyal</div>
                        <span>Canlı</span>
                    </div>
                    <div class="action-box">
                        <div class="row"><span>Bot durum</span><strong style="color: var(--green);">Aktif</strong></div>
                        <div class="row"><span>Web servis</span><strong style="color: var(--blue-2);">Render / PORT</strong></div>
                        <div class="row"><span>Son güncelleme</span><strong>Bugün</strong></div>
                    </div>
                </section>
            </div>
        </div>

        <footer class="footer-bar">
            <div>© 2026 Xyrin Flow AI</div>
            <div>Discord Bot Control Panel</div>
        </footer>
    </main>
</div>

<script>
    const form = document.getElementById('panel-form');
    const switches = document.querySelectorAll('.switch');
    for (const el of switches) {
        el.addEventListener('click', () => el.classList.toggle('on'));
    }

    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        const payload = {
            command: document.getElementById('command-name').value,
            language: document.getElementById('language').value,
            welcome_message: document.getElementById('welcome-message').value,
            modules: Array.from(document.querySelectorAll('.switch')).reduce((acc, el) => {
                acc[el.dataset.module || 'general'] = el.classList.contains('on');
                return acc;
            }, {})
        };

        try {
            const res = await fetch('/api/moderation', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (data.success) {
                alert('Ayarlar kaydedildi.');
            } else {
                alert('Hata oluştu.');
            }
        } catch (e) {
            console.error(e);
            alert('Sunucuya bağlanırken hata oluştu.');
        }
    });
</script>
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
