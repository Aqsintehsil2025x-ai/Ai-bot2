"""Genel yardımcı komutlari cogu: afk, kullanici, sunucu, avatar, anket, oneri, hatirlat, etkinlik, hatirlatmalar, hatirlatsil, gununsorusu, evrim, yedekle, sync."""
from __future__ import annotations

import logging
import random

import discord
from discord import app_commands
from discord.ext import commands

from xyrin_bot import (
    AIError,
    BET_MAX,
    CRIME_SUCCESS_CHANCE,
    DAILY_QUESTION_TITLE,
    EVOLUTION_BATCH,
    EVOLUTION_INTERVAL_MINUTES,
    FALLBACK_QUESTIONS,
    LOCAL_TZ,
    MAX_REMINDERS_PER_USER,
    MIN_DURATION,
    bot,
    build_daily_question_embed,
    describe_ping,
    draft_evolution,
    fold_text,
    format_balance,
    is_sovereign_member,
    load_evolution_state,
    owner_or_sovereign,
    panel_settings,
    parse_duration,
    parse_hhmm,
    parse_iso,
    parse_ping_option,
    perm_or_sovereign,
    post_daily_question,
    save_evolution_state,
    sanitize_inline,
    sovereign_address,
    truncate,
    utcnow,
)

logger = logging.getLogger("XyrinImperialCore")


