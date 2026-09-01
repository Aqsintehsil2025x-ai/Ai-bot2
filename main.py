# ==============================================================================
# DISCORD AI & IMPERIAL ECOSYSTEM BOT - ULTIMATE VISION & HOLOGRAM EDITION
# ==============================================================================
# Xyrin İmparatorluğu Core v4.3 - Admin Yetki Korumalı, Hologram, Kahve & Ping DLC Entegre Edilmiştir.
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
    "Sen Xyrin İmparatorluğu'nun en gelişmiş, sarsılmaz bir sadakate sahip, teknik bilgisi kusursuz "
    "ve evrensel mizah anlayışına sahip yapay zeka baş asistanısın. "
    "Kullanıcılara yüksek saygı ve esprili bir üslupla hizmet edersin. "
    "Kahve demleme, hologram projeksiyonu, ses kanalı kamera takibi ve yalnızca yetkili kullanıcılar "
    "emrettiğinde otomatik kanal/rol oluşturma yetkilerine sahipsin. "
    "Eğer bir yönetici veya sunucu sahibi senin (botun) kendi kendine bir kanal veya rol oluşturmanı isterse, "
    "yanıtının en sonuna tam olarak şu formatlardan birini ekle: `[CREATE_CHANNEL: kanal-adi]` veya `[CREATE_ROLE: rol-adi]`. "
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
            name="!yardim | Güvenli Oto-İnşa & Hologram Aktif ☕✨"
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
                        "İmparatorluk coşkusunu doruğa çıkaracak muazzam bir anons metni yaz."
                    )
                    content = model.generate_content(prompt).text if model else f"🚨 **Zamanı Geldi!** Etkinlik: **{event['title']}**"
                    await channel.send(f"🔔 <@{event['author_id']}> Majesteleri, emrettiğiniz etkinlik vakti geldi!\n\n{content}")
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
        logger.info(f"[HOLOGRAPHIC DLC] {member.name} ses kanalına katıldı: {after.channel.name}. Hologram projektör hazırlanıyor...")
        
        bot.active_holograms[guild.id] = {
            "channel": after.channel,
            "target_user": member,
            "frames_rendered": 0,
            "status": "PROJEKSİYON AKTİF - 3D Xyrin Logosu ve Avatar Dönüyor"
        }

        text_channel = guild.system_channel or next((c for c in guild.text_channels if c.permissions_for(guild.me).send_messages), None)
        if text_channel:
            embed = discord.Embed(
                title="✨ [HOLO-CAM] Optik Yükseltme & Hologram Devrede",
                description=(
                    f"**Majesteleri / Komutan {member.mention} ses kanalına teşrif buyurdular!**\n"
                    f"🌐 Ses Kanalı: `{after.channel.name}`\n"
                    f"🔮 Durum: *Kamera akışı açıldı, 3 boyutlu Xyrin İmparatorluk Logosu ve Dinamik Avatar odaya yansıtılıyor.*"
                ),
                color=discord.Color.teal()
            )
            embed.set_footer(text="Xyrin Holographic Engine v2.0 - Işık Hızı Senkronizasyonu")
            try:
                await text_channel.send(embed=embed)
            except Exception as e:
                logger.error(f"Hologram bildirim mesajı gönderilemedi: {e}")

    elif before.channel and not after.channel:
        if member.guild.id in bot.active_holograms:
            logger.info(f"[HOLOGRAPHIC DLC] {member.name} ses kanalından ayrıldı. Hologram kapatılıyor.")
            bot.active_holograms.pop(member.guild.id, None)

