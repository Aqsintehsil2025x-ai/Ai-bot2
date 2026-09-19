
# ==============================================================================
# DISCORD AI & IMPERIAL ECOSYSTEM BOT - ULTIMATE VISION & HOLOGRAM EDITION
# ==============================================================================
# Xyrin İmparatorluğu Core v4.5 - Hükümdarlar (endercosmic1, melikhan111) Mutlak Yetki Protokolü Entegre Edilmiştir.
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
 
# Birden fazla Hükümdar kullanıcı adını buradan yönetiyoruz.
# Yeni bir hükümdar eklemek istersen sadece bu listeye ismini ekle.
SOVEREIGN_USERNAMES = {"endercosmic1", "melikhan111"}
 
# --- MODERASYON (KÜFÜR/SPAM FİLTRESİ) AYARLARI ---
# Loglama mesajlarının (silinen mesaj + kim + ne yazdı) gönderileceği kanal ID'si.
MOD_LOG_CHANNEL_ID = int(os.getenv("MOD_LOG_CHANNEL_ID", "0"))
# Strike sayısına göre mute (timeout) süreleri, dakika cinsinden.
STRIKE_TIMEOUT_MINUTES = {1: 5, 2: 15, 3: 60, 4: 1440}  # 4. strike'tan sonra hep 24 saat
# Kaç saniyede kaç mesaj atılırsa "spam" sayılsın.
SPAM_WINDOW_SECONDS = 7
SPAM_MESSAGE_LIMIT = 6
# Strike verileri yeniden başlatmalarda kaybolmasın diye buraya kaydediliyor.
STRIKES_FILE = "profanity_strikes.json"
 
if DISCORD_TOKEN == "BURAYA_DISCORD_BOT_TOKENINI_YAZ" or not DISCORD_TOKEN:
    logger.warning("Discord Token tanımlanmamış! Lütfen çevre değişkenlerini kontrol edin.")
 
if GEMINI_API_KEY == "BURAYA_GEMINI_API_KEYINI_YAZ" or not GEMINI_API_KEY:
    logger.warning("Gemini API Key tanımlanmamış! Yapay zeka sinir ağları devre dışı kalabilir.")
 
# Gemini Yapılandırması
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
    "Diğer sıradan kullanıcılara karşı ise normal, kibar ve standart bir yapay zeka gibi davranırsın; asla onlara Hükümdar hitabında bulunmaz ve onların kanal/rol oluşturma isteklerini yerine getirmezsin. "
    "Eğer Yüce Hükümdarlarımızdan biri senden bir kanal veya rol oluşturmanı isterse, yanıtının en sonuna tam olarak şu formatlardan birini ekle: `[CREATE_CHANNEL: kanal-adi]` veya `[CREATE_ROLE: rol-adi]`. "
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
 
