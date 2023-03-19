import logging
from typing import Optional

import disnake
from disnake.ext import commands

from math_tavern_bot.utils import fmt_user


class AutoSullyPlugin(commands.Cog):
    """
    Automatically sullies configured users
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        self._sully_emoji: Optional[disnake.Emoji] = None
        self._sully_users: set[disnake.User] = set()

        self.logger.info("AutoSully plugin loaded")

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
        if self._sully_emoji:
            await ctx.send(f"Sully emoji is already set to {self._sully_emoji}")
            return
        self._sully_emoji = emoji
        await ctx.send(f"Set sully emoji to {self._sully_emoji}")

    @autosully.sub_command()
    async def sully_user(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        user: disnake.User = commands.Param(description="The user to sully"),
    ):
        if not self._sully_emoji:
            await ctx.send("Sully emoji is not set")
            return
        self._sully_users.add(user)
        await ctx.send(f"Added {fmt_user(user)} to the sully list")

    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):
        if not message.guild:
            return
        if message.author in self._sully_users:
            await message.add_reaction(self._sully_emoji)
