"""
Plugin that automatically reacts with a configured emoji to configured users
whenever they send a message.

This is useful for automatically reacting with a sully emoji to a user who
sends a message that is cringe.
"""
from os import getenv
from typing import Optional, Union

import aioredis
import disnake
from derpz_botlib.bot_classes import ConfigurableCogsBot
from derpz_botlib.cog import CogConfiguration, DatabaseConfigurableCog
from derpz_botlib.utils import fmt_user
from disnake import ApplicationCommandInteraction
from disnake.ext import commands
from disnake.ext.commands import CheckFailure, MissingRole
from pydantic import BaseModel


class AutoSullyConfig(CogConfiguration):
    sully_emoji: Optional[int] = None
    sully_users: set[int] = set()
    roles_allowed_to_setup_autosully: set[int] = set()


class AutoSullyRequest(BaseModel):
    guild_id: int
    channel_id: int
    message_id: int
    emoji_id: Union[int, str]


class AutoSullyPlugin(DatabaseConfigurableCog[AutoSullyConfig]):
    """
    Automatically sullies configured users
    """

    def __init__(self, bot: ConfigurableCogsBot):
        super().__init__(bot, AutoSullyConfig)
        self._sully_emoji: Optional[disnake.Emoji] = None
        # TODO: Refactor this out of here
        self.redis_conn = aioredis.Redis.from_url(getenv("REDIS_URL"))

    @commands.slash_command(name="autosully")
    async def cmd_auto_sully(self, ctx: disnake.ApplicationCommandInteraction):
        pass

    @cmd_auto_sully.sub_command(
        description="Sets the emoji which will be used to sully users"
    )
    @commands.has_permissions(manage_emojis=True)
    @commands.guild_only()
    async def set_sully(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        *,
        emoji: disnake.Emoji = commands.Param(
            description="The emoji to sully users with"
        ),
    ):
        if emoji.guild != ctx.guild:
            await ctx.send("The emoji must be from this server")
            return

        guild_config = self.get_guild_config(ctx.guild)
        guild_config.sully_emoji = emoji.id
        await self.save_guild_config(ctx.guild, guild_config)
        await ctx.send(f"Set sully emoji to {emoji}")

    @cmd_auto_sully.sub_command_group()
    async def plugin_config(self, ctx: disnake.ApplicationCommandInteraction):
        pass

    @plugin_config.sub_command(
        description="Add a role that is allowed to setup autosully"
    )
    @commands.has_permissions(manage_roles=True)
    @commands.guild_only()
    async def add_allowed_role(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        role: disnake.Role = commands.Param(),
    ):
        guild_config = self.get_guild_config(ctx.guild)
        guild_config.roles_allowed_to_setup_autosully.add(role.id)
        await self.save_guild_config(ctx.guild, guild_config)
        await ctx.send(
            f"Added {role.mention} to allowed roles",
            ephemeral=True,
            allowed_mentions=disnake.AllowedMentions.none(),
        )

    @plugin_config.sub_command(
        descripotion="Remove a role that is allowed to setup autosully"
    )
    @commands.has_permissions(manage_roles=True)
    @commands.guild_only()
    async def remove_allowed_role(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        role: disnake.Role = commands.Param(),
    ):
        guild_config = self.get_guild_config(ctx.guild)
        guild_config.roles_allowed_to_setup_autosully.remove(role.id)
        await self.save_guild_config(ctx.guild, guild_config)
        await ctx.send(
            f"Removed {role.mention} from allowed roles",
            ephemeral=True,
            allowed_mentions=disnake.AllowedMentions.none(),
        )

    @cmd_auto_sully.sub_command(description="Marks a user for automatic sullies")
    @commands.guild_only()
    async def sully_user(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        user: disnake.Member = commands.Param(description="The user to sully"),
    ):
        guild_config = self.get_guild_config(ctx.guild)
        allowed_sully_roles = guild_config.roles_allowed_to_setup_autosully
        if user.id == self.bot.user.id:
            await ctx.send("I'm not going to sully myself")
            return
        if user.id in self.bot.owner_ids or user.id == self.bot.owner_id:
            await ctx.send("I'm not going to sully my owners")
            return
        if (
            set(ctx.user.roles).intersection(allowed_sully_roles) == set()
            and not ctx.user.guild_permissions.manage_roles
        ):
            await ctx.send("You do not have a required role to use this")
            raise CheckFailure()
        guild_config = self.config.get(ctx.guild, AutoSullyConfig())
        guild_config.sully_users.add(user.id)
        self.config[ctx.guild] = guild_config
        await self.bot.cog_config_store.set_cog_config(self, ctx.guild, guild_config)
        await ctx.send(f"Added {fmt_user(user)} to the sully list")

    @cmd_auto_sully.sub_command(
        description="Removes a user from the automatic sully list"
    )
    @commands.guild_only()
    async def stop_sullying_user(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        user: disnake.Member = commands.Param(description="The user to stop sullying"),
    ):
        guild_config = self.get_guild_config(ctx.guild)
        allowed_sully_roles = guild_config.roles_allowed_to_setup_autosully
        if (
            set(ctx.user.roles).intersection(allowed_sully_roles) == set()
            and not ctx.user.guild_permissions.manage_roles
        ):
            await ctx.send("You do not have a required role to use this")
            raise CheckFailure()
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
        guild_config = self.get_guild_config(ctx.guild)
        if guild_config.sully_users:
            sullied_users = []
            # TODO: Cache
            for user in guild_config.sully_users:
                sullied_users.append(await ctx.guild.fetch_member(user))

            await ctx.send(
                embed=disnake.Embed(
                    title="Sullied Users",
                    description="\n".join(map(lambda u: u.mention, sullied_users)),
                    colour=disnake.Colour.blurple(),
                ),
                allowed_mentions=disnake.AllowedMentions.none(),
            )
        else:
            await ctx.send("No users are currently being autosullied")

    @commands.command(description="Mass reacts to a message", name="massreact")
    @commands.guild_only()
    async def mass_react(self, ctx: commands.Context, emoji: Union[str, disnake.Emoji]):
        guild_config = self.get_guild_config(ctx.guild)
        if (
            set(ctx.author.roles).intersection(
                guild_config.roles_allowed_to_setup_autosully
            )
            == set()
        ):
            await ctx.send("You do not have a required role to use this")
            raise CheckFailure()
        if ctx.message.reference is None:
            await ctx.send("You must reply to a message to mass react to it")
            raise CheckFailure()
        if not isinstance(emoji, str):
            # unicode emoji
            if emoji.guild != ctx.guild:
                await ctx.send("The emoji must be from this server")
                raise commands.EmojiNotFound(argument=str(emoji))
        message = await ctx.fetch_message(ctx.message.reference.message_id)
        await message.add_reaction(emoji)
        # TODO: Bad naming
        emoji_id = emoji.id if isinstance(emoji, disnake.Emoji) else emoji
        await self.publish_sully_request(
            AutoSullyRequest(
                guild_id=ctx.guild.id,
                channel_id=message.channel.id,
                message_id=message.id,
                emoji_id=emoji_id,
            )
        )

    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):
        if not message.guild:
            return
        guild_config = self.get_guild_config(message.guild)
        if message.author.id in guild_config.sully_users:
            if guild_config.sully_emoji is not None:
                emoji = await message.guild.fetch_emoji(guild_config.sully_emoji)
                await message.add_reaction(emoji)

    async def publish_sully_request(self, req: AutoSullyRequest):
        """Requests for mass sullying from the sully army"""
        # TODO: Hardcoded redis channel
        await self.redis_conn.publish("autosully", req.json())

    async def cog_slash_command_error(
        self, inter: ApplicationCommandInteraction, error: Exception
    ) -> None:
        if isinstance(error, commands.EmojiNotFound):
            await inter.response.send_message(
                "The emoji you specified is not from this server", ephemeral=True
            )
            return
        await super().cog_slash_command_error(inter, error)

    async def cog_message_command_error(
        self, inter: ApplicationCommandInteraction, error: Exception
    ) -> None:
        if isinstance(error, commands.EmojiNotFound):
            await inter.response.send_message(
                "The emoji you specified is not from this server"
            )
            return
        await super().cog_message_command_error(inter, error)


def setup(bot: ConfigurableCogsBot):
    bot.add_cog(AutoSullyPlugin(bot))