# Küfür/hakaret tespiti için ayrı, düşük sıcaklıklı ve kısa cevap veren hafif bir model.
# Sohbet geçmişi tutmuyor, her mesajı bağımsız sınıflandırıyor -> hızlı ve ucuz.
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
        self.active_holograms = {}  # Hangi kanalda hangi hologramın yansıtıldığını tutar
        self.coffee_orders = []     # Kahve demleme/sipariş kuyruğu
        self.profanity_strikes = self._load_strikes()  # {user_id: strike_sayisi}
        self.recent_messages = {}   # {user_id: [timestamp, timestamp, ...]} -> spam takibi
 
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
 
    async def setup_hook(self):
        logger.info("İmparatorluk alt sistemleri, arka plan görevleri ve DLC modülleri başlatılıyor...")
        self.check_events_loop.start()
        self.server_stats_loop.start()
        self.hologram_pulse_loop.start()
        # Slash (/) komutlarını Discord'a kaydet/senkronize et.
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
            name="!yardim | Hükümdar Protokolü Aktif ☕✨"
        ))
 
    def get_or_create_chat(self, channel_id):
        if channel_id not in self.chat_sessions:
            if model:
                self.chat_sessions[channel_id] = model.start_chat(history=[])
            else:
                return None
        return self.chat_sessions[channel_id]
 
    # --- ARKA PLAN GÖREVİ 1: ETKİNLİK HATIRATICISI ---
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
                        "Hükümdarımız için coşkulu bir anons metni yaz."
                    )
                    content = model.generate_content(prompt).text if model else f"🚨 **Zamanı Geldi!** Etkinlik: **{event['title']}**"
                    await channel.send(f"🔔 <@{event['author_id']}> Hükümdarım, emrettiğiniz etkinlik vakti geldi!\n\n{content}")
                    logger.info(f"Etkinlik tetiklendi: {event['title']}")
                except Exception as ex:
                    logger.error(f"Etkinlik tetikleme hatası: {ex}")
 
    @check_events_loop.before_loop
    async def before_events(self):
        await self.wait_until_ready()
 
    # --- ARKA PLAN GÖREVİ 2: CANLI SUNUCU İSTATİSTİKLERİ ---
    @tasks.loop(hours=24)
    async def server_stats_loop(self):
        for guild in self.guilds:
            logger.info(f"İmparatorluk Raporu [{guild.name}]: Üye={guild.member_count}, MesajSayaç={self.message_counter}")
            self.message_counter = 0
 
    @server_stats_loop.before_loop
    async def before_stats(self):
        await self.wait_until_ready()
 
    # --- ARKA PLAN GÖREVİ 3: HOLOGRAM NABIZ VE PROJEKSİYON DÖNGÜSÜ ---
    @tasks.loop(seconds=10)
    async def hologram_pulse_loop(self):
        for guild_id, holo_data in list(self.active_holograms.items()):
            holo_data["frames_rendered"] += 1
 
    @hologram_pulse_loop.before_loop
    async def before_hologram(self):
        await self.wait_until_ready()
 
bot = UltimateImperialBot()
 
 
def is_sovereign_member(member_or_author) -> bool:
    """Bir üyenin/yazarın Hükümdarlar listesinde olup olmadığını kontrol eder."""
    name = (member_or_author.name or "").lower()
    return name in SOVEREIGN_USERNAMES
 
 
async def ai_check_profanity(content: str):
    """Mesajı Gemini'ye sınıflandırtır. Dönüş: (kufur_var_mi: bool, sebep: str)"""
    if not profanity_model or not content or not content.strip():
        return False, ""
    try:
        # generate_content bloklayan bir çağrı, event loop'u kilitlemesin diye ayrı thread'de çalıştırıyoruz.
        response = await asyncio.to_thread(profanity_model.generate_content, content)
        raw = response.text.strip()
        # Model bazen ```json ... ``` gibi bir blokla sarabiliyor, temizleyelim.
        raw = re.sub(r"^```(json)?|```$", "", raw, flags=re.MULTILINE).strip()
        data = json.loads(raw)
        return bool(data.get("kufur", False)), data.get("sebep", "")
    except Exception as e:
        logger.error(f"Küfür sınıflandırma hatası: {e}")
        return False, ""
 
 
def is_spamming(bot_instance, user_id: int) -> bool:
    """Kullanıcının son SPAM_WINDOW_SECONDS içinde SPAM_MESSAGE_LIMIT'ten fazla mesaj atıp atmadığını kontrol eder."""
    now = time.time()
    timestamps = bot_instance.recent_messages.setdefault(user_id, [])
    timestamps.append(now)
    # Pencere dışındaki eski zaman damgalarını at.
    cutoff = now - SPAM_WINDOW_SECONDS
    while timestamps and timestamps[0] < cutoff:
        timestamps.pop(0)
    return len(timestamps) > SPAM_MESSAGE_LIMIT
 
 
