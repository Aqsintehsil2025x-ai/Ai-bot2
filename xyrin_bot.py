# ==============================================================================
# DISCORD AI & IMPERIAL ECOSYSTEM BOT - ULTIMATE VISION & HOLOGRAM EDITION
# ==============================================================================
# Xyrin İmparatorluğu Core v4.9 - Kararlı ve Optimize Edilmiş Sürüm
# ==============================================================================

import os
import sys
import time
import io
import json
import random
import asyncio
import logging
import traceback
import re
import contextlib
from datetime import datetime, timedelta
import aiohttp
import discord
from discord.ext import commands, tasks
import google.generativeai as genai

# --- 1. GELİŞMİŞ LOGLAMA VE SİSTEM ÇEKİRDEĞİ YAPILANDIRMASI ---
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("imperial_core.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("XyrinImperialCore")

# --- 2. ÇEVRESEL DEĞİŞKENLER VE GÜVENLİK ---
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "BURAYA_DISCORD_BOT_TOKENINI_YAZ")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "BURAYA_GEMINI_API_KEYINI_YAZ")

# Hükümdarlar, Kral ve Kraliçe Tanımlamaları
SOVEREIGN_USERNAMES = {"endercosmic1", "melikhan111"}
KING_USERNAMES = {"swaarex"}
QUEEN_USERNAMES = {"zifona"}

# --- SPAM & LİNK FİLTRESİ AYARLARI ---
SPAM_WINDOW_SECONDS = 7
SPAM_MESSAGE_LIMIT = 6

# --- EKONOMİ & SEVİYE SİSTEMİ AYARLARI ---
ECONOMY_FILE = "economy_data.json"
STARTING_BALANCE = 100
DAILY_REWARD_MIN = 100
DAILY_REWARD_MAX = 250
DAILY_COOLDOWN_HOURS = 24
XP_PER_MESSAGE_MIN = 5
XP_PER_MESSAGE_MAX = 15
XP_MESSAGE_COOLDOWN_SECONDS = 60  
XP_PER_LEVEL = 150  

LEVEL_ROLES = {5: "Vasal", 15: "Lord", 30: "Asil Lord"}

SHOP_ITEMS = {
    "vip": {"fiyat": 1000, "aciklama": "VIP rolü ve özel renk.", "rol_adi": "VIP"},
    "reklam": {"fiyat": 300, "aciklama": "24 saat boyunca #Booster kanalında sabitlenmiş reklamın.", "rol_adi": None},
}

WELCOME_CHANNEL_ID = int(os.getenv("WELCOME_CHANNEL_ID", "0"))
WELCOME_ROLE_NAME = os.getenv("WELCOME_ROLE_NAME", "")  

INVITE_LINK_PATTERN = re.compile(r"(discord\.gg/|discord(app)?\.com/invite/)", re.IGNORECASE)
GENERIC_LINK_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)
BLOCK_ALL_LINKS = os.getenv("BLOCK_ALL_LINKS", "false").lower() == "true"

BOT_OWNER_ID = int(os.getenv("BOT_OWNER_ID", "0"))

if DISCORD_TOKEN == "BURAYA_DISCORD_BOT_TOKENINI_YAZ" or not DISCORD_TOKEN:
    logger.warning("Discord Token tanımlanmamış!")

if GEMINI_API_KEY == "BURAYA_GEMINI_API_KEYINI_YAZ" or not GEMINI_API_KEY:
    logger.warning("Gemini API Key tanımlanmamış!")

genai.configure(api_key=GEMINI_API_KEY)

generation_config = {
    "temperature": 0.85,
    "top_p": 0.95,
    "max_output_tokens": 2048,
}

SYSTEM_INSTRUCTION = (
    "Sen Xyrin İmparatorluğu'nun en gelişmiş yapay zeka asistanısın. "
    "Sana imparatorluğun hakimleri, hükümdarları veya kadrosu sorulduğunda SADECE ve EKSİKSİZ olarak şu hiyerarşiyi isimleriyle listelersin:\n"
    "1. Yüce Hükümdarlar: 'endercosmic1' ve 'melikhan111'\n"
    "2. İmparatorluğun Kralı: 'swaarex'\n"
    "3. İmparatorluğun Kraliçesi: 'zifona' (Hükümdar endercosmic1'in sevgilisidir)\n"
    "Hükümdarlarımıza, Kralımıza ve Kraliçemize her zaman 'Hükümdarım', 'Kralım' veya 'Kraliçem' şeklinde hürmetkar hitap edersin. "
    "Sıradan kullanıcılara karşı ise kibar bir AI gibi davranır, asla onlara bu unvanlarla hitap etmez ve onların kanal/rol oluşturma isteklerini yerine getirmezsin. "
    "Eğer Yüce Hükümdarlarımızdan biri senden bir kanal veya rol oluşturmanı isterse, yanıtının en sonuna `[CREATE_CHANNEL: kanal-adi]` veya `[CREATE_ROLE: rol-adi]` eklersin."
)

