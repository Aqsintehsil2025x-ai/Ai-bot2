"""Wire Discord !panel + Flask /panel API onto the running bot/app."""
from __future__ import annotations

import os
import secrets
import time

from flask import jsonify, make_response, render_template_string, request


PANEL_HTML = """<!doctype html>
<html lang=\"tr\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
<title>Xyrin Panel</title>
<style>
body{margin:0;background:#0b1222;color:#eef2ff;font:14px/1.5 system-ui,sans-serif}
.wrap{max-width:520px;margin:8vh auto;padding:24px}
.card{background:#151f35;border:1px solid #344463;border-radius:12px;padding:22px}
h1{font-size:28px;margin:0 0 8px}p{color:#a6b2cb}
input{width:100%;box-sizing:border-box;padding:12px;border-radius:8px;border:1px solid #465777;background:#0e1729;color:#fff;margin:10px 0}
button{background:#e4e9f8;color:#18213a;border:0;border-radius:8px;padding:12px 16px;font-weight:700;cursor:pointer}
.row{display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px solid #ffffff18}
.msg{min-height:1.2em;color:#c9d4f2;margin-top:10px}.hidden{display:none!important}
label.field{display:block;margin-top:12px;font-size:12px;color:#a6b2cb}
</style></head><body>
<div class=\"wrap\">
<section id=\"login\" class=\"card\">
  <h1>Botunu tani.</h1>
  <p>Discord'da <b>!panel</b> yaz, gelen 6 haneli kodu buraya gir.</p>
  <form id=\"login-form\"><input id=\"code\" maxlength=\"6\" placeholder=\"6 haneli kod\" required>
  <button type=\"submit\">Panele baglan</button></form>
  <div id=\"login-msg\" class=\"msg\"></div>
</section>
<section id=\"dashboard\" class=\"card hidden\">
  <h1 id=\"guild-name\">Sunucu</h1>
  <p>Ayarlar canli bota kaydedilir.</p>
  <label class=\"row\"><span>Yapay zeka</span><input id=\"ai\" type=\"checkbox\"></label>
  <label class=\"row\"><span>Moderasyon</span><input id=\"moderation\" type=\"checkbox\"></label>
  <label class=\"row\"><span>Eglence</span><input id=\"entertainment\" type=\"checkbox\"></label>
  <label class=\"field\">Prefix <input id=\"prefix\" maxlength=\"5\"></label>
  <label class=\"field\">Dil <input id=\"language\" maxlength=\"40\"></label>
  <label class=\"field\">Karsilama <input id=\"welcome\" maxlength=\"300\"></label>
  <p style=\"margin-top:16px\"><button id=\"save\" type=\"button\">Kaydet</button>
  <button id=\"logout\" type=\"button\" style=\"margin-left:8px;background:#202d47;color:#fff\">Cikis</button></p>
  <div id=\"settings-msg\" class=\"msg\"></div>
</section>
</div>
<script>
const login=document.querySelector('#login'), dash=document.querySelector('#dashboard');
function fill(d){login.classList.add('hidden');dash.classList.remove('hidden');
 document.querySelector('#guild-name').textContent=d.guild.name;
 for(const k of ['ai','moderation','entertainment']) document.querySelector('#'+k).checked=!!d.settings[k];
 for(const k of ['prefix','language','welcome']) document.querySelector('#'+k).value=d.settings[k]||'';}
async function load(){try{const r=await fetch('/api/panel/settings');if(r.ok)fill(await r.json());}catch(e){}}
document.querySelector('#login-form').onsubmit=async e=>{e.preventDefault();
 const r=await fetch('/api/panel/redeem',{method:'POST',headers:{'Content-Type':'application/json'},
  body:JSON.stringify({code:document.querySelector('#code').value})});
 const d=await r.json(); if(!r.ok){document.querySelector('#login-msg').textContent=d.error||'Hata';return;} fill(d);};
document.querySelector('#save').onclick=async()=>{
 const body={ai:ai.checked,moderation:moderation.checked,entertainment:entertainment.checked,
  prefix:prefix.value,language:language.value,welcome:welcome.value};
 const r=await fetch('/api/panel/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
 const d=await r.json(); document.querySelector('#settings-msg').textContent=r.ok?'Kaydedildi.':(d.error||'Hata');};
document.querySelector('#logout').onclick=async()=>{await fetch('/api/panel/logout',{method:'POST'});location.reload();};
load();
</script></body></html>
"""


