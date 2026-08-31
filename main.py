import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

# .env dosyasındaki gizli bilgileri projeye yükle
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Bot ayarları
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"{bot.user} olarak giriş yapıldı!")

@bot.command(name="merhaba")
async def merhaba(ctx):
    await ctx.send("Selam! Bot aktif ve çalışıyor.")

# Botu çalıştır
if DISCORD_TOKEN:
    bot.run(DISCORD_TOKEN)
else:
    print("HATA: Discord token bulunamadı! .env dosyasını kontrol et.")
