# ==============================================================================
# DISCORD AI & IMPERIAL ECOSYSTEM BOT - ULTIMATE VISION & HOLOGRAM EDITION
# ==============================================================================
# Xyrin İmparatorluğu Core v5.2 - Render Web Service Uyumlu Tam Sürüm
# ==============================================================================

import os
import sys
import time
import io
import json
import random
import asyncio
import logging
import threading
import re
import contextlib
from datetime import datetime, timedelta
import aiohttp
import discord
from discord.ext import commands, tasks
import google.generativeai as genai
from flask import Flask

# --- 0. RENDER PORT BAĞLANTISI İÇİN MİNİ WEB SUNUCUSU ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Xyrin Imperial Bot Aktif ve Çalışıyor! 👑"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

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
    embed.add_field(name="☕ Ekstra", value="`!ping`, `!kahve`, `!hologram`, `!rapor`", inline=False)
    embed.set_footer(text="Xyrin Empire Core v5.2")
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
    embed.add_field(name="🤖 Durum", value="Kral, Kraliçe ve Hükümdار Protokolleri Devrede", inline=False)
    await ctx.send(embed=embed)

# --- ÇALIŞTIRMA BLOĞU ---
if __name__ == "__main__":
    if DISCORD_TOKEN != "BURAYA_DISCORD_BOT_TOKENINI_YAZ":
        # Flask sunucusunu arka plandaki ayrı bir thread'de başlatıyoruz
        t = threading.Thread(target=run_web)
        t.daemon = True
        t.start()
        
        # Discord botunu çalıştırıyoruz
        bot.run(DISCORD_TOKEN)
