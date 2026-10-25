# ==============================================================================
# DISCORD AI & IMPERIAL ECOSYSTEM BOT - ULTIMATE VISION & HOLOGRAM EDITION
# ==============================================================================
# Xyrin İmparatorluğu Core v4.6 - Hükümdarlar, Kraliçe, Süvari Swaarex Zifon ve Dinamik Küür Kontrolü Entegre Edilmiştir.
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

# Hükümdarlar, Kraliçe ve Özel İmparatorluk Üyeleri
SOVEREIGN_USERNAMES = {"endercosmic1", "melikhan111", "kralice zifon", "swaarex zifon"}

# --- MODERASYON (KÜFÜR/SPAM FİLTRESİ) AYARLARI ---
MOD_LOG_CHANNEL_ID = int(os.getenv("MOD_LOG_CHANNEL_ID", "0"))
STRIKE_TIMEOUT_MINUTES = {1: 5, 2: 15, 3: 60, 4: 1440}  # 4. strike'tan sonra hep 24 saat
SPAM_WINDOW_SECONDS = 7
SPAM_MESSAGE_LIMIT = 6
STRIKES_FILE = "profanity_strikes.json"

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
    logger.warning("Discord Token tanımlanmamış! Lütfen çevre değişkenlerini kontrol edin.")

if GEMINI_API_KEY == "BURAYA_GEMINI_API_KEYINI_YAZ" or not GEMINI_API_KEY:
    logger.warning("Gemini API Key tanımlanmamış! Yapay zeka sinir ağları devre dışı kalabilir.")

genai.configure(api_key=GEMINI_API_KEY)

generation_config = {
    "temperature": 0.85,
    "top_p": 0.95,
    "max_output_tokens": 2048,
}

SYSTEM_INSTRUCTION = (
    "Sen Xyrin İmparatorluğu'nun en gelişmiş yapay zeka asistanısın. "
    "Sistemin kurucuları ve hakimleri 'endercosmic1' ve 'melikhan111' adlı kullanıcılardır "
    "(Onları her zaman 'Hükümdarım' diye anarsın). "
    "İmparatorlukta 'kralice zifon' (Kraliçe Zifon) en yüce makamlardan biridir. "
    "Ayrıca 'swaarex zifon' (Süvari Swaarex Zifon), Yüce Hükümdarımız 'endercosmic1'in sevgilisidir; ona sonsuz bir hürmetle, sevgiyle ve imparatorluğun en değerli hanımefendisi olarak yaklaşır, hitaplarında bunu asla unutmazsın. "
    "Diğer sıradan kullanıcılara karşı ise normal, kibar ve standart bir yapay zeka gibi davranırsın; asla onlara Hükümdar hitabında bulunmaz ve onların kanal/rol oluşturma isteklerini yerine getirmezsin. "
    "Eğer Yüce Hükümdarlarımızdan biri, Kraliçe Zifon veya Süvari Swaarex Zifon senden bir kanal veya rol oluşturmanı isterse, yanıtının en sonuna tam olarak şu formatlardan birini ekle: `[CREATE_CHANNEL: kanal-adi]` veya `[CREATE_ROLE: rol-adi]`. "
    "Geçmiş sohbetleri hafızanda tutar, görselleri (Vision) en ince detayına kadar analiz edersin."
)

try:
    model = genai.GenerativeModel(
        model_name="gemini-3.5-flash-lite",
        generation_config=generation_config,
        system_instruction=SYSTEM_INSTRUCTION
    )
    logger.info("Gemini modeli ('gemini-3.5-flash-lite') başarıyla yüklendi ve senkronize edildi.")
except Exception as e:
    logger.error(f"Gemini modeli yüklenirken kritik hata: {e}")
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

