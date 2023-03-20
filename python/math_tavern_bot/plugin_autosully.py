import logging
from typing import Optional

import disnake
from disnake.ext import commands

from math_tavern_bot.bot_classes import KvStoredBot
from math_tavern_bot.config.models import CogConfiguration
from math_tavern_bot.utils import fmt_user, check_in_guild


class AutoSullyConfig(CogConfiguration):
    sully_emoji: Optional[int] = None
    sully_users: set[int] = set()


class AutoSullyPlugin(commands.Cog):
    """
    Automatically sullies configured users
    """

    config: dict[disnake.Guild, AutoSullyConfig]

    def __init__(self, bot: KvStoredBot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        self._sully_emoji: Optional[disnake.Emoji] = None
        self.config: dict[disnake.Guild, AutoSullyConfig] = {}

    async def cog_load(self) -> None:
        self.logger.info("AutoSully plugin loaded")
        # load config from DB
        config = await self.bot.cog_config_store.get_cog_config(self)
        if config:
            self.config = dict(
                map(
                    lambda x: (self.bot.get_guild(x[0]), AutoSullyConfig.parse_obj(x[1])),
                    config.items(),
                )
            )
        else:
            self.logger.warning("No config found in DB")

    @commands.slash_command()
    async def autosully(self, ctx: disnake.ApplicationCommandInteraction):
        pass

    @autosully.sub_command()
    @commands.has_permissions(manage_emojis=True)
    @commands.check(check_in_guild)
    async def set_sully(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        *,
        emoji: disnake.Emoji = commands.Param(
            description="The emoji to sully users with"
        ),
    ):
        guild_config = self.config.get(ctx.guild, AutoSullyConfig())
        guild_config.sully_emoji = emoji.id
        self.config[ctx.guild] = guild_config
        await self.bot.cog_config_store.set_cog_config(self, ctx.guild, guild_config)
        await ctx.send(f"Set sully emoji to {emoji}")

    @autosully.sub_command(description="Marks a user for automatic sullies")
    @commands.has_permissions(manage_messages=True)
    @commands.check(check_in_guild)
    async def sully_user(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        user: disnake.User = commands.Param(description="The user to sully"),
    ):
        guild_config = self.config.get(ctx.guild, AutoSullyConfig())
        guild_config.sully_users.add(user.id)
        self.config[ctx.guild] = guild_config
        await self.bot.cog_config_store.set_cog_config(self, ctx.guild, guild_config)
        await ctx.send(f"Added {fmt_user(user)} to the sully list")

    @autosully.sub_command(description="Removes a user from the automatic sully list")
    @commands.has_permissions(manage_messages=True)
    async def stop_sullying_user(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        user: disnake.User = commands.Param(description="The user to stop sullying"),
    ):
        guild_config = self.config.get(ctx.guild, AutoSullyConfig())
        guild_config.sully_users.discard(user.id)
        self.config[ctx.guild] = guild_config
        await self.bot.cog_config_store.set_cog_config(self, ctx.guild, guild_config)
        await ctx.send(f"Removed {fmt_user(user)} from the sully list")

    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):
        if not message.guild:
            return
        guild_config = self.config.get(message.guild, AutoSullyConfig())
        if message.author.id in guild_config.sully_users:
            if guild_config.sully_emoji is not None:
                emoji = await message.guild.fetch_emoji(guild_config.sully_emoji)
                await message.add_reaction(emoji)
