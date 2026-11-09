"""Moderasyon komutlari cogu: kanaloluştur, rololuştur, uyarilar, uyarisifirla, kufur, modlog, hosgeldin, kick, ban, unban, mute, unmute, temizle, slowmode, kilitle, kilita, rolover, rolal, nick, duyuru."""
from __future__ import annotations

import logging
from datetime import timedelta

import discord
from discord import app_commands
from discord.ext import commands

from xyrin_bot import (
    COMMAND_PREFIX,
    MOD_AI_ENABLED,
    STRIKE_DECAY_DAYS,
    STRIKE_TIMEOUT_MINUTES,
    bot,
    is_mod_exempt,
    is_sovereign_member,
    panel_settings,
    perm_or_sovereign,
    profanity_filter_enabled,
    truncate,
)

logger = logging.getLogger("XyrinImperialCore")


class ModerationCog(commands.Cog, name="Moderasyon"):
    def __init__(self, bot_instance: commands.Bot):
        self.bot = bot_instance

    @commands.hybrid_command(name="kanaloluştur", aliases=["createchannel", "kanalolustur"], description="Yeni bir metin kanalı oluşturur (yönetici).")
    @app_commands.describe(kanal_adi="Oluşturulacak kanalın adı")
    @commands.guild_only()
    @perm_or_sovereign()
    async def manuel_kanal_olustur(self, ctx: commands.Context, *, kanal_adi: str):
        from xyrin_bot import sanitize_channel_name
        name = sanitize_channel_name(kanal_adi)
        if not name:
            await ctx.send("❌ Geçerli bir kanal adı gir.")
            return
        created = await ctx.guild.create_text_channel(name, reason=f"{ctx.author} ({ctx.author.id}) tarafından oluşturuldu")
        await ctx.send(f"✅ Başarıyla yeni kanal oluşturuldu: {created.mention}")

    @commands.hybrid_command(name="rololuştur", aliases=["createrole", "rololustur"], description="Yeni bir rol oluşturur (yönetici).")
    @app_commands.describe(rol_adi="Oluşturulacak rolün adı")
    @commands.guild_only()
    @perm_or_sovereign()
    async def manuel_rol_olustur(self, ctx: commands.Context, *, rol_adi: str):
        from xyrin_bot import sanitize_role_name
        name = sanitize_role_name(rol_adi)
        if not name:
            await ctx.send("❌ Geçerli bir rol adı gir.")
            return
        created = await ctx.guild.create_role(
            name=name, color=discord.Color.random(), permissions=discord.Permissions.none(),
            reason=f"{ctx.author} ({ctx.author.id}) tarafından oluşturuldu")
        await ctx.send(f"✨ Yeni rol başarıyla yaratıldı: **{created.name}**")

    @commands.hybrid_command(name="uyarilar", aliases=["strikes", "warnlist"], description="Bir üyenin küfür/spam strike sayısını gösterir.")
    @app_commands.describe(member="Strike sayısına bakılacak üye")
    @commands.guild_only()
    @perm_or_sovereign(moderate_members=True)
    async def uyarilar_komutu(self, ctx: commands.Context, member: discord.Member = None):
        member = member or ctx.author
        embed = discord.Embed(title="⚠️ Uyarı Sicili", color=discord.Color.orange())
        embed.add_field(name="Kullanıcı", value=member.mention, inline=True)
        embed.add_field(name="Toplam strike", value=str(self.bot.strikes.get(member.id)), inline=True)
        if STRIKE_DECAY_DAYS > 0:
            embed.set_footer(text=f"Her {STRIKE_DECAY_DAYS} günde bir strike silinir.")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="uyarisifirla", aliases=["resetstrikes"], description="Bir üyenin strike sicilini sıfırlar (yönetici).")
    @app_commands.describe(member="Sicili sıfırlanacak üye")
    @commands.guild_only()
    @perm_or_sovereign()
    async def uyari_sifirla_komutu(self, ctx: commands.Context, member: discord.Member):
        self.bot.strikes.reset(member.id)
        await ctx.send(f"✅ {member.mention} kullanıcısının uyarı sicili sıfırlandı.")

    async def set_profanity_filter(self, ctx: commands.Context, enabled: bool):
        """/kufur ac ve /kufur kapa için ortak işlem."""
        if profanity_filter_enabled(ctx.guild.id) == enabled:
            await ctx.send("ℹ️ Küfür filtresi zaten " + ("açık." if enabled else "kapalı."))
            return
        self.bot.settings.set(ctx.guild.id, "profanity_filter", enabled)
        if enabled:
            await ctx.send("✅ Küfür/hakaret filtresi **açıldı**. Yasaklı kelime listesi ve yapay zeka denetimi yeniden çalışıyor.")
        else:
            await ctx.send(
                "⏸️ Küfür/hakaret filtresi **kapatıldı**: yasaklı kelime listesi ve yapay zeka denetimi devre dışı.\n"
                f"Spam, toplu etiket ve link koruması açık kalmaya devam ediyor. Tekrar açmak için `/kufur ac` "
                f"(ya da `{COMMAND_PREFIX}kufur ac`)."
            )
        embed = discord.Embed(title="⚙️ Moderasyon Ayarı Değişti",
                              color=discord.Color.green() if enabled else discord.Color.orange())
        embed.add_field(name="Ayar", value="Küfür/hakaret filtresi", inline=True)
        embed.add_field(name="Yeni durum", value="✅ Açık" if enabled else "⏸️ Kapalı", inline=True)
        embed.add_field(name="Değiştiren", value=ctx.author.mention, inline=True)
        embed.timestamp = discord.utils.utcnow()
        await self.bot.send_modlog(ctx.guild, embed)

    @commands.hybrid_group(name="kufur", aliases=["küfür", "profanity"], fallback="durum", invoke_without_command=True,
                  description="Küfür/hakaret filtresini açar veya kapatır (ac, kapa, durum).")
    @commands.guild_only()
    @perm_or_sovereign(moderate_members=True)
    async def kufur_group(self, ctx: commands.Context):
        enabled = profanity_filter_enabled(ctx.guild.id)
        ai_ok = bool(self.bot.ai is not None and self.bot.ai.enabled and MOD_AI_ENABLED)
        embed = discord.Embed(title="🛡️ Küfür / Hakaret Filtresi",
                              color=discord.Color.green() if enabled else discord.Color.orange())
        embed.add_field(name="Durum", value="✅ Açık" if enabled else "⏸️ Kapalı", inline=True)
        embed.add_field(name="Yapay zeka denetimi", value="✅ Hazır" if ai_ok else "⚠️ Devre dışı", inline=True)
        embed.add_field(name="Yasaklı kelime listesi", value=f"{self.bot.word_filter.count} kelime", inline=True)
        embed.add_field(name="Filtre kapalıyken de çalışanlar", value="Spam, toplu etiket ve link koruması", inline=False)
        embed.set_footer(text=f"Değiştirmek için: /kufur ac  •  /kufur kapa  (ya da {COMMAND_PREFIX}kufur ac / {COMMAND_PREFIX}kufur kapa)")
        await ctx.send(embed=embed)

    @kufur_group.command(name="ac", aliases=["aç", "on"], description="Küfür/hakaret filtresini açar.")
    @perm_or_sovereign()
    async def kufur_ac(self, ctx: commands.Context):
        await self.set_profanity_filter(ctx, True)

    @kufur_group.command(name="kapa", aliases=["kapat", "off"], description="Küfür/hakaret filtresini kapatır (spam ve link koruması açık kalır).")
    @perm_or_sovereign()
    async def kufur_kapa(self, ctx: commands.Context):
        await self.set_profanity_filter(ctx, False)

    @commands.hybrid_command(name="modlog", aliases=["setmodlog"], description="Moderasyon loglarının gideceği kanalı bu kanal yapar.")
    @commands.guild_only()
    @perm_or_sovereign()
    async def modlog_kanal_ayarla(self, ctx: commands.Context):
        self.bot.settings.set(ctx.guild.id, "mod_log", ctx.channel.id)
        await ctx.send(f"✅ Moderasyon logları artık bu kanala (`{ctx.channel.name}`) gönderilecek. Ayar kalıcı olarak kaydedildi.")

    @commands.hybrid_command(name="hosgeldin", aliases=["setwelcome"], description="Karşılama mesajlarının gideceği kanalı bu kanal yapar.")
    @commands.guild_only()
    @perm_or_sovereign()
    async def hosgeldin_kanal_ayarla(self, ctx: commands.Context):
        self.bot.settings.set(ctx.guild.id, "welcome", ctx.channel.id)
        await ctx.send(f"✅ Karşılama mesajları artık bu kanala (`{ctx.channel.name}`) gönderilecek. Ayar kalıcı olarak kaydedildi.")

    # --- Manuel moderasyon ---

    def _can_moderate(self, ctx: commands.Context, target: discord.Member):
        if target.id == ctx.author.id:
            return "Kendine işlem uygulayamazsın."
        if target.id == ctx.guild.me.id:
            return "Bana işlem uygulayamazsın."
        if is_sovereign_member(target):
            return "Hükümdarlara işlem uygulanamaz."
        if (ctx.author.top_role <= target.top_role and not is_sovereign_member(ctx.author)
                and not ctx.author.guild_permissions.administrator):
            return "Bu üyenin rolü senden yüksek veya eşit."
        if ctx.guild.me.top_role <= target.top_role:
            return "Botun rolü bu üyenin rolünden düşük."
        return None

    @commands.hybrid_command(name="kick", aliases=["at"], description="Üyeyi sunucudan atar.")
    @app_commands.describe(member="Atılacak üye", sebep="Sebep")
    @commands.guild_only()
    @perm_or_sovereign(kick_members=True)
    async def kick_komutu(self, ctx: commands.Context, member: discord.Member, *, sebep: str = "Sebep belirtilmedi"):
        err = self._can_moderate(ctx, member)
        if err:
            await ctx.send(f"❌ {err}")
            return
        reason = f"{ctx.author}: {sebep}"[:500]
        try:
            await member.kick(reason=reason)
        except discord.HTTPException as e:
            await ctx.send(f"❌ Kick başarısız: {e}")
            return
        embed = discord.Embed(title="👢 Kick", color=discord.Color.orange())
        embed.add_field(name="Üye", value=f"{member} (`{member.id}`)", inline=True)
        embed.add_field(name="Yetkili", value=ctx.author.mention, inline=True)
        embed.add_field(name="Sebep", value=truncate(sebep, 500), inline=False)
        embed.timestamp = discord.utils.utcnow()
        await self.bot.send_modlog(ctx.guild, embed)
        await ctx.send(f"✅ **{member}** sunucudan atıldı.")

    @commands.hybrid_command(name="ban", aliases=["yasakla"], description="Üyeyi sunucudan yasaklar.")
    @app_commands.describe(member="Yasaklanacak üye", sebep="Sebep", sil_gun="Mesaj silme günü (0-7)")
    @commands.guild_only()
    @perm_or_sovereign(ban_members=True)
    async def ban_komutu(self, ctx: commands.Context, member: discord.Member, sil_gun: commands.Range[int, 0, 7] = 0, *, sebep: str = "Sebep belirtilmedi"):
        err = self._can_moderate(ctx, member)
        if err:
            await ctx.send(f"❌ {err}")
            return
        reason = f"{ctx.author}: {sebep}"[:500]
        try:
            await member.ban(reason=reason, delete_message_days=sil_gun)
        except discord.HTTPException as e:
            await ctx.send(f"❌ Ban başarısız: {e}")
            return
        embed = discord.Embed(title="🔨 Ban", color=discord.Color.red())
        embed.add_field(name="Üye", value=f"{member} (`{member.id}`)", inline=True)
        embed.add_field(name="Yetkili", value=ctx.author.mention, inline=True)
        embed.add_field(name="Sebep", value=truncate(sebep, 500), inline=False)
        embed.timestamp = discord.utils.utcnow()
        await self.bot.send_modlog(ctx.guild, embed)
        await ctx.send(f"✅ **{member}** yasaklandı.")

    @commands.hybrid_command(name="unban", aliases=["yasakkaldir"], description="Yasağı kaldırır (kullanıcı ID ile).")
    @app_commands.describe(user_id="Yasağı kaldırılacak kullanıcının ID'si")
    @commands.guild_only()
    @perm_or_sovereign(ban_members=True)
    async def unban_komutu(self, ctx: commands.Context, user_id: str):
        if not user_id.isdigit():
            await ctx.send("❌ Geçerli bir kullanıcı ID'si gir.")
            return
        uid = int(user_id)
        try:
            user = await self.bot.fetch_user(uid)
            await ctx.guild.unban(user, reason=f"{ctx.author} tarafından kaldırıldı")
        except discord.NotFound:
            await ctx.send("❌ Bu kullanıcı yasaklı değil veya bulunamadı.")
            return
        except discord.HTTPException as e:
            await ctx.send(f"❌ Unban başarısız: {e}")
            return
        await ctx.send(f"✅ **{user}** yasağı kaldırıldı.")
        embed = discord.Embed(title="🕊️ Unban", color=discord.Color.green())
        embed.add_field(name="Kullanıcı", value=f"{user} (`{user.id}`)", inline=True)
        embed.add_field(name="Yetkili", value=ctx.author.mention, inline=True)
        await self.bot.send_modlog(ctx.guild, embed)

    @commands.hybrid_command(name="mute", aliases=["sustur", "timeout"], description="Üyeyi belirli süre susturur.")
    @app_commands.describe(member="Susturulacak üye", sure="Süre (örn: 10m, 1h, 1d)", sebep="Sebep")
    @commands.guild_only()
    @perm_or_sovereign(moderate_members=True)
    async def mute_komutu(self, ctx: commands.Context, member: discord.Member, sure: str, *, sebep: str = "Sebep belirtilmedi"):
        err = self._can_moderate(ctx, member)
        if err:
            await ctx.send(f"❌ {err}")
            return
        from xyrin_bot import parse_duration, format_duration
        delta = parse_duration(sure)
        if delta is None or delta < timedelta(seconds=10) or delta > timedelta(days=28):
            await ctx.send("❌ Süre 10 sn – 28 gün arasında olmalı (`10m`, `1h`, `1d` gibi).")
            return
        until = discord.utils.utcnow() + delta
        try:
            await member.timeout(until, reason=f"{ctx.author}: {sebep}"[:500])
        except discord.HTTPException as e:
            await ctx.send(f"❌ Mute başarısız: {e}")
            return
        embed = discord.Embed(title="🔇 Mute", color=discord.Color.dark_orange())
        embed.add_field(name="Üye", value=member.mention, inline=True)
        embed.add_field(name="Süre", value=format_duration(delta), inline=True)
        embed.add_field(name="Yetkili", value=ctx.author.mention, inline=True)
        embed.add_field(name="Sebep", value=truncate(sebep, 500), inline=False)
        await self.bot.send_modlog(ctx.guild, embed)
        await ctx.send(f"✅ {member.mention} **{format_duration(delta)}** susturuldu.")

    @commands.hybrid_command(name="unmute", aliases=["susturkaldir"], description="Üyenin susturmasını kaldırır.")
    @app_commands.describe(member="Susturması kaldırılacak üye")
    @commands.guild_only()
    @perm_or_sovereign(moderate_members=True)
    async def unmute_komutu(self, ctx: commands.Context, member: discord.Member):
        try:
            await member.timeout(None, reason=f"{ctx.author} tarafından kaldırıldı")
        except discord.HTTPException as e:
            await ctx.send(f"❌ Unmute başarısız: {e}")
            return
        await ctx.send(f"✅ {member.mention} susturması kaldırıldı.")
        embed = discord.Embed(title="🔊 Unmute", color=discord.Color.green())
        embed.add_field(name="Üye", value=member.mention, inline=True)
        embed.add_field(name="Yetkili", value=ctx.author.mention, inline=True)
        await self.bot.send_modlog(ctx.guild, embed)

    @commands.hybrid_command(name="temizle", aliases=["clear", "purge", "sil"], description="Kanaldan belirli sayıda mesaj siler.")
    @app_commands.describe(adet="Silinecek mesaj sayısı (1-100)")
    @commands.guild_only()
    @perm_or_sovereign(manage_messages=True)
    async def temizle_komutu(self, ctx: commands.Context, adet: commands.Range[int, 1, 100]):
        try:
            deleted = await ctx.channel.purge(limit=adet + (0 if ctx.interaction else 1))
            count = max(0, len(deleted) - (0 if ctx.interaction else 1))
        except discord.HTTPException as e:
            await ctx.send(f"❌ Mesajlar silinemedi: {e}")
            return
        await ctx.send(f"🧹 **{count}** mesaj silindi.", delete_after=5)
        embed = discord.Embed(title="🧹 Temizleme", color=discord.Color.blue())
        embed.add_field(name="Kanal", value=ctx.channel.mention, inline=True)
        embed.add_field(name="Adet", value=str(count), inline=True)
        embed.add_field(name="Yetkili", value=ctx.author.mention, inline=True)
        await self.bot.send_modlog(ctx.guild, embed)

    @commands.hybrid_command(name="slowmode", aliases=["yavasmod", "yavaşmod"], description="Kanal yavaş modunu ayarlar (saniye).")
    @app_commands.describe(saniye="0 = kapat, max 21600")
    @commands.guild_only()
    @perm_or_sovereign(manage_channels=True)
    async def slowmode_komutu(self, ctx: commands.Context, saniye: commands.Range[int, 0, 21600]):
        try:
            await ctx.channel.edit(slowmode_delay=saniye)
        except discord.HTTPException as e:
            await ctx.send(f"❌ Ayarlanamadı: {e}")
            return
        if saniye == 0:
            await ctx.send("✅ Yavaş mod kapatıldı.")
        else:
            await ctx.send(f"✅ Yavaş mod **{saniye} saniye** olarak ayarlandı.")

    @commands.hybrid_command(name="kilitle", aliases=["lock"], description="Kanalı kilitler (@everyone yazamasın).")
    @commands.guild_only()
    @perm_or_sovereign(manage_channels=True)
    async def kilitle_komutu(self, ctx: commands.Context):
        overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = False
        try:
            await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite, reason=f"{ctx.author}")
        except discord.HTTPException as e:
            await ctx.send(f"❌ Kilitlenemedi: {e}")
            return
        await ctx.send("🔒 Kanal kilitlendi.")

    @commands.hybrid_command(name="kilita", aliases=["unlock", "kilitac", "kilitaç"], description="Kanal kilidini açar.")
    @commands.guild_only()
    @perm_or_sovereign(manage_channels=True)
    async def kilita_komutu(self, ctx: commands.Context):
        overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = None
        try:
            await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite, reason=f"{ctx.author}")
        except discord.HTTPException as e:
            await ctx.send(f"❌ Açılamadı: {e}")
            return
        await ctx.send("🔓 Kanal kilidi açıldı.")

    @commands.hybrid_command(name="rolver", aliases=["addrole", "giverole"], description="Üyeye rol verir.")
    @app_commands.describe(member="Üye", role="Rol")
    @commands.guild_only()
    @perm_or_sovereign(manage_roles=True)
    async def rolver_komutu(self, ctx: commands.Context, member: discord.Member, role: discord.Role):
        if role >= ctx.guild.me.top_role:
            await ctx.send("❌ Bu rol botun en yüksek rolünden yüksek veya eşit.")
            return
        if role in member.roles:
            await ctx.send("ℹ️ Üye zaten bu role sahip.")
            return
        try:
            await member.add_roles(role, reason=f"{ctx.author}")
        except discord.HTTPException as e:
            await ctx.send(f"❌ Rol verilemedi: {e}")
            return
        await ctx.send(f"✅ {member.mention} kullanıcısına {role.mention} verildi.")

    @commands.hybrid_command(name="rolal", aliases=["removerole", "takerole"], description="Üyeden rol alır.")
    @app_commands.describe(member="Üye", role="Rol")
    @commands.guild_only()
    @perm_or_sovereign(manage_roles=True)
    async def rolal_komutu(self, ctx: commands.Context, member: discord.Member, role: discord.Role):
        if role >= ctx.guild.me.top_role:
            await ctx.send("❌ Bu rol botun en yüksek rolünden yüksek veya eşit.")
            return
        if role not in member.roles:
            await ctx.send("ℹ️ Üyede bu rol yok.")
            return
        try:
            await member.remove_roles(role, reason=f"{ctx.author}")
        except discord.HTTPException as e:
            await ctx.send(f"❌ Rol alınamadı: {e}")
            return
        await ctx.send(f"✅ {member.mention} kullanıcısından {role.mention} alındı.")

    @commands.hybrid_command(name="nick", aliases=["isim", "nickname"], description="Üyenin takma adını değiştirir.")
    @app_commands.describe(member="Üye", yeni_isim="Yeni isim (boş = sıfırla)")
    @commands.guild_only()
    @perm_or_sovereign(manage_nicknames=True)
    async def nick_komutu(self, ctx: commands.Context, member: discord.Member, *, yeni_isim: str = None):
        if member.id != ctx.author.id:
            err = self._can_moderate(ctx, member)
            if err and not is_sovereign_member(ctx.author):
                await ctx.send(f"❌ {err}")
                return
        name = (yeni_isim or "")[:32] or None
        try:
            await member.edit(nick=name, reason=f"{ctx.author}")
        except discord.HTTPException as e:
            await ctx.send(f"❌ İsim değiştirilemedi: {e}")
            return
        await ctx.send(f"✅ {member.mention} yeni isim: **{name or member.name}**")

    @commands.hybrid_command(name="duyuru", aliases=["announce", "say"], description="Embed duyuru gönderir.")
    @app_commands.describe(mesaj="Duyuru metni")
    @commands.guild_only()
    @perm_or_sovereign(manage_messages=True)
    async def duyuru_komutu(self, ctx: commands.Context, *, mesaj: str):
        embed = discord.Embed(
            title="📢 İmparatorluk Duyurusu",
            description=truncate(mesaj, 4000),
            color=discord.Color.dark_purple(),
        )
        embed.set_footer(text=f"Duyuran: {ctx.author.display_name}")
        embed.timestamp = discord.utils.utcnow()
        if ctx.interaction:
            await ctx.send("✅ Duyuru gönderildi.", ephemeral=True)
            await ctx.channel.send(embed=embed)
        else:
            try:
                await ctx.message.delete()
            except discord.HTTPException:
                pass
            await ctx.channel.send(embed=embed)


async def setup(bot_instance: commands.Bot):
    await bot_instance.add_cog(ModerationCog(bot_instance))
