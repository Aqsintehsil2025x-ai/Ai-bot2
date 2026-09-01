import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import google.generativeai as genai

# .env dosyasındaki gizli bilgileri yükle
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Gemini API yapılandırması
genai.configure(api_key=GOOGLE_API_KEY)
# En güncel ve hızlı modellerden biri
generation_config = {"temperature": 0.7, "max_output_tokens": 2048}
model = genai.GenerativeModel('gemini-3.5-flash-lite', generation_config=generation_config)
system_instruction="Sen Discord platformunda çalışan akıllı bir yapay zeka asistanısın. Kullanıcılara Discord üzerinden yardımcı oluyorsun."
# Bot ayarları (Ön ek: !)
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Sohbet geçmişini hafızada tutmak için sözlük (Kanal bazlı)
chat_histories = {}

@bot.event
async def on_ready():
    print(f"🚀 {bot.user} sistemine giriş yapıldı ve bot aktif!")
    await bot.change_presence(activity=discord.Game(name="!yardım | Yapay Zeka Devrede"))

# ==================== 1. TEMEL VE EĞLENCE KOMUTLARI ====================

@bot.command(name="merhaba", help="Botun çalıştığını test eder.")
async def merhaba(ctx):
    await ctx.send(f"Selam {ctx.author.mention}! 🤖 Bot aktif ve emre amade.")

@bot.command(name="ping", help="Botun gecikme süresini (ms) gösterir.")
async def ping(ctx):
    latency = round(bot.latency * 1000)
    await ctx.send(f" Pong! Gecikme süresi: **{latency}ms**")

@bot.command(name="temizle", help="Belirtilen miktarda mesajı siler (Örn: !temizle 10).")
@commands.has_permissions(manage_messages=True)
async def temizle(ctx, miktar: int = 5):
    if miktar > 100:
        await ctx.send("❌ Tek seferde en fazla 100 mesaj silebilirsin.")
        return
    await ctx.channel.purge(limit=miktar + 1)
    await ctx.send(f"🧹 Başarıyla **{miktar}** mesaj silindi.", delete_after=5)

@temizle.error
async def temizle_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("⛔ Bu komutu kullanmak için mesajları yönet yetkin olmalı!")

# ==================== 2. YAPAY ZEKA (GEMINI) KOMUTLARI ====================

@bot.command(name="sor", help="Yapay zekaya soru sorarsın (Örn: !sor Python nedir?).")
async def sor(ctx, *, soru: str):
    async with ctx.typing():
        try:
            response = model.generate_content(soru)
            
            # Discord mesaj sınırlandırması (2000 karakter) için parça parça gönderme kontrolü
            text = response.text
            if len(text) > 2000:
                chunks = [text[i:i+1999] for i in range(0, len(text), 1999)]
                for chunk in chunks:
                    await ctx.send(chunk)
            else:
                await ctx.send(text)
        except Exception as e:
            await ctx.send(f"⚠️ Yapay zeka yanıt üretirken bir hata oluştu: `{e}`")

@bot.command(name="kod", help="Yapay zekaya kod yazdırır (Örn: !kod discord bot python ile).")
async def kod(ctx, *, istek: str):
    async with ctx.typing():
        try:
            prompt = f"Sen profesyonel bir yazılımcısın. Lütfen şu istek için temiz, açıklamalı ve hatasız kod blokları yaz:\n\n{istek}"
            response = model.generate_content(prompt)
            
            text = response.text
            if len(text) > 2000:
                await ctx.send("📄 Kod çok uzun olduğu için dosya veya parça olarak atılamıyor, kısaltılmış sürüm gönderiliyor:")
                await ctx.send(text[:1999])
            else:
                await ctx.send(text)
        except Exception as e:
            await ctx.send(f"⚠️ Kod üretilirken hata oluştu: `{e}`")

