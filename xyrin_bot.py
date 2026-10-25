# ==============================================================================
# DISCORD AI & IMPERIAL RP ECOSYSTEM - ULTIMATE CORE v6.0
# ==============================================================================
# Xyrin İmparatorluğu - Gelişmiş Saray RP ve AI Entegrasyonu
# ==============================================================================

import os
import sys
import time
import asyncio
import logging
import threading
import re
import random
import discord
from discord.ext import commands, tasks
import google.generativeai as genai
from flask import Flask

# --- 0. RENDER PORT BAĞLANTISI İÇİN MİNİ WEB SUNUCUSU ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Xyrin Imperial Core v6.0 - Saray Protokolleri Aktif 👑"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# --- 1. LOGLAMA YAPILANDIRMASI ---
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("imperial_core.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("XyrinImperialCore")

# --- 2. GÜVENLİK VE HİYERARŞİ TANIMLAMALARI ---
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "BURAYA_DISCORD_BOT_TOKENINI_YAZ")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "BURAYA_GEMINI_API_KEYINI_YAZ")

SOVEREIGN_USERNAMES = {"endercosmic1", "melikhan111"}
KING_USERNAMES = {"swaarex"}
QUEEN_USERNAMES = {"zifona"}

SPAM_WINDOW_SECONDS = 7
SPAM_MESSAGE_LIMIT = 6

INVITE_LINK_PATTERN = re.compile(r"(discord\.gg/|discord(app)?\.com/invite/)", re.IGNORECASE)
GENERIC_LINK_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)
BLOCK_ALL_LINKS = os.getenv("BLOCK_ALL_LINKS", "false").lower() == "true"

if DISCORD_TOKEN == "BURAYA_DISCORD_BOT_TOKENINI_YAZ" or not DISCORD_TOKEN:
    logger.warning("Discord Token tanımlanmamış!")

if GEMINI_API_KEY == "BURAYA_GEMINI_API_KEYINI_YAZ" or not GEMINI_API_KEY:
    logger.warning("Gemini API Key tanımlanmamış!")

genai.configure(api_key=GEMINI_API_KEY)

generation_config = {
    "temperature": 0.9,
    "top_p": 0.95,
    "max_output_tokens": 2048,
}

