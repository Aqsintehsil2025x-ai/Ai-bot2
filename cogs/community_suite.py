"""Per-server community analytics, FAQ knowledge base, and anti-raid alerts.

This cog deliberately observes raid-like join bursts without automatically
punishing members. Moderators decide what action, if any, is appropriate.
"""
from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timezone
from difflib import SequenceMatcher
import re

import discord
from discord import app_commands
from discord.ext import commands


def _day_key() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _normalise(value: str) -> str:
    return re.sub(r"\s+", " ", value.casefold()).strip()


class CommunitySuite(commands.Cog):
    """Small, persistent community tools built on the bot's existing guild store."""

    kb = app_commands.Group(name="kb", description="Sunucu FAQ bilgi tabanını yönetir.")
    antiraid = app_commands.Group(name="antiraid", description="Şüpheli katılım artışları için uyarı sistemi.")

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._join_windows: dict[int, deque[float]] = defaultdict(deque)
        self._raid_alert_at: dict[int, float] = {}

    def _stats(self, guild_id: int) -> dict:
        raw = self.bot.settings.value(guild_id, "community_analytics", {})
        if not isinstance(raw, dict):
            raw = {}
        days = raw.setdefault("days", {})
        if not isinstance(days, dict):
            raw["days"] = {}
        return raw

    def _mark_stats(self, guild_id: int, stats: dict) -> None:
        stats["days"] = dict(sorted(stats["days"].items())[-30:])
        self.bot.settings.set(guild_id, "community_analytics", stats)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.guild is None or message.author.bot:
            return
        stats = self._stats(message.guild.id)
        day = stats["days"].setdefault(_day_key(), {"messages": 0, "joins": 0, "users": {}})
        day["messages"] = int(day.get("messages", 0)) + 1
        users = day.setdefault("users", {})
        key = str(message.author.id)
        users[key] = int(users.get(key, 0)) + 1
        self._mark_stats(message.guild.id, stats)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        if member.bot:
            return
        stats = self._stats(member.guild.id)
        day = stats["days"].setdefault(_day_key(), {"messages": 0, "joins": 0, "users": {}})
        day["joins"] = int(day.get("joins", 0)) + 1
        self._mark_stats(member.guild.id, stats)

        config = self.bot.settings.value(member.guild.id, "anti_raid", {})
        if not isinstance(config, dict) or not config.get("enabled", False):
            return
        now = __import__("time").monotonic()
        window = self._join_windows[member.guild.id]
        window.append(now)
        while window and now - window[0] > 60:
            window.popleft()
        threshold = max(3, min(30, int(config.get("threshold", 6))))
        if len(window) < threshold or now - self._raid_alert_at.get(member.guild.id, 0) < 60:
            return
        self._raid_alert_at[member.guild.id] = now
        embed = discord.Embed(
            title="⚠️ Şüpheli katılım artışı",
            description=(
                f"Son 60 saniyede **{len(window)}** yeni üye katıldı. "
                "Bu yalnızca bir uyarıdır; otomatik ceza uygulanmadı."
            ),
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(name="Sunucu", value=member.guild.name, inline=True)
        embed.add_field(name="Eşik", value=str(threshold), inline=True)
        try:
            await self.bot.send_modlog(member.guild, embed)
        except Exception:
            # Analytics must never interrupt member-join processing.
            pass

    @app_commands.command(name="analytics", description="Sunucunun son 7 günlük aktivite özetini gösterir.")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def analytics(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("Bu komut yalnızca sunucuda kullanılabilir.", ephemeral=True)
            return
        stats = self._stats(guild.id)
        days = stats.get("days", {})
        recent = sorted(days.items())[-7:]
        messages = sum(int(value.get("messages", 0)) for _, value in recent)
        joins = sum(int(value.get("joins", 0)) for _, value in recent)
        users: dict[str, int] = {}
        for _, value in recent:
            for user_id, count in value.get("users", {}).items():
                users[user_id] = users.get(user_id, 0) + int(count)
        top = sorted(users.items(), key=lambda item: item[1], reverse=True)[:5]
        top_text = "\n".join(
            f"<@{user_id}> — **{count}** mesaj" for user_id, count in top
        ) or "Henüz yeterli veri yok."
        embed = discord.Embed(
            title=f"📊 {guild.name} — Aktivite",
            color=discord.Color.blurple(),
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(name="Son 7 gün mesaj", value=f"**{messages:,}**", inline=True)
        embed.add_field(name="Son 7 gün katılım", value=f"**{joins:,}**", inline=True)
        embed.add_field(name="Toplam üye", value=f"**{guild.member_count or 0:,}**", inline=True)
        embed.add_field(name="En aktif üyeler", value=top_text, inline=False)
        embed.set_footer(text="Veriler botun çalıştığı andan itibaren toplanır; geçmişe dönük değildir.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @kb.command(name="add", description="FAQ bilgi tabanına soru ve yanıt ekler.")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(question="Sık sorulan soru", answer="Kısa ve doğrulanmış yanıt")
    async def kb_add(self, interaction: discord.Interaction, question: str, answer: str) -> None:
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("Bu komut yalnızca sunucuda kullanılabilir.", ephemeral=True)
            return
        question, answer = question.strip(), answer.strip()
        if not question or len(question) > 180 or not answer or len(answer) > 1500:
            await interaction.response.send_message(
                "Soru 1–180, yanıt 1–1500 karakter olmalıdır.", ephemeral=True
            )
            return
        entries = self.bot.settings.value(guild.id, "knowledge_base", [])
        if not isinstance(entries, list):
            entries = []
        normal = _normalise(question)
        for entry in entries:
            if _normalise(str(entry.get("question", ""))) == normal:
                entry["question"], entry["answer"] = question, answer
                self.bot.settings.set(guild.id, "knowledge_base", entries)
                await interaction.response.send_message("Mevcut FAQ kaydı güncellendi.", ephemeral=True)
                return
        if len(entries) >= 100:
            await interaction.response.send_message("Bilgi tabanı 100 kayıt sınırına ulaştı.", ephemeral=True)
            return
        entries.append({"question": question, "answer": answer})
        self.bot.settings.set(guild.id, "knowledge_base", entries)
        await interaction.response.send_message("FAQ kaydı eklendi.", ephemeral=True)

    @kb.command(name="ask", description="Sunucu bilgi tabanında yanıt arar.")
    @app_commands.describe(query="Yanıtını aradığın soru")
    async def kb_ask(self, interaction: discord.Interaction, query: str) -> None:
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("Bu komut yalnızca sunucuda kullanılabilir.", ephemeral=True)
            return
        entries = self.bot.settings.value(guild.id, "knowledge_base", [])
        if not isinstance(entries, list) or not entries:
            await interaction.response.send_message("Bu sunucunun FAQ bilgi tabanı henüz boş.", ephemeral=True)
            return
        needle = _normalise(query)
        ranked = sorted(
            (
                (SequenceMatcher(None, needle, _normalise(str(entry.get("question", "")))).ratio(), entry)
                for entry in entries
                if isinstance(entry, dict) and entry.get("question") and entry.get("answer")
            ),
            key=lambda item: item[0],
            reverse=True,
        )
        if not ranked or ranked[0][0] < 0.48:
            await interaction.response.send_message(
                "Bilgi tabanında buna uygun bir yanıt bulamadım. Bir moderatör /kb add ile ekleyebilir.",
                ephemeral=True,
            )
            return
        score, entry = ranked[0]
        embed = discord.Embed(
            title=str(entry["question"])[:256],
            description=str(entry["answer"])[:4000],
            color=discord.Color.teal(),
        )
        embed.set_footer(text=f"Sunucu FAQ • Eşleşme %{round(score * 100)}")
        await interaction.response.send_message(embed=embed)

    @kb.command(name="list", description="Bilgi tabanındaki soruları listeler.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def kb_list(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("Bu komut yalnızca sunucuda kullanılabilir.", ephemeral=True)
            return
        entries = self.bot.settings.value(guild.id, "knowledge_base", [])
        lines = [f"• {str(item.get('question', ''))[:160]}" for item in entries[:25] if isinstance(item, dict)]
        await interaction.response.send_message(
            "\n".join(lines) if lines else "Bilgi tabanı boş.",
            ephemeral=True,
        )

    @kb.command(name="remove", description="FAQ kaydını soru metnine göre siler.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def kb_remove(self, interaction: discord.Interaction, question: str) -> None:
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("Bu komut yalnızca sunucuda kullanılabilir.", ephemeral=True)
            return
        entries = self.bot.settings.value(guild.id, "knowledge_base", [])
        target = _normalise(question)
        updated = [item for item in entries if not (
            isinstance(item, dict) and _normalise(str(item.get("question", ""))) == target
        )]
        if len(updated) == len(entries):
            await interaction.response.send_message("Bu soru için kayıt bulunamadı.", ephemeral=True)
            return
        self.bot.settings.set(guild.id, "knowledge_base", updated)
        await interaction.response.send_message("FAQ kaydı silindi.", ephemeral=True)

    @antiraid.command(name="set", description="Katılım artışı uyarılarını açar veya kapatır.")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(enabled="Uyarıları aç/kapat", threshold="60 saniyede kaç yeni üye olunca uyarı verilsin (3–30)")
    async def antiraid_set(
        self,
        interaction: discord.Interaction,
        enabled: bool,
        threshold: app_commands.Range[int, 3, 30] = 6,
    ) -> None:
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("Bu komut yalnızca sunucuda kullanılabilir.", ephemeral=True)
            return
        self.bot.settings.set(guild.id, "anti_raid", {"enabled": enabled, "threshold": int(threshold)})
        status = "açık" if enabled else "kapalı"
        await interaction.response.send_message(
            f"Katılım artışı uyarıları **{status}**. Eşik: **{threshold}** üye / 60 saniye. "
            "Bu sistem yalnızca moderatörlere uyarı gönderir; otomatik ceza vermez.",
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CommunitySuite(bot))