try:
    model = genai.GenerativeModel(
        model_name="gemini-3.5-flash-lite",
        generation_config=generation_config,
        system_instruction=SYSTEM_INSTRUCTION
    )
    logger.info("Gemini modeli başarıyla yüklendi.")
except Exception as e:
    logger.error(f"Gemini modeli yüklenirken hata: {e}")
    model = None

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.voice_states = True

class UltimateImperialBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents, help_command=None)
        self.scheduled_events = []
        self.chat_sessions = {}
        self.message_counter = 0
        self.active_holograms = {}  
        self.coffee_orders = []     
        self.recent_messages = {}   
        self.economy = self._load_economy()  
        self.last_xp_time = {}      

    def _load_economy(self):
        if os.path.exists(ECONOMY_FILE):
            try:
                with open(ECONOMY_FILE, "r", encoding="utf-8") as f:
                    return {int(k): v for k, v in json.load(f).items()}
            except Exception as e:
                logger.error(f"Ekonomi dosyası okunamadı: {e}")
        return {}

    def _save_economy(self):
        try:
            with open(ECONOMY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.economy, f)
        except Exception as e:
            logger.error(f"Ekonomi dosyası kaydedilemedi: {e}")

    def get_account(self, user_id: int) -> dict:
        if user_id not in self.economy:
            self.economy[user_id] = {
                "balance": STARTING_BALANCE,
                "xp": 0,
                "level": 0,
                "last_daily": None
            }
        return self.economy[user_id]

    async def setup_hook(self):
        logger.info("İmparatorluk alt sistemleri başlatılıyor...")
        self.check_events_loop.start()
        self.server_stats_loop.start()
        self.hologram_pulse_loop.start()
        try:
            synced = await self.tree.sync()
            logger.info(f"{len(synced)} slash komutu senkronize edildi.")
        except Exception as e:
            logger.error(f"Slash komutları senkronize edilemedi: {e}")

    async def on_ready(self):
        logger.info(f"İmparatorluk Botu Çevrimiçi: {self.user} (ID: {self.user.id})")
        await self.change_presence(activity=discord.Activity(
            type=discord.ActivityType.playing,
            name="!yardim | Hükümdar, Kral ve Kraliçe Protokolü Aktif ☕✨"
        ))

    def get_or_create_chat(self, channel_id):
        if channel_id not in self.chat_sessions:
            if model:
                self.chat_sessions[channel_id] = model.start_chat(history=[])
            else:
                return None
        return self.chat_sessions[channel_id]

    @tasks.loop(seconds=30)
    async def check_events_loop(self):
        pass

    @tasks.loop(hours=24)
    async def server_stats_loop(self):
        for guild in self.guilds:
            logger.info(f"İmparatorluk Raporu [{guild.name}]: Üye={guild.member_count}")

    @tasks.loop(seconds=10)
    async def hologram_pulse_loop(self):
        for guild_id, holo_data in list(self.active_holograms.items()):
            holo_data["frames_rendered"] += 1

bot = UltimateImperialBot()

def is_privileged_member(member_or_author) -> bool:
    name = (member_or_author.name or "").lower()
    return name in SOVEREIGN_USERNAMES or name in KING_USERNAMES or name in QUEEN_USERNAMES

def is_spamming(bot_instance, user_id: int) -> bool:
    now = time.time()
    timestamps = bot_instance.recent_messages.setdefault(user_id, [])
    timestamps.append(now)
    cutoff = now - SPAM_WINDOW_SECONDS
    while timestamps and timestamps[0] < cutoff:
        timestamps.pop(0)
    return len(timestamps) > SPAM_MESSAGE_LIMIT

async def award_xp(member: discord.Member):
    if member.bot:
        return
    now = time.time()
    last = bot.last_xp_time.get(member.id, 0)
    if now - last < XP_MESSAGE_COOLDOWN_SECONDS:
        return
    bot.last_xp_time[member.id] = now

    account = bot.get_account(member.id)
    gained = random.randint(XP_PER_MESSAGE_MIN, XP_PER_MESSAGE_MAX)
    account["xp"] += gained
    new_level = account["xp"] // XP_PER_LEVEL

    if new_level > account["level"]:
        old_level = account["level"]
        account["level"] = new_level
        bot._save_economy()
        for lvl in range(old_level + 1, new_level + 1):
            role_name = LEVEL_ROLES.get(lvl)
            if role_name:
                role = discord.utils.get(member.guild.roles, name=role_name)
                if role:
                    try:
                        await member.add_roles(role)
                    except Exception:
                        pass
    else:
        bot._save_economy()

def format_balance(amount: int) -> str:
    return f"{amount:,} 🪙".replace(",", ".")

