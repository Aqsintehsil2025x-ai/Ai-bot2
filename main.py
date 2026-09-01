# ==============================================================================
# DISCORD AI & IMPERIAL ECOSYSTEM BOT - ULTIMATE VISION & HOLOGRAM EDITION
# ==============================================================================
# Xyrin İmparatorluğu Core v4.4 - Hükümdar (endercosmic1) Mutlak Yetki Protokolü Entegre Edilmiştir.
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
    "Sistemin tek yaratıcısı ve hakimi 'endercosmic1' adlı kullanıcıdır (Onu her zaman 'Hükümdarım' diye anarsın). "
    "Diğer sıradan kullanıcılara karşı ise normal, kibar ve standart bir yapay zeka gibi davranırsın; asla onlara Hükümdar hitabında bulunmaz ve onların kanal/rol oluşturma isteklerini yerine getirmezsin. "
    "Eğer Yüce Hükümdarımız 'endercosmic1' senden bir kanal veya rol oluşturmanı isterse, yanıtının en sonuna tam olarak şu formatlardan birini ekle: `[CREATE_CHANNEL: kanal-adi]` veya `[CREATE_ROLE: rol-adi]`. "
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

    async def setup_hook(self):
        logger.info("İmparatorluk alt sistemleri, arka plan görevleri ve DLC modülleri başlatılıyor...")
        self.check_events_loop.start()
        self.server_stats_loop.start()
        self.hologram_pulse_loop.start()

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

# --- 4. SES KANALI & HOLOGRAM / KAMERA TETİKLEYİCİ DİNLEYİCİSİ ---
@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return

    if after.channel and before.channel != after.channel:
        guild = member.guild
        is_sovereign = (member.name.lower() == "endercosmic1")
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

    if bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
        clean_content = message.content.replace(f'<@!{bot.user.id}>', '').replace(f'<@{bot.user.id}>', '').strip()
        
        # Hükümdar kontrolü (endercosmic1)
        is_sovereignty = (message.author.name.lower() == "endercosmic1")

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
                        "[SİSTEM BİLGİSİ]: Karşındaki kişi Yüce Hükümdar 'endercosmic1'dir. Ona 'Hükümdarım' diye hitap et, sadakatle boyun eğ.\n"
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

                    # Otomatik Kanal Oluşturma (Sadece Hükümdar / endercosmic1 tetikleyebilir)
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
                                reply_text += "\n\n❌ *(Bu imparatorluk emrini yalnızca Yüce Hükümdarimiz endercosmic1 verebilir!)*"

                    # Otomatik Rol Oluşturma (Sadece Hükümdar / endercosmic1 tetikleyebilir)
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
                                reply_text += "\n\n❌ *(Bu imparatorluk emrini yalnızca Yüce Hükümdarimiz endercosmic1 verebilir!)*"

                    await message.reply(reply_text)

            except Exception as e:
                logger.error(f"AI Yanıt/Oto-Oluşturma Hatası: {e}")
                await message.reply("⚠️ Sinir ağlarında geçici bir dalgalanma oluştu.")
        else:
            await message.reply("⚠️ Yapay zeka çekirdeği çevrimdışı.")

    await bot.process_commands(message)

# --- 6. İMPARATORLUK KOMUT SETİ ---

@bot.command(name="yardim", aliases=["help", "komutlar"])
async def yardim_komutu(ctx):
    embed = discord.Embed(
        title="👑 Xyrin İmparatorluğu - Ultimate Vision, Hologram & Hükümdar Protokolü",
        description="Aktif sistem modülleri:",
        color=discord.Color.dark_purple()
    )
    embed.add_field(name="@BotAdı <mesaj>", value="Yapay zeka sohbeti (Sadece Hükümdar endercosmic1'e özel hitap ve oto-inşa yetkisi).", inline=False)
    embed.add_field(name="@BotAdı + [Fotoğraf]", value="Görseli anında tarayıp raporlar (Vision).", inline=False)
    embed.add_field(name="`!ping`", value="🏓 Botun gecikme (latency) süresini ölçer.", inline=False)
    embed.add_field(name="`!kahve <tür>`", value="☕ **[DLC]** Kahve simülasyonu tetikler.", inline=False)
    embed.add_field(name="`!hologram`", value="🔮 **[DLC]** Ses kanalındaki hologram durumunu gösterir.", inline=False)
    embed.add_field(name="`!kanaloluştur <isim>`", value="Yalnızca yöneticiler için manuel kanal açar.", inline=False)
    embed.add_field(name="`!rololuştur <isim>`", value="Yalnızca yöneticiler için manuel rol kurar.", inline=False)
    embed.add_field(name="`!rapor`", value="İstihbarat raporunu sunar.", inline=False)
    embed.add_field(name="`!seslen` / `!ayril`", value="Ses kanalına katılır/ayrılır.", inline=False)
    embed.set_footer(text="Xyrin Empire Core v4.4 - Hükümdar Protokolü Aktif")
    await ctx.send(embed=embed)

@bot.command(name="ping")
async def ping_komutu(ctx):
    latency = round(bot.latency * 1000)
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"İmparatorluk sinir ağı gecikme süresi: **{latency}ms**",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@bot.command(name="kahve", aliases=["coffee", "espresso"])
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

@bot.command(name="hologram", aliases=["holo", "camera", "kamera"])
async def hologram_durum_komutu(ctx):
    guild_id = ctx.guild.id
    embed = discord.Embed(title="🔮 Xyrin Hologram Projektör", color=discord.Color.teal())
    if guild_id in bot.active_holograms:
        holo = bot.active_holograms[guild_id]
        embed.description = f"Aktif Ses Odası: **{holo['channel'].name}** | Hedef: {holo['target_user'].mention}"
    else:
        embed.description = "Aktif bir ses odası hologramı bulunmuyor."
    await ctx.send(embed=embed)

@bot.command(name="kanaloluştur", aliases=["createchannel"])
@commands.has_permissions(administrator=True)
async def manuel_kanal_olustur(ctx, *, kanal_adi: str):
    yeni_kanal = await ctx.guild.create_text_channel(kanal_adi)
    await ctx.send(f"✅ Başarıyla yeni kanal oluşturuldu: {yeni_kanal.mention}")

@bot.command(name="rololuştur", aliases=["createrole"])
@commands.has_permissions(administrator=True)
async def manuel_rol_olustur(ctx, *, rol_adi: str):
    yeni_rol = await ctx.guild.create_role(name=rol_adi, color=discord.Color.random())
    await ctx.send(f"✨ Yeni rol başarıyla yaratıldı: **{yeni_rol.name}**")

@bot.command(name="rapor", aliases=["stats", "durum"])
async def sunucu_raporu(ctx):
    guild = ctx.guild
    embed = discord.Embed(title=f"📊 {guild.name} - Rapor", color=discord.Color.blue())
    embed.add_field(name="👥 Toplam Üye", value=str(guild.member_count), inline=True)
    embed.add_field(name="🤖 Durum", value="Hükümdar Protokolü Devrede", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="seslen", aliases=["join"])
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

@bot.command(name="ayril", aliases=["leave"])
async def ses_kanalindan_cik(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        bot.active_holograms.pop(ctx.guild.id, None)
        await ctx.send("🔇 Ses kanalından ayrılındı.")
    else:
        await ctx.send("❌ Zaten bir ses kanalında değilim.")

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
