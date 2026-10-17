from keep_alive import keep_alive
keep_alive()

import os
import random
import re
import json
import discord
from discord.ext import commands
from dotenv import load_dotenv
from keep_alive import keep_alive

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
TARGET_CHANNEL_ID = int(os.getenv("TARGET_CHANNEL_ID", 0))

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

from translator import translate_to_shakespearean

# ---------------------------------------------------------
# BOT COMMANDS
# ---------------------------------------------------------
async def get_or_create_webhook(channel: discord.TextChannel) -> discord.Webhook:
    webhooks = await channel.webhooks()
    for wh in webhooks:
        if wh.user == bot.user:
            return wh
    return await channel.create_webhook(name="BardImpersonator")

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user.name} (ID: {bot.user.id})")
    print("Advanced Grammar Bard is active!")

@bot.command(name="s")
async def bard_prefix(ctx: commands.Context, *, message: str):
    try:
        await ctx.message.delete()
    except discord.Forbidden:
        pass

    translated = translate_to_shakespearean(message)
    webhook = await get_or_create_webhook(ctx.channel)
    await webhook.send(
        content=translated,
        username=ctx.author.display_name,
        avatar_url=ctx.author.display_avatar.url,
    )

@bot.tree.command(name="bard", description="Speak modern words, delivered as the Bard.")
async def bard_slash(interaction: discord.Interaction, message: str):
    await interaction.response.defer(ephemeral=True)
    translated = translate_to_shakespearean(message)
    webhook = await get_or_create_webhook(interaction.channel)

    await webhook.send(
        content=translated,
        username=interaction.user.display_name,
        avatar_url=interaction.user.display_avatar.url,
    )
    await interaction.followup.send("Delivered anon!", ephemeral=True)


@bot.event
async def on_message(message: discord.Message):
    # 1. Ignore messages from bots and webhooks to prevent infinite translation loops
    if message.author.bot or message.webhook_id:
        return

    # 2. If the message is in your designated auto-translate channel
    if message.channel.id == TARGET_CHANNEL_ID:
        try:
            await message.delete()
        except discord.Forbidden:
            print("Missing permissions to delete messages in this channel.")

        translated = translate_to_shakespearean(message.content)
        webhook = await get_or_create_webhook(message.channel)

        await webhook.send(
            content=translated,
            username=message.author.display_name,
            avatar_url=message.author.display_avatar.url,
        )
        return  # Stop processing here so it doesn't trigger commands twice

    # 3. Ensure prefix commands (!s) still work normally in OTHER channels
    await bot.process_commands(message)
    
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
