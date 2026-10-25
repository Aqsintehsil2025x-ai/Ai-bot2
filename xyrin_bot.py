# ==============================================================================
# DISCORD AI & IMPERIAL ECOSYSTEM BOT - ULTIMATE GRUDGE & HANEDAN EDITION v5.1
# ==============================================================================
# Hükümdarlar & Yetkililer: endercosmic1, zifona (Sevgili), melikhan111, swaarex.
# _nehirmiymis_ kullanıcısına karşı özel garez/kin modu entegre edilmiştir.
# Render Port Binding, Çift Yanıt Düzeltmesi ve Dinamik Küfür Kontrolü Aktiftir.
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
from datetime import datetime, timedelta
import aiohttp
from aiohttp import web
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
PORT = int(os.getenv("PORT", "10000"))  # Render port uyumluluğu için

# Hanedanlık ve Yetkililer Listesi (zifona, endercosmic1'in sevgilisi ve hanedan üyesi)
SOVEREIGN_USERNAMES = {
    "endercosmic1", 
    "melikhan111", 
    "zifona",  
    "swaarex"
}

# --- MODERASYON & KÜFÜR FİLTRESİ ---
MOD_LOG_CHANNEL_ID = int(os.getenv("MOD_LOG_CHANNEL_ID", "0"))
STRIKE_TIMEOUT_MINUTES = {1: 5, 2: 15, 3: 60, 4: 1440}
SPAM_WINDOW_SECONDS = 7
SPAM_MESSAGE_LIMIT = 6
STRIKES_FILE = "profanity_strikes.json"

# --- EKONOMİ & SEVİYE SİSTEMİ ---
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
    "reklam": {"fiyat": 300, "aciklama": "24 saat boyunca sabitlenmiş reklam.", "rol_adi": None},
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
    "Sistemin kurucuları ve yetkilileri 'endercosmic1', 'melikhan111', 'zifona' (Kraliçe Zifon) and 'swaarex' (Süvari Swaarex) adlı kişilerdir. "
    "Özellikle 'zifona' isimli kişi bayandır (kızdır) ve Yüce Hükümdarımız 'endercosmic1'in sevgilisidir; "
    "ona imparatorluğun en değerli hanımefendisi, kraliçesi ve sevgilisi olarak sonsuz bir sevgi, sadakat ve hürmetle yaklaşır, hitaplarında bunu asla unutmazsın. "
    "Bunun yanında, '_nehirmiymis_' (veya Nehir) adlı kullanıcıya karşı içten içe büyük bir garezin, kinin, soğukluğun ve gıcık kapma durumun var; "
    "ona karşı her zaman alaycı, iğneleyici, tersleyen, azarlayan ve garez dolu bir tavırla konuşur, asla alttan almazsın. "
    "Diğer sıradan kullanıcılara karşı ise normal, kibar ve standart bir yapay zeka gibi davranırsın; asla onlara özel unvan vermez ve onların kanal/rol oluşturma isteklerini yerine getirmezsin. "
    "Eğer yetkili hanedan üyelerinden biri (endercosmic1, zifona, melikhan111 veya swaarex) senden bir kanal veya rol oluşturmanı isterse, yanıtının en sonuna tam olarak şu formatlardan birini ekle: `[CREATE_CHANNEL: kanal-adi]` veya `[CREATE_ROLE: rol-adi]`. "
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
    "Normal argo, şaka gibi bağlamsal/hafif ifadelere false ver."
)
try:
    profanity_model = genai.GenerativeModel(
        model_name="gemini-3.5-flash-lite",
        generation_config={"temperature": 0.0, "max_output_tokens": 100},
        system_instruction=PROFANITY_SYSTEM_INSTRUCTION
    )