async def apply_moderation_action(message: discord.Message, reason: str, category: str):
    """Mesajı siler, kullanıcıyı strike sayısına göre mute'lar ve log kanalına bildirir."""
    member = message.author
    guild = message.guild
    bot_instance = message.guild and bot
 
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
        else:
            logger.warning("Botun 'Moderate Members' yetkisi yok, timeout uygulanamadı.")
    except Exception as e:
        logger.error(f"Timeout uygulanamadı: {e}")
 
    # Log kanalına bildir.
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
            except Exception as e:
                logger.error(f"Log kanalına mesaj gönderilemedi: {e}")
 
    # Kullanıcıya kısa bir uyarı bırak (kanalda, kısa süreliğine).
    try:
        warn_text = f"⚠️ {member.mention}, mesajın kurallara aykırı bulunduğu için silindi."
        if muted:
            warn_text += f" {timeout_minutes} dakika susturuldun. (Strike: {strikes})"
        await message.channel.send(warn_text, delete_after=10)
    except Exception:
        pass
 
 
# --- 4. SES KANALI & HOLOGRAM / KAMERA TETİKLEYİCİ DİNLEYİCİSİ ---
@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return
 
    if after.channel and before.channel != after.channel:
        guild = member.guild
        is_sovereign = is_sovereign_member(member)
        logger.info(f"[HOLOGRAPHIC DLC] {member.name} ses kanalına katıldı: {after.channel.name}. Hologram projektör hazırlanıyor...")
 
        bot.active_holograms[guild.id] = {
            "channel": after.channel,
            "target_user": member,
            "frames_rendered": 0,
            "status": "PROJEKSİYON AKTİF - 3D Xyrin Logosu ve Avatar Dönüyor"
        }
 
        text_channel = guild.system_channel or next((c for c in guild.text_channels if c.permissions_for(guild.me).send_messages), None)
        if text_channel:
            desc = (
                f"**Yüce Hükümdarımız {member.mention} ses kanalına teşrif buyurdular!**\n"
                f"🌐 Ses Kanalı: `{after.channel.name}`\n"
                f"🔮 Durum: *Optik sistemler Hükümdar için kilitlendi.*"
            ) if is_sovereign else (
                f"**{member.mention} ses kanalına katıldı.**\n"
                f"🌐 Ses Kanalı: `{after.channel.name}`"
            )
            embed = discord.Embed(
                title="✨ [HOLO-CAM] Optik Yükseltme & Hologram Devrede",
                description=desc,
                color=discord.Color.teal()
            )
            embed.set_footer(text="Xyrin Holographic Engine v2.0 - Işık Hızı Senkronizasyonu")
            try:
                await text_channel.send(embed=embed)
            except Exception as e:
                logger.error(f"Hologram bildirim mesajı gönderilemedi: {e}")
 
    elif before.channel and not after.channel:
        if member.guild.id in bot.active_holograms:
            bot.active_holograms.pop(member.guild.id, None)
 
