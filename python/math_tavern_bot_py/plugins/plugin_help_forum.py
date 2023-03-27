from typing import Optional

import disnake
from derpz_botlib.bot_classes import ConfigurableCogsBot
from derpz_botlib.cog import DatabaseConfigurableCog
from derpz_botlib.database.storage import CogConfiguration
from disnake.ext import commands


class HelpForumConfiguration(CogConfiguration):
    help_forum_channel: Optional[int]


class HelpForumPlugin(DatabaseConfigurableCog[HelpForumConfiguration]):
    def __init__(self, bot: ConfigurableCogsBot):
        super().__init__(bot, HelpForumConfiguration)

    @commands.command(name="close")
    async def close_command(self, ctx: commands.Context):
        guild_config = self.get_guild_config(ctx.guild)
        if guild_config.help_forum_channel is None:
            return
        if ctx.channel.type != disnake.ChannelType.public_thread:
            await ctx.message.add_reaction("\N{CROSS MARK}")
            return
        # we may assume that parent_id exists because we are in a thread
        if ctx.channel.parent_id != guild_config.help_forum_channel:
            await ctx.message.add_reaction("\N{CROSS MARK}")
            await ctx.message.reply("This is not a help forum thread")
            return
        await ctx.channel.edit(archived=True)
