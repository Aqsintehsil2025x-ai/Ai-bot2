# ==========================================
# DISCORD AI & EVENT BOT - MEMORY VERSION
# ==========================================

import os
import sys
import time
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
logger = logging.getLogger("DiscordAIBot")

# --- 2. AYARLAR VE YAPILANDIRMA ---
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "BURAYA_DISCORD_BOT_TOKENINI_YAZ")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "BURAYA_GEMINI_API_KEYINI_YAZ")

if DISCORD_TOKEN == "BURAYA_DISCORD_BOT_TOKENINI_YAZ" or not DISCORD_TOKEN:
    logger.warning("Discord Token tanımlanmamış! Lütfen çevresel değişkenleri kontrol edin.")

if GEMINI_API_KEY == "BURAYA_GEMINI_API_KEYINI_YAZ" or not GEMINI_API_KEY:
    logger.warning("Gemini API Key tanımlanmamış! Yapay zeka özellikleri çalışmayabilir.")

# Gemini API Yapılandırması
genai.configure(api_key=GEMINI_API_KEY)

generation_config = {
    "temperature": 0.75,
    "top_p": 0.9,
    "max_output_tokens": 1200,
}

SYSTEM_INSTRUCTION = (
    "Sen gelişmiş, arkadaş canlısı, teknik bilgisi yüksek ve samimi bir Discord sunucu asistanısın. "
    "Kullanıcılara hem genel konularda yardımcı oluyor hem de sunucu etkinlikleri için içerikler üretebiliyorsun. "
    "Sohbet geçmişini aklında tutar ve konuşmanın akışına göre doğal yanıtlar verirsin."
)

try:
    model = genai.GenerativeModel(
        model_name="gemini-3.5-flash-lite",
        generation_config=generation_config,
        system_instruction=SYSTEM_INSTRUCTION
    )
    logger.info("Gemini modeli ('gemini-3.5-flash-lite') başarıyla yüklendi.")
except Exception as e:
    logger.error(f"Gemini modeli yüklenirken hata oluştu: {e}")
    model = None

# --- 3. DISCORD INTENTS VE BOT TANIMLAMASI ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class AdvancedBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents, help_command=None)
        # Aktif etkinlikleri tutmak için liste
        self.scheduled_events = []
        # Her kanal için ayrı bir sohbet oturumu (hafıza) tutacağız: {channel_id: chat_session}
        self.chat_sessions = {}

    async def setup_hook(self):
        logger.info("Bot kurulum kancaları (setup_hook) çalıştırılıyor...")
        self.check_events_loop.start()

    async def on_ready(self):
        logger.info(f"Bot başarıyla çevrimiçi oldu: {self.user} (ID: {self.user.id})")
        logger.info(f"Bağlı olduğu sunucu sayısı: {len(self.guilds)}")
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="!yardim | @bot yaz sohbet et"))

    def get_or_create_chat(self, channel_id):
        """Her kanal için hafızalı bir sohbet oturumu döner veya yoksa oluşturur."""
        if channel_id not in self.chat_sessions:
            if model:
                # Yeni bir chat oturumu başlatıyoruz (geçmişi hafızada tutar)
                self.chat_sessions[channel_id] = model.start_chat(history=[])
            else:
                return None
        return self.chat_sessions[channel_id]

    # --- ARKA PLAN ETKİNLİK KONTROLÜ ---
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
                        f"Şu anda '{event['title']}' adlı planlanan etkinlik vakti geldi! "
                        "Bu etkinlik için katılımcıları coşturan, heyecan verici, kısa ve dikkat çekici bir duyuru mesajı hazırla."
                    )
                    
                    if model:
                        ai_response = model.generate_content(prompt)
                        content = ai_response.text
                    else:
                        content = f"🚨 **Zamanı Geldi!** Etkinlik başladı: **{event['title']}**"

                    await channel.send(f"🔔 <@{event['author_id']}> tarafından planlanan etkinlik vakti geldi!\n\n{content}")
                    logger.info(f"Etkinlik tetiklendi ve gönderildi: {event['title']}")
                except Exception as ex:
                    logger.error(f"Etkinlik gönderilirken hata oluştu: {ex}")

    @check_events_loop.before_loop
    async def before_check_events(self):
        await self.wait_until_ready()

bot = AdvancedBot()

# --- 4. OLAYLAR (EVENTS) VE MESAJ YÖNETİMİ ---

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Etiketlenme veya DM kontrolü
    if bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
        clean_content = message.content.replace(f'<@!{bot.user.id}>', '').replace(f'<@{bot.user.id}>', '').strip()
        
        if clean_content:
            if model:
                try:
                    async with message.channel.typing():
                        # Kanalın hafızalı sohbet oturumunu alıyoruz
                        chat_session = bot.get_or_create_chat(message.channel.id)
                        if chat_session:
                            response = chat_session.send_message(clean_content)
                            await message.reply(response.text)
                        else:
                            await message.reply("⚠️ Model başlatılamadı.")
                except Exception as e:
                    logger.error(f"Gemini API yanıt hatası: {e}")
                    await message.reply("⚠️ Yapay zeka işlem sırasında bir hata ile karşılaştı, lütfen biraz sonra tekrar deneyin.")
            else:
                await message.reply("⚠️ Yapay zeka modeli şu an aktif değil.")

    await bot.process_commands(message)

# --- 5. GELİŞMİŞ KOMUTLAR ---