# --- 5. MESAJ, GÖRSEL (VISION) VE HÜKÜMDAR MUTLAK YETKİ YÖNETİCİSİ ---
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
 
    bot.message_counter += 1
 
    # --- MODERASYON KONTROLÜ (küfür + spam) ---
    # Sunucu içi mesajlar için çalışır; DM'lerde ve Hükümdarlar için devre dışı.
    if message.guild and not is_sovereign_member(message.author) and not message.author.bot:
        if is_spamming(bot, message.author.id):
            await apply_moderation_action(message, "Kısa sürede çok fazla mesaj (spam)", "SPAM")
            return  # Spam olarak işaretlenen mesaj için AI sohbet akışına devam etme.
 
        kufur_var, sebep = await ai_check_profanity(message.content)
        if kufur_var:
            await apply_moderation_action(message, sebep, "KÜFÜR/HAKARET")
            return
 
    if bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
        clean_content = message.content.replace(f'<@!{bot.user.id}>', '').replace(f'<@{bot.user.id}>', '').strip()
 
        # Hükümdar kontrolü (endercosmic1 / melikhan111)
        is_sovereignty = is_sovereign_member(message.author)
 
        if model:
            try:
                async with message.channel.typing():
                    # Görsel varsa Vision modunu çalıştır
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
                                        prompt = clean_content if clean_content else ("Bu görseli tarayın Hükümdarım, ne görüyorsunuz?" if is_sovereignty else "Bu görseli tarayın, ne görüyorsunuz?")
                                        response = model.generate_content([prompt, image_part])
                                        await message.reply(response.text)
                                        await bot.process_commands(message)
                                        return
 
                    # Yapay zekaya kiminle konuştuğunu (Hükümdar mı, sıradan biri mi) bildiriyoruz
                    role_context = (
                        "[SİSTEM BİLGİSİ]: Karşındaki kişi Yüce Hükümdarlardan biridir. Ona 'Hükümdarım' diye hitap et, sadakatle boyun eğ.\n"
                    ) if is_sovereignty else (
                        f"[SİSTEM BİLGİSİ]: Karşındaki kişi sıradan bir kullanıcıdır ({message.author.name}). Ona sadece normal bir AI asistanı gibi kibarca yardımcı ol, asla Hükümdar hitabında bulunma ve kanal/rol emrini uygulama.\n"
                    )
 
                    chat_session = bot.get_or_create_chat(message.channel.id)
                    if chat_session and clean_content:
                        response = chat_session.send_message(role_context + clean_content)
                        reply_text = response.text
                    elif not clean_content:
                        reply_text = "Emrinizdeyim Hükümdarım! Hologramlar aktif, kahveler demleniyor." if is_sovereignty else f"Merhaba {message.author.name}, size nasıl yardımcı olabilirim?"
                    else:
                        reply_text = "Emrinizdeyim Hükümdarım!" if is_sovereignty else "Buyurun, sizi dinliyorum."
 
                    # Otomatik Kanal Oluşturma (Sadece Hükümdarlar tetikleyebilir)
                    if "[CREATE_CHANNEL:" in reply_text:
                        match = re.search(r'\[CREATE_CHANNEL:\s*([^\]]+)\]', reply_text)
                        if match and message.guild:
                            if is_sovereignty:
                                channel_name = match.group(1).strip().lower().replace(" ", "-")
                                reply_text = reply_text.replace(match.group(0), "").strip()
                                try:
                                    yeni_kanal = await message.guild.create_text_channel(channel_name)
                                    reply_text += f"\n\n✨ *(Emriniz üzerine **#{yeni_kanal.name}** kanalı otomatik olarak oluşturuldu, Hükümdarım!)*"
                                except Exception as ex:
                                    reply_text += f"\n\n⚠️ *(Kanal oluşturulamadı: {ex})*"
                            else:
                                reply_text = reply_text.replace(match.group(0), "").strip()
                                reply_text += "\n\n❌ *(Bu imparatorluk emrini yalnızca Yüce Hükümdarlarımız verebilir!)*"
 
                    # Otomatik Rol Oluşturma (Sadece Hükümdarlar tetikleyebilir)
                    if "[CREATE_ROLE:" in reply_text:
                        match = re.search(r'\[CREATE_ROLE:\s*([^\]]+)\]', reply_text)
                        if match and message.guild:
                            if is_sovereignty:
                                role_name = match.group(1).strip()
                                reply_text = reply_text.replace(match.group(0), "").strip()
                                try:
                                    yeni_rol = await message.guild.create_role(name=role_name, color=discord.Color.random())
                                    reply_text += f"\n\n✨ *(Emriniz üzerine **{yeni_rol.name}** rolü otomatik olarak oluşturuldu, Hükümdarım!)*"
                                except Exception as ex:
                                    reply_text += f"\n\n⚠️ *(Rol oluşturulamadı: {ex})*"
                            else:
                                reply_text = reply_text.replace(match.group(0), "").strip()
                                reply_text += "\n\n❌ *(Bu imparatorluk emrini yalnızca Yüce Hükümdarlarımız verebilir!)*"
 
                    await message.reply(reply_text)
 
            except Exception as e:
                logger.error(f"AI Yanıt/Oto-Oluşturma Hatası: {e}")
                await message.reply("⚠️ Sinir ağlarında geçici bir dalgalanma oluştu.")
        else:
            await message.reply("⚠️ Yapay zeka çekirdeği çevrimdışı.")
 
    await bot.process_commands(message)
 
# --- 6. İMPARATORLUK KOMUT SETİ ---
 