# --- 3. DISCORD INTENTS VE GELİŞMİŞ BOT MİMARİSİ ---
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
        self.profanity_enabled = True  # Küfür sisteminin açma/kapama durumu

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
        logger.info("İmparatorluk alt sistemleri, arka plan görevleri ve DLC modülleri başlatılıyor...")
        self.check_events_loop.start()
        self.server_stats_loop.start()
        self.hologram_pulse_loop.start()
        try:
            synced = await self.tree.sync()
            logger.info(f"{len(synced)} slash (/) komutu başarıyla senkronize edildi.")
        except Exception as e:
            logger.error(f"Slash komutları senkronize edilemedi: {e}")

    async def on_ready(self):
        logger.info(f"İmparatorluk Botu Çevrimiçi: {self.user} (ID: {self.user.id})")
        logger.info(f"Hizmet Verilen Evren/Sunucu Sayısı: {len(self.guilds)}")
        await self.change_presence(activity=discord.Activity(
            type=discord.ActivityType.playing,
            name="!yardim | Hükümdar, Kraliçe ve Süvari Swaarex Protokolü Aktif ☕✨"
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
        now = datetime.now()
        due_events = [e for e in self.scheduled_events if e["time"] <= now]
        for event in due_events:
            self.scheduled_events.remove(event)
            channel = self.get_channel(event["channel_id"])
            if channel:
                try:
                    prompt = (
                        f"Şu anda '{event['title']}' adlı planlanan imparatorluk etkinliğinin vakti geldi! "
                        "Hükümdarımız ve Kraliçemiz için coşkulu bir anons metni yaz."
                    )
                    content = model.generate_content(prompt).text if model else f"🚨 **Zamanı Geldi!** Etkinlik: **{event['title']}**"
                    await channel.send(f"🔔 <@{event['author_id']}> Hükümdarım, emrettiğiniz etkinlik vakti geldi!\n\n{content}")
                    logger.info(f"Etkinlik tetiklendi: {event['title']}")
                except Exception as ex:
                    logger.error(f"Etkinlik tetikleme hatası: {ex}")

    @check_events_loop.before_loop
    async def before_events(self):
        await self.wait_until_ready()

    @tasks.loop(hours=24)
    async def server_stats_loop(self):
        for guild in self.guilds:
            logger.info(f"İmparatorluk Raporu [{guild.name}]: Üye={guild.member_count}, MesajSayaç={self.message_counter}")
            self.message_counter = 0

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


def is_sovereign_member(member_or_author) -> bool:
    name = (member_or_author.name or "").lower()
    return name in SOVEREIGN_USERNAMES


async def ai_check_profanity(content: str):
    if not bot.profanity_enabled:
        return False, ""
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
    original_content = message.content or "*(içerik yok / sadece ek dosya)*"

    try:
        await message.delete()
    except Exception as e:
        logger.error(f"Mesaj silinemedi: {e}")

    strikes = bot.profanity_strikes.get(member.id, 0) + 1
    bot.profanity_strikes[member.id] = strikes
    bot._save_strikes()

    timeout_minutes = STRIKE_TIMEOUT_MINUTES.get(strikes, STRIKE_TIMEOUT_MINUTES[max(STRIKE_TIMEOUT_MINUTES)])
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
            embed = discord.Embed(
                title=f"🚫 Moderasyon Eylemi — {category}",
                color=discord.Color.red()
            )
            embed.add_field(name="Kullanıcı", value=f"{member.mention} (`{member.name}`)", inline=True)
            embed.add_field(name="Strike sayısı", value=str(strikes), inline=True)
            embed.add_field(name="Kanal", value=message.channel.mention, inline=True)
            embed.add_field(name="Sebep", value=reason or "Belirtilmedi", inline=False)
            embed.add_field(name="Silinen mesaj (tam içerik)", value=original_content[:1024], inline=False)
            embed.add_field(
                name="Uygulanan eylem",
                value=(f"Mesaj silindi + {timeout_minutes} dakika mute" if muted else "Mesaj silindi (mute yetkisi yok)"),
                inline=False
            )
            embed.timestamp = discord.utils.utcnow()
            try:
                await log_channel.send(embed=embed)
            except Exception:
                pass

    try:
        warn_text = f"⚠️ {member.mention}, mesajın kurallara aykırı bulunduğu için silindi."
        if muted:
            warn_text += f" {timeout_minutes} dakika susturuldun. (Strike: {strikes})"
        await message.channel.send(warn_text, delete_after=10)
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
                        await member.add_roles(role, reason=f"Seviye {lvl}'e ulaştı")
                    except Exception as e:
                        logger.error(f"Seviye rolü verilemedi: {e}")
        try:
            channel = member.guild.system_channel
            if channel:
                await channel.send(f"🎉 {member.mention} **Seviye {new_level}**'e yükseldi!", delete_after=15)
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
    except Exception as e:
        logger.error(f"Link mesajı silinemedi: {e}")
    try:
        await message.channel.send(
            f"🔗 {message.author.mention}, sunucu davet linki/izinsiz link paylaşımı yasak, mesajın silindi.",
            delete_after=10
        )
    except Exception:
        pass
    if MOD_LOG_CHANNEL_ID:
        log_channel = message.guild.get_channel(MOD_LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(title="🔗 Link/Davet Engellendi", color=discord.Color.gold())
            embed.add_field(name="Kullanıcı", value=message.author.mention, inline=True)
            embed.add_field(name="Kanal", value=message.channel.mention, inline=True)
            embed.add_field(name="İçerik", value=content[:1024], inline=False)
            embed.timestamp = discord.utils.utcnow()
            try:
                await log_channel.send(embed=embed)
            except Exception:
                pass
    return True


@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return

    if after.channel and before.channel != after.channel:
        guild = member.guild
        is_sovereign = is_sovereign_member(member)
        bot.active_holograms[guild.id] = {
            "channel": after.channel,
            "target_user": member,
            "frames_rendered": 0,
            "status": "PROJEKSİYON AKTİF"
        }

        text_channel = guild.system_channel or next((c for c in guild.text_channels if c.permissions_for(guild.me).send_messages), None)
        if text_channel:
            desc = (
                f"**İmparatorluk hanedanından {member.mention} ses kanalına teşrif buyurdular!**\n"
                f"🌐 Ses Kanalı: `{after.channel.name}`"
            ) if is_sovereign else (
                f"**{member.mention} ses kanalına katıldı.**\n"
                f"🌐 Ses Kanalı: `{after.channel.name}`"
            )
            embed = discord.Embed(
                title="✨ [HOLO-CAM] Optik Yükseltme & Hologram Devrede",
                description=desc,
                color=discord.Color.teal()
            )
            try:
                await text_channel.send(embed=embed)
            except Exception:
                pass

    elif before.channel and not after.channel:
        if member.guild.id in bot.active_holograms:
            bot.active_holograms.pop(member.guild.id, None)


@bot.event
async def on_member_join(member: discord.Member):
    bot.get_account(member.id)
    bot._save_economy()

    if WELCOME_ROLE_NAME:
        role = discord.utils.get(member.guild.roles, name=WELCOME_ROLE_NAME)
        if role:
            try:
                await member.add_roles(role, reason="Otomatik karşılama rolü")
            except Exception:
                pass

    channel = None
    if WELCOME_CHANNEL_ID:
        channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
    channel = channel or member.guild.system_channel
    if channel:
        embed = discord.Embed(
            title="✨ Xyrin İmparatorluğu'na Hoş Geldin!",
            description=(
                f"{member.mention}, imparatorluğumuzun {member.guild.member_count}. üyesi oldun!\n"
                f"`!yardim` ile bota göz atabilirsin."
            ),
            color=discord.Color.dark_purple()
        )
        if member.display_avatar:
            embed.set_thumbnail(url=member.display_avatar.url)
        try:
            await channel.send(embed=embed)
        except Exception:
            pass


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, (commands.CommandNotFound, commands.CheckFailure)):
        if isinstance(error, commands.CheckFailure):
            try:
                await ctx.send("❌ Bu komutu kullanmak için yetkin yok.", delete_after=8)
            except Exception:
                pass
        return

    logger.error(f"Komut hatası ({ctx.command}): {error}")
    try:
        await ctx.send("⚠️ Komut çalıştırılırken bir hata oluştu.", delete_after=8)
    except Exception:
        pass


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    bot.message_counter += 1

    if message.guild and not is_sovereign_member(message.author) and not message.author.bot:
        if is_spamming(bot, message.author.id):
            await apply_moderation_action(message, "Kısa sürede çok fazla mesaj (spam)", "SPAM")
            return

        if not message.author.guild_permissions.administrator:
            link_silindi = await check_link_violation(message)
            if link_silindi:
                return

        kufur_var, sebep = await ai_check_profanity(message.content)
        if kufur_var:
            await apply_moderation_action(message, sebep, "KÜFÜR/HAKARET")
            return

        await award_xp(message.author)

    if bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
        clean_content = message.content.replace(f'<@!{bot.user.id}>', '').replace(f'<@{bot.user.id}>', '').strip()
        is_sovereignty = is_sovereign_member(message.author)

        if model:
            try:
                async with message.channel.typing():
                    if message.attachments:
                        attachment = message.attachments[0]
                        if attachment.content_type and attachment.content_type.startswith("image/"):
                            async with aiohttp.ClientSession() as session:
                                async with session.get(attachment.url) as resp:
                                    if resp.status == 200:
                                        image_bytes = await resp.read()
                                        image_part = {
                                            "mime_type": attachment.content_type,
                                            "data": image_bytes
                                        }
                                        prompt = clean_content if clean_content else "Bu görseli tarayın Hükümdarım/Kraliçem/Süvari hazretleri."
                                        response = model.generate_content([prompt, image_part])
                                        await message.reply(response.text)
                                        await bot.process_commands(message)
                                        return

                    role_context = (
                        f"[SİSTEM BİLGİSİ]: Karşındaki kişi imparatorluk hanedanındandır ({message.author.name}). Ona en üst düzeyde saygı, sadakat ve sevgiyle hitap et.\n"
                    ) if is_sovereignty else (
                        f"[SİSTEM BİLGİSİ]: Karşındaki kişi sıradan bir kullanıcıdır ({message.author.name}). Normal bir AI asistanı gibi kibarca yardımcı ol, asla özel unvan veya yetki verme.\n"
                    )

                    chat_session = bot.get_or_create_chat(message.channel.id)
                    if chat_session and clean_content:
                        response = chat_session.send_message(role_context + clean_content)
                        reply_text = response.text
                    elif not clean_content:
                        reply_text = "Emrinizdeyim!" if is_sovereignty else f"Merhaba {message.author.name}, size nasıl yardımcı olabilirim?"
                    else:
                        reply_text = "Emrinizdeyim!" if is_sovereignty else "Buyurun, sizi dinliyorum."

                    if "[CREATE_CHANNEL:" in reply_text:
                        match = re.search(r'\[CREATE_CHANNEL:\s*([^\]]+)\]', reply_text)
                        if match and message.guild:
                            if is_sovereignty:
                                channel_name = match.group(1).strip().lower().replace(" ", "-")
                                reply_text = reply_text.replace(match.group(0), "").strip()
                                try:
                                    yeni_kanal = await message.guild.create_text_channel(channel_name)
                                    reply_text += f"\n\n✨ *(Emriniz üzerine **#{yeni_kanal.name}** kanalı otomatik olarak oluşturuldu!)*"
                                except Exception as ex:
                                    reply_text += f"\n\n⚠️ *(Kanal oluşturulamadı: {ex})*"
                            else:
                                reply_text = reply_text.replace(match.group(0), "").strip()
                                reply_text += "\n\n❌ *(Bu imparatorluk emrini yalnızca hanedan üyeleri verebilir!)*"

                    if "[CREATE_ROLE:" in reply_text:
                        match = re.search(r'\[CREATE_ROLE:\s*([^\]]+)\]', reply_text)
                        if match and message.guild:
                            if is_sovereignty:
                                role_name = match.group(1).strip()
                                reply_text = reply_text.replace(match.group(0), "").strip()
                                try:
                                    yeni_rol = await message.guild.create_role(name=role_name, color=discord.Color.random())
                                    reply_text += f"\n\n✨ *(Emriniz üzerine **{yeni_rol.name}** rolü otomatik olarak oluşturuldu!)*"
                                except Exception as ex:
                                    reply_text += f"\n\n⚠️ *(Rol oluşturulamadı: {ex})*"
                            else:
                                reply_text = reply_text.replace(match.group(0), "").strip()
                                reply_text += "\n\n❌ *(Bu imparatorluk emrini yalnızca hanedan üyeleri verebilir!)*"

                    await message.reply(reply_text)

            except Exception as e:
                logger.error(f"AI Yanıt Hatası: {e}")
                await message.reply("⚠️ Sinir ağlarında geçici bir dalgalanma oluştu.")
        else:
            await message.reply("⚠️ Yapay zeka çekirdeği çevrimdışı.")

    await bot.process_commands(message)


# --- 6. İMPARATORLUK KOMUT SETİ ---

@bot.hybrid_command(name="yardim", aliases=["help", "komutlar"])
async def yardim_komutu(ctx):
    embed = discord.Embed(
        title="👑 Xyrin İmparatorluğu - Hanedanlık ve Hükümdar Protokolü",
        description="Aktif sistem modülleri:",
        color=discord.Color.dark_purple()
    )
    embed.add_field(name="@BotAdı <mesaj>", value="Yapay zeka sohbeti (Hanedan üyelerine özel hitap ve oto-inşa yetkisi).", inline=False)
    embed.add_field(name="`!ping`", value="🏓 Botun gecikme süresini ölçer.", inline=False)
    embed.add_field(name="`!kahve <tür>`", value="☕ Kahve simülasyonu tetikler.", inline=False)
    embed.add_field(name="`!hologram`", value="🔮 Ses kanalındaki hologram durumunu gösterir.", inline=False)
    embed.add_field(name="`!kufur ac` / `!kufur kapa`", value="🛡️ Küfür koruma sistemini açar veya kapatır (Yönetici).", inline=False)
    embed.add_field(name="`!bakiye` `!gunluk` `!transfer`", value="Ekonomi sistemi.", inline=False)
    embed.add_field(name="`!market` `!satinal`", value="Marketten eşya satın al.", inline=False)
    embed.set_footer(text="Xyrin Empire Core - Hükümdar, Kraliçe ve Süvari Swaarex Zifon Protokolü Aktif")
    await ctx.send(embed=embed)

@bot.hybrid_command(name="ping")
async def ping_komutu(ctx):
    latency = round(bot.latency * 1000)
    embed = discord.Embed(title="🏓 Pong!", description=f"İmparatorluk sinir ağı gecikme süresi: **{latency}ms**", color=discord.Color.green())
    await ctx.send(embed=embed)

@bot.hybrid_command(name="kahve", aliases=["coffee", "espresso"])
async def kahve_komutu(ctx, *, kahve_turu: str = "Espresso"):
    msg = await ctx.send("☕ Kahve çekirdekleri öğütülüyor...")
    await asyncio.sleep(1.2)
    await msg.edit(content=f"🚀 Süvari Swaarex Zifon, Kraliçe Zifon ve Hükümdar hazretleri için özel **{kahve_turu}** hazır!")

@bot.hybrid_command(name="hologram", aliases=["holo"])
async def hologram_durum_komutu(ctx):
    guild_id = ctx.guild.id
    embed = discord.Embed(title="🔮 Xyrin Hologram Projektör", color=discord.Color.teal())
    if guild_id in bot.active_holograms:
        holo = bot.active_holograms[guild_id]
        embed.description = f"Aktif Ses Odası: **{holo['channel'].name}** | Hedef: {holo['target_user'].mention}"
    else:
        embed.description = "Aktif bir ses odası hologramı bulunmuyor."
    await ctx.send(embed=embed)

# --- KÜFÜR SİSTEMİ AÇMA / KAPAMA KOMUTU ---
@bot.hybrid_command(name="kufur", aliases=["profanity"])
@commands.has_permissions(administrator=True)
async def kufur_kontrol_komutu(ctx, durum: str):
    durum = durum.lower().strip()
    if durum in ("ac", "aç", "on", "enable", "aktif"):
        bot.profanity_enabled = True
        await ctx.send("🛡️ Küfür ve Hakaret Filtreleme Sistemi **AKTİFLEŞTİRİLDİ**.")
    elif durum in ("kapa", "kapat", "off", "disable", "pasif"):
        bot.profanity_enabled = False
        await ctx.send("⚠️ Küfür ve Hakaret Filtreleme Sistemi **DEVRE DIŞI BIRAKILDI**.")
    else:
        await ctx.send("❌ Kullanım: `/kufur ac` veya `/kufur kapa`")

@bot.hybrid_command(name="rapor", aliases=["stats"])
async def sunucu_raporu(ctx):
    guild = ctx.guild
    embed = discord.Embed(title=f"📊 {guild.name} - Rapor", color=discord.Color.blue())
    embed.add_field(name="👥 Toplam Üye", value=str(guild.member_count), inline=True)
    embed.add_field(name="🛡️ Küfür Filtresi", value="Aktif" if bot.profanity_enabled else "Pasif", inline=True)
    embed.add_field(name="🤖 Durum", value="Hanedanlık Protokolü Devrede", inline=False)
    await ctx.send(embed=embed)

@bot.hybrid_command(name="bakiye", aliases=["balance", "cuzdan"])
async def bakiye_komutu(ctx, member: discord.Member = None):
    member = member or ctx.author
    account = bot.get_account(member.id)
    embed = discord.Embed(title="🪙 İmparatorluk Hazinesi", color=discord.Color.gold())
    embed.add_field(name="Kullanıcı", value=member.mention, inline=True)
    embed.add_field(name="Bakiye", value=format_balance(account["balance"]), inline=True)
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
    await ctx.send(f"🎁 {ctx.author.mention} günlük ödülün: **{format_balance(reward)}**!")

@bot.hybrid_command(name="transfer", aliases=["pay"])
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
    await ctx.send(f"✅ {ctx.author.mention}, {member.mention} kullanıcısına **{format_balance(miktar)}** gönderdi.")

@bot.hybrid_command(name="market", aliases=["shop"])
async def market_komutu(ctx):
    embed = discord.Embed(title="🏪 İmparatorluk Marketi", description="Satın almak için `!satinal <isim>` yaz.", color=discord.Color.purple())
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
    if item["rol_adi"]:
        role = discord.utils.get(ctx.guild.roles, name=item["rol_adi"])
        if role:
            try:
                await ctx.author.add_roles(role)
            except Exception:
                pass
    await ctx.send(f"✅ {ctx.author.mention}, **{item_adi}** satın alındı!")

if __name__ == "__main__":
    if DISCORD_TOKEN == "BURAYA_DISCORD_BOT_TOKENINI_YAZ":
        logger.critical("Geçerli bir Discord Token yapılandırılmadı!")
    else:
        try:
            logger.info("İmparatorluk Botu başlatılıyor...")
            bot.run(DISCORD_TOKEN)
        except Exception as e:
            logger.critical(f"Çalışma zamanı kritik hatası: {e}")
