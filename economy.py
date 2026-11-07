# ==============================================================================
# COGS — EKONOMİ MODÜLÜ (Örnek)
# Bu dosya, tek dosyalık xyrin_bot.py'deki ekonomi komutlarını
# ayrı bir cog olarak ayırmanın nasıl yapılacağını gösterir.
# Tam geçiş yaparken xyrin_bot.py'deki ilgili komutları buraya taşıyıp,
# @bot.hybrid_command yerine @commands.hybrid_command kullanın.
# ==============================================================================

import discord
from discord import app_commands
from discord.ext import commands


class EconomyCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="bakiye", aliases=["balance", "cuzdan"], description="Bakiyeni gösterir.")
    @app_commands.describe(member="Bakiyesine bakılacak üye")
    @commands.guild_only()
    async def bakiye(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        # Gerçek mantık xyrin_bot.py'deki EconomyManager'dan çekilir.
        await ctx.send(f"🪙 {member.mention} bakiye komutu (cogs yapısı örneği).")

    @commands.hybrid_command(name="seviye", aliases=["level", "rank"], description="Seviye kartını gösterir.")
    @app_commands.describe(member="Seviyesine bakılacak üye")
    @commands.guild_only()
    async def seviye(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        await ctx.send(f"📈 {member.mention} seviye komutu (cogs yapısı örneği).")


async def setup(bot: commands.Bot):
    await bot.add_cog(EconomyCog(bot))