from typing import Optional

import disnake
from disnake.ext import commands

from math_tavern_bot.database.models import CogConfiguration
from math_tavern_bot.library.bot_classes import KvStoredBot
from math_tavern_bot.library.cog import DatabaseConfiguredCog
from math_tavern_bot.library.utils import check_in_guild, fmt_user


class AutoSullyConfig(CogConfiguration):
    sully_emoji: Optional[int] = None
    sully_users: set[int] = set()


class AutoSullyPlugin(DatabaseConfiguredCog):
    """
    Automatically sullies configured users
    """

    config: dict[disnake.Guild, AutoSullyConfig]

    def __init__(self, bot: KvStoredBot):
        super().__init__(bot, AutoSullyConfig)
        self._sully_emoji: Optional[disnake.Emoji] = None

    @commands.slash_command()
    async def autosully(self, ctx: disnake.ApplicationCommandInteraction):
        pass

    @autosully.sub_command(
        description="Sets the emoji which will be used to sully users"
    )
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

    @commands.command("whoissully")
    async def who_is_sully(self, ctx: commands.Context):
        """
        Lists all users who are currently being autosullied
        :param ctx: The context of the command
        :return: None
        """
        guild_config = self.config.get(ctx.guild, AutoSullyConfig())
        if guild_config.sully_users:
            sullied_users = []
            # TODO: Cache
            for user in guild_config.sully_users:
                sullied_users.append(await ctx.guild.fetch_member(user))

            await ctx.send(
                embed=disnake.Embed(
                    title="Sullied Users",
                    description="\n".join(map(lambda u: u.mention, sullied_users)),
                ),
                allowed_mentions=disnake.AllowedMentions.none(),
            )
        else:
            await ctx.send("No users are currently being autosullied")

    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):
        if not message.guild:
            return
        guild_config = self.config.get(message.guild, AutoSullyConfig())
        if message.author.id in guild_config.sully_users:
            if guild_config.sully_emoji is not None:
                emoji = await message.guild.fetch_emoji(guild_config.sully_emoji)
                await message.add_reaction(emoji)
