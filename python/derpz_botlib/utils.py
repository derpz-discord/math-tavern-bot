from typing import Union

import disnake
from disnake import ApplicationCommandInteraction
from disnake.ext import commands
from disnake.ext.commands import CommandError, Context


def fmt_user(user: disnake.User) -> str:
    return f"{user.name}#{user.discriminator}"


def fmt_guild_include_id(guild: disnake.Guild) -> str:
    return f"{guild.name} ({guild.id})"


def fmt_user_include_id(user: disnake.User) -> str:
    return f"{user.name}#{user.discriminator} ({user.id})"


async def reply_feature_wip(
    ctx: Union[commands.Context, ApplicationCommandInteraction]
):
    await ctx.reply("\N{CONSTRUCTION SIGN} This feature is still a work in progress!")


def check_in_guild(ctx: Context):
    if not ctx.guild:
        raise CommandError("This command can only be used in a guild")
    return True