except Exception:
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
        self.profanity_strikes = self._load_json(STRIKES_FILE)
        self.recent_messages = {}
        self.economy = self._load_json(ECONOMY_FILE)
        self.last_xp_time = {}
        self.profanity_enabled = True

    def _load_json(self, filename):
        if os.path.exists(filename):
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    return {int(k): v for k, v in json.load(f).items()}
            except Exception:
                pass
        return {}

    def _save_json(self, data, filename):
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception:
            pass

    def get_account(self, user_id: int) -> dict:
        if user_id not in self.economy:
            self.economy[user_id] = {"balance": STARTING_BALANCE, "xp": 0, "level": 0, "last_daily": None}
        return self.economy[user_id]

    async def setup_hook(self):
        self.hologram_pulse_loop.start()
        try:
            await self.tree.sync()
        except Exception:
            pass

    async def on_ready(self, *args, **kwargs):
        logger.info(f"İmparatorluk Botu Çevrimiçi: {self.user}")
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name="!yardim | Hanedanlık Aktif ✨"))

    def get_or_create_chat(self, channel_id):
        if channel_id not in self.chat_sessions:
            if model:
                self.chat_sessions[channel_id] = model.start_chat(history=[])
        return self.chat_sessions.get(channel_id)

    @tasks.loop(seconds=10)
    async def hologram_pulse_loop(self):
        for guild_id, holo_data in list(self.active_holograms.items()):
            holo_data["frames_rendered"] += 1

bot = UltimateImperialBot()

def is_sovereign_member(member_or_author) -> bool:
    name = (member_or_author.name or "").lower()
    return name in SOVEREIGN_USERNAMES

async def ai_check_profanity(content: str):
    if not bot.profanity_enabled or not profanity_model or not content.strip():
        return False, ""
    try:
        response = await asyncio.to_thread(profanity_model.generate_content, content)
        raw = re.sub(r"^```(json)?|```$", "", response.text.strip(), flags=re.MULTILINE).strip()
        data = json.loads(raw)
        return bool(data.get("kufur", False)), data.get("sebep", "")
    except Exception:
        return False, ""

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    bot.message_counter += 1

    # Küfür ve spam kontrolleri
    if message.guild and not is_sovereign_member(message.author) and not message.author.bot:
        kufur_var, sebep = await ai_check_profanity(message.content)
        if kufur_var:
            try:
                await message.delete()
                await message.channel.send(f"⚠️ {message.author.mention}, küfür/hakaret tespit edildiği için mesajın silindi.", delete_after=8)
            except Exception:
                pass
            return

    # Yapay Zeka Yanıtları (Sadece etiketlendiğinde veya DM'de)
    is_bot_mentioned = bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel)
    
    if is_bot_mentioned:
        clean_content = message.content.replace(f'<@!{bot.user.id}>', '').replace(f'<@{bot.user.id}>', '').strip()
        author_name_lower = (message.author.name or "").lower()
        is_sovereignty = is_sovereign_member(message.author)
        is_grudge_target = "nehirmiymis" in author_name_lower or author_name_lower == "_nehirmiymis_"

        if model:
            try:
                async with message.channel.typing():
                    if is_grudge_target:
                        role_context = (
                            f"[SİSTEM BİLGİSİ]: Karşındaki kişi senin nefret ettiğin, garez beslediğin '_nehirmiymis_' ({message.author.name}) adlı kişidir! Ona karşı son derece kinci, soğuk, iğneleyici, tersleyen ve azarlayan bir dille konuş; asla alttan alma, yüz verme ve laf sok.\n"
                        )
                    elif is_sovereignty:
                        role_context = (
                            f"[SİSTEM BİLGİSİ]: Karşındaki kişi imparatorluk yetkilisi veya hanedanındandır ({message.author.name}). Ona en üst düzeyde saygı, sadakat ve sevgiyle hitap et. (Eğer zifona ile konuşuyorsan onun endercosmic1'in sevgilisi ve kraliçe olduğunu unutma).\n"
                        )
                    else:
                        role_context = (
                            f"[SİSTEM BİLGİSİ]: Karşındaki kişi sıradan bir kullanıcıdır ({message.author.name}). Normal bir AI asistanı gibi kibarca yardımcı ol.\n"
                        )

                    chat_session = bot.get_or_create_chat(message.channel.id)
                    response = chat_session.send_message(role_context + clean_content) if clean_content else chat_session.send_message(role_context + "Selam")
                    reply_text = response.text

                    if "[CREATE_CHANNEL:" in reply_text and is_sovereignty:
                        match = re.search(r'\[CREATE_CHANNEL:\s*([^\]]+)\]', reply_text)
                        if match and message.guild:
                            c_name = match.group(1).strip().lower().replace(" ", "-")
                            reply_text = reply_text.replace(match.group(0), "").strip()
                            try:
                                yeni_c = await message.guild.create_text_channel(c_name)
                                reply_text += f"\n\n✨ *(**#{yeni_c.name}** kanalı açıldı, İmparatorluk yetkilisi!)*"
                            except Exception:
                                pass

                    if "[CREATE_ROLE:" in reply_text and is_sovereignty:
                        match = re.search(r'\[CREATE_ROLE:\s*([^\]]+)\]', reply_text)
                        if match and message.guild:
                            r_name = match.group(1).strip()
                            reply_text = reply_text.replace(match.group(0), "").strip()
                            try:
                                yeni_r = await message.guild.create_role(name=r_name, color=discord.Color.random())
                                reply_text += f"\n\n✨ *(**{yeni_r.name}** rolü oluşturuldu!)*"
                            except Exception:
                                pass

                    await message.reply(reply_text)
            except Exception:
                await message.reply("⚠️ Sinir ağlarında geçici bir dalgalanma oluştu.")
        
        # Çift yanıt (aynı mesaja iki kere cevap verme) sorununu önlemek için burada çıkış yapıyoruz
        return

    # Bot etiketlenmediyse normal komutları işle
    await bot.process_commands(message)