@bot.command(name="sohbet", help="Yapay zeka ile hafızalı sohbet başlatır/devam ettirir.")
async def sohbet(ctx, *, mesaj: str):
    channel_id = ctx.channel.id
    async with ctx.typing():
        try:
            # Kanal için geçmiş yoksa başlat
            if channel_id not in chat_histories:
                chat_histories[channel_id] = model.start_chat(history=[])
            
            chat_session = chat_histories[channel_id]
            response = chat_session.send_message(mesaj)
            
            await ctx.send(response.text)
        except Exception as e:
            await ctx.send(f"⚠️ Sohbet oturumunda hata oluştu: `{e}`")

@bot.command(name="hafizasifirla", help="Kanalın yapay zeka sohbet geçmişini sıfırlar.")
async def hafizasifirla(ctx):
    channel_id = ctx.channel.id
    if channel_id in chat_histories:
        del chat_histories[channel_id]
        await ctx.send("🗑️ Bu kanalın yapay zeka hafızası başarıyla sıfırlandı!")
    else:
        await ctx.send("ℹ️ Zaten aktif bir sohbet hafızası bulunmuyor.")

# ==================== 3. KULLANICI VE SUNUCU BİLGİ KOMUTLARI ====================

@bot.command(name="sunucubilgi", help="Sunucu hakkında detaylı bilgi verir.")
async def sunucubilgi(ctx):
    guild = ctx.guild
    embed = discord.Embed(title=f"🏰 {guild.name} Sunucu Bilgileri", color=discord.Color.blue())
    embed.add_field(name="👑 Sunucu Sahibi", value=guild.owner, inline=True)
    embed.add_field(name="👥 Üye Sayısı", value=guild.member_count, inline=True)
    embed.add_field(name="📅 Kuruluş Tarihi", value=guild.created_at.strftime("%d-%m-%Y"), inline=True)
    embed.add_field(name="💬 Kanal Sayısı", value=len(guild.channels), inline=True)
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    await ctx.send(embed=embed)

@bot.command(name="kullanicibilgi", help="Etiketlenen veya komutu yazan kullanıcı hakkında bilgi verir.")
async def kullanicibilgi(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = discord.Embed(title=f"👤 {member.name} - Kullanıcı Bilgileri", color=discord.Color.green())
    embed.add_field(name="ID", value=member.id, inline=True)
    embed.add_field(name="Kayıt Adı", value=member.display_name, inline=True)
    embed.add_field(name="Sunucuya Katılım", value=member.joined_at.strftime("%d-%m-%Y") if member.joined_at else "Bilinmiyor", inline=True)
    embed.set_thumbnail(url=member.display_avatar.url)
    await ctx.send(embed=embed)

# ==================== 4. GELİŞMİŞ YARDIM MENÜSÜ ====================

@bot.command(name="yardım", help="Tüm komutları ve açıklamalarını listeler.")
async def yardim(ctx):
    embed = discord.Embed(title="🤖 Gelişmiş Bot Komut Menüsü", description="Aşağıda kullanabileceğin tüm komutlar listelenmiştir:", color=discord.Color.purple())
    
    embed.add_field(name="✨ Temel Komutlar", value="`!merhaba` - Botu test eder.\n`!ping` - Gecikme süresini gösterir.\n`!temizle [sayı]` - Mesaj siler.", inline=False)
    embed.add_field(name="🧠 Yapay Zeka Komutları", value="`!sor [soru]` - Yapay zekaya soru sorar.\n`!kod [istek]` - Kod blokları üretir.\n`!sohbet [mesaj]` - Hafızalı sohbet başlatır.\n`!hafizasifirla` - Sohbet hafızasını temizler.", inline=False)
    embed.add_field(name="📊 Bilgi Komutları", value="`!sunucubilgi` - Sunucu detaylarını gösterir.\n`!kullanicibilgi [@kullanıcı]` - Kullanıcı bilgilerini gösterir.", inline=False)
    
    embed.set_footer(text="Geliştirici: Aqsin | Güçlü AI Altyapısı")
    await ctx.send(embed=embed)

# Botu Çalıştır
if DISCORD_TOKEN:
    bot.run(DISCORD_TOKEN)
else:
    print("HATA: Discord token bulunamadı!")
