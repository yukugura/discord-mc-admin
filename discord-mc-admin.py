from dotenv import load_dotenv
import os
import discord
from discord.ext import commands

# .env読み込み
load_dotenv()

# 環境設定
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
intents = discord.Intents.default()
intents.message_content = True
# Botインスタンスを作成
bot = commands.Bot(command_prefix"!", intents=intents)

# Bot起動時処理
@bot.event
async def on_ready():
    print(f"{bot.user}がオンラインになりました！")

bot.run(BOT_TOKEN)