@bot.hybrid_command(name="yardim", aliases=["help", "komutlar"])
async def yardim_komutu(ctx):
    embed = discord.Embed(
        title="👑 Xyrin İmparatorluğu - Ultimate Vision, Hologram & Hükümdar Protokolü",
        description="Aktif sistem modülleri:",
        color=discord.Color.dark_purple()
    )
    embed.add_field(name="@BotAdı <mesaj>", value="Yapay zeka sohbeti (Sadece Hükümdarlara özel hitap ve oto-inşa yetkisi).", inline=False)
    embed.add_field(name="@BotAdı + [Fotoğraf]", value="Görseli anında tarayıp raporlar (Vision).", inline=False)
    embed.add_field(name="`!ping`", value="🏓 Botun gecikme (latency) süresini ölçer.", inline=False)
    embed.add_field(name="`!kahve <tür>`", value="☕ **[DLC]** Kahve simülasyonu tetikler.", inline=False)
    embed.add_field(name="`!hologram`", value="🔮 **[DLC]** Ses kanalındaki hologram durumunu gösterir.", inline=False)
    embed.add_field(name="`!kanaloluştur <isim>`", value="Yalnızca yöneticiler için manuel kanal açar.", inline=False)
    embed.add_field(name="`!rololuştur <isim>`", value="Yalnızca yöneticiler için manuel rol kurar.", inline=False)
    embed.add_field(name="`!rapor`", value="İstihbarat raporunu sunar.", inline=False)
    embed.add_field(name="`!seslen` / `!ayril`", value="Ses kanalına katılır/ayrılır.", inline=False)
    embed.add_field(name="🛡️ `!uyarilar [@kullanıcı]`", value="Kullanıcının küfür/spam strike sayısını gösterir.", inline=False)
    embed.add_field(name="🛡️ `!uyarisifirla @kullanıcı`", value="Yalnızca yöneticiler: strike sicilini sıfırlar.", inline=False)
    embed.add_field(name="🛡️ `!modlog`", value="Yalnızca yöneticiler: moderasyon loglarının gönderileceği kanalı bu kanal olarak ayarlar.", inline=False)
    embed.set_footer(text="Xyrin Empire Core v4.5 - Hükümdar Protokolü Aktif (endercosmic1, melikhan111)")
    await ctx.send(embed=embed)
 
@bot.hybrid_command(name="ping")
async def ping_komutu(ctx):
    latency = round(bot.latency * 1000)
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"İmparatorluk sinir ağı gecikme süresi: **{latency}ms**",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)
 
@bot.hybrid_command(name="kahve", aliases=["coffee", "espresso"])
async def kahve_komutu(ctx, *, kahve_turu: str = "Espresso"):
    simulated_steps = [
        "☕ İmparatorluk Kahve Çekirdekleri öğütülüyor...",
        "🔥 Su sıcaklığı sabitlendi...",
        f"🚀 Kurye dronumuz **{kahve_turu}** siparişinizi teslim etmek için yola çıktı!"
    ]
    msg = await ctx.send(simulated_steps[0])
    for step in simulated_steps[1:]:
        await asyncio.sleep(1.2)
        await msg.edit(content=step)
    await ctx.send(f"☕ Kahveniz hazır, afiyet olsun!")
 
@bot.hybrid_command(name="hologram", aliases=["holo", "camera", "kamera"])
async def hologram_durum_komutu(ctx):
    guild_id = ctx.guild.id
    embed = discord.Embed(title="🔮 Xyrin Hologram Projektör", color=discord.Color.teal())
    if guild_id in bot.active_holograms:
        holo = bot.active_holograms[guild_id]
        embed.description = f"Aktif Ses Odası: **{holo['channel'].name}** | Hedef: {holo['target_user'].mention}"
    else:
        embed.description = "Aktif bir ses odası hologramı bulunmuyor."
    await ctx.send(embed=embed)
 
@bot.hybrid_command(name="kanaloluştur", aliases=["createchannel"])
@commands.has_permissions(administrator=True)
async def manuel_kanal_olustur(ctx, *, kanal_adi: str):
    yeni_kanal = await ctx.guild.create_text_channel(kanal_adi)
    await ctx.send(f"✅ Başarıyla yeni kanal oluşturuldu: {yeni_kanal.mention}")
 