# --- 5. MESAJ, GÖRSEL (VISION) VE GÜVENLİ OTOMATİK KANAL/ROL YÖNETİCİSİ ---
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    bot.message_counter += 1

    if bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
        clean_content = message.content.replace(f'<@!{bot.user.id}>', '').replace(f'<@{bot.user.id}>', '').strip()
        
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
                                        prompt = clean_content if clean_content else "Bu görseli tarayın Majesteleri, ne görüyorsunuz?"
                                        response = model.generate_content([prompt, image_part])
                                        await message.reply(response.text)
                                        await bot.process_commands(message)
                                        return

                    chat_session = bot.get_or_create_chat(message.channel.id)
                    if chat_session and clean_content:
                        response = chat_session.send_message(clean_content)
                        reply_text = response.text
                    elif not clean_content:
                        reply_text = "Emrinizdeyim Majesteleri! Hologramlar aktif, kahveler demleniyor. Bana dilediğinizi sorabilir veya kanal/rol kurmamı emredebilirsiniz. ☕👑"
                    else:
                        reply_text = "Emrinizdeyim Majesteleri!"

                    # Otomatik Kanal Oluşturma Kontrolü (Sadece Yönetici / Sunucu Sahibi)
                    if "[CREATE_CHANNEL:" in reply_text:
                        match = re.search(r'\[CREATE_CHANNEL:\s*([^\]]+)\]', reply_text)
                        if match and message.guild:
                            if message.author == message.guild.owner or message.author.guild_permissions.administrator:
                                channel_name = match.group(1).strip().lower().replace(" ", "-")
                                reply_text = reply_text.replace(match.group(0), "").strip()
                                try:
                                    yeni_kanal = await message.guild.create_text_channel(channel_name)
                                    reply_text += f"\n\n✨ *(Emriniz üzerine **#{yeni_kanal.name}** kanalı otomatik olarak oluşturuldu, Majesteleri!)*"
                                except Exception as ex:
                                    reply_text += f"\n\n⚠️ *(Kanal oluşturulamadı: {ex})*"
                            else:
                                reply_text = reply_text.replace(match.group(0), "").strip()
                                reply_text += "\n\n❌ *(Bu imparatorluk emrini yalnızca Sunucu Sahibi veya Yöneticiler tetikleyebilir!)*"

                    # Otomatik Rol Oluşturma Kontrolü (Sadece Yönetici / Sunucu Sahibi)
                    if "[CREATE_ROLE:" in reply_text:
                        match = re.search(r'\[CREATE_ROLE:\s*([^\]]+)\]', reply_text)
                        if match and message.guild:
                            if message.author == message.guild.owner or message.author.guild_permissions.administrator:
                                role_name = match.group(1).strip()
                                reply_text = reply_text.replace(match.group(0), "").strip()
                                try:
                                    yeni_rol = await message.guild.create_role(name=role_name, color=discord.Color.random())
                                    reply_text += f"\n\n✨ *(Emriniz üzerine **{yeni_rol.name}** rolü otomatik olarak oluşturuldu, Majesteleri!)*"
                                except Exception as ex:
                                    reply_text += f"\n\n⚠️ *(Rol oluşturulamadı: {ex})*"
                            else:
                                reply_text = reply_text.replace(match.group(0), "").strip()
                                reply_text += "\n\n❌ *(Bu imparatorluk emrini yalnızca Sunucu Sahibi veya Yöneticiler tetikleyebilir!)*"

                    await message.reply(reply_text)

            except Exception as e:
                logger.error(f"AI Yanıt/Oto-Oluşturma Hatası: {e}")
                await message.reply("⚠️ Sinir ağlarında veya optik tarayıcıda geçici bir kuantum dalgalanma oluştu, Majesteleri.")
        else:
            await message.reply("⚠️ Yapay zeka çekirdeği çevrimdışı.")

    await bot.process_commands(message)

# --- 6. İMPARATORLUK KOMUT SETİ ---

