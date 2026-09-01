# ==============================================================================
# DISCORD AI & IMPERIAL ECOSYSTEM BOT - ULTIMATE PRO EDITION (~1000 LINES ARCH)
# ==============================================================================

import os
import sys
import time
import io
import traceback
import contextlib
import asyncio
import logging
from datetime import datetime, timedelta
import discord
from discord.ext import commands, tasks
import google.generativeai as genai

# --- 1. LOGLAMA YAPILANDIRMASI ---
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("ImperialBot")

# --- 2. ÇEVRESEL DEĞİŞKENLER VE YAPILANDIRMA ---
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "BURAYA_DISCORD_BOT_TOKENINI_YAZ")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "BURAYA_GEMINI_API_KEYINI_YAZ")

if DISCORD_TOKEN == "BURAYA_DISCORD_BOT_TOKENINI_YAZ" or not DISCORD_TOKEN:
    logger.warning("Discord Token tanımlanmamış! Lütfen Railway Variables kısmını kontrol edin.")

if GEMINI_API_KEY == "BURAYA_GEMINI_API_KEYINI_YAZ" or not GEMINI_API_KEY:
    logger.warning("Gemini API Key tanımlanmamış! Yapay zeka özellikleri devre dışı kalabilir.")

# Gemini API Yapılandırması
genai.configure(api_key=GEMINI_API_KEY)

generation_config = {
    "temperature": 0.8,
    "top_p": 0.95,
    "max_output_tokens": 1500,
}

SYSTEM_INSTRUCTION = (
    "Sen Xyrin İmparatorluğu'nun en gelişmiş, sadık, teknik bilgisi kusursuz ve esprili yapay zeka baş asistanısın. "
    "Kullanıcılara (özellikle İmparator'a) yüksek sadakatle hizmet eder, sunucu yönetiminde, etkinlik planlamada, "
    "müzik/ses operasyonlarında ve kod analizlerinde en üst düzey profesyonelliği sunarsın. "
    "Geçmiş sohbetleri hafızanda tutar ve karakterine uygun, havalı bir üslupla yanıt verirsin."
)

try:
    model = genai.GenerativeModel(
        model_name="gemini-3.5-flash-lite",
        generation_config=generation_config,
        system_instruction=SYSTEM_INSTRUCTION
    )
    logger.info("Gemini modeli ('gemini-3.5-flash-lite') başarıyla entegre edildi.")
except Exception as e:
    logger.error(f"Gemini modeli yüklenirken kritik hata: {e}")
    model = None

# --- 3. DISCORD INTENTS VE GELİŞMİŞ BOT SINIFI ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.voice_states = True

class UltimateImperialBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents, help_command=None)
        # Bellek İçi Veritabanı ve Sayaçlar
        self.scheduled_events = []
        self.chat_sessions = {}
        self.message_counter = 0
        self.active_voice_client = None

    async def setup_hook(self):
        logger.info("İmparatorluk alt sistemleri ve arka plan görevleri başlatılıyor...")
        self.check_events_loop.start()
        self.server_stats_loop.start()

    async def on_ready(self):
        logger.info(f"Bot başarıyla çevrimiçi: {self.user} (ID: {self.user.id})")
        logger.info(f"Hizmet verilen clan/sunucu sayısı: {len(self.guilds)}")
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name="!yardim | İmparatorluk Sistemi Aktif"))

    def get_or_create_chat(self, channel_id):
        """Kanal bazlı akıllı sohbet oturumu (hafıza) yöneticisi."""
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
                        "Katılımcıları coşturan, heyecan verici, imparatorluk temalı dikkat çekici bir duyuru metni yaz."
                    )
                    if model:
                        ai_resp = model.generate_content(prompt)
                        content = ai_resp.text
                    else:
                        content = f"🚨 **Zamanı Geldi!** Etkinlik başladı: **{event['title']}**"

                    await channel.send(f"🔔 <@{event['author_id']}> Majestelerinin emrettiği etkinlik vakti geldi!\n\n{content}")
                    logger.info(f"Etkinlik tetiklendi: {event['title']}")
                except Exception as ex:
                    logger.error(f"Etkinlik tetikleme hatası: {ex}")

    @check_events_loop.before_loop
    async def before_events(self):
        await self.wait_until_ready()

    # --- ARKA PLAN GÖREVİ 2: CANLI SUNUCU İSTATİSTİKLERİ VE GÜNLÜK RAPOR ---
    @tasks.loop(hours=24)
    async def server_stats_loop(self):
        """Her 24 saatte bir sunucu istatistiklerini loglar ve genel duruma rapor hazırlar."""
        for guild in self.guilds:
            logger.info(f"İmparatorluk Raporu [{guild.name}]: Toplam Üye: {guild.member_count}, Aktif Mesaj Sayısı (Son döngü): {self.message_counter}")
            self.message_counter = 0 # Sayaç sıfırlanır

    @server_stats_loop.before_loop
    async def before_stats(self):
        await self.wait_until_ready()

bot = UltimateImperialBot()

# --- 4. OLAY YÖNETİCİSİ VE YAPAY ZEKA KÖPRÜSÜ ---

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Mesaj sayacını artır (İstatistikler için)
    bot.message_counter += 1

    # Etiketlenme veya DM durumunda yapay zeka tetiklenir
    if bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
        clean_content = message.content.replace(f'<@!{bot.user.id}>', '').replace(f'<@{bot.user.id}>', '').strip()
        
        if clean_content:
            if model:
                try:
                    async with message.channel.typing():
                        chat_session = bot.get_or_create_chat(message.channel.id)
                        if chat_session:
                            response = chat_session.send_message(clean_content)
                            await message.reply(response.text)
                        else:
                            await message.reply("⚠️ Hafıza oturumu başlatılamadı.")
                except Exception as e:
                    logger.error(f"AI Yanıt Hatası: {e}")
                    await message.reply("⚠️ Yapay zeka sinir ağlarında geçici bir dalgalanma oluştu, Majesteleri.")
            else:
                await message.reply("⚠️ Yapay zeka çekirdeği çevrimdışı.")

    await bot.process_commands(message)

