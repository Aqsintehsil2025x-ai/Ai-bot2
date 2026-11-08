"""Authenticated server-settings panel routes for the Flask website.

A panel access code is created by the existing Discord !panel command, which is
restricted to members with Manage Server. It is single-use, short-lived, and
bound to the requesting user and guild.
"""
from flask import jsonify, make_response, render_template_string, request
import secrets
import time


PANEL_HTML = r"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Xyrin Flower — Sunucu paneli</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
:root{color-scheme:dark;--bg:#0b1222;--card:#151f35;--card2:#1d2943;--line:#344463;--text:#eef2ff;--muted:#a6b2cb;--blue:#8da2ff;--pink:#d98db6;--green:#73dbb3}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at 50% -20%,#26365c 0,transparent 55%),var(--bg);color:var(--text);font:14px/1.5 Inter,Arial,sans-serif;min-height:100vh}
header{height:64px;border-bottom:1px solid #ffffff12;display:flex;align-items:center;justify-content:space-between;padding:0 28px;background:#0b1222cc;position:sticky;top:0;backdrop-filter:blur(14px)}
a{color:inherit;text-decoration:none}.logo{font-weight:800;letter-spacing:.08em}.logo em{color:var(--blue);font-style:normal}.nav{display:flex;gap:20px;color:var(--muted);font-size:12px}.wrap{width:min(1080px,calc(100% - 32px));margin:46px auto 60px}.head{display:flex;justify-content:space-between;align-items:end;gap:20px;margin-bottom:26px}.eyebrow{font-size:10px;letter-spacing:.18em;color:#aab8ff;text-transform:uppercase}.head h1{font-size:clamp(34px,6vw,58px);letter-spacing:-.06em;line-height:1;margin:8px 0}.head p{color:var(--muted);margin:0}.status{border:1px solid var(--line);border-radius:11px;background:var(--card);padding:11px 14px;color:var(--muted);font-size:11px;white-space:nowrap}.status b{color:var(--green)}.notice{border:1px solid #617bb566;background:#1a2845;border-radius:10px;padding:14px 18px;display:flex;gap:12px;align-items:center;margin-bottom:18px;color:var(--muted);font-size:12px}.notice strong{color:var(--text)}.grid{display:grid;grid-template-columns:minmax(0,1.7fr) minmax(260px,.8fr);gap:18px}.card{background:linear-gradient(145deg,#17223a,#121b2f);border:1px solid var(--line);border-radius:12px;padding:22px;box-shadow:0 18px 50px #0003}.card h2{font-size:19px;letter-spacing:-.04em;margin:7px 0}.card p.sub{color:var(--muted);font-size:12px;margin:0 0 18px}.rows{border-top:1px solid #ffffff18}.row{display:flex;align-items:center;justify-content:space-between;gap:14px;border-bottom:1px solid #ffffff18;padding:15px 2px}.row-label{display:flex;align-items:center;gap:12px}.icon{width:34px;height:34px;display:grid;place-items:center;border:1px solid #596b94;border-radius:50%;background:#293755;color:#c7d2ff}.row small{display:block;color:var(--muted);font-size:10px;margin-top:3px}.switch{appearance:none;width:38px;height:21px;border-radius:20px;background:#58627a;position:relative;cursor:pointer;flex:none;transition:.18s}.switch:checked{background:#828cf4}.switch:after{content:"";position:absolute;left:3px;top:3px;width:15px;height:15px;border-radius:50%;background:white;transition:.18s}.switch:checked:after{left:20px}.field{display:grid;grid-template-columns:1fr 1.15fr;align-items:center;gap:14px;margin:14px 0}.field label{font-size:11px;font-weight:600}.field label small{display:block;color:var(--muted);font-weight:400;margin-top:4px}input[type=text],select,textarea{width:100%;border:1px solid #465777;border-radius:6px;padding:11px;background:#0e1729;color:var(--text);font:12px Inter,Arial}textarea{min-height:78px;resize:vertical}.btn{border:0;border-radius:7px;background:#e4e9f8;color:#18213a;padding:11px 16px;font-weight:700;cursor:pointer}.btn:hover{filter:brightness(1.08)}.btn.secondary{border:1px solid #465777;background:#202d47;color:var(--text)}.actions{display:flex;gap:9px;flex-wrap:wrap;margin-top:16px}.server-card{position:relative;overflow:hidden}.server-card:after{content:"";position:absolute;width:170px;height:170px;border:1px solid #aebeff22;border-radius:50%;right:-78px;top:92px;pointer-events:none}.server-title{font-size:25px;line-height:1.15;letter-spacing:-.05em;margin:16px 0 9px}.stats{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:20px}.stat{background:#0d1628;border:1px solid #ffffff12;border-radius:8px;padding:12px}.stat strong{display:block;font-size:20px}.stat span{color:var(--muted);font-size:10px}.hidden{display:none!important}.msg{min-height:20px;color:#c9d4f2;font-size:12px;margin-top:10px}.login{max-width:480px;margin:10vh auto}.login input{margin:12px 0}.muted{color:var(--muted)}footer{text-align:center;color:#71809f;font-size:10px;letter-spacing:.13em;margin-top:28px}
@media(max-width:760px){header{padding:0 16px}.nav{gap:10px}.wrap{margin-top:30px}.head{align-items:flex-start;flex-direction:column}.grid{grid-template-columns:1fr}.field{grid-template-columns:1fr;gap:7px}.login{margin:7vh auto}.card{padding:17px}}
</style>
</head>
<body>
<header><a class="logo" href="/">XYRIN <em>FLOWER</em></a><nav class="nav"><a href="/">Ana sayfa</a><a href="https://discord.gg/Dkj8VFnga" target="_blank" rel="noopener">Discord sunucusu ↗</a></nav></header>
<main class="wrap">
<section id="login" class="card login">
  <div class="eyebrow">GÜVENLİ SUNUCU PANELİ</div><h1>Botunu tanı.</h1>
  <p class="sub">Discord sunucunda <b>!panel</b> komutunu kullan. Sana özel, 10 dakika geçerli kodu buraya gir.</p>
  <form id="login-form"><label for="code">Bağlantı kodu</label><input id="code" type="text" maxlength="6" autocomplete="one-time-code" placeholder="6 haneli kod" required><button class="btn" type="submit">Panele bağlan</button></form>
  <div id="login-msg" class="msg" role="status"></div>
</section>
<section id="dashboard" class="hidden">
  <div class="head"><div><div class="eyebrow">XYRIN FLOWER · YÖNETİM</div><h1>Botunu tanı.</h1><p>Sunucu tercihlerini ve moderasyon modüllerini buradan yönet.</p></div><div class="status">● <b id="connection">Bağlı</b><br><span id="guild-name">Sunucu</span></div></div>
  <div class="notice"><span class="icon">▣</span><span><strong>Yalnızca yetkili paneli.</strong><br>Bu bağlantı Discord'daki !panel komutuyla oluşturulan tek kullanımlık kodla açılır.</span></div>
  <div class="grid">
    <div>
      <section class="card"><div class="eyebrow">01 — MODÜLLER</div><h2>Hangi tarafı açık?</h2><p class="sub">Değişiklikleri kaydedince ayarlar sunucunun botuna uygulanır.</p>
        <div class="rows">
          <label class="row"><span class="row-label"><span class="icon">✧</span><span>Yapay zekâ sohbeti<small>Botla sohbet ve yanıt özellikleri</small></span></span><input id="ai" class="switch" type="checkbox"></label>
          <label class="row"><span class="row-label"><span class="icon">♜</span><span>Akıllı moderasyon<small>Spam, link ve uygunsuz içerik denetimi</small></span></span><input id="moderation" class="switch" type="checkbox"></label>
          <label class="row"><span class="row-label"><span class="icon">✦</span><span>Ekonomi ve eğlence<small>Ekonomi, seviye ve mini oyunlar</small></span></span><input id="entertainment" class="switch" type="checkbox"></label>
        </div>
      </section>
      <section class="card" style="margin-top:18px"><div class="eyebrow">02 — TEMEL AYARLAR</div><h2>İnce ayar senin.</h2><p class="sub">Kaydedilen ayarlar bu sunucu için kalıcı tutulur.</p>
        <form id="settings-form">
          <div class="field"><label for="prefix">Komut ön eki<small>Komutların başında kullanılır</small></label><input id="prefix" type="text" maxlength="5"></div>
          <div class="field"><label for="language">Yanıt dili<small>Botun konuşacağı dil</small></label><select id="language"><option>Türkçe</option><option>English</option><option>Deutsch</option></select></div>
          <div class="field"><label for="welcome">Karşılama mesajı<small>{kullanıcı} ve {sunucu} kullanılabilir</small></label><textarea id="welcome" maxlength="300"></textarea></div>
          <div class="actions"><button class="btn" type="submit">Ayarları kaydet</button><button id="logout" class="btn secondary" type="button">Oturumu kapat</button></div>
          <div id="settings-msg" class="msg" role="status"></div>
        </form>
      </section>
    </div>
    <aside class="card server-card"><div class="eyebrow">03 — SUNUCU BAĞLANTISI</div><h2 class="server-title" id="server-heading">Sunucuya bağlanıyor…</h2><p class="sub">Yönetim tercihleri seçili Discord sunucusuna kaydedilir.</p>
      <div class="stats"><div class="stat"><strong id="guild-count">—</strong><span>BOTUN BULUNDUĞU SUNUCU</span></div><div class="stat"><strong id="latency">—</strong><span>BOT PING</span></div></div>
      <div class="actions"><a class="btn secondary" href="https://discord.gg/Dkj8VFnga" target="_blank" rel="noopener">Discord sunucusu</a></div>
      <p class="msg">🔒 Oturum kodu tek kullanımlıktır; ayarlar botun JSON deposuna kaydedilir.</p>
    </aside>
  </div>
  <footer>XYRIN FLOWER · SUNUCU AYARLARI</footer>
</section>
</main>
<script>
const login=document.querySelector('#login'), dashboard=document.querySelector('#dashboard');
const loginMsg=document.querySelector('#login-msg'), settingsMsg=document.querySelector('#settings-msg');
function showError(el,text){el.textContent=text;}
function fill(data){
  login.classList.add('hidden'); dashboard.classList.remove('hidden');
  document.querySelector('#guild-name').textContent=data.guild.name;
  document.querySelector('#server-heading').textContent=data.guild.name;
  document.querySelector('#guild-count').textContent=data.stats.guilds;
  document.querySelector('#latency').textContent=data.stats.latency+' ms';
  for(const key of ['ai','moderation','entertainment']) document.querySelector('#'+key).checked=!!data.settings[key];
  for(const key of ['prefix','language','welcome']) document.querySelector('#'+key).value=data.settings[key]||'';
}
async function loadSession(){
  try { const r=await fetch('/api/panel/settings'); if(r.ok) fill(await r.json()); }
  catch(e){ /* unauthenticated or network offline */ }
}
document.querySelector('#login-form').addEventListener('submit',async e=>{
  e.preventDefault(); showError(loginMsg,'Bağlanıyor…');
  try {
    const r=await fetch('/api/panel/redeem',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code:document.querySelector('#code').value})});
    const data=await r.json(); if(!r.ok){showError(loginMsg,data.error||'Kod kabul edilmedi.');return;} fill(data); showError(settingsMsg,'Bağlandı.');
  } catch(err){showError(loginMsg,'Sunucuya ulaşılamadı. Lütfen tekrar dene.');}
});
document.querySelector('#settings-form').addEventListener('submit',async e=>{
  e.preventDefault(); showError(settingsMsg,'Kaydediliyor…');
  const body={ai:document.querySelector('#ai').checked,moderation:document.querySelector('#moderation').checked,entertainment:document.querySelector('#entertainment').checked,prefix:document.querySelector('#prefix').value,language:document.querySelector('#language').value,welcome:document.querySelector('#welcome').value};
  try {const r=await fetch('/api/panel/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const data=await r.json();if(!r.ok){showError(settingsMsg,data.error||'Kaydedilemedi.');return;}showError(settingsMsg,'Ayarlar sunucuya kaydedildi.');}
  catch(err){showError(settingsMsg,'Sunucuya ulaşılamadı.');}
});
document.querySelector('#logout').addEventListener('click',async()=>{await fetch('/api/panel/logout',{method:'POST'});location.reload();});
loadSession();
</script>
</body>
</html>"""


def register_panel_routes(bot, panel_settings, is_sovereign_member):
    """Register panel endpoints against the already-running Flask app and bot."""
    if app.config.get("XYRIN_PANEL_ROUTES_REGISTERED"):
        return
    app.config["XYRIN_PANEL_ROUTES_REGISTERED"] = True

    def session_for_request():
        token = request.cookies.get("xyrin_panel", "")
        session = bot.panel_sessions.get(token)
        if not session or session.get("exp", 0) < time.monotonic():
            bot.panel_sessions.pop(token, None)
            return None
        guild = bot.get_guild(session.get("guild_id", 0))
        member = guild.get_member(session.get("user_id", 0)) if guild else None
        if not guild or not member:
            bot.panel_sessions.pop(token, None)
            return None
        perms = member.guild_permissions
        if not (is_sovereign_member(member) or perms.administrator or perms.manage_guild):
            bot.panel_sessions.pop(token, None)
            return None
        return session, guild

    def panel_payload(guild):
        stats = {
            "guilds": len(bot.guilds),
            "latency": round(bot.latency * 1000) if bot.is_ready() else 0,
        }
        return {
            "guild": {"id": str(guild.id), "name": guild.name},
            "stats": stats,
            "settings": panel_settings(guild.id),
        }

    def same_origin_required():
        origin = request.headers.get("Origin")
        if not origin:
            return True
        expected = request.host_url.rstrip("/")
        forwarded_proto = request.headers.get("X-Forwarded-Proto", "").split(",", 1)[0].strip()
        if forwarded_proto:
            expected = expected.replace(request.scheme + "://", forwarded_proto + "://", 1)
        return origin.rstrip("/") == expected

    @app.get("/panel")
    def panel_page():
        return render_template_string(PANEL_HTML)

    @app.post("/api/panel/redeem")
    def panel_redeem():
        if not same_origin_required():
            return jsonify({"error": "İstek kaynağı doğrulanamadı."}), 403
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return jsonify({"error": "Geçersiz istek."}), 400
        code = str(body.get("code", "")).strip().upper()
        found = bot.panel_codes.get(code)
        if not found or found[2] < time.monotonic():
            bot.panel_codes.pop(code, None)
            return jsonify({"error": "Kod geçersiz veya süresi dolmuş. Discord sunucusunda !panel komutunu yeniden kullan."}), 403
        user_id, guild_id, _expires = found
        guild = bot.get_guild(guild_id)
        member = guild.get_member(user_id) if guild else None
        if not guild or not member:
            bot.panel_codes.pop(code, None)
            return jsonify({"error": "Kullanıcı veya sunucu bulunamadı. !panel ile yeni kod al."}), 403
        perms = member.guild_permissions
        if not (is_sovereign_member(member) or perms.administrator or perms.manage_guild):
            bot.panel_codes.pop(code, None)
            return jsonify({"error": "Sunucu ayarlarını yönetme yetkin bulunmuyor."}), 403
        bot.panel_codes.pop(code, None)
        token = secrets.token_urlsafe(32)
        bot.panel_sessions[token] = {"user_id": user_id, "guild_id": guild_id, "exp": time.monotonic() + 12 * 3600}
        response = make_response(jsonify(panel_payload(guild)))
        secure = request.is_secure or request.headers.get("X-Forwarded-Proto", "").split(",", 1)[0].strip() == "https"
        response.set_cookie("xyrin_panel", token, max_age=12 * 3600, httponly=True, secure=secure, samesite="Lax", path="/")
        return response

    @app.get("/api/panel/settings")
    def panel_get():
        auth = session_for_request()
        if auth is None:
            return jsonify({"error": "Önce Discord'da !panel komutuyla yeni bağlantı kodu al."}), 401
        _session, guild = auth
        return jsonify(panel_payload(guild))

    @app.post("/api/panel/settings")
    def panel_save():
        if not same_origin_required():
            return jsonify({"error": "İstek kaynağı doğrulanamadı."}), 403
        auth = session_for_request()
        if auth is None:
            return jsonify({"error": "Oturum kapandı. Discord'da !panel komutuyla yeni kod al."}), 401
        _session, guild = auth
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return jsonify({"error": "Geçersiz istek."}), 400
        current = panel_settings(guild.id)
        prefix = str(body.get("prefix", current["prefix"])).strip()
        if not (1 <= len(prefix) <= 5 and not any(ch.isspace() for ch in prefix) and not prefix.startswith("/")):
            return jsonify({"error": "Komut ön eki 1–5 karakter olmalı; boşluk veya / içeremez."}), 400
        language = str(body.get("language", current["language"])).strip()[:40] or "Türkçe"
        welcome = str(body.get("welcome", current["welcome"])).strip()[:300] or "Aramıza hoş geldin, {kullanıcı}!"
        saved = {
            "ai": bool(body.get("ai", current["ai"])),
            "moderation": bool(body.get("moderation", current["moderation"])),
            "entertainment": bool(body.get("entertainment", current["entertainment"])),
            "prefix": prefix,
            "language": language,
            "welcome": welcome,
        }
        bot.settings.set(guild.id, "panel", saved)
        # JsonStore's normal persistence task flushes dirty stores; make a synchronous
        # flush attempt as well so a panel save survives an immediate restart.
        bot.settings.store.flush_sync()
        return jsonify({"success": True, **panel_payload(guild)})

    @app.post("/api/panel/logout")
    def panel_logout():
        token = request.cookies.get("xyrin_panel", "")
        bot.panel_sessions.pop(token, None)
        response = make_response(jsonify({"success": True}))
        response.delete_cookie("xyrin_panel", path="/")
        return response
