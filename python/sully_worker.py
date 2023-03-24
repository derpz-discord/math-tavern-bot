import asyncio
import logging
import os

import async_timeout
import disnake
from dotenv import load_dotenv
from disnake.ext import commands
import aioredis
from pydantic import BaseModel

load_dotenv()

WORKER_NUMBER = os.getenv("WORKER_NUMBER")
DISCORD_TOKEN = os.getenv(f"WORKER_{WORKER_NUMBER}_TOKEN")

bot = commands.InteractionBot(intents=disnake.Intents.default())
redis = aioredis.from_url(os.getenv("REDIS_URL"))
pubsub = redis.pubsub()

logging.basicConfig(level=logging.INFO)


class AutoSullyRequest(BaseModel):
    guild_id: int
    channel_id: int
    message_id: int
    emoji_id: int


async def reader(ps_channel: aioredis.client.PubSub):
    while True:
        try:
            async with async_timeout.timeout(1):
                message = await ps_channel.get_message(ignore_subscribe_messages=True)
                if message is not None:
                    print(f"(Reader) Message Received: {message}")
                    msg = AutoSullyRequest.parse_raw(message["data"])
                    print(f"(Reader) Parsed Message: {msg}")
                    guild = bot.get_guild(msg.guild_id)
                    if guild is None:
                        print(f"(Reader) Guild not found: {msg.guild_id}")
                        continue
                    print(f"(Reader) Guild found: {guild.name}")
                    channel: disnake.TextChannel = guild.get_channel(msg.channel_id)
                    if channel is None:
                        print(f"(Reader) Channel not found: {msg.channel_id}")
                        continue
                    print(f"(Reader) Channel found: {channel.name}")
                    message = await channel.fetch_message(msg.message_id)
                    if message is None:
                        print(f"(Reader) Message not found: {msg.message_id}")
                        continue
                    print(f"(Reader) Message found: {message.content}")
                    # print(guild.emojis)
                    emoji = bot.get_emoji(msg.emoji_id)
                    if emoji is None:
                        print(f"(Reader) Emoji not found: {msg.emoji_id}")
                        continue
                    # emoji = disnake.PartialEmoji(name="sully", id=emoji.id)
                    await message.add_reaction(emoji)
                    print(f"(Reader) Reaction added: {emoji}")
                await asyncio.sleep(0.01)

        except asyncio.TimeoutError:
            pass


@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}")
    await bot.change_presence(activity=disnake.Game(name="Ready to sully"))
    async with pubsub as p:
        await p.subscribe("autosully")
        await reader(pubsub)

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