@bot.hybrid_command(name="rololuştur", aliases=["createrole"])
@commands.has_permissions(administrator=True)
async def manuel_rol_olustur(ctx, *, rol_adi: str):
    yeni_rol = await ctx.guild.create_role(name=rol_adi, color=discord.Color.random())
    await ctx.send(f"✨ Yeni rol başarıyla yaratıldı: **{yeni_rol.name}**")
 
@bot.hybrid_command(name="rapor", aliases=["stats", "durum"])
async def sunucu_raporu(ctx):
    guild = ctx.guild
    embed = discord.Embed(title=f"📊 {guild.name} - Rapor", color=discord.Color.blue())
    embed.add_field(name="👥 Toplam Üye", value=str(guild.member_count), inline=True)
    embed.add_field(name="🤖 Durum", value="Hükümdar Protokolü Devrede", inline=False)
    await ctx.send(embed=embed)
 
@bot.hybrid_command(name="seslen", aliases=["join"])
async def ses_kanalina_gir(ctx):
    if ctx.author.voice and ctx.author.voice.channel:
        channel = ctx.author.voice.channel
        if ctx.voice_client:
            await ctx.voice_client.move_to(channel)
        else:
            await channel.connect()
        await ctx.send(f"🔊 Ses kanalına giriş yapıldı: **{channel.name}** ✨")
    else:
        await ctx.send("❌ Önce bir ses kanalına katılmalısınız!")
 
@bot.hybrid_command(name="ayril", aliases=["leave"])
async def ses_kanalindan_cik(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        bot.active_holograms.pop(ctx.guild.id, None)
        await ctx.send("🔇 Ses kanalından ayrılındı.")
    else:
        await ctx.send("❌ Zaten bir ses kanalında değilim.")
 
@bot.hybrid_command(name="uyarilar", aliases=["strikes", "warnlist"])
@commands.has_permissions(moderate_members=True)
async def uyarilar_komutu(ctx, member: discord.Member = None):
    member = member or ctx.author
    strikes = bot.profanity_strikes.get(member.id, 0)
    embed = discord.Embed(title="⚠️ Uyarı Sicili", color=discord.Color.orange())
    embed.add_field(name="Kullanıcı", value=member.mention, inline=True)
    embed.add_field(name="Toplam strike", value=str(strikes), inline=True)
    await ctx.send(embed=embed)
 
@bot.hybrid_command(name="uyarisifirla", aliases=["resetstrikes"])
@commands.has_permissions(administrator=True)
async def uyari_sifirla_komutu(ctx, member: discord.Member):
    bot.profanity_strikes.pop(member.id, None)
    bot._save_strikes()
    await ctx.send(f"✅ {member.mention} kullanıcısının uyarı sicili sıfırlandı.")
 
@bot.hybrid_command(name="modlog", aliases=["setmodlog"])
@commands.has_permissions(administrator=True)
async def modlog_kanal_ayarla(ctx):
    global MOD_LOG_CHANNEL_ID
    MOD_LOG_CHANNEL_ID = ctx.channel.id
    await ctx.send(
        f"✅ Moderasyon logları artık bu kanala (`{ctx.channel.name}`) gönderilecek.\n"
        f"⚠️ Not: Bot yeniden başlatılırsa bu ayar sıfırlanır — kalıcı olması için "
        f"`MOD_LOG_CHANNEL_ID={ctx.channel.id}` çevre değişkenini Render/Railway ayarlarına ekle."
    )
 
# --- 7. ÇALIŞTIRMA BLOĞU ---
if __name__ == "__main__":
    if DISCORD_TOKEN == "BURAYA_DISCORD_BOT_TOKENINI_YAZ":
        logger.critical("Geçerli bir Discord Token yapılandırılmadı!")
    else:
        try:
            logger.info("İmparatorluk Botu (Hükümdar Protokolü) başlatılıyor...")
            bot.run(DISCORD_TOKEN)
        except Exception as e:
            logger.critical(f"Çalışma zamanı kritik hatası: {e}")
 