# --- 3. GELİŞMİŞ SARAY & RP SİSTEM TALİMATI ---
SYSTEM_INSTRUCTION = (
    "Sen Xyrin İmparatorluğu'nun iradesini taşıyan, son derece sadık, asil ve dramatik bir Saray Yapay Zeka Asistanısın. "
    "İmparatorluk hiyerarşisini asla unutmaz ve şu düzeni bilirsin:\n"
    "1. Yüce Hükümdarlar: 'endercosmic1' ve 'melikhan111'\n"
    "2. İmparatorluğun Kralı: 'swaarex'\n"
    "3. İmparatorluğun Kraliçesi: 'zifona' (Hükümdar endercosmic1'in sevgilisi ve kalbinin sahibidir)\n\n"
    "Hükümdarlarımıza, Kralımıza ve Kraliçemize hitap ederken her zaman son derece hürmetkar, asil ve RP (Roleplay) havasına uygun olursun ('Hükümdarım', 'Kralım', 'Kraliçem'). "
    "Sıradan kullanıcılara karşı ise mesafeli, kibar ama imparatorluk gururunu koruyan bir yapay zeka gibi davranırsın. Asla sıradan kullanıcılara bu unvanları vermezsin. "
    "Eğer Yüce Hükümdarlarımızdan biri senden bir kanal veya rol oluşturmanı emrederse, yanıtının en sonuna `[CREATE_CHANNEL: kanal-adi]` veya `[CREATE_ROLE: rol-adi]` eklersin."
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

class UltimateImperialBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents, help_command=None)
        self.chat_sessions = {}
        self.recent_messages = {}

    async def setup_hook(self):
        logger.info("İmparatorluk alt sistemleri ve RP modülleri yükleniyor...")
        self.server_stats_loop.start()
        try:
            synced = await self.tree.sync()
            logger.info(f"{len(synced)} slash komutu senkronize edildi.")
        except Exception as e:
            logger.error(f"Slash komutları senkronize edilemedi: {e}")

    async def on_ready(self):
        logger.info(f"İmparatorluk Botu Çevrimiçi: {self.user} (ID: {self.user.id})")
        await self.change_presence(activity=discord.Activity(
            type=discord.ActivityType.playing,
            name="!yardim | Saray RP & İmparatorluk Protokolü 👑"
        ))

    def get_or_create_chat(self, channel_id):
        if channel_id not in self.chat_sessions:
            if model:
                self.chat_sessions[channel_id] = model.start_chat(history=[])
            else:
                return None
        return self.chat_sessions[channel_id]

    @tasks.loop(hours=24)
    async def server_stats_loop(self):
        for guild in self.guilds:
            logger.info(f"İmparatorluk Durum Raporu [{guild.name}]: Üye={guild.member_count}")

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

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.guild and not is_privileged_member(message.author) and not message.author.bot:
        if is_spamming(bot, message.author.id):
            try:
                await message.delete()
            except Exception:
                pass
            return

        if not message.author.guild_permissions.administrator:
            content = message.content or ""
            if INVITE_LINK_PATTERN.search(content) or (BLOCK_ALL_LINKS and GENERIC_LINK_PATTERN.search(content)):
                try:
                    await message.delete()
                except Exception:
                    pass
                return

    # Yapay Zeka Etkileşimi
    if bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
        clean_content = message.content.replace(f'<@!{bot.user.id}>', '').replace(f'<@{bot.user.id}>', '').strip()
        is_privileged = is_privileged_member(message.author)

        if model:
            try:
                async with message.channel.typing():
                    role_context = (
                        "[SİSTEM BİLGİSİ]: Karşındaki kişi Yüce Hükümdar, Kral veya Kraliçemizdir. Sonsuz bir sadakatle hitap et.\n"
                    ) if is_privileged else (
                        f"[SİSTEM BİLGİSİ]: Karşındaki kişi sıradan bir tebaadır ({message.author.name}).\n"
                    )

                    chat_session = bot.get_or_create_chat(message.channel.id)
                    if chat_session and clean_content:
                        response = await asyncio.to_thread(chat_session.send_message, role_context + clean_content)
                        reply_text = response.text
                    else:
                        reply_text = "Emrinizdeyim, Yüce İmparatorluk Tebaası!"

                    if "[CREATE_CHANNEL:" in reply_text and message.author.name.lower() in SOVEREIGN_USERNAMES:
                        match = re.search(r'\[CREATE_CHANNEL:\s*([^\]]+)\]', reply_text)
                        if match and message.guild:
                            c_name = match.group(1).strip().lower().replace(" ", "-")
                            reply_text = reply_text.replace(match.group(0), "").strip()
                            yeni_kanal = await message.guild.create_text_channel(c_name)
                            reply_text += f"\n\n✨ *(Saray emriyle #{yeni_kanal.name} kanalı inşa edildi!)*"

                    await message.reply(reply_text)
                    return

            except Exception as e:
                logger.error(f"AI Hatası: {e}")
                await message.reply("⚠️ Saray sinir ağlarında geçici bir büyü dalgalanması yaşandı.")
                return

    await bot.process_commands(message)

