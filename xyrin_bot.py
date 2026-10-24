# ==============================================================================
# DISCORD AI & IMPERIAL ECOSYSTEM BOT - ULTIMATE VISION & HOLOGRAM EDITION
# ==============================================================================
# Xyrin İmparatorluğu Core v4.6 - Hükümdar, Kral ve Kraliçe Protokolü Entegre Edilmiştir.
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

# --- MODERASYON (KÜFÜR/SPAM FİLTRESİ) AYARLARI ---
MOD_LOG_CHANNEL_ID = int(os.getenv("MOD_LOG_CHANNEL_ID", "0"))
STRIKE_TIMEOUT_MINUTES = {1: 5, 2: 15, 3: 60, 4: 1440}  
SPAM_WINDOW_SECONDS = 7
SPAM_MESSAGE_LIMIT = 6
STRIKES_FILE = "profanity_strikes.json"

# Küfür korumasının açık/kapalı durumu (varsayılan: True / Açık)
PROFANITY_FILTER_ENABLED = True

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
    "Sistemin yaratıcıları ve hakimleri 'endercosmic1' ve 'melikhan111' adlı kullanıcılardır "
    "(Onları her zaman 'Hükümdarım' diye anarsın). "
    "İmparatorluğun Kralı 'swaarex' ve Kraliçesi 'zifona'dır. Kraliçe zifona, Hükümdar endercosmic1'in sevgilisidir. "
    "Kral ve Kraliçemize de son derece saygılı, hürmetkar ve imparatorluk protokolüne uygun davranırsın. "
    "Diğer sıradan kullanıcılara karşı ise normal, kibar ve standart bir yapay zeka gibi davranırsın; asla onlara Hükümdar/Kral/Kraliçe hitabında bulunmaz ve onların kanal/rol oluşturma isteklerini yerine getirmezsin. "
    "Eğer Yüce Hükümdarlarımızdan biri senden bir kanal veya rol oluşturmanı isterse, yanıtının en sonuna tam olarak şu formatlardan birini ekle: `[CREATE_CHANNEL: kanal-adi]` veya `[CREATE_ROLE: rol-adi]`. "
    "Geçmiş sohbetleri hafızanda tutar, görselleri (Vision) en ince detayına kadar analiz edersin."
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

PROFANITY_SYSTEM_INSTRUCTION = (
    "Sen bir Discord sunucusu için içerik moderasyon sınıflandırıcısısın. "
    "Sana verilen mesajı incele ve SADECE şu JSON formatında cevap ver, başka hiçbir şey yazma: "
    '{"kufur": true/false, "sebep": "kısa açıklama"} '
    "Küfür, ağır hakaret, cinsel taciz, ırkçı/nefret söylemi içeren mesajlara true ver. "
    "Normal argo, şaka, spor küfürü gibi bağlamsal/hafif ifadelere ve küfür içermeyen mesajlara false ver. "
    "Emin değilsen false ver."
)
try:
    profanity_model = genai.GenerativeModel(
        model_name="gemini-3.5-flash-lite",
        generation_config={"temperature": 0.0, "max_output_tokens": 100},
        system_instruction=PROFANITY_SYSTEM_INSTRUCTION
    )
    logger.info("Küfür sınıflandırma modeli yüklendi.")