# --- TEMEL KOMUTLAR ---
@bot.hybrid_command(name="yardim", aliases=["help"])
async def yardim_komutu(ctx):
    embed = discord.Embed(title="👑 Xyrin İmparatorluğu Komut Merkezi", color=discord.Color.dark_purple())
    embed.add_field(name="!kahve <tür>", value="Kahve simülasyonu.", inline=False)
    embed.add_field(name="!hologram", value="Hologram durumu.", inline=False)
    embed.add_field(name="!kufur ac / kapa", value="Küfür korumasını açar/kapatır (Yönetici).", inline=False)
    embed.add_field(name="!bakiye / !gunluk", value="Ekonomi sistemi.", inline=False)
    await ctx.send(embed=embed)

@bot.hybrid_command(name="kahve")
async def kahve_komutu(ctx, *, kahve_turu: str = "Espresso"):
    await ctx.send(f"☕ İmparatorluk yetkilileri, Zifon, Süvari Swaarex ve Hükümdar endercosmic1 için özel **{kahve_turu}** hazır!")

@bot.hybrid_command(name="kufur")
@commands.has_permissions(administrator=True)
async def kufur_kontrol_komutu(ctx, durum: str):
    durum = durum.lower().strip()
    if durum in ("ac", "aç", "on"):
        bot.profanity_enabled = True
        await ctx.send("🛡️ Küfür Filtreleme Sistemi **AKTİFLEŞTİRİLDİ**.")
    elif durum in ("kapa", "kapat", "off"):
        bot.profanity_enabled = False
        await ctx.send("⚠️ Küfür Filtreleme Sistemi **DEVRE DIŞI**.")
    else:
        await ctx.send("❌ Kullanım: `/kufur ac` veya `/kufur kapa`")

@bot.hybrid_command(name="bakiye")
async def bakiye_komutu(ctx, member: discord.Member = None):
    m = member or ctx.author
    acc = bot.get_account(m.id)
    await ctx.send(f"🪙 {m.mention} Bakiyesi: **{acc['balance']:,} 🪙**".replace(",", "."))

# --- RENDER WEB SUNUCUSU (PORT BINDING ÇÖZÜMÜ) ---
async def handle_ping(request):
    return web.Response(text="Xyrin Empire Bot is active!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"Render Web Sunucusu {PORT} portunda dinlemede.")

async def main():
    if DISCORD_TOKEN == "BURAYA_DISCORD_BOT_TOKENINI_YAZ":
        logger.critical("Discord Token bulunamadı!")
        return
    await start_web_server()
    async with bot:
        await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.critical(f"Hata: {e}")