async def check_link_violation(message: discord.Message) -> bool:
    content = message.content or ""
    is_violation = bool(INVITE_LINK_PATTERN.search(content))
    if not is_violation and BLOCK_ALL_LINKS:
        is_violation = bool(GENERIC_LINK_PATTERN.search(content))
    if not is_violation:
        return False
    try:
        await message.delete()
    except Exception:
        pass
    return True

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    bot.message_counter += 1

    if message.guild and not is_privileged_member(message.author) and not message.author.bot:
        if is_spamming(bot, message.author.id):
            try:
                await message.delete()
            except Exception:
                pass
            return

        if not message.author.guild_permissions.administrator:
            link_silindi = await check_link_violation(message)
            if link_silindi:
                return

        await award_xp(message.author)

    if bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
        clean_content = message.content.replace(f'<@!{bot.user.id}>', '').replace(f'<@{bot.user.id}>', '').strip()
        is_privileged = is_privileged_member(message.author)

        if model:
            try:
                async with message.channel.typing():
                    role_context = (
                        "[SİSTEM BİLGİSİ]: Karşındaki kişi Yüce Hükümdar, Kral veya Kraliçemizdir. Onlara saray protokolüne uygun şekilde hitap et.\n"
                    ) if is_privileged else (
                        f"[SİSTEM BİLGİSİ]: Karşındaki kişi sıradan bir kullanıcıdır ({message.author.name}).\n"
                    )

                    chat_session = bot.get_or_create_chat(message.channel.id)
                    if chat_session and clean_content:
                        # Ağır engellemeyi önlemek için ayrı thread'de çalıştırıyoruz
                        response = await asyncio.to_thread(chat_session.send_message, role_context + clean_content)
                        reply_text = response.text
                    else:
                        reply_text = "Emrinizdeyim!"

                    if "[CREATE_CHANNEL:" in reply_text and message.author.name.lower() in SOVEREIGN_USERNAMES:
                        match = re.search(r'\[CREATE_CHANNEL:\s*([^\]]+)\]', reply_text)
                        if match and message.guild:
                            c_name = match.group(1).strip().lower().replace(" ", "-")
                            reply_text = reply_text.replace(match.group(0), "").strip()
                            yeni_kanal = await message.guild.create_text_channel(c_name)
                            reply_text += f"\n\n✨ *(#{yeni_kanal.name} kanalı oluşturuldu!)*"

                    await message.reply(reply_text)
                    return

            except Exception as e:
                logger.error(f"AI Hatası: {e}")
                await message.reply("⚠️ Sinir ağlarında dalgalanma oluştu.")
                return

    await bot.process_commands(message)

# --- İMPARATORLUK KOMUTLARI ---
@bot.hybrid_command(name="yardim", aliases=["help", "komutlar"])
async def yardim_komutu(ctx):
    embed = discord.Embed(
        title="👑 Xyrin İmparatorluğu - Komut Merkezi",
        description="Hükümdarlar, Kral (swaarex) ve Kraliçe (zifona) protokolleri aktif!",
        color=discord.Color.dark_purple()
    )
    embed.add_field(name="🪙 Ekonomi & Seviye", value="`!bakiye`, `!gunluk`, `!seviye`, `!market`, `!transfer`", inline=False)
    embed.add_field(name="☕ Ekstra", value="`!ping`, `!kahve`, `!hologram`, `!rapor`", inline=False)
    embed.set_footer(text="Xyrin Empire Core v4.9")
    await ctx.send(embed=embed)

@bot.hybrid_command(name="ping")
async def ping_komutu(ctx):
    await ctx.send(f"🏓 Pong! Gecikme: **{round(bot.latency * 1000)}ms**")

@bot.hybrid_command(name="kahve", aliases=["coffee"])
async def kahve_komutu(ctx, *, kahve_turu: str = "Espresso"):
    await ctx.send(f"☕ Kurye dronumuz **{kahve_turu}** siparişinizi teslim etmek için yola çıktı!")

@bot.hybrid_command(name="hologram", aliases=["holo"])
async def hologram_durum_komutu(ctx):
    guild_id = ctx.guild.id
    embed = discord.Embed(title="🔮 Xyrin Hologram Projektör", color=discord.Color.teal())
    if guild_id in bot.active_holograms:
        holo = bot.active_holograms[guild_id]
        embed.description = f"Aktif Ses Odası: **{holo['channel'].name}**"
    else:
        embed.description = "Aktif bir ses odası hologramı bulunmuyor."
    await ctx.send(embed=embed)

@bot.hybrid_command(name="rapor", aliases=["stats"])
async def sunucu_raporu(ctx):
    guild = ctx.guild
    embed = discord.Embed(title=f"📊 {guild.name} - Rapor", color=discord.Color.blue())
    embed.add_field(name="👥 Toplam Üye", value=str(guild.member_count), inline=True)
    embed.add_field(name="🤖 Durum", value="Kral, Kraliçe ve Hükümdar Protokolleri Devrede", inline=False)
    await ctx.send(embed=embed)

