"""Genel komutlar cogu: yardim, ping, kimlik, yetki, kahve, hologram, rapor, seslen, ayril."""
from __future__ import annotations

import asyncio
import logging

import discord
from discord import app_commands
from discord.ext import commands

from xyrin_bot import (
    BACKUP_CHANNEL_ID,
    COMMAND_PREFIX,
    INSTANCE_ID,
    PLATFORM,
    bot,
    format_duration,
    is_sovereign_member,
    panel_settings,
    progress_bar,
    sanitize_inline,
    sovereign_address,
    truncate,
    utcnow,
    owner_or_sovereign,
)

logger = logging.getLogger("XyrinImperialCore")


class GeneralCog(commands.Cog, name="Genel"):
    def __init__(self, bot_instance: commands.Bot):
        self.bot = bot_instance

    @commands.hybrid_command(name="yardim", aliases=["help", "komutlar"], description="Komut menüsünü açar.")
    async def yardim_komutu(self, ctx: commands.Context):
        from xyrin_bot import build_help_embed, HelpView
        view = HelpView(ctx.author.id)
        view.message = await ctx.send(embed=build_help_embed("genel"), view=view)

    @commands.hybrid_command(name="ping", description="Botun gecikme (latency) süresini ölçer.")
    async def ping_komutu(self, ctx: commands.Context):
        latency = round(self.bot.latency * 1000)
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"İmparatorluk sinir ağı gecikme süresi: **{latency}ms**",
            color=discord.Color.green(),
        )
        embed.set_footer(text=f"Çalıştığı yer: {PLATFORM} • Örnek: {INSTANCE_ID}")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="kimlik", aliases=["id", "whoami"], description="Discord ID'ni ve Hükümdar durumunu gösterir.")
    async def kimlik_komutu(self, ctx: commands.Context):
        from xyrin_bot import SOVEREIGN_IDS
        embed = discord.Embed(title="🪪 Kimlik", color=discord.Color.blurple())
        embed.add_field(name="Kullanıcı", value=f"{ctx.author.mention} (`{ctx.author.name}`)", inline=False)
        embed.add_field(name="ID", value=f"`{ctx.author.id}`", inline=True)
        embed.add_field(name="Hükümdar", value="👑 Evet" if is_sovereign_member(ctx.author) else "Hayır", inline=True)
        if not SOVEREIGN_IDS:
            embed.set_footer(text="İpucu: ID'leri SOVEREIGN_IDS çevre değişkenine virgülle yaz; yetki kullanıcı adına değil ID'ye bağlanır.")
        await ctx.send(embed=embed, ephemeral=True)

    @commands.hybrid_command(
        name="yetki",
        aliases=["kralice", "kraliçe", "hukumdarkralice"],
        description="Tek komut: üyeyi Hükümdar Kraliçe yapar (yetki + rol).",
    )
    @app_commands.describe(yetkili="Hükümdar Kraliçe olacak üye")
    @commands.guild_only()
    @owner_or_sovereign()
    async def yetki_komutu(self, ctx: commands.Context, yetkili: discord.Member):
        from xyrin_bot import QUEEN_ADDRESS, QUEEN_ROLE_NAME, now_local, sovereign_store
        if yetkili.bot:
            await ctx.send("❌ Botlar Hükümdar olamaz.")
            return
        store = sovereign_store()
        queens = store.data["queens"]
        key = str(yetkili.id)
        already = key in queens
        queens[key] = {
            "name": yetkili.name,
            "unvan": QUEEN_ADDRESS,
            "by": ctx.author.id,
            "at": now_local().isoformat(),
        }
        store.mark_dirty()
        store.flush_sync()

        role_note = ""
        role = discord.utils.get(ctx.guild.roles, name=QUEEN_ROLE_NAME)
        try:
            if role is None:
                role = await ctx.guild.create_role(
                    name=QUEEN_ROLE_NAME,
                    color=discord.Color.gold(),
                    permissions=discord.Permissions.none(),
                    reason=f"Hükümdar Kraliçe: {ctx.author} ({ctx.author.id})",
                )
            if role not in yetkili.roles:
                await yetkili.add_roles(role, reason=f"Hükümdar Kraliçe ataması: {ctx.author} ({ctx.author.id})")
            role_note = f"Discord rolü **{role.mention}** verildi."
        except discord.Forbidden:
            role_note = "Yetki kaydı yazıldı ama rol verilemedi. Botun rolünü **Hükümdar Kraliçe** rolünün üstüne al."
        except discord.HTTPException as e:
            role_note = f"Yetki kaydı yazıldı, rol sırasında hata: {e}"

        embed = discord.Embed(
            title="👑 Hükümdar Kraliçe",
            description=(
                f"{yetkili.mention} artık **Hükümdar Kraliçe**.\n"
                f"Yapay zeka ona **{QUEEN_ADDRESS}** diyecek.\n"
                + ("Kayıt zaten vardı, unvan yenilendi.\n" if already else "")
                + role_note
            ),
            color=discord.Color.gold(),
        )
        embed.set_footer(text="Kayıt sovereigns.json içinde durur; bot yeniden başlasa da silinmez.")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="kahve", aliases=["coffee", "espresso"], description="Kahve siparişi ver ☕")
    @app_commands.describe(kahve_turu="Hangi kahve? (örn: Latte)")
    async def kahve_komutu(self, ctx: commands.Context, *, kahve_turu: str = "Espresso"):
        kahve_turu = sanitize_inline(kahve_turu, 40)
        steps = [
            "☕ İmparatorluk Kahve Çekirdekleri öğütülüyor...",
            "🔥 Su sıcaklığı sabitlendi...",
            f"🚀 Kurye dronumuz **{kahve_turu}** siparişinizi teslim etmek için yola çıktı!",
        ]
        msg = await ctx.send(steps[0])
        for step in steps[1:]:
            await asyncio.sleep(1.2)
            await msg.edit(content=step)
        await ctx.send("☕ Kahveniz hazır, afiyet olsun!")

    @commands.hybrid_command(name="hologram", aliases=["holo", "camera", "kamera"], description="Ses kanalındaki hologram durumunu gösterir.")
    @commands.guild_only()
    async def hologram_durum_komutu(self, ctx: commands.Context):
        embed = discord.Embed(title="🔮 Xyrin Hologram Projektör", color=discord.Color.teal())
        holo = self.bot.active_holograms.get(ctx.guild.id)
        if holo:
            embed.description = f"Aktif Ses Odası: **{holo['channel'].name}** | Hedef: {holo['target_user'].mention}"
            embed.add_field(name="Durum", value=holo["status"], inline=False)
            embed.add_field(name="Render edilen kare", value=str(holo["frames_rendered"]), inline=True)
        else:
            embed.description = "Aktif bir ses odası hologramı bulunmuyor."
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="rapor", aliases=["stats", "durum"], description="Sunucu ve bot raporunu gösterir.")
    @commands.guild_only()
    async def sunucu_raporu(self, ctx: commands.Context):
        guild = ctx.guild
        bot_count = sum(1 for m in guild.members if m.bot)
        ai_ok = self.bot.ai is not None and getattr(self.bot.ai, "enabled", False)
        embed = discord.Embed(title=f"📊 {guild.name} - Rapor", color=discord.Color.blue())
        embed.add_field(name="👥 Toplam Üye", value=f"{guild.member_count} ({bot_count} bot)", inline=True)
        embed.add_field(name="💬 Kanallar", value=f"{len(guild.text_channels)} metin / {len(guild.voice_channels)} ses", inline=True)
        embed.add_field(name="🏷️ Roller", value=str(len(guild.roles)), inline=True)
        embed.add_field(name="🏓 Gecikme", value=f"{round(self.bot.latency * 1000)} ms", inline=True)
        embed.add_field(name="⏱️ Çalışma süresi", value=format_duration(utcnow() - self.bot.start_time), inline=True)
        embed.add_field(name="🤖 Yapay zeka", value="✅ Çevrimiçi" if ai_ok else "⚠️ Çevrimdışı", inline=True)
        embed.add_field(name="🖥️ Çalıştığı yer", value=f"{PLATFORM} • örnek `{INSTANCE_ID}`", inline=True)
        embed.add_field(name="💾 Veri yedeği", value="✅ Discord kanalı" if BACKUP_CHANNEL_ID else "⚠️ Kapalı (BACKUP_CHANNEL_ID)", inline=True)
        embed.add_field(name="🤖 Durum", value="Hükümdar Protokolü Devrede", inline=False)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="seslen", aliases=["join"], description="Bulunduğun ses kanalına katılır.")
    @commands.guild_only()
    async def ses_kanalina_gir(self, ctx: commands.Context):
        if not (ctx.author.voice and ctx.author.voice.channel):
            await ctx.send("❌ Önce bir ses kanalına katılmalısınız!")
            return
        channel = ctx.author.voice.channel
        try:
            if ctx.voice_client:
                await ctx.voice_client.move_to(channel)
            else:
                await channel.connect()
        except (discord.ClientException, asyncio.TimeoutError) as e:
            logger.warning(f"Ses kanalına bağlanılamadı: {e}")
            await ctx.send("❌ Ses kanalına bağlanılamadı (sunucuda PyNaCl kurulu olmayabilir).")
            return
        await ctx.send(f"🔊 Ses kanalına giriş yapıldı: **{channel.name}** ✨")

    @commands.hybrid_command(name="ayril", aliases=["leave"], description="Ses kanalından ayrılır.")
    @commands.guild_only()
    async def ses_kanalindan_cik(self, ctx: commands.Context):
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            self.bot.active_holograms.pop(ctx.guild.id, None)
            await ctx.send("🔇 Ses kanalından ayrılındı.")
        else:
            await ctx.send("❌ Zaten bir ses kanalında değilim.")


async def setup(bot_instance: commands.Bot):
    await bot_instance.add_cog(GeneralCog(bot_instance))
