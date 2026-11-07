# ==============================================================================
# XYRIN BOT — WEB SUNUCUSU (Flask)
# Botun sitesi: https://sunucu-adi.onrender.com
# ==============================================================================
from flask import Flask, render_template_string, jsonify
import os
import asyncio
import threading

app = Flask(__name__)

# --- Bot referansı (main.py'den atanacak) ---
_bot = None

def set_bot(bot):
    global _bot
    _bot = bot


# --- Ana sayfa ---
@app.route("/")
def index():
    guild_count = len(_bot.guilds) if _bot else 0
    member_count = sum(g.member_count or 0 for g in _bot.guilds) if _bot else 0
    latency = round(_bot.latency * 1000) if _bot and _bot.is_ready() else 0

    html = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Xyrin İmparatorluğu Botu</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Poppins', sans-serif; background: #0f0f12; color: #e0e0e0; overflow-x: hidden; }
        .container { max-width: 1000px; margin: 0 auto; padding: 0 20px; }

        /* Navbar */
        nav { display: flex; justify-content: space-between; align-items: center; padding: 20px 0; }
        .logo { font-size: 24px; font-weight: 700; color: #7289da; text-decoration: none; }
        .logo span { color: #ffffff; }
        .nav-links { display: flex; gap: 30px; }
        .nav-links a { color: #b9bbbe; text-decoration: none; font-weight: 400; transition: 0.3s; }
        .nav-links a:hover { color: #ffffff; }

        /* Hero */
        .hero { text-align: center; padding: 100px 0 60px; }
        .hero h1 { font-size: 48px; margin-bottom: 20px; background: linear-gradient(135deg, #7289da, #99aab5); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .hero p { font-size: 20px; color: #b9bbbe; margin-bottom: 40px; }
        .hero-buttons { display: flex; gap: 20px; justify-content: center; }
        .btn { padding: 14px 32px; border-radius: 500px; text-decoration: none; font-weight: 600; font-size: 16px; transition: 0.3s; display: inline-block; }
        .btn-primary { background: #7289da; color: #fff; }
        .btn-primary:hover { background: #677bc4; transform: translateY(-2px); }
        .btn-outline { border: 2px solid #7289da; color: #7289da; }
        .btn-outline:hover { background: #7289da; color: #fff; transform: translateY(-2px); }

        /* Stats */
        .stats { display: flex; justify-content: center; gap: 40px; margin: 60px 0; padding: 0 20px; }
        .stat-card { background: #1e1e26; padding: 30px; border-radius: 16px; text-align: center; min-width: 150px; border: 1px solid #2e2e38; }
        .stat-card h3 { font-size: 32px; color: #ffffff; margin-bottom: 8px; }
        .stat-card p { color: #b9bbbe; font-size: 14px; }

        /* Commands */
        .commands { background: #1e1e26; border-radius: 20px; padding: 60px 0; border: 1px solid #2e2e38; }
        .section-title { text-align: center; font-size: 32px; margin-bottom: 40px; color: #ffffff; }
        .cmd-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 25px; padding: 0 40px 40px; }
        .cmd-card { background: #2e2e38; padding: 25px; border-radius: 16px; border: 1px solid #3e3e48; transition: 0.3s; }
        .cmd-card:hover { border-color: #7289da; transform: translateY(-5px); }
        .cmd-card h4 { color: #7289da; margin-bottom: 12px; font-size: 20px; }
        .cmd-card p { color: #b9bbbe; font-size: 14px; line-height: 1.6; }

        /* Footer */
        footer { text-align: center; padding: 40px 0; color: #8e9297; font-size: 14px; border-top: 1px solid #2e2e38; margin-top: 60px; }

        /* Responsive */
        @media (max-width: 768px) {
            .hero h1 { font-size: 32px; }
            .hero-buttons { flex-direction: column; align-items: center; }
            .stats { flex-direction: column; align-items: center; }
            .nav-links { display: none; }
        }
    </style>
</head>
<body>

<nav>
    <a href="/" class="logo">Xyrin<span>Bot</span></a>
    <div class="nav-links">
        <a href="#komutlar">Komutlar</a>
        <a href="#istatistikler">İstatistikler</a>
        <a href="#davet">Davet Et</a>
    </div>
</nav>

<section class="hero">
    <h1>Xyrin İmparatorluğu'na Hoş Geldiniz</h1>
    <p>Discord sunucunuz için yapay zeka destekli, gelişmiş moderasyon, ekonomi ve eğlence botu.</p>
    <div class="hero-buttons">
        <a href="https://discord.com/api/oauth2/authorize?client_id=BOT_ID_BURAYA&permissions=8&scope=bot%20applications.commands" class="btn btn-primary" target="_blank">Sunucuya Ekle</a>
        <a href="#komutlar" class="btn btn-outline">Komutları Gör</a>
    </div>
</section>

<section id="istatistikler" class="stats">
    <div class="stat-card">
        <h3 id="stat-guilds">{{ guild_count }}</h3>
        <p>Sunucu</p>
    </div>
    <div class="stat-card">
        <h3 id="stat-members">{{ member_count }}</h3>
        <p>Üye</p>
    </div>
    <div class="stat-card">
        <h3 id="stat-latency">{{ latency }}ms</h3>
        <p>Gecikme</p>
    </div>
</section>

<section id="komutlar" class="commands">
    <h2 class="section-title">Öne Çıkan Komutlar</h2>
    <div class="cmd-grid">
        <div class="cmd-card">
            <h4>🤖 Yapay Zeka</h4>
            <p>@etiket, /sor, /ara, /ozetle — Gemini ve NVIDIA destekli sohbet, görsel analiz ve internet araması.</p>
        </div>
        <div class="cmd-card">
            <h4>🪙 Ekonomi</h4>
            <p>/bakiye, /gunluk, /calis, /suc, /soy, /market, /bahis — Seviye sistemi ve market dahil.</p>
        </div>
        <div class="cmd-card">
            <h4>🛡️ Moderasyon</h4>
            <p>/kick, /ban, /mute, /temizle, /kilitle, /kufur — Otomatik spam ve küfür filtresi.</p>
        </div>
        <div class="cmd-card">
            <h4>⏰ Araçlar</h4>
            <p>/hatirlat, /etkinlik, /cekilis, /anket, /oneri, /afk — Sunucu etkinliği için hazır.</p>
        </div>
    </div>
</section>

<section id="davet" style="text-align:center; padding: 80px 0;">
    <h2 class="section-title">Botu Sunucuna Ekle</h2>
    <p style="color:#b9bbbe; margin-bottom: 30px;">Xyrin Bot'u şimdi own Discord sunucuna ekleyin.</p>
    <a href="https://discord.com/api/oauth2/authorize?client_id=BOT_ID_BURAYA&permissions=8&scope=bot%20applications.commands" class="btn btn-primary" target="_blank">➕ Sunucuya Ekle</a>
</section>

<footer>
    &copy; 2026 Xyrin İmparatorluğu Botu. Tüm hakları saklıdır.<br>
    Discord: <a href="#" style="color:#7289da; text-decoration:none;">Discord Sunucu</a>
</footer>

<script>
    // Canlı istatistik güncellemesi
    async function updateStats() {
        try {
            const res = await fetch('/api/stats');
            const data = await res.json();
            document.getElementById('stat-guilds').innerText = data.guilds || 0;
            document.getElementById('stat-members').innerText = data.members || 0;
            document.getElementById('stat-latency').innerText = (data.latency || 0) + 'ms';
        } catch (e) {
            console.log('Stats API yok');
        }
    }
    setInterval(updateStats, 10000);
    updateStats();
</script>

</body>
</html>
    """
    return render_template_string(html, guild_count=guild_count, member_count=member_count, latency=latency)


# --- API: Bot istatistikleri ---
@app.route("/api/stats")
def api_stats():
    if _bot is None:
        return jsonify({"guilds": 0, "members": 0, "latency": 0})
    return jsonify({
        "guilds": len(_bot.guilds),
        "members": sum(g.member_count or 0 for g in _bot.guilds),
        "latency": round(_bot.latency * 1000) if _bot.is_ready() else 0,
        "ready": _bot.is_ready()
    })


def run_web_server(port: int):
    """Flask sunucusu ayrı bir thread'de çalışır."""
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)