@bot.command(name="yardim", aliases=["help", "komutlar"])
async def yardim_komutu(ctx):
    embed = discord.Embed(
        title="🤖 Bot Komutları ve Yardım Menüsü (Hafızalı Sürüm)",
        description="Sunucunuzda kullanabileceğiniz gelişmiş komut listesi aşağıdadır:",
        color=discord.Color.blue()
    )
    embed.add_field(name="@BotAdı <mesaj>", value="Yapay zeka asistanı ile geçmişi hatırlayarak sohbet etmenizi sağlar.", inline=False)
    embed.add_field(name="`!event <başlık> <YYYY-MM-DD HH:MM>`", value="Belirtilen tarih ve saatte otomatik hatırlatıcı oluşturur.", inline=False)
    embed.add_field(name="`!etkinlikler`", value="Aktif planlanmış tüm etkinlikleri listeler.", inline=False)
    embed.add_field(name="`!ping`", value="Botun gecikme sürelerini ve durumunu gösterir.", inline=False)
    embed.add_field(name="`!hafizayisifirla`", value="Bulunduğunuz kanaldaki yapay zeka hafızasını sıfırlar.", inline=False)
    embed.set_footer(text="Geliştirilmiş Discord AI & Event Bot Sistemi")
    await ctx.send(embed=embed)

@bot.command(name="ping")
async def ping_komutu(ctx):
    latency = round(bot.latency * 1000)
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"Bot gecikme süresi: **{latency}ms**",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@bot.command(name="hafizayisifirla", aliases=["clearmemory", "resetchat"])
async def hafizayi_sifirla(ctx):
    """Bulundugunuz kanaldaki bot gecmisini sifirlar"""
    if ctx.channel.id in bot.chat_sessions:
        del bot.chat_sessions[ctx.channel.id]
    
    # Yeniden boş bir oturum aç
    bot.get_or_create_chat(ctx.channel.id)
    
    embed = discord.Embed(
        title="🧹 Hafıza Sıfırlandı",
        description="Bu kanaldaki yapay zeka sohbet geçmişi başarıyla temizlendi. Bot her şeyi unuttu! 😉",
        color=discord.Color.gold()
    )
    await ctx.send(embed=embed)

# --- ETKINLİK SİSTEMİ KOMUTLARI ---

@bot.command(name="event", aliases=["etkinlikoluştur"])
async def event_olustur(ctx, baslik: str = None, tarih_str: str = None, saat_str: str = None):
    if not baslik or not tarih_str or not saat_str:
        embed = discord.Embed(
            title="⚠️ Eksik Parametre",
            description="Lütfen komutu doğru formatta girin:\n`!event \"Etkinlik Başlığı\" YYYY-MM-DD HH:MM`\n\n**Örnek:** `!event \"Oyun Gecesi\" 2026-09-10 20:00`",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
        return

    try:
        tam_zaman_str = f"{tarih_str} {saat_str}"
        event_time = datetime.strptime(tam_zaman_str, "%Y-%m-%d %H:%M")
        
        if event_time <= datetime.now():
            await ctx.send("❌ Geçmiş bir zaman için etkinlik planlayamazsın! Lütfen gelecekteki bir tarih gir.")
            return

        event_data = {
            "title": baslik,
            "time": event_time,
            "channel_id": ctx.channel.id,
            "author_id": ctx.author.id
        }
        bot.scheduled_events.append(event_data)

        embed = discord.Embed(
            title="✅ Etkinlik Başarıyla Planlandı!",
            description=f"**Başlık:** {baslik}\n**Zaman:** {event_time.strftime('%d.%m.%Y %H:%M')}\n**Kanal:** {ctx.channel.mention}",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
        logger.info(f"Yeni etkinlik kaydedildi: {baslik} - Zaman: {event_time}")

    except ValueError:
        await ctx.send("❌ Tarih veya saat formatı geçersiz! `YYYY-MM-DD HH:MM` formatını kullan.")
    except Exception as e:
        logger.error(f"Etkinlik oluşturma hatası: {e}")
        await ctx.send("⚠️ Etkinlik oluşturulurken beklenmeyen bir hata meydana geldi.")

@bot.command(name="etkinlikler", aliases=["listevents"])
async def etkinlikleri_listele(ctx):
    if not bot.scheduled_events:
        await ctx.send("📭 Şu anda planlanmış aktif bir etkinlik bulunmuyor.")
        return

    embed = discord.Embed(
        title="📅 Planlanan Aktif Etkinlikler",
        description="Zamanı geldiğinde bot otomatik olarak ilgili kanala duyuru yapacaktır.",
        color=discord.Color.purple()
    )

    for i, event in enumerate(bot.scheduled_events, 1):
        embed.add_field(
            name=f"{i}. {event['title']}",
            value=f"🕒 **Zaman:** {event['time'].strftime('%d.%m.%Y %H:%M')}\n👤 **Planlayan:** <@{event['author_id']}>",
            inline=False
        )

    await ctx.send(embed=embed)

# --- 6. HATA YÖNETİMİ ---
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("⚠️ Eksik parametre girdin! `!yardim` yazarak komutlara göz atabilirsin.")
    else:
        logger.error(f"Komut Hatası: {error}")
        await ctx.send(f"⚠️ Komut çalıştırılırken bir hata oluştu: `{error}`")

# --- 7. BOTU BAŞLAT ---
if __name__ == "__main__":
    if DISCORD_TOKEN == "BURAYA_DISCORD_BOT_TOKENINI_YAZ":
        logger.critical("Botu çalıştırmak için geçerli bir Discord Token girmelisin!")
    else:
        try:
            logger.info("Bot başlatılıyor...")
            bot.run(DISCORD_TOKEN)
        except Exception as e:
            logger.critical(f"Bot başlatılamadı veya çalışırken kritik hata oluştu: {e}")
