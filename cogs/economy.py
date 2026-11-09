"""Ekonomi & seviye komutlari cogu: bakiye, seviye, gunluk, transfer, market, satinal, zar, yazitura, bahis, siralama, calis, suc, soy."""
from __future__ import annotations

import logging
import random
from datetime import timedelta

import discord
from discord import app_commands
from discord.ext import commands

from xyrin_bot import (
    BET_MAX,
    CRIME_ACTIONS,
    CRIME_COOLDOWN_SECONDS,
    CRIME_FAIL_FINE_MAX,
    CRIME_FAIL_FINE_MIN,
    CRIME_REWARD_MAX,
    CRIME_REWARD_MIN,
    CRIME_SUCCESS_CHANCE,
    COMMAND_PREFIX,
    DAILY_COOLDOWN_HOURS,
    DAILY_REWARD_MAX,
    DAILY_REWARD_MIN,
    DAILY_STREAK_BONUS,
    DAILY_STREAK_MAX_DAYS,
    fold_text,
    LEVEL_ROLES,
    progress_bar,
    ROB_COOLDOWN_SECONDS,
    ROB_MAX_PERCENT,
    ROB_MIN_TARGET_BALANCE,
    ROB_SUCCESS_CHANCE,
    SHOP_ITEMS,
    WORK_COOLDOWN_SECONDS,
    WORK_JOBS,
    WORK_REWARD_MAX,
    WORK_REWARD_MIN,
    XP_PER_LEVEL,
    bot,
    format_balance,
    format_duration,
    is_mod_exempt,
    is_sovereign_member,
    parse_iso,
    sanitize_inline,
    truncate,
    utcnow,
)

logger = logging.getLogger("XyrinImperialCore")