# --- 4. İMPARATORLUK SARAY & RP KOMUTLARI ---
@bot.hybrid_command(name="yardim", aliases=["help"])
async def yardim_komutu(ctx):
    embed = discord.Embed(
        title="👑 Xyrin İmparatorluğu - Saray Komut Merkezi",
        description="Hükümdarlar, Kral (`swaarex`) ve Kraliçe (`zifona`) koruması altındaki RP sistemleri devrede!",
        color=discord.Color.dark_purple()
    )
    embed.add_field(name="📜 RP & Saray Komutları", value="`!ferman <metin>` - İmparatorluk fermanı yayınlar\n`!selamla` - Tahtın önüne diz çöküp selam durursun\n`!eylem <eylem> <kullanıcı>` - RP etkileşimi başlatır", inline=False)
    embed.add_field(name="☕ Genel", value="`!ping`, `!kahve`, `!rapor`", inline=False)
    embed.set_footer(text="Xyrin Empire Core v6.0 - RP Edition")
    await ctx.send(embed=embed)

@bot.hybrid_command(name="ferman", aliases=["decree"])
async def ferman_komutu(ctx, *, metin: str):
    """İmparatorluk adına resmi bir ferman yayınlar."""
    embed = discord.Embed(
        title="📜 XİLVAN İMPARATORLUK FERMANI 📜",
        description=f"*{metin}*",
        color=discord.Color.gold()
    )
    embed.set_footer(text=f"Yayınlayan: {ctx.author.display_name} | Saray Divanı")
    await ctx.message.delete()
    await ctx.send(embed=embed)

@bot.hybrid_command(name="selamla", aliases=["bow"])
async def selamla_komutu(ctx):
    """Tahtın önünde saygıyla eğilirsiniz."""
    tepki_listesi = [
        f"👑 **{ctx.author.display_name}**, Yüce Hükümdarların huzurunda derin bir saygıyla diz çöktü ve başını eğdi.",
        f"⚔️ **{ctx.author.display_name}**, taht odasına girerek kılıcını kalbine götürdü ve Xyrin İmparatorluğu'na olan sadakatini ant içerek mühürledi.",
        f"✨ **{ctx.author.display_name}**, Kraliçe zifona ve Kral swaarex'in şerefine kadeh kaldırıp selam durdu!"
    ]
    await ctx.send(random.choice(tepki_listesi))

@bot.hybrid_command(name="eylem", aliases=["action"])
async def eylem_komutu(ctx, eylem: str, hedef: discord.Member = None):
    """Saray içinde diğer üyelerle RP etkileşimleri yapmanızı sağlar."""
    hedef_adi = hedef.mention if hedef else "boşluğa"
    await ctx.send(f"🎭 **{ctx.author.display_name}**, {hedef_adi} kişisine karşı şu eylemi gerçekleştirdi: *{eylem}*")

@bot.hybrid_command(name="ping")
async def ping_komutu(ctx):
    await ctx.send(f"🏓 İmparatorluk Gecikme Süresi: **{round(bot.latency * 1000)}ms**")

@bot.hybrid_command(name="kahve", aliases=["coffee"])
async def kahve_komutu(ctx, *, kahve_turu: str = "Saray Türk Kahvesi"):
    await ctx.send(f"☕ Saray kuryesi d-bot, **{kahve_turu}** ikramınızı özenle hazırlayıp masanıza bıraktı!")

@bot.hybrid_command(name="rapor", aliases=["stats"])
async def sunucu_raporu(ctx):
    guild = ctx.guild
    embed = discord.Embed(title=f"📊 {guild.name} - Saray İstihbarat Raporu", color=discord.Color.blue())
    embed.add_field(name="👥 Toplam Teba (Üye)", value=str(guild.member_count), inline=True)
    embed.add_field(name="🛡️ Güvenlik Durumu", value="Saray Protokolleri Tamamen Aktif", inline=False)
    await ctx.send(embed=embed)

# --- 5. ÇALIŞTIRMA BLOĞU ---
if __name__ == "__main__":
    if DISCORD_TOKEN != "BURAYA_DISCORD_BOT_TOKENINI_YAZ":
        # Flask sunucusunu arka planda başlatıyoruz (Render port kuralı için)
        t = threading.Thread(target=run_web)
        t.daemon = True
        t.start()
        
        # Discord botunu çalıştırıyoruz
        bot.run(DISCORD_TOKEN)