def wire_panel(app, bot):
    """Register /panel API routes and Discord !panel command once."""
    if getattr(bot, "_xyrin_panel_wired", False):
        return
    bot._xyrin_panel_wired = True

    import discord
    from discord.ext import commands
    from xyrin_bot import panel_settings, is_sovereign_member, perm_or_sovereign

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
        return {
            "guild": {"id": str(guild.id), "name": guild.name},
            "stats": {
                "guilds": len(bot.guilds),
                "latency": round(bot.latency * 1000) if bot.is_ready() else 0,
            },
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

    @app.get("/legacy-panel")
    def legacy_panel_page():
        return render_template_string(PANEL_HTML)

    @app.post("/api/panel/redeem")
    def panel_redeem():
        if not same_origin_required():
            return jsonify({"error": "Origin rejected."}), 403
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return jsonify({"error": "Bad request."}), 400
        code = str(body.get("code", "")).strip().upper()
        found = bot.panel_codes.get(code)
        if not found or found[2] < time.monotonic():
            bot.panel_codes.pop(code, None)
            return jsonify({"error": "Kod gecersiz. Discord'da !panel yaz."}), 403
        user_id, guild_id, _exp = found
        guild = bot.get_guild(guild_id)
        member = guild.get_member(user_id) if guild else None
        if not guild or not member:
            bot.panel_codes.pop(code, None)
            return jsonify({"error": "Guild/user not found."}), 403
        perms = member.guild_permissions
        if not (is_sovereign_member(member) or perms.administrator or perms.manage_guild):
            bot.panel_codes.pop(code, None)
            return jsonify({"error": "Yetkin yok."}), 403
        bot.panel_codes.pop(code, None)
        token = secrets.token_urlsafe(32)
        bot.panel_sessions[token] = {
            "user_id": user_id,
            "guild_id": guild_id,
            "exp": time.monotonic() + 12 * 3600,
        }
        response = make_response(jsonify(panel_payload(guild)))
        secure = request.is_secure or request.headers.get("X-Forwarded-Proto", "").split(",", 1)[0].strip() == "https"
        response.set_cookie(
            "xyrin_panel", token, max_age=12 * 3600, httponly=True, secure=secure, samesite="Lax", path="/"
        )
        return response

    @app.get("/api/panel/settings")
    def panel_get():
        auth = session_for_request()
        if auth is None:
            return jsonify({"error": "Once !panel ile kod al."}), 401
        _s, guild = auth
        return jsonify(panel_payload(guild))

    @app.post("/api/panel/settings")
    def panel_save():
        if not same_origin_required():
            return jsonify({"error": "Origin rejected."}), 403
        auth = session_for_request()
        if auth is None:
            return jsonify({"error": "Oturum kapandi."}), 401
        _s, guild = auth
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return jsonify({"error": "Bad request."}), 400
        current = panel_settings(guild.id)
        prefix = str(body.get("prefix", current["prefix"])).strip()
        if not (1 <= len(prefix) <= 5 and not any(ch.isspace() for ch in prefix) and not prefix.startswith("/")):
            return jsonify({"error": "Prefix 1-5 karakter."}), 400
        language = str(body.get("language", current["language"])).strip()[:40] or "Turkce"
        welcome = str(body.get("welcome", current["welcome"])).strip()[:300] or "Aramiza hos geldin, {kullanici}!"
        saved = {
            "ai": bool(body.get("ai", current["ai"])),
            "moderation": bool(body.get("moderation", current["moderation"])),
            "entertainment": bool(body.get("entertainment", current["entertainment"])),
            "prefix": prefix,
            "language": language,
            "welcome": welcome,
        }
        bot.settings.set(guild.id, "panel", saved)
        bot.settings.store.flush_sync()
        return jsonify({"success": True, **panel_payload(guild)})

    @app.post("/api/panel/logout")
    def panel_logout():
        token = request.cookies.get("xyrin_panel", "")
        bot.panel_sessions.pop(token, None)
        response = make_response(jsonify({"success": True}))
        response.delete_cookie("xyrin_panel", path="/")
        return response

    @bot.hybrid_command(name="panel", description="Bu sunucunun ayar panelini baglayan kodu gonderir.")
    @commands.guild_only()
    @perm_or_sovereign(manage_guild=True)
    async def panel_komutu(ctx):
        code = secrets.token_hex(3).upper()
        bot.panel_codes[code] = (ctx.author.id, ctx.guild.id, time.monotonic() + 600)
        now = time.monotonic()
        for k in [k for k, v in list(bot.panel_codes.items()) if v[2] < now]:
            bot.panel_codes.pop(k, None)
        base = os.getenv("PANEL_PUBLIC_URL", "").strip().rstrip("/")
        if not base:
            domain = (os.getenv("REPLIT_DOMAINS") or os.getenv("REPLIT_DEV_DOMAIN") or "").split(",")[0].strip()
            if domain:
                base = domain if domain.startswith(("https://", "http://")) else f"https://{domain}"
        if not base.startswith(("https://", "http://")):
            bot.panel_codes.pop(code, None)
            kwargs = {"ephemeral": True} if ctx.interaction else {}
            await ctx.reply("Panel adresi yapılandırılmamış. PANEL_PUBLIC_URL ortam değişkenini ayarla.", **kwargs)
            return
        text = (
            f"**Panel kodun:** `{code}`\n"
            f"**Adres:** {base}/panel\n"
            f"Kod 10 dakika gecerli. Sunucu: **{ctx.guild.name}**"
        )
        note = "Kodu ozel mesajina gonderdim."
        try:
            await ctx.author.send(text)
        except discord.HTTPException:
            note = text
        kwargs = {"ephemeral": True} if ctx.interaction else {}
        await ctx.reply(note, **kwargs)

    print("[panel_wire] panel + !panel wired", flush=True)