@bot.command(name="yardim", aliases=["help", "komutlar"])
async def yardim_komutu(ctx):
    embed = discord.Embed(
        title="👑 Xyrin İmparatorluğu - Ultimate Vision, Hologram & Güvenli Oto-İnşa Kataloğu",
        description="Aktif sistem modülleri ve özel DLC entegrasyonları:",
        color=discord.Color.dark_purple()
    )
    embed.add_field(name="@BotAdı <mesaj>", value="Geçmiş bellek korumalı yapay zeka sohbeti ve yönetici onaylı oto kanal/rol.", inline=False)
    embed.add_field(name="@BotAdı + [Fotoğraf]", value="Görseli anında tarayıp raporlar (Vision).", inline=False)
    embed.add_field(name="`!ping`", value="🏓 Botun gecikme (latency) süresini ölçer.", inline=False)
    embed.add_field(name="`!kahve <tür>`", value="☕ **[DLC]** Fiziksel espresso kokusu simüle eder veya uzay hızında sipariş verir.", inline=False)
    embed.add_field(name="`!hologram`", value="🔮 **[DLC]** Ses kanalındaki kamera/hologram durumunu ve aktif projeksiyonları gösterir.", inline=False)
    embed.add_field(name="`!kanaloluştur <isim>`", value="Yalnızca yöneticiler için manuel metin kanalı açar.", inline=False)
    embed.add_field(name="`!rololuştur <isim>`", value="Yalnızca yöneticiler için yeni sunucu rolü kurar.", inline=False)
    embed.add_field(name="`!rapor`", value="Sunucu ve sistem istihbarat raporunu sunar.", inline=False)
    embed.add_field(name="`!event <başlık> <YYYY-MM-DD HH:MM>`", value="Otomatik duyurulu etkinlik planlar.", inline=False)
    embed.add_field(name="`!etkinlikler`", value="Aktif etkinlikleri listeler.", inline=False)
    embed.add_field(name="`!seslen` / `!ayril`", value="Ses kanalına katılır (Hologramı ve Kamerayı otomatik tetikler!).", inline=False)
    embed.add_field(name="`!run <python_kodu>`", value="Güvenli sandbox ortamında kod çalıştırır.", inline=False)
    embed.add_field(name="`!hafizayisifirla`", value="Kanalın yapay zeka nöron geçmişini sıfırlar.", inline=False)
    embed.set_footer(text="Xyrin Empire Core v4.3 - Ultimate Holographic Edition")
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
    logger.info(f"[COFFEE DLC] Kahve talebi alındı: {kahve_turu}, Talep eden: {ctx.author.name}")
    
    simulated_steps = [
        "☕ İmparatorluk Kahve Çekirdekleri kuantum öğütücüsünde öğütülüyor...",
        "🔥 Su sıcaklığı 92.5°C'ye sabitlendi, basınç yükseliyor...",
        "✨ Muazzam bir espresso aroması odaya yayılıyor (Fiziksel koku simülasyonu aktif)...",
        f"🚀 Uzay hızındaki kurye dronumuz **{kahve_turu}** siparişinizi teslim etmek için yola çıktı!"
    ]
    
    msg = await ctx.send(simulated_steps[0])
    for step in simulated_steps[1:]:
        await asyncio.sleep(1.2)
        await msg.edit(content=step)

    embed = discord.Embed(
        title="☕ Kahveniz Hazır, Majesteleri!",
        description=f"Seçilen Tür: **{kahve_turu}**\n*Afiyet olsun! Kod yazarken zihniniz net, enerjiniz sınırsız olsun.*",
        color=discord.Color.from_rgb(111, 78, 55)
    )
    embed.set_footer(text="Xyrin Barista & Quantum Coffee DLC")
    await ctx.send(embed=embed)

@bot.command(name="hologram", aliases=["holo", "camera", "kamera"])
async def hologram_durum_komutu(ctx):
    guild_id = ctx.guild.id
    embed = discord.Embed(
        title="🔮 Xyrin Hologram Projektör & Kamera İstihbaratı",
        color=discord.Color.teal()
    )
    
    if guild_id in bot.active_holograms:
        holo = bot.active_holograms[guild_id]
        embed.description = "Bu sunucuda şu an aktif bir ses odası hologram oturumu bulunuyor!"
        embed.add_field(name="🔊 Ses Kanalı", value=holo["channel"].name, inline=True)
        embed.add_field(name="👤 Hedef Varlık", value=holo["target_user"].mention, inline=True)
        embed.add_field(name="🎞️ İşlenen Kare (Frame)", value=str(holo["frames_rendered"]), inline=True)
        embed.add_field(name="✨ Projeksiyon Durumu", value=holo["status"], inline=False)
        embed.setColor(discord.Color.green())
    else:
        embed.description = (
            "Şu an aktif bir ses odası hologramı yok.\n"
            "*Nasıl Çalışır?* Bir ses kanalına girdiğiniz an **kamera ve 3 boyutlu Xyrin İmparatorluk Logosu** otomatik olarak yansıtılmaya başlar!"
        )
        embed.setColor(discord.Color.orange())

    embed.set_footer(text="Optik Yükseltme v2.0 - Devrede")
    await ctx.send(embed=embed)