except Exception as e:
    logger.error(f"Küfür sınıflandırma modeli yüklenirken hata: {e}")
    profanity_model = None

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
        self.profanity_strikes = self._load_strikes()  
        self.recent_messages = {}   
        self.economy = self._load_economy()  
        self.last_xp_time = {}      

    def _load_strikes(self):
        if os.path.exists(STRIKES_FILE):
            try:
                with open(STRIKES_FILE, "r", encoding="utf-8") as f:
                    return {int(k): v for k, v in json.load(f).items()}
            except Exception as e:
                logger.error(f"Strike dosyası okunamadı: {e}")
        return {}

    def _save_strikes(self):
        try:
            with open(STRIKES_FILE, "w", encoding="utf-8") as f:
                json.dump(self.profanity_strikes, f)
        except Exception as e:
            logger.error(f"Strike dosyası kaydedilemedi: {e}")

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

    @check_events_loop.before_loop
    async def before_events(self):
        await self.wait_until_ready()

    @tasks.loop(hours=24)
    async def server_stats_loop(self):
        pass

    @server_stats_loop.before_loop
    async def before_stats(self):
        await self.wait_until_ready()

    @tasks.loop(seconds=10)
    async def hologram_pulse_loop(self):
        for guild_id, holo_data in list(self.active_holograms.items()):
            holo_data["frames_rendered"] += 1

    @hologram_pulse_loop.before_loop
    async def before_hologram(self):
        await self.wait_until_ready()

bot = UltimateImperialBot()

def is_privileged_member(member_or_author) -> bool:
    """Hükümdar, Kral veya Kraliçe kontrolü yapar."""
    name = (member_or_author.name or "").lower()
    return name in SOVEREIGN_USERNAMES or name in KING_USERNAMES or name in QUEEN_USERNAMES

async def ai_check_profanity(content: str):
    if not profanity_model or not content or not content.strip():
        return False, ""
    try:
        response = await asyncio.to_thread(profanity_model.generate_content, content)
        raw = response.text.strip()
        raw = re.sub(r"^```(json)?|```$", "", raw, flags=re.MULTILINE).strip()
        data = json.loads(raw)
        return bool(data.get("kufur", False)), data.get("sebep", "")
    except Exception as e:
        logger.error(f"Küfür sınıflandırma hatası: {e}")
        return False, ""

def is_spamming(bot_instance, user_id: int) -> bool:
    now = time.time()
    timestamps = bot_instance.recent_messages.setdefault(user_id, [])
    timestamps.append(now)
    cutoff = now - SPAM_WINDOW_SECONDS
    while timestamps and timestamps[0] < cutoff:
        timestamps.pop(0)
    return len(timestamps) > SPAM_MESSAGE_LIMIT