class EconomyCog(commands.Cog, name="Ekonomi"):
    def __init__(self, bot_instance: commands.Bot):
        self.bot = bot_instance

    @commands.hybrid_command(name="bakiye", aliases=["balance", "cuzdan"], description="Bakiyeni (ya da başka birinin bakiyesini) gösterir.")
    @app_commands.describe(member="Bakiyesine bakılacak üye")
    @commands.guild_only()
    async def bakiye_komutu(self, ctx: commands.Context, member: discord.Member = None):
        member = member or ctx.author
        account = self.bot.economy.get(member.id)
        embed = discord.Embed(title="🪙 İmparatorluk Hazinesi", color=discord.Color.gold())
        embed.add_field(name="Kullanıcı", value=member.mention, inline=True)
        embed.add_field(name="Bakiye", value=format_balance(account["balance"]), inline=True)
        if account.get("streak"):
            embed.add_field(name="🔥 Günlük serisi", value=f"{account['streak']} gün", inline=True)
        buffs = []
        if self.bot.economy.has_shield(member.id):
            until = parse_iso(account.get("shield_until"))
            buffs.append(f"🛡️ Kalkan (<t:{int(until.timestamp())}:R>)" if until else "🛡️ Kalkan")
        if self.bot.economy.has_xp_boost(member.id):
            until = parse_iso(account.get("xp_boost_until"))
            buffs.append(f"⚡ XP Boost (<t:{int(until.timestamp())}:R>)" if until else "⚡ XP Boost")
        if buffs:
            embed.add_field(name="Aktif bufflar", value="\n".join(buffs), inline=False)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="seviye", aliases=["level", "rank"], description="Seviye kartını gösterir.")
    @app_commands.describe(member="Seviyesine bakılacak üye")
    @commands.guild_only()
    async def seviye_komutu(self, ctx: commands.Context, member: discord.Member = None):
        member = member or ctx.author
        account = self.bot.economy.get(member.id)
        xp_in_level = account["xp"] % XP_PER_LEVEL
        rank = self.bot.economy.rank_in_guild(ctx.guild, member.id, "xp")
        embed = discord.Embed(title="📈 Seviye Kartı", color=discord.Color.blurple())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Kullanıcı", value=member.mention, inline=True)
        embed.add_field(name="Seviye", value=str(account["level"]), inline=True)
        if rank:
            embed.add_field(name="Sıra", value=f"#{rank}", inline=True)
        embed.add_field(
            name="XP",
            value=f"{progress_bar(xp_in_level, XP_PER_LEVEL)}\n{xp_in_level}/{XP_PER_LEVEL} (toplam: {account['xp']})",
            inline=False,
        )
        next_role_lvl = next((lvl for lvl in sorted(LEVEL_ROLES) if lvl > account["level"]), None)
        if next_role_lvl:
            embed.add_field(name="Sıradaki rol", value=f"Seviye {next_role_lvl}: **{LEVEL_ROLES[next_role_lvl]}**", inline=False)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="gunluk", aliases=["daily"], description="Günlük ödülünü al (üst üste gün alırsan bonus!).")
    async def gunluk_komutu(self, ctx: commands.Context):
        account = self.bot.economy.get(ctx.author.id)
        now = utcnow()
        last = parse_iso(account.get("last_daily"))
        streak = 1
        if last is not None:
            elapsed = now - last
            remaining = timedelta(hours=DAILY_COOLDOWN_HOURS) - elapsed
            if remaining.total_seconds() > 0:
                await ctx.send(f"⏳ Günlük ödülünü zaten aldın! {format_duration(remaining)} sonra tekrar gel.")
                return
            if elapsed < timedelta(hours=DAILY_COOLDOWN_HOURS * 2):
                streak = account.get("streak", 0) + 1

        bonus = DAILY_STREAK_BONUS * (min(streak, DAILY_STREAK_MAX_DAYS) - 1)
        reward = random.randint(DAILY_REWARD_MIN, DAILY_REWARD_MAX) + bonus
        account["balance"] += reward
        account["last_daily"] = now.isoformat()
        account["streak"] = streak
        self.bot.economy.save()
        text = f"🎁 {ctx.author.mention} günlük ödülün: **{format_balance(reward)}**!"
        if bonus:
            text += f" (🔥 {streak}. gün serisi bonusu: +{bonus})"
        await ctx.send(f"{text} Yeni bakiye: {format_balance(account['balance'])}")

    @commands.hybrid_command(name="transfer", aliases=["pay", "gonder"], description="Başka bir üyeye bakiye gönderir.")
    @app_commands.describe(member="Alıcı", miktar="Gönderilecek miktar")
    @commands.guild_only()
    async def transfer_komutu(self, ctx: commands.Context, member: discord.Member, miktar: commands.Range[int, 1, 10_000_000]):
        if member.bot:
            await ctx.send("❌ Botlara para gönderemezsin.")
            return
        if member.id == ctx.author.id:
            await ctx.send("❌ Kendine para gönderemezsin.")
            return
        sender = self.bot.economy.get(ctx.author.id)
        if sender["balance"] < miktar:
            await ctx.send(f"❌ Yetersiz bakiye! Şu an: {format_balance(sender['balance'])}")
            return
        receiver = self.bot.economy.get(member.id)
        sender["balance"] -= miktar
        receiver["balance"] += miktar
        self.bot.economy.save()
        await ctx.send(f"✅ {ctx.author.mention}, {member.mention} kullanıcısına **{format_balance(miktar)}** gönderdi!")

    @commands.hybrid_command(name="market", aliases=["shop", "magaza"], description="İmparatorluk marketindeki eşyaları listeler.")
    async def market_komutu(self, ctx: commands.Context):
        embed = discord.Embed(
            title="🏪 İmparatorluk Marketi",
            description=f"Satın almak için `{COMMAND_PREFIX}satinal <isim>` yaz.",
            color=discord.Color.purple(),
        )
        for key, item in SHOP_ITEMS.items():
            embed.add_field(name=f"{key} — {format_balance(item['fiyat'])}", value=item["aciklama"], inline=False)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="satinal", aliases=["buy"], description="Marketten bir eşya satın alır.")
    @app_commands.describe(item_adi="Eşyanın adı (örn: vip)")
    @commands.guild_only()
    async def satinal_komutu(self, ctx: commands.Context, item_adi: str):
        key = fold_text(item_adi).strip()
        item = SHOP_ITEMS.get(key)
        if not item:
            await ctx.send(f"❌ Böyle bir eşya yok. `{COMMAND_PREFIX}market` ile listeye bakabilirsin.")
            return

        role = None
        if item["rol_adi"]:
            role = discord.utils.get(ctx.guild.roles, name=item["rol_adi"])
            if role is None:
                logger.warning(f"'{item['rol_adi']}' adında market rolü sunucuda bulunamadı.")
                await ctx.send("⚠️ Bu eşyanın rolü sunucuda bulunamadı; yetkililere haber ver. Bakiyenden bir şey düşülmedi.")
                return
            if role in ctx.author.roles:
                await ctx.send("ℹ️ Bu role zaten sahipsin.")
                return

        async with self.bot.economy.lock(ctx.author.id):
            account = self.bot.economy.get(ctx.author.id)
            if account["balance"] < item["fiyat"]:
                await ctx.send(f"❌ Yetersiz bakiye! Gereken: {format_balance(item['fiyat'])}, mevcut: {format_balance(account['balance'])}")
                return
            if role is not None:
                try:
                    await ctx.author.add_roles(role, reason=f"Market satın alma: {key}")
                except discord.HTTPException as e:
                    logger.error(f"Market rolü verilemedi: {e}")
                    await ctx.send("⚠️ Rol verilemedi (botun yetkisini ve rol sırasını kontrol et). Bakiyenden bir şey düşülmedi.")
                    return
            account["balance"] -= item["fiyat"]
            self.bot.economy.save()

        extra = ""
        if key == "kalkan":
            self.bot.economy.set_shield(ctx.author.id, 24)
            extra = " 24 saat boyunca soyguna karşı korunuyorsun!"
        elif key == "boost":
            self.bot.economy.set_xp_boost(ctx.author.id, 12)
            extra = " 12 saat boyunca 1.5x XP kazanacaksın!"
        elif role is None:
            embed = discord.Embed(title="🛒 Market Satın Alma — Teslimat Bekliyor", color=discord.Color.gold())
            embed.add_field(name="Üye", value=ctx.author.mention, inline=True)
            embed.add_field(name="Eşya", value=key, inline=True)
            embed.timestamp = discord.utils.utcnow()
            await self.bot.send_modlog(ctx.guild, embed)
            extra = " Yetkililer seninle iletişime geçecek."
        await ctx.send(f"✅ {ctx.author.mention}, **{key}** satın alındı! Kalan bakiye: {format_balance(account['balance'])}.{extra}")

    @commands.hybrid_command(name="zar", aliases=["dice", "roll"], description="Zar atar.")
    @app_commands.describe(max_sayi="Zarın en yüksek değeri (varsayılan 100)")
    async def zar_komutu(self, ctx: commands.Context, max_sayi: commands.Range[int, 2, 1_000_000] = 100):
        await ctx.send(f"🎲 {ctx.author.mention} zar attı: **{random.randint(1, max_sayi)}** / {max_sayi}")

    @commands.hybrid_command(name="yazitura", aliases=["coinflip"], description="Yazı tura atar.")
    async def yazitura_komutu(self, ctx: commands.Context):
        await ctx.send(f"🪙 {ctx.author.mention}, sonuç: **{random.choice(['Yazı', 'Tura'])}**!")

    @commands.hybrid_command(name="bahis", aliases=["bet"], description="Yazı/tura bahsi: kazanırsan bahsin kadar daha kazanırsın.")
    @app_commands.describe(secim="yazi veya tura", miktar="Bahis miktarı")
    @commands.cooldown(1, 4, commands.BucketType.user)
    async def bahis_komutu(self, ctx: commands.Context, secim: str, miktar: commands.Range[int, 1, BET_MAX]):
        choice = fold_text(secim).strip()
        if choice not in ("yazi", "tura"):
            await ctx.send(f"❌ Seçimin `yazi` ya da `tura` olmalı. Örnek: `{COMMAND_PREFIX}bahis yazi 100`")
            return
        account = self.bot.economy.get(ctx.author.id)
        if account["balance"] < miktar:
            await ctx.send(f"❌ Yetersiz bakiye! Şu an: {format_balance(account['balance'])}")
            return

        result = random.choice(["yazi", "tura"])
        pretty = "Yazı" if result == "yazi" else "Tura"
        if result == choice:
            account["balance"] += miktar
            self.bot.economy.save()
            await ctx.send(f"🎉 {ctx.author.mention} kazandı! Sonuç: **{pretty}**. Kazanç: +{format_balance(miktar)}. Yeni bakiye: {format_balance(account['balance'])}")
        else:
            account["balance"] -= miktar
            self.bot.economy.save()
            await ctx.send(f"💸 {ctx.author.mention} kaybetti! Sonuç: **{pretty}**. Kayıp: -{format_balance(miktar)}. Yeni bakiye: {format_balance(account['balance'])}")

    @commands.hybrid_command(name="siralama", aliases=["leaderboard", "top"], description="Sunucunun zenginlik ya da seviye sıralaması.")
    @app_commands.describe(tur="Neye göre sıralansın?")
    @app_commands.choices(tur=[
        app_commands.Choice(name="Bakiye", value="bakiye"),
        app_commands.Choice(name="Seviye / XP", value="seviye"),
    ])
    @commands.guild_only()
    async def siralama_komutu(self, ctx: commands.Context, tur: str = "bakiye"):
        by_xp = fold_text(tur).strip() in ("seviye", "xp", "level")
        key = "xp" if by_xp else "balance"
        rows = [(uid, acc) for uid, acc in self.bot.economy.data.items() if ctx.guild.get_member(uid)]
        if not rows:
            await ctx.send("Henüz kimsenin bir hesabı yok.")
            return
        rows.sort(key=lambda r: r[1].get(key, 0), reverse=True)
        lines = []
        for i, (uid, acc) in enumerate(rows[:10], start=1):
            member = ctx.guild.get_member(uid)
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"**{i}.**")
            value = f"Seviye {acc.get('level', 0)} • {acc.get('xp', 0)} XP" if by_xp else format_balance(acc.get("balance", 0))
            lines.append(f"{medal} {member.mention} — {value}")
        embed = discord.Embed(
            title="📈 İmparatorluk Seviye Sıralaması" if by_xp else "🏆 İmparatorluk Zenginlik Sıralaması",
            description="\n".join(lines),
            color=discord.Color.gold(),
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="calis", aliases=["work", "çalış"], description="Çalışarak bakiye kazan.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def calis_komutu(self, ctx: commands.Context):
        account = self.bot.economy.get(ctx.author.id)
        last = parse_iso(account.get("last_work"))
        if last is not None:
            remaining = timedelta(seconds=WORK_COOLDOWN_SECONDS) - (utcnow() - last)
            if remaining.total_seconds() > 0:
                await ctx.send(f"⏳ Biraz dinlen! **{format_duration(remaining)}** sonra tekrar çalışabilirsin.")
                return
        job, mult = random.choice(WORK_JOBS)
        reward = max(1, int(random.randint(WORK_REWARD_MIN, WORK_REWARD_MAX) * mult))
        account["balance"] += reward
        account["last_work"] = utcnow().isoformat()
        self.bot.economy.save()
        await ctx.send(f"💼 {ctx.author.mention}, {job} ve **{format_balance(reward)}** kazandın! Bakiye: {format_balance(account['balance'])}")

    @commands.hybrid_command(name="suc", aliases=["crime", "suç"], description="Riskli suç işle — kazanırsan çok, yakalanırsan ceza.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def suc_komutu(self, ctx: commands.Context):
        account = self.bot.economy.get(ctx.author.id)
        last = parse_iso(account.get("last_crime"))
        if last is not None:
            remaining = timedelta(seconds=CRIME_COOLDOWN_SECONDS) - (utcnow() - last)
            if remaining.total_seconds() > 0:
                await ctx.send(f"⏳ Polis hâlâ peşinde! **{format_duration(remaining)}** bekle.")
                return
        action = random.choice(CRIME_ACTIONS)
        account["last_crime"] = utcnow().isoformat()
        if random.random() < CRIME_SUCCESS_CHANCE:
            reward = random.randint(CRIME_REWARD_MIN, CRIME_REWARD_MAX)
            account["balance"] += reward
            self.bot.economy.save()
            await ctx.send(f"🕶️ {ctx.author.mention}, {action}... **Başarılı!** +{format_balance(reward)} | Bakiye: {format_balance(account['balance'])}")
        else:
            fine = min(account["balance"], random.randint(CRIME_FAIL_FINE_MIN, CRIME_FAIL_FINE_MAX))
            account["balance"] -= fine
            self.bot.economy.save()
            await ctx.send(f"🚨 {ctx.author.mention}, {action}... **Yakalandın!** Ceza: -{format_balance(fine)} | Bakiye: {format_balance(account['balance'])}")

    @commands.hybrid_command(name="soy", aliases=["rob", "çal"], description="Başka bir üyeyi soymaya çalış (riskli!).")
    @app_commands.describe(member="Soyulacak üye")
    @commands.guild_only()
    @commands.cooldown(1, 8, commands.BucketType.user)
    async def soy_komutu(self, ctx: commands.Context, member: discord.Member):
        if member.bot or member.id == ctx.author.id:
            await ctx.send("❌ Geçerli bir hedef seç.")
            return
        if is_mod_exempt(member) or is_sovereign_member(member):
            await ctx.send("❌ Bu kişiyi soyamazsın.")
            return
        attacker = self.bot.economy.get(ctx.author.id)
        last = parse_iso(attacker.get("last_rob"))
        if last is not None:
            remaining = timedelta(seconds=ROB_COOLDOWN_SECONDS) - (utcnow() - last)
            if remaining.total_seconds() > 0:
                await ctx.send(f"⏳ Soygun için **{format_duration(remaining)}** beklemen lazım.")
                return
        if self.bot.economy.has_shield(member.id):
            await ctx.send(f"🛡️ {member.display_name} kalkanlı! Soygun başarısız.")
            attacker["last_rob"] = utcnow().isoformat()
            self.bot.economy.save()
            return
        target = self.bot.economy.get(member.id)
        if target["balance"] < ROB_MIN_TARGET_BALANCE:
            await ctx.send(f"❌ {member.display_name} çok fakir, soymaya değmez.")
            return
        attacker["last_rob"] = utcnow().isoformat()
        if random.random() < ROB_SUCCESS_CHANCE:
            stolen = max(1, int(target["balance"] * random.uniform(0.05, ROB_MAX_PERCENT)))
            stolen = min(stolen, target["balance"])
            target["balance"] -= stolen
            attacker["balance"] += stolen
            self.bot.economy.save()
            await ctx.send(f"💰 {ctx.author.mention}, {member.mention} kullanıcısından **{format_balance(stolen)}** çaldı!")
        else:
            fine = min(attacker["balance"], random.randint(20, 80))
            attacker["balance"] -= fine
            self.bot.economy.save()
            await ctx.send(f"🚔 {ctx.author.mention} soygun sırasında yakalandı! Ceza: -{format_balance(fine)}")


async def setup(bot_instance: commands.Bot):
    await bot_instance.add_cog(EconomyCog(bot_instance))