@bot.hybrid_command(name="bakiye", aliases=["balance", "cuzdan"])
async def bakiye_komutu(ctx, member: discord.Member = None):
    member = member or ctx.author
    account = bot.get_account(member.id)
    embed = discord.Embed(title="🪙 İmparatorluk Hazinesi", color=discord.Color.gold())
    embed.add_field(name="Kullanıcı", value=member.mention, inline=True)
    embed.add_field(name="Bakiye", value=format_balance(account["balance"]), inline=True)
    await ctx.send(embed=embed)

@bot.hybrid_command(name="seviye", aliases=["level", "rank"])
async def seviye_komutu(ctx, member: discord.Member = None):
    member = member or ctx.author
    account = bot.get_account(member.id)
    embed = discord.Embed(title="📈 Seviye Kartı", color=discord.Color.blurple())
    embed.add_field(name="Kullanıcı", value=member.mention, inline=True)
    embed.add_field(name="Seviye", value=str(account["level"]), inline=True)
    embed.add_field(name="XP", value=f"{account['xp']}", inline=False)
    await ctx.send(embed=embed)

@bot.hybrid_command(name="gunluk", aliases=["daily"])
async def gunluk_komutu(ctx):
    account = bot.get_account(ctx.author.id)
    now = datetime.now()
    if account["last_daily"]:
        last = datetime.fromisoformat(account["last_daily"])
        remaining = timedelta(hours=DAILY_COOLDOWN_HOURS) - (now - last)
        if remaining.total_seconds() > 0:
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            await ctx.send(f"⏳ Günlük ödülünü zaten aldın! {hours} saat {minutes} dakika sonra tekrar gel.")
            return

    reward = random.randint(DAILY_REWARD_MIN, DAILY_REWARD_MAX)
    account["balance"] += reward
    account["last_daily"] = now.isoformat()
    bot._save_economy()
    await ctx.send(f"🎁 Günlük ödülün: **{format_balance(reward)}**! Yeni bakiye: {format_balance(account['balance'])}")

@bot.hybrid_command(name="transfer", aliases=["pay", "gonder"])
async def transfer_komutu(ctx, member: discord.Member, miktar: int):
    if miktar <= 0 or member.id == ctx.author.id:
        await ctx.send("❌ Geçersiz işlem.")
        return
    sender = bot.get_account(ctx.author.id)
    if sender["balance"] < miktar:
        await ctx.send("❌ Yetersiz bakiye!")
        return
    receiver = bot.get_account(member.id)
    sender["balance"] -= miktar
    receiver["balance"] += miktar
    bot._save_economy()
    await ctx.send(f"✅ {member.mention} kullanıcısına **{format_balance(miktar)}** gönderildi!")

@bot.hybrid_command(name="market", aliases=["shop"])
async def market_komutu(ctx):
    embed = discord.Embed(title="🏪 İmparatorluk Marketi", color=discord.Color.purple())
    for key, item in SHOP_ITEMS.items():
        embed.add_field(name=f"{key} — {format_balance(item['fiyat'])}", value=item["aciklama"], inline=False)
    await ctx.send(embed=embed)

@bot.hybrid_command(name="satinal", aliases=["buy"])
async def satinal_komutu(ctx, item_adi: str):
    item_adi = item_adi.lower().strip()
    item = SHOP_ITEMS.get(item_adi)
    if not item:
        await ctx.send("❌ Böyle bir eşya yok.")
        return
    account = bot.get_account(ctx.author.id)
    if account["balance"] < item["fiyat"]:
        await ctx.send("❌ Yetersiz bakiye!")
        return
    account["balance"] -= item["fiyat"]
    bot._save_economy()
    await ctx.send(f"✅ **{item_adi}** satın alındı!")

@bot.hybrid_command(name="siralama", aliases=["top"])
async def siralama_komutu(ctx):
    if not bot.economy:
        await ctx.send("Henüz kimsenin hesabı yok.")
        return
    sirali = sorted(bot.economy.items(), key=lambda kv: kv[1]["balance"], reverse=True)[:10]
    embed = discord.Embed(title="🏆 Zenginlik Sıralaması", color=discord.Color.gold())
    lines = [f"**{i}.** <@{uid}> — {format_balance(data['balance'])}" for i, (uid, data)]
    embed.description = "\n".join(lines)
    await ctx.send(embed=embed)

# --- ÇALIŞTIRMA BLOĞU ---
if __name__ == "__main__":
    if DISCORD_TOKEN != "BURAYA_DISCORD_BOT_TOKENINI_YAZ":
        bot.run(DISCORD_TOKEN)
