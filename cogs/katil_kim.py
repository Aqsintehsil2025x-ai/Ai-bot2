"""Turkish, DM-driven Katil Kim? party game cog.

All actions are fictional game mechanics. Game state is in-memory and scoped to
the guild/channel; no game data is written to the bot's economy or moderation stores.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

import discord
from discord import app_commands
from discord.ext import commands


MIN_PLAYERS = 4
MAX_PLAYERS = 12
LOBBY_TIMEOUT = 180
ACTION_TIMEOUT = 120
VOTE_TIMEOUT = 90


@dataclass
class Game:
    guild_id: int
    channel_id: int
    host_id: int
    players: dict[int, discord.Member] = field(default_factory=dict)
    roles: dict[int, str] = field(default_factory=dict)
    actions: dict[str, int] = field(default_factory=dict)
    votes: dict[int, int] = field(default_factory=dict)
    message: discord.Message | None = None
    phase: str = "lobby"


class ActionSelect(discord.ui.Select):
    def __init__(self, game: Game, action: str, candidates: list[discord.Member]):
        self.game = game
        self.action = action
        labels = {
            "kill": "Hedef seç",
            "investigate": "Şüpheliyi sorgula",
            "protect": "Korumak istediğin kişiyi seç",
        }
        options = [
            discord.SelectOption(label=m.display_name[:100], value=str(m.id))
            for m in candidates
        ]
        super().__init__(
            placeholder=labels[action],
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id not in self.game.players:
            await interaction.response.send_message("Bu oyun sana ait değil.", ephemeral=True)
            return
        self.game.actions[self.action] = int(self.values[0])
        await interaction.response.send_message(
            "✅ Seçimin gizlice kaydedildi. Oyun kanalındaki sonucu bekle.",
            ephemeral=True,
        )
        await try_resolve_night(self.game)


class ActionView(discord.ui.View):
    def __init__(self, game: Game, action: str, candidates: list[discord.Member]):
        super().__init__(timeout=ACTION_TIMEOUT)
        self.add_item(ActionSelect(game, action, candidates))


class VoteSelect(discord.ui.Select):
    def __init__(self, game: Game, candidates: list[discord.Member]):
        self.game = game
        super().__init__(
            placeholder="Şüphelendiğin oyuncuyu seç",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(label=m.display_name[:100], value=str(m.id))
                for m in candidates
            ],
        )

    async def callback(self, interaction: discord.Interaction):
        uid = interaction.user.id
        if uid not in self.game.players or uid not in self.game.roles:
            await interaction.response.send_message("Bu oylamaya katılamazsın.", ephemeral=True)
            return
        if self.game.roles.get(uid) == "elenen":
            await interaction.response.send_message("Oyundan elendin; oy kullanamazsın.", ephemeral=True)
            return
        self.game.votes[uid] = int(self.values[0])
        await interaction.response.send_message("🗳️ Oyun gizli olarak kaydedildi.", ephemeral=True)
        if len(self.game.votes) >= len(self.game.roles) - 1:
            await resolve_vote(self.game)


class VoteView(discord.ui.View):
    def __init__(self, game: Game, candidates: list[discord.Member]):
        super().__init__(timeout=VOTE_TIMEOUT)
        self.add_item(VoteSelect(game, candidates))

    async def on_timeout(self):
        await resolve_vote(self.game) if hasattr(self, "game") else None


class LobbyView(discord.ui.View):
    def __init__(self, cog: "KatilKim", game: Game):
        super().__init__(timeout=LOBBY_TIMEOUT)
        self.cog = cog
        self.game = game

    @discord.ui.button(label="🎮 Katıl", style=discord.ButtonStyle.success)
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.game.phase != "lobby":
            await interaction.response.send_message("Kayıt süresi sona erdi.", ephemeral=True)
            return
        if interaction.user.bot:
            await interaction.response.send_message("Botlar oyuna katılamaz.", ephemeral=True)
            return
        if interaction.user.id in self.game.players:
            await interaction.response.send_message("Zaten katıldın!", ephemeral=True)
            return
        if len(self.game.players) >= MAX_PLAYERS:
            await interaction.response.send_message("Oyun dolu.", ephemeral=True)
            return
        member = interaction.user
        if not isinstance(member, discord.Member):
            await interaction.response.send_message("Bu oyun yalnızca sunucuda oynanabilir.", ephemeral=True)
            return
        self.game.players[member.id] = member
        await interaction.response.send_message("✅ Oyuna katıldın!", ephemeral=True)
        await self.cog.refresh_lobby(self.game)

    @discord.ui.button(label="🚀 Oyunu Başlat", style=discord.ButtonStyle.primary)
    async def start(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.game.host_id:
            await interaction.response.send_message("Oyunu yalnızca başlatan kişi başlatabilir.", ephemeral=True)
            return
        if len(self.game.players) < MIN_PLAYERS:
            await interaction.response.send_message(
                f"Başlamak için en az {MIN_PLAYERS} oyuncu gerekli. Şu an: {len(self.game.players)}",
                ephemeral=True,
            )
            return
        await interaction.response.defer(ephemeral=True)
        ok, reason = await self.cog.start_game(self.game)
        if not ok:
            await interaction.followup.send(reason, ephemeral=True)
        else:
            self.stop()

    @discord.ui.button(label="✖️ İptal", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.game.host_id:
            await interaction.response.send_message("Oyunu yalnızca başlatan kişi iptal edebilir.", ephemeral=True)
            return
        self.game.phase = "finished"
        self.cog.games.pop((self.game.guild_id, self.game.channel_id), None)
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content="❌ Oyun iptal edildi.", view=self)


class KatilKim(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.games: dict[tuple[int, int], Game] = {}

    async def refresh_lobby(self, game: Game):
        if not game.message:
            return
        names = "\n".join(f"• {m.display_name}" for m in game.players.values()) or "Henüz kimse katılmadı."
        embed = discord.Embed(
            title="🕵️ KATİL KİM? — Oyuncu Lobisi",
            description=f"**Oyuncular ({len(game.players)}/{MAX_PLAYERS})**\n{names}\n\n"
                        f"En az {MIN_PLAYERS} oyuncu gerekli. Katılmak için düğmeye bas!",
            color=discord.Color.dark_purple(),
        )
        embed.set_footer(text="Roller oyun başlayınca DM üzerinden gizlice gönderilir.")
        try:
            await game.message.edit(embed=embed)
        except discord.HTTPException:
            pass

    async def start_game(self, game: Game) -> tuple[bool, str]:
        game.phase = "assigning"
        players = list(game.players.values())
        roles = ["Katil", "Dedektif", "Şerif"] + ["Masum"] * (len(players) - 3)
        random.shuffle(roles)
        game.roles = {m.id: role for m, role in zip(players, roles)}

        # Önce bütün DM'leri test et; hiç kimseye rol açıklanmadan hata varsa oyunu iptal et.
        try:
            for member in players:
                await member.send(
                    "🎭 **KATİL KİM? — Gizli rolün**\n"
                    "Rollerin oyun başlayınca bu DM'de açıklanacak. Bu mesajı başkalarıyla paylaşma."
                )
        except discord.Forbidden:
            game.phase = "lobby"
            return False, "❌ En az bir oyuncunun DM'si kapalıdır. Herkes sunucu üyelerinden DM almayı açsın ve tekrar dene."
        except discord.HTTPException:
            game.phase = "lobby"
            return False, "❌ DM gönderilemedi. Biraz sonra tekrar dene."

        game.phase = "night"
        candidates = players
        role_map = {m.id: game.roles[m.id] for m in players}
        for member in players:
            role = role_map[member.id]
            intro = {
                "Katil": "🔪 **KATİL**\nGizlice hedefini seç. Amacın yakalanmadan kalmak.",
                "Dedektif": "🔎 **DEDEKTİF**\nBir oyuncuyu sorgula. Sana onun Katil olup olmadığı söylenecek.",
                "Şerif": "🛡️ **ŞERİF**\nBir oyuncuyu koru. Katilin hedefi o kişiyse gece elenmez.",
                "Masum": "👤 **MASUM**\nDikkatli ol, ipuçlarını değerlendir ve oylamada katili bul.",
            }[role]
            try:
                if role in ("Katil", "Dedektif", "Şerif"):
                    action = {"Katil": "kill", "Dedektif": "investigate", "Şerif": "protect"}[role]
                    view = ActionView(game, action, [m for m in candidates if m.id != member.id])
                    await member.send(intro, view=view)
                else:
                    await member.send(intro)
            except discord.HTTPException:
                # Preflight DM was successful; temporary failures are reported and game remains playable.
                pass

        channel = self.bot.get_channel(game.channel_id)
        if channel:
            await channel.send(
                "🌙 **Gece başladı!** Herkes rolüne ait seçimi DM'den yapsın. "
                "Katil, Dedektif ve Şerif seçimlerini gizlice gönderir."
            )
        return True, "Oyun başladı."

    @app_commands.command(name="katilkim", description="Türkçe Katil Kim? oyununu başlatır.")
    async def katilkim(self, interaction: discord.Interaction):
        if not interaction.guild or not interaction.channel:
            await interaction.response.send_message("Bu komut yalnızca sunucuda kullanılabilir.", ephemeral=True)
            return
        key = (interaction.guild.id, interaction.channel.id)
        current = self.games.get(key)
        if current and current.phase != "finished":
            await interaction.response.send_message("Bu kanalda zaten aktif bir oyun var.", ephemeral=True)
            return
        game = Game(interaction.guild.id, interaction.channel.id, interaction.user.id)
        if isinstance(interaction.user, discord.Member):
            game.players[interaction.user.id] = interaction.user
        self.games[key] = game
        embed = discord.Embed(
            title="🕵️ KATİL KİM? — Oyuncu Lobisi",
            description=f"**Oyuncular (1/{MAX_PLAYERS})**\n• {interaction.user.display_name}\n\n"
                        f"En az {MIN_PLAYERS} oyuncu gerekli. Katılmak için düğmeye bas!",
            color=discord.Color.dark_purple(),
        )
        embed.add_field(name="🎭 Roller", value="Katil • Dedektif • Şerif • Masumlar", inline=False)
        embed.set_footer(text="Gizli roller DM ile gönderilir • Lobi 3 dakika açık")
        view = LobbyView(self, game)
        await interaction.response.send_message(embed=embed, view=view)
        game.message = await interaction.original_response()

    async def cog_unload(self):
        self.games.clear()


async def try_resolve_night(game: Game):
    required = {"kill", "investigate", "protect"}
    if game.phase != "night" or not required.issubset(game.actions):
        return
    game.phase = "discussion"
    killer_id = next((uid for uid, role in game.roles.items() if role == "Katil"), None)
    detective_id = next((uid for uid, role in game.roles.items() if role == "Dedektif"), None)
    target_id = game.actions["kill"]
    protected_id = game.actions["protect"]
    detective = game.players.get(detective_id)
    if detective:
        is_killer = game.roles.get(game.actions["investigate"]) == "Katil"
        try:
            await detective.send(
                "🔎 Sorgu sonucu: **Bu oyuncu Katil.**" if is_killer
                else "🔎 Sorgu sonucu: **Bu oyuncu Katil değil.**"
            )
        except discord.HTTPException:
            pass
    channel = game.players[next(iter(game.players))].guild.get_channel(game.channel_id)
    if channel:
        if target_id == protected_id:
            await channel.send("🌅 **Sabah oldu!** Şerif doğru kişiyi korudu. Bu gece kimse elenmedi.")
        else:
            game.roles[target_id] = "elenen"
            await channel.send(
                f"🌅 **Sabah oldu!** {game.players[target_id].display_name} bu tur oyundan elendi. "
                "Şimdi tartışma ve gizli oylama zamanı."
            )
        alive = [m for uid, m in game.players.items() if game.roles.get(uid) != "elenen"]
        if killer_id not in [m.id for m in alive]:
            await finish_game(game, "🎉 Masumlar kazandı! Katil elendi.")
            return
        await channel.send(
            "🗳️ **Oylama başladı!** Herkes DM'deki bağlantı yerine aşağıdaki menüden şüphelendiği kişiyi seçsin."
        )
        view = VoteView(game, alive)
        view.game = game
        await channel.send("Gizli oyunu kullan:", view=view)


async def resolve_vote(game: Game):
    if game.phase != "discussion":
        return
    game.phase = "voting_done"
    alive = [uid for uid, role in game.roles.items() if role != "elenen"]
    votes = [target for voter, target in game.votes.items() if voter in alive and target in alive]
    channel = game.players[next(iter(game.players))].guild.get_channel(game.channel_id)
    if not votes:
        if channel:
            await channel.send("⏰ Oylama tamamlanamadı. Kimse elenmedi.")
        await finish_game(game, "🔪 Katil bu tur yakalanmadı. Katil kazandı!")
        return
    counts = {uid: votes.count(uid) for uid in set(votes)}
    highest = max(counts.values())
    winners = [uid for uid, count in counts.items() if count == highest]
    if len(winners) == 1 and game.roles.get(winners[0]) == "Katil":
        await finish_game(game, "🎉 Masumlar kazandı! Oylamada Katil bulundu.")
    elif len(winners) == 1:
        game.roles[winners[0]] = "elenen"
        await finish_game(game, "🔪 Yanlış kişi seçildi. Katil bu tur hayatta kaldı ve kazandı.")
    else:
        await finish_game(game, "⚖️ Oylama berabere kaldı. Katil kazandı.")


async def finish_game(game: Game, result: str):
    game.phase = "finished"
    channel = game.players[next(iter(game.players))].guild.get_channel(game.channel_id)
    killer = next((uid for uid, role in game.roles.items() if role == "Katil"), None)
    if channel:
        roles = "\n".join(
            f"• {member.display_name}: **{('Katil' if uid == killer else role)}**"
            for uid, member in game.players.items()
        )
        embed = discord.Embed(title="🎭 Oyun Bitti!", description=result, color=discord.Color.gold())
        embed.add_field(name="Gizli roller", value=roles[:1024], inline=False)
        await channel.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(KatilKim(bot))
