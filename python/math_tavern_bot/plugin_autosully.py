import logging
from typing import Optional

import disnake
from disnake.ext import commands

from math_tavern_bot.bot_classes import KvStoredBot
from math_tavern_bot.config.models import CogConfiguration
from math_tavern_bot.utils import fmt_user


class AutoSullyConfig(CogConfiguration):
    sully_emoji: Optional[int] = None
    sully_users: set[int] = set()


class AutoSullyPlugin(commands.Cog):
    """
    Automatically sullies configured users
    """
    config: AutoSullyConfig

    def __init__(self, bot: KvStoredBot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        self._sully_emoji: Optional[disnake.Emoji] = None

    async def cog_load(self) -> None:
        self.logger.info("AutoSully plugin loaded")
        config = await self.bot.cog_config_store.get_cog_config(self)
        if isinstance(config, CogConfiguration):
            self.logger.info("Loaded config from DB")
            self.config = AutoSullyConfig.parse_obj(config)
            # if self.config.sully_emoji:
            #     # TODO: This probably needs to be ran in a guild context
            #     self._sully_emoji = self.bot.get_emoji(self.config.sully_emoji)
        else:
            self.config = AutoSullyConfig()
            self.logger.warning("")

    @commands.slash_command()
    async def autosully(self, ctx: disnake.ApplicationCommandInteraction):
        pass

    @autosully.sub_command()
    @commands.has_permissions(manage_emojis=True)
    async def set_sully(
            self,
            ctx: disnake.ApplicationCommandInteraction,
            *,
            emoji: disnake.Emoji = commands.Param(
                description="The emoji to sully users with"
            ),
    ):
        if not ctx.guild:
            await ctx.send("This command can only be used in a guild")
            return
        self.config.sully_emoji = emoji.id
        await self.bot.cog_config_store.set_cog_config(self, self.config)
        await ctx.send(f"Set sully emoji to {emoji}")

    @autosully.sub_command(description="Marks a user for automatic sullies")
    @commands.has_permissions(manage_messages=True)
    async def sully_user(
            self,
            ctx: disnake.ApplicationCommandInteraction,
            user: disnake.User = commands.Param(description="The user to sully"),
    ):
        self.config.sully_users.add(user.id)
        await self.bot.cog_config_store.set_cog_config(self, self.config)
        await ctx.send(f"Added {fmt_user(user)} to the sully list")

    @autosully.sub_command(description="Removes a user from the automatic sully list")
    @commands.has_permissions(manage_messages=True)
    async def stop_sullying_user(self,
            ctx: disnake.ApplicationCommandInteraction,
            user: disnake.User = commands.Param(description="The user to stop sullying"),
    ):
        self.config.sully_users.discard(user.id)
        await self.bot.cog_config_store.set_cog_config(self, self.config)
        await ctx.send(f"Removed {fmt_user(user)} from the sully list")

    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):
        if not message.guild:
            return
        if message.author.id in self.config.sully_users:
            if self._sully_emoji is not None:
                await message.add_reaction(self._sully_emoji)