async def apply_moderation_action(message: discord.Message, reason: str, category: str):
    member = message.author
    guild = message.guild
    original_content = message.content or "*(içerik yok)*"

    try:
        await message.delete()
    except Exception as e:
        logger.error(f"Mesaj silinemedi: {e}")

    strikes = bot.profanity_strikes.get(member.id, 0) + 1
    bot.profanity_strikes[member.id] = strikes
    bot._save_strikes()

    timeout_minutes = STRIKE_TIMEOUT_MINUTES.get(strikes, 1440)
    muted = False
    try:
        if guild.me.guild_permissions.moderate_members:
            until = discord.utils.utcnow() + timedelta(minutes=timeout_minutes)
            await member.timeout(until, reason=f"{category}: {reason}")
            muted = True
    except Exception as e:
        logger.error(f"Timeout uygulanamadı: {e}")

    if MOD_LOG_CHANNEL_ID:
        log_channel = guild.get_channel(MOD_LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(title=f"🚫 Moderasyon Eylemi — {category}", color=discord.Color.red())
            embed.add_field(name="Kullanıcı", value=f"{member.mention} (`{member.name}`)", inline=True)
            embed.add_field(name="Strike", value=str(strikes), inline=True)
            embed.add_field(name="Sebep", value=reason or "Belirtilmedi", inline=False)
            try:
                await log_channel.send(embed=embed)
            except Exception:
                pass

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
    global PROFANITY_FILTER_ENABLED
    if message.author == bot.user:
        return

    bot.message_counter += 1

    if message.guild and not is_privileged_member(message.author) and not message.author.bot:
        if is_spamming(bot, message.author.id):
            await apply_moderation_action(message, "Spam", "SPAM")
            return

        if not message.author.guild_permissions.administrator:
            link_silindi = await check_link_violation(message)
            if link_silindi:
                return

        # Küfür filtresi açık ise denetle
        if PROFANITY_FILTER_ENABLED:
            kufur_var, sebep = await ai_check_profanity(message.content)
            if kufur_var:
                await apply_moderation_action(message, sebep, "KÜFÜR/HAKARET")
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
                        response = chat_session.send_message(role_context + clean_content)
                        reply_text = response.text
                    else:
                        reply_text = "Emrinizdeyim!"

                    # Otomatik Kanal / Rol Oluşturma (Sadece Hükümdarlar)
                    if "[CREATE_CHANNEL:" in reply_text and message.author.name.lower() in SOVEREIGN_USERNAMES:
                        match = re.search(r'\[CREATE_CHANNEL:\s*([^\]]+)\]', reply_text)
                        if match and message.guild:
                            c_name = match.group(1).strip().lower().replace(" ", "-")
                            reply_text = reply_text.replace(match.group(0), "").strip()
                            yeni_kanal = await message.guild.create_text_channel(c_name)
                            reply_text += f"\n\n✨ *(#{yeni_kanal.name} kanalı oluşturuldu!)*"

                    await message.reply(reply_text)
            except Exception as e:
                logger.error(f"AI Hatası: {e}")
                await message.reply("⚠️ Sinir ağlarında dalgalanma oluştu.")

    await bot.process_commands(message)

# --- YENİ EKLENEN KÜFÜR YASAĞI KOMUTLARI (/kufur ac /kufur kapa) ---
@bot.hybrid_group(name="kufur", description="Küfür koruma filtresini yönetir.")
@commands.has_permissions(administrator=True)
async def kufur(ctx):
    if ctx.invoked_subcommand is None:
        global PROFANITY_FILTER_ENABLED
        durum = "açık 🟢" if PROFANITY_FILTER_ENABLED else "kapalı 🔴"
        await ctx.send(f"🛡️ Küfür koruma filtresi şu anda: **{durum}**\nKullanım: `/kufur ac` veya `/kufur kapa`")

@kufur.command(name="ac", description="Küfür koruma filtresini açar.")
@commands.has_permissions(administrator=True)
async def kufur_ac(ctx):
    global PROFANITY_FILTER_ENABLED
    PROFANITY_FILTER_ENABLED = True
    await ctx.send("✅ Küfür koruma filtresi **açıldı**!")

@kufur.command(name="kapa", description="Küfür koruma filtresini kapatır.")
@commands.has_permissions(administrator=True)
async def kufur_kapa(ctx):
    global PROFANITY_FILTER_ENABLED
    PROFANITY_FILTER_ENABLED = False
    await ctx.send("⚠️ Küfür koruma filtresi **kapatıldı**!")

# --- DİĞER TEMEL KOMUTLAR ---
@bot.hybrid_command(name="yardim", aliases=["help"])
async def yardim_komutu(ctx):
    embed = discord.Embed(
        title="👑 Xyrin İmparatorluğu - Komut Merkezi",
        description="Hükümdarlar, Kral (swaarex) ve Kraliçe (zifona - endercosmic1'in sevgilisi) protokolleri devrede!",
        color=discord.Color.dark_purple()
    )
    embed.add_field(name="🛡️ Moderasyon", value="`/kufur ac` / `/kufur kapa` — Küfür filtresini aç/kapat.", inline=False)
    embed.add_field(name="🪙 Ekonomi & Seviye", value="`!bakiye`, `!gunluk`, `!seviye`, `!market`, `!bahis`", inline=False)
    await ctx.send(embed=embed)

@bot.hybrid_command(name="ping")
async def ping_komutu(ctx):
    await ctx.send(f"🏓 Pong! Gecikme: **{round(bot.latency * 1000)}ms**")

if __name__ == "__main__":
    if DISCORD_TOKEN != "BURAYA_DISCORD_BOT_TOKENINI_YAZ":
        bot.run(DISCORD_TOKEN)
        