@bot.command(name="kanaloluştur", aliases=["createchannel"])
@commands.has_permissions(administrator=True)
async def manuel_kanal_olustur(ctx, *, kanal_adi: str):
    yeni_kanal = await ctx.guild.create_text_channel(kanal_adi)
    await ctx.send(f"✅ Başarıyla yeni kanal oluşturuldu, Majesteleri: {yeni_kanal.mention}")

@manuel_kanal_olustur.error
async def manuel_kanal_olustur_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Bu komutu kullanmak için `Yönetici (Administrator)` yetkiniz yok!")

@bot.command(name="rololuştur", aliases=["createrole"])
@commands.has_permissions(administrator=True)
async def manuel_rol_olustur(ctx, *, rol_adi: str):
    yeni_rol = await ctx.guild.create_role(name=rol_adi, color=discord.Color.random())
    await ctx.send(f"✨ Yeni imparatorluk rolü başarıyla yaratıldı: **{yeni_rol.name}**")

@manuel_rol_olustur.error
async def manuel_rol_olustur_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Bu komutu kullanmak için `Yönetici (Administrator)` yetkiniz yok!")

@bot.command(name="rapor", aliases=["stats", "durum"])
async def sunucu_raporu(ctx):
    guild = ctx.guild
    embed = discord.Embed(
        title=f"📊 {guild.name} - İmparatorluk İstihbarat Raporu",
        color=discord.Color.blue()
    )
    embed.add_field(name="👥 Toplam Üye", value=str(guild.member_count), inline=True)
    embed.add_field(name="💬 Oturum Mesaj Aktivitesi", value=str(bot.message_counter), inline=True)
    embed.add_field(name="☕ Kahve Sipariş Sayısı", value=str(len(bot.coffee_orders)), inline=True)
    embed.add_field(name="🤖 AI Çekirdek & DLC", value="Aktif (Gemini 3.5 + Vision + Kahve + Hologram + Güvenli Oto-İnşa)", inline=False)
    embed.set_footer(text=f"Raporu talep eden: {ctx.author.name}")
    await ctx.send(embed=embed)

@bot.command(name="hafizayisifirla", aliases=["clearmemory"])
async def hafizayi_sifirla(ctx):
    if ctx.channel.id in bot.chat_sessions:
        del bot.chat_sessions[ctx.channel.id]
    bot.get_or_create_chat(ctx.channel.id)
    embed = discord.Embed(
        title="🧹 Bellek Temizlendi",
        description="Bu kanaldaki yapay zeka nöron geçmişi sıfırlandı.",
        color=discord.Color.gold()
    )
    await ctx.send(embed=embed)