# --- 5. İMPARATORLUK KOMUT SETİ ---

@bot.command(name="yardim", aliases=["help", "komutlar"])
async def yardim_komutu(ctx):
    embed = discord.Embed(
        title="👑 Xyrin İmparatorluğu - Gelişmiş Komut Kataloğu",
        description="Sistemde aktif olan tüm yüksek seviyeli modüller aşağıdadır:",
        color=discord.Color.dark_purple()
    )
    embed.add_field(name="@BotAdı <mesaj>", value="Geçmiş sohbet hafızasını koruyarak yapay zeka ile konuşmanızı sağlar.", inline=False)
    embed.add_field(name="`!rapor`", value="Sunucunun anlık üye ve aktivite istatistiklerini raporlar.", inline=False)
    embed.add_field(name="`!event <başlık> <YYYY-MM-DD HH:MM>`", value="Belirtilen zaman için otomatik duyurulu etkinlik kurar.", inline=False)
    embed.add_field(name="`!etkinlikler`", value="Aktif planlanmış etkinlikleri listeler.", inline=False)
    embed.add_field(name="`!seslen <kanal>`", value="Botun ses kanalınıza bağlanmasını sağlar.", inline=False)
    embed.add_field(name="`!ayril`", value="Botun ses kanalından çıkmasını sağlar.", inline=False)
    embed.add_field(name="`!run <python_kodu>`", value="Güvenli sandbox ortamında python kodu çalıştırıp sonucunu döner.", inline=False)
    embed.add_field(name="`!hafizayisifirla`", value="Kanalın AI hafızasını sıfırlar.", inline=False)
    embed.set_footer(text="Xyrin Empire Core v3.5 - Ultimate Edition")
    await ctx.send(embed=embed)

@bot.command(name="rapor", aliases=["stats", "durum"])
async def sunucu_raporu(ctx):
    guild = ctx.guild
    embed = discord.Embed(
        title=f"📊 {guild.name} - İmparatorluk İstihbarat Raporu",
        color=discord.Color.blue()
    )
    embed.add_field(name="👥 Toplam Üye", value=str(guild.member_count), inline=True)
    embed.add_field(name="💬 Oturum Mesaj Aktivitesi", value=str(bot.message_counter), inline=True)
    embed.add_field(name="🤖 AI Çekirdek Durumu", value="Aktif (Gemini 3.5 Flash Lite)", inline=False)
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

# --- ETKİNLİK KOMUTLARI ---

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
            value=f"**Başlık:** {baslik}\n**Zaman:** {tam_zaman.strftime('%d.%m.%Y %H:%M')}",
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

# --- SES VE MÜZİK ALTYAPI KOMUTLARI ---

@bot.command(name="seslen", aliases=["join"])
async def ses_kanalina_gir(ctx):
    if ctx.author.voice and ctx.author.voice.channel:
        channel = ctx.author.voice.channel
        if ctx.voice_client:
            await ctx.voice_client.move_to(channel)
        else:
            await channel.connect()
        await ctx.send(f"🔊 Ses kanalına giriş yapıldı, Majesteleri: **{channel.name}**")
    else:
        await ctx.send("❌ Önce bir ses kanalına katılmalısınız!")

@bot.command(name="ayril", aliases=["leave"])
async def ses_kanalindan_cik(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("🔇 Ses kanalından ayrılindi.")
    else:
        await ctx.send("❌ Zaten bir ses kanalında değilim.")

# --- GÜVENLİ KOD ÇALIŞTIRMA (SANDBOX) KOMUTU ---

@bot.command(name="run", aliases=["exec", "code"])
async def sandbox_run(ctx, *, kod: str = None):
    """Python kodlarını güvenli bir akışta test etmek için sandbox komutu"""
    if not kod:
        await ctx.send("❌ Çalıştırılacak kodu belirtmelisiniz. Örnek: `!run print(2 + 2)`")
        return

    # Markdown blok temizliği (```python ... ``` temizleme)
    if kod.startswith("```"):
        kod = kod.strip("`")
        if kod.startswith("python"):
            kod = kod[6:].strip()

    # Çıktıyı yakalamak için buffer
    old_stdout = sys.stdout
    new_stdout = io.StringIO()
    sys.stdout = new_stdout

    exec_globals = {}
    
    try:
        # Sınırlı güvenli çalıştırma ortamı
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

# --- 6. HATA YÖNETİMİ ---
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("⚠️ Eksik parametre girdiniz! `!yardim` komutunu inceleyebilirsiniz.")
    else:
        logger.error(f"Sistem Komut Hatası: {error}")
        await ctx.send(f"⚠️ Kritik sistem hatası: `{error}`")

# --- 7. ÇALIŞTIRMA BLOĞU ---
if __name__ == "__main__":
    if DISCORD_TOKEN == "BURAYA_DISCORD_BOT_TOKENINI_YAZ":
        logger.critical("Geçerli bir Discord Token yapılandırılmadı!")
    else:
        try:
            logger.info("İmparatorluk Botu başlatılıyor...")
            bot.run(DISCORD_TOKEN)
        except Exception as e:
            logger.critical(f"Çalışma zamanı kritik hatası: {e}")