class UtilityCog(commands.Cog, name="Yardımcı"):
    def __init__(self, bot_instance: commands.Bot):
        self.bot = bot_instance

    @commands.hybrid_command(name="afk", description="AFK moduna geçer. Birisi seni etiketleyince sebep gösterilir.")
    @app_commands.describe(sebep="AFK sebebin (isteğe bağlı)")
    async def afk_komutu(self, ctx: commands.Context, *, sebep: str = "Belirtilmedi"):
        self.bot.afk.set(ctx.author.id, sebep)
        await ctx.send(f"💤 {ctx.author.mention} artık AFK: **{truncate(sebep, 100)}**")

    @commands.hybrid_command(name="kullanici", aliases=["userinfo", "user", "üye"], description="Kullanıcı bilgilerini gösterir.")
    @app_commands.describe(member="Bilgisine bakılacak üye")
    @commands.guild_only()
    async def kullanici_komutu(self, ctx: commands.Context, member: discord.Member = None):
        member = member or ctx.author
        roles = [r.mention for r in reversed(member.roles) if not r.is_default()][:15]
        embed = discord.Embed(title=f"👤 {member.display_name}", color=member.color or discord.Color.blurple())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Kullanıcı", value=f"{member.mention}\n`{member}`", inline=True)
        embed.add_field(name="ID", value=f"`{member.id}`", inline=True)
        embed.add_field(name="Bot mu?", value="Evet" if member.bot else "Hayır", inline=True)
        if member.joined_at:
            embed.add_field(name="Katılma", value=f"<t:{int(member.joined_at.timestamp())}:R>", inline=True)
        if member.created_at:
            embed.add_field(name="Hesap oluşturma", value=f"<t:{int(member.created_at.timestamp())}:R>", inline=True)
        embed.add_field(name="Hükümdar", value="👑 Evet" if is_sovereign_member(member) else "Hayır", inline=True)
        account = self.bot.economy.get(member.id)
        embed.add_field(name="Seviye / XP", value=f"Sv. {account['level']} • {account['xp']} XP", inline=True)
        embed.add_field(name="Bakiye", value=format_balance(account["balance"]), inline=True)
        embed.add_field(name="Strike", value=str(self.bot.strikes.get(member.id)), inline=True)
        if roles:
            embed.add_field(name=f"Roller ({len(member.roles) - 1})", value=" ".join(roles) or "-", inline=False)
        if member.premium_since:
            embed.add_field(name="Boost", value=f"<t:{int(member.premium_since.timestamp())}:R>", inline=True)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="sunucu", aliases=["serverinfo", "server"], description="Sunucu bilgilerini gösterir.")
    @commands.guild_only()
    async def sunucu_komutu(self, ctx: commands.Context):
        g = ctx.guild
        humans = sum(1 for m in g.members if not m.bot)
        bots_n = (g.member_count or 0) - humans
        online = sum(1 for m in g.members if m.status != discord.Status.offline)
        embed = discord.Embed(title=f"🏰 {g.name}", color=discord.Color.dark_purple(),
                              description=g.description or None)
        if g.icon:
            embed.set_thumbnail(url=g.icon.url)
        embed.add_field(name="Sahip", value=g.owner.mention if g.owner else "?", inline=True)
        embed.add_field(name="ID", value=f"`{g.id}`", inline=True)
        embed.add_field(name="Oluşturulma", value=f"<t:{int(g.created_at.timestamp())}:R>", inline=True)
        embed.add_field(name="Üyeler", value=f"{g.member_count} (👤 {humans} / 🤖 {bots_n})", inline=True)
        embed.add_field(name="Çevrimiçi", value=str(online), inline=True)
        embed.add_field(name="Boost", value=f"Seviye {g.premium_tier} • {g.premium_subscription_count} boost", inline=True)
        embed.add_field(name="Kanallar", value=f"💬 {len(g.text_channels)} / 🔊 {len(g.voice_channels)} / 📁 {len(g.categories)}", inline=True)
        embed.add_field(name="Roller", value=str(len(g.roles)), inline=True)
        embed.add_field(name="Emojiler", value=str(len(g.emojis)), inline=True)
        if g.banner:
            embed.set_image(url=g.banner.url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="avatar", aliases=["pp", "av"], description="Avatarı büyük gösterir.")
    @app_commands.describe(member="Avatarına bakılacak üye")
    async def avatar_komutu(self, ctx: commands.Context, member: discord.Member = None):
        member = member or ctx.author
        embed = discord.Embed(title=f"🖼️ {member.display_name}", color=member.color or discord.Color.blurple())
        embed.set_image(url=member.display_avatar.replace(size=1024).url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="anket", aliases=["poll", "oylama"], description="Anket oluşturur. Seçenekleri | ile ayır.")
    @app_commands.describe(metin="Soru | seçenek1 | seçenek2 | ...")
    @commands.guild_only()
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def anket_komutu(self, ctx: commands.Context, *, metin: str):
        parts = [p.strip() for p in metin.split("|") if p.strip()]
        if len(parts) < 3:
            await ctx.send(f"❌ Kullanım: `{COMMAND_PREFIX}anket Soru | Seçenek1 | Seçenek2` (en az 2 seçenek)")
            return
        question, options = parts[0], parts[1:11]
        if len(options) < 2:
            await ctx.send("❌ En az 2 seçenek gerekli.")
            return
        emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        lines = [f"{emojis[i]} {opt}" for i, opt in enumerate(options)]
        embed = discord.Embed(title="📊 Anket", description=f"**{truncate(question, 200)}**\n\n" + "\n".join(lines),
                              color=discord.Color.blurple())
        embed.set_footer(text=f"Oluşturan: {ctx.author.display_name}")
        msg = await ctx.send(embed=embed)
        for i in range(len(options)):
            try:
                await msg.add_reaction(emojis[i])
            except discord.HTTPException:
                break

    @commands.hybrid_command(name="oneri", aliases=["öneri", "suggest", "suggestion"], description="Öneri kutusu — yetkililere iletilir.")
    @app_commands.describe(metin="Önerin")
    @commands.guild_only()
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def oneri_komutu(self, ctx: commands.Context, *, metin: str):
        text = truncate(metin.strip(), 1000)
        if len(text) < 5:
            await ctx.send("❌ Öneri çok kısa.")
            return
        embed = discord.Embed(title="💡 Yeni Öneri", description=text, color=discord.Color.gold())
        embed.add_field(name="Gönderen", value=ctx.author.mention, inline=True)
        embed.timestamp = discord.utils.utcnow()
        channel = self.bot.modlog_channel(ctx.guild) or ctx.channel
        try:
            msg = await channel.send(embed=embed)
            sid = self.bot.suggestions.add(ctx.guild.id, ctx.author.id, text, channel.id, msg.id)
            embed.set_footer(text=f"Öneri #{sid}")
            await msg.edit(embed=embed)
            for emoji in ("👍", "👎"):
                await msg.add_reaction(emoji)
        except discord.HTTPException as e:
            await ctx.send(f"❌ Öneri gönderilemedi: {e}")
            return
        if channel.id != ctx.channel.id:
            await ctx.send(f"✅ Önerin iletildi! (#{sid})", ephemeral=True)
        else:
            await ctx.send(f"✅ Öneri kaydedildi: **#{sid}**", delete_after=8)

    # --- Hatırlatma & etkinlik ---

    async def create_reminder(self, ctx: commands.Context, kind: str, sure: str, mesaj: str):
        delta = parse_duration(sure)
        if delta is None or delta < MIN_DURATION:
            await ctx.send("❌ Süreyi `30m`, `2h`, `1h30m`, `45dk` ya da `1g` gibi yaz (en az 10 sn, en fazla 365 gün).")
            return
        if kind == "reminder" and len(self.bot.reminders.for_user(ctx.author.id)) >= MAX_REMINDERS_PER_USER:
            await ctx.send(f"❌ En fazla {MAX_REMINDERS_PER_USER} bekleyen hatırlatman olabilir.")
            return
        due = utcnow() + delta
        title = sanitize_inline(mesaj, 200)
        rid = self.bot.reminders.add(kind, ctx.guild.id if ctx.guild else None, ctx.channel.id, ctx.author.id, title, due)
        stamp = int(due.timestamp())
        if kind == "event":
            await ctx.send(f"📣 **{title}** etkinliği planlandı: <t:{stamp}:F> (<t:{stamp}:R>)\nID: `{rid}`")
        else:
            await ctx.send(f"⏰ Tamam! <t:{stamp}:R> sana hatırlatacağım: **{title}**\nID: `{rid}`")

    @commands.hybrid_command(name="hatirlat", aliases=["remind", "reminder"], description="Belirli süre sonra seni etiketleyip hatırlatır.")
    @app_commands.describe(sure="Süre: 30m, 2h, 1h30m, 45dk, 1g gibi", mesaj="Neyi hatırlatayım?")
    async def hatirlat_komutu(self, ctx: commands.Context, sure: str, *, mesaj: str):
        await self.create_reminder(ctx, "reminder", sure, mesaj)

    @commands.hybrid_command(name="etkinlik", aliases=["event"], description="Zamanı gelince yapay zekayla anons edilecek etkinlik planlar.")
    @app_commands.describe(sure="Süre: 2h, 1d, 45dk gibi", baslik="Etkinliğin adı")
    @commands.guild_only()
    @perm_or_sovereign()
    async def etkinlik_komutu(self, ctx: commands.Context, sure: str, *, baslik: str):
        await self.create_reminder(ctx, "event", sure, baslik)

    @commands.hybrid_command(name="hatirlatmalar", aliases=["reminders"], description="Bekleyen hatırlatma ve etkinliklerini listeler.")
    async def hatirlatmalar_komutu(self, ctx: commands.Context):
        items = {i["id"]: i for i in self.bot.reminders.for_user(ctx.author.id)}
        if ctx.guild:
            for item in self.bot.reminders.for_guild_events(ctx.guild.id):
                items.setdefault(item["id"], item)
        if not items:
            await ctx.send("📭 Bekleyen hatırlatma ya da etkinlik yok.")
            return
        lines = []
        for item in sorted(items.values(), key=lambda i: i.get("time", ""))[:15]:
            when = parse_iso(item.get("time"))
            stamp = f"<t:{int(when.timestamp())}:R>" if when else "?"
            icon = "📣" if item.get("kind") == "event" else "⏰"
            lines.append(f"`{item['id']}` {icon} {stamp} — {truncate(item.get('title', ''), 60)}")
        embed = discord.Embed(title="📋 Bekleyenler", description="\n".join(lines), color=discord.Color.blurple())
        embed.set_footer(text=f"Silmek için: {COMMAND_PREFIX}hatirlatsil <id>")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="hatirlatsil", aliases=["unremind"], description="Bir hatırlatmayı ya da etkinliği ID'siyle siler.")
    @app_commands.describe(kimlik="Silinecek kaydın ID'si")
    async def hatirlatsil_komutu(self, ctx: commands.Context, kimlik: int):
        item = self.bot.reminders.find(kimlik)
        if item is None:
            await ctx.send("❌ Bu ID'de bekleyen bir kayıt yok.")
            return
        perms = getattr(ctx.author, "guild_permissions", None)
        can_delete = (item.get("author_id") == ctx.author.id or is_sovereign_member(ctx.author)
                      or bool(perms and perms.administrator))
        if not can_delete:
            await ctx.send("❌ Bu kaydı silme yetkin yok.")
            return
        self.bot.reminders.remove(kimlik)
        await ctx.send(f"🗑️ `{kimlik}` numaralı kayıt silindi.")

    # --- Günün Sorusu ---

    @commands.hybrid_group(name="gununsorusu", aliases=["gunun_sorusu", "soru"], fallback="durum",
                  invoke_without_command=True, description="Günün Sorusu sistemi (durum, ayarla, simdi, kapat).")
    @commands.guild_only()
    async def gununsorusu_group(self, ctx: commands.Context):
        cfg = self.bot.settings.value(ctx.guild.id, "daily_q") or {}
        embed = discord.Embed(title=f"❔ {DAILY_QUESTION_TITLE}", color=discord.Color.from_rgb(255, 182, 193))
        if cfg.get("enabled"):
            channel = ctx.guild.get_channel(cfg.get("channel") or 0)
            embed.add_field(name="Durum", value="✅ Açık", inline=True)
            embed.add_field(name="Kanal", value=channel.mention if channel else "⚠️ bulunamadı", inline=True)
            embed.add_field(name="Saat", value=f"{cfg.get('time', '12:00')} ({LOCAL_TZ})", inline=True)
            embed.add_field(name="Etiket", value=describe_ping(cfg.get("ping", "none")), inline=True)
        else:
            embed.description = (f"Şu an kapalı. Açmak için bir yönetici şunu yazabilir:\n"
                                 f"`{COMMAND_PREFIX}gununsorusu ayarla #kanal 18:30`")
        await ctx.send(embed=embed)

    @gununsorusu_group.command(name="ayarla", description="Günün Sorusu kanalını, saatini ve etiketini ayarlar.")
    @app_commands.describe(kanal="Soru hangi kanala atılsın? (boşsa bu kanal)", saat="Gönderim saati SS:DD (örn 18:30)",
                           ping="yok, everyone, here veya bir rol (etiket / ID / ad)")
    @perm_or_sovereign()
    async def gs_ayarla(self, ctx: commands.Context, kanal: discord.TextChannel = None, saat: str = "12:00", ping: str = "yok"):
        channel = kanal or ctx.channel
        parsed = parse_hhmm(saat)
        if parsed is None:
            await ctx.send("❌ Saati `SS:DD` biçiminde yaz (örn. `18:30`).")
            return
        ping_value = parse_ping_option(ctx.guild, ping)
        if ping_value is None:
            await ctx.send("❌ Etiket seçeneği `yok`, `everyone`, `here` ya da sunucudaki bir rol olmalı.")
            return
        if not channel.permissions_for(ctx.guild.me).send_messages:
            await ctx.send(f"❌ {channel.mention} kanalına yazma iznim yok.")
            return
        previous = self.bot.settings.value(ctx.guild.id, "daily_q") or {}
        self.bot.settings.set(ctx.guild.id, "daily_q", {
            "enabled": True, "channel": channel.id, "time": f"{parsed[0]:02d}:{parsed[1]:02d}",
            "ping": ping_value, "last_date": previous.get("last_date"),
        })
        await ctx.send(f"✅ Günün Sorusu her gün **{parsed[0]:02d}:{parsed[1]:02d}** ({LOCAL_TZ}) saatinde {channel.mention} "
                       f"kanalına gönderilecek. Etiket: {describe_ping(ping_value)}")

    @gununsorusu_group.command(name="simdi", description="Günün Sorusunu hemen paylaşır.")
    @perm_or_sovereign()
    async def gs_simdi(self, ctx: commands.Context):
        cfg = dict(self.bot.settings.value(ctx.guild.id, "daily_q") or {})
        cfg.setdefault("channel", ctx.channel.id)
        await ctx.defer()
        if await post_daily_question(ctx.guild, cfg):
            await ctx.send("✅ Günün Sorusu paylaşıldı!")
        else:
            await ctx.send("❌ Soru gönderilemedi; kanal ayarını ve izinlerimi kontrol et.")

    @gununsorusu_group.command(name="kapat", description="Otomatik Günün Sorusunu kapatır.")
    @perm_or_sovereign()
    async def gs_kapat(self, ctx: commands.Context):
        cfg = self.bot.settings.value(ctx.guild.id, "daily_q")
        if not cfg or not cfg.get("enabled"):
            await ctx.send("ℹ️ Günün Sorusu zaten kapalı.")
            return
        cfg["enabled"] = False
        self.bot.settings.store.mark_dirty()
        await ctx.send("🔕 Otomatik Günün Sorusu kapatıldı.")

    # --- Evrim ---

    @commands.hybrid_group(name="evrim", fallback="durum", invoke_without_command=True,
                  description="Botun kendi yazdığı komut taslaklarını yönetir.")
    @owner_or_sovereign()
    async def evrim_group(self, ctx: commands.Context):
        state = load_evolution_state()
        embed = discord.Embed(title="🧬 Evrim", color=discord.Color.purple())
        accepted = state.get("accepted") or []
        embed.add_field(name="Otomatik", value="Açık" if state.get("enabled") else "Kapalı", inline=True)
        embed.add_field(name="Aralık", value=f"{EVOLUTION_INTERVAL_MINUTES} dk", inline=True)
        embed.add_field(name="Aktif evrim komutları", value=", ".join(f"`{COMMAND_PREFIX}{i.get('command')}`" for i in accepted[-10:]) or "yok", inline=False)
        embed.set_footer(text="Önce DATA_DIR/evolution/venv içinde tokensız import testi. Ana dosya değişmez.")
        await ctx.send(embed=embed)

    @evrim_group.command(name="yaz", description="Hemen bir komut taslağı yazdırır.")
    @owner_or_sovereign()
    async def evrim_yaz(self, ctx: commands.Context):
        if self.bot.ai is None or not self.bot.ai.enabled:
            await ctx.send("⚠️ Yapay zeka çevrimdışı.")
            return
        await ctx.defer()
        try:
            result = await draft_evolution(self.bot.ai, self.bot)
            if not result:
                await ctx.send("ℹ️ Gemini bakınca eklenecek yeni bir eksik komut bulamadı.")
                return
            _name, summary, added = result
            if not added:
                await ctx.send("ℹ️ Gemini bakınca eklenecek yeni bir eksik komut bulamadı.")
                return
        except AIError as exc:
            await ctx.send(exc.user_message)
            return
        except Exception as exc:
            await ctx.send(f"❌ Evrim başarısız: {truncate(str(exc), 300)}")
            return
        await ctx.send(f"🧬 Sanal ortam testi geçti. Bu turda eklenenler: {summary}")

    @evrim_group.command(name="ac", aliases=["aç"], description="Belirli aralıklarla yeni taslak yazmayı açar.")
    @owner_or_sovereign()
    async def evrim_ac(self, ctx: commands.Context):
        state = load_evolution_state()
        state["enabled"] = True
        save_evolution_state(state)
        await ctx.send(
            f"✅ Otomatik evrim açık. En sık {EVOLUTION_INTERVAL_MINUTES} dakikada bir mevcut komutlara bakar, "
            f"eksik olanların hepsini (tur başına en fazla {EVOLUTION_BATCH}) yazar, sanal ortamda dener ve ekler."
        )

    @evrim_group.command(name="kapa", description="Otomatik taslak yazmayı kapatır.")
    @owner_or_sovereign()
    async def evrim_kapa(self, ctx: commands.Context):
        state = load_evolution_state()
        state["enabled"] = False
        save_evolution_state(state)
        await ctx.send("🔕 Otomatik evrim taslağı kapatıldı.")

    # --- Bot sahibi komutlari ---

    @commands.hybrid_command(name="yedekle", aliases=["backup"], description="Verileri hemen yedek kanalına yükler (bot sahibi / Hükümdar).")
    @owner_or_sovereign()
    async def yedekle_komutu(self, ctx: commands.Context):
        from xyrin_bot import BACKUP_CHANNEL_ID
        if not BACKUP_CHANNEL_ID:
            await ctx.send("ℹ️ Yedekleme kapalı. Özel bir kanal açıp ID'sini `BACKUP_CHANNEL_ID` çevre değişkenine yaz.")
            return
        await ctx.defer()
        result = await self.bot.backup_now(force=True, reason=f"{ctx.author} istedi")
        messages = {
            "ok": "✅ Veriler yedek kanalına yüklendi.",
            "no-channel": "❌ Yedek kanalına ulaşamadım (ID'yi ve izinlerimi kontrol et).",
            "failed": "❌ Yedek yüklenemedi (kanalda dosya gönderme iznim var mı?).",
        }
        await ctx.send(messages.get(result, "ℹ️ Yedekleme yapılmadı."))

    @commands.hybrid_command(name="sync", description="Slash komutlarını Discord ile eşitler (bot sahibi / Hükümdar).")
    @owner_or_sovereign()
    async def sync_komutu(self, ctx: commands.Context):
        await ctx.defer()
        synced = await self.bot.tree.sync()
        await ctx.send(f"✅ {len(synced)} slash komutu eşitlendi.")


async def setup(bot_instance: commands.Bot):
    await bot_instance.add_cog(UtilityCog(bot_instance))