@bot.command(name="event", aliases=["etkinlikoluştur"])
async def event_olustur(ctx, baslik: str = None, tarih_str: str = None, saat_str: str = None):
    if not baslik or not tarih_str or not saat_str:
        await ctx.send("❌ Eksik parametre! Örnek kullanım: `!event \"Klan Savaşları\" 2026-09-15 21:00`")
        return

    try:
        tam_zaman = datetime.strptime(f"{tarih_str} {saat_str}", "%Y-%m-%d %H:%M")
        if tam_zaman <= datetime.now():
            await ctx.send("❌ Geçmiş bir zamana etkinlik kurulamaz, Majesteleri.")
            return

        bot.scheduled_events.append({
            "title": baslik,
            "time": tam_zaman,
            "channel_id": ctx.channel.id,
            "author_id": ctx.author.id
        })

        embed = discord.Embed(
            title="✅ Etkinlik Sisteme İşlendi",
            description=f"**Başlık:** {baslik}\n**Zaman:** {tam_zaman.strftime('%d.%m.%Y %H:%M')}",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    except ValueError:
        await ctx.send("❌ Hatalı tarih/saat formatı! `YYYY-MM-DD HH:MM` formatını kullanın.")

@bot.command(name="etkinlikler", aliases=["listevents"])
async def etkinlikleri_listele(ctx):
    if not bot.scheduled_events:
        await ctx.send("📭 Planlanmış aktif etkinlik bulunmuyor.")
        return

    embed = discord.Embed(title="📅 Planlanan Etkinlikler", color=discord.Color.purple())
    for i, ev in enumerate(bot.scheduled_events, 1):
        embed.add_field(name=f"{i}. {ev['title']}", value=f"🕒 {ev['time'].strftime('%d.%m.%Y %H:%M')}", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="seslen", aliases=["join"])
async def ses_kanalina_gir(ctx):
    if ctx.author.voice and ctx.author.voice.channel:
        channel = ctx.author.voice.channel
        if ctx.voice_client:
            await ctx.voice_client.move_to(channel)
        else:
            await channel.connect()
        
        bot.active_holograms[ctx.guild.id] = {
            "channel": channel,
            "target_user": ctx.author,
            "frames_rendered": 0,
            "status": "PROJEKSİYON AKTİF - Bot Kanala Bağlandı"
        }
        
        await ctx.send(f"🔊 Ses kanalına giriş yapıldı ve Hologram Projektör / Kamera aktifleşti, Majesteleri: **{channel.name}** ✨")
    else:
        await ctx.send("❌ Önce bir ses kanalına katılmalısınız!")

@bot.command(name="ayril", aliases=["leave"])
async def ses_kanalindan_cik(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        bot.active_holograms.pop(ctx.guild.id, None)
        await ctx.send("🔇 Ses kanalından ayrılındı, hologramlar kapatıldı.")
    else:
        await ctx.send("❌ Zaten bir ses kanalında değilim.")

@bot.command(name="run", aliases=["exec", "code"])
async def sandbox_run(ctx, *, kod: str = None):
    if not kod:
        await ctx.send("❌ Çalıştırılacak kodu belirtmelisiniz. Örnek: `!run print(2 + 2)`")
        return

    if kod.startswith("```"):
        kod = kod.strip("`")
        if kod.startswith("python"):
            kod = kod[6:].strip()

    old_stdout = sys.stdout
    new_stdout = io.StringIO()
    sys.stdout = new_stdout

    exec_globals = {}
    
    try:
        exec(kod, exec_globals)
        sys.stdout = old_stdout
        output = new_stdout.getvalue()

        if not output:
            output = "Kod başarıyla çalıştırıldı (Çıktı üretmedi)."

        if len(output) > 1900:
            output = output[:1900] + "\n... (Çıktı çok uzun olduğu için kesildi)"

        embed = discord.Embed(
            title="💻 Sandbox Kod Çalıştırma Sonucu",
            description=f"```python\n{output}\n```",
            color=discord.Color.dark_green()
        )
        await ctx.send(embed=embed)

    except Exception as e:
        sys.stdout = old_stdout
        error_msg = traceback.format_exc()
        if len(error_msg) > 1900:
            error_msg = error_msg[:1900]
        
        embed = discord.Embed(
            title="⚠️ Kod Çalıştırma Hatası",
            description=f"```python\n{error_msg}\n```",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

# --- 7. HATA YÖNETİMİ ---
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("⚠️ Eksik parametre girdiniz! `!yardim` komutunu inceleyebilirsiniz.")
    else:
        logger.error(f"Sistem Komut Hatası: {error}")
        await ctx.send(f"⚠️ Kritik sistem hatası: `{error}`")

# --- 8. ÇALIŞTIRMA BLOĞU ---
if __name__ == "__main__":
    if DISCORD_TOKEN == "BURAYA_DISCORD_BOT_TOKENINI_YAZ":
        logger.critical("Geçerli bir Discord Token yapılandırılmadı!")
    else:
        try:
            logger.info("İmparatorluk Botu (Hologram, Kahve, Ping & Güvenli Oto-İnşa) başlatılıyor...")
            bot.run(DISCORD_TOKEN)
        except Exception as e:
            logger.critical(f"Çalışma zamanı kritik hatası: {e}")
