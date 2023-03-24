import datetime
import enum
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


def fmt_guild_channel_include_id(channel: disnake.abc.GuildChannel) -> str:
    return f"{channel.name} ({channel.id}) in {fmt_guild_include_id(channel.guild)}"


async def reply_feature_wip(
    ctx: Union[commands.Context, ApplicationCommandInteraction]
):
    await ctx.reply("\N{CONSTRUCTION SIGN} This feature is still a work in progress!")


class DiscordTimeFormat(enum.Enum):
    """
    Discord time formats
    See: https://r.3v.fi/discord-timestamps/
    """

    short_time = "t"
    long_time = "T"
    short_date = "d"
    long_date = "D"
    long_date_with_short_time = "f"
    long_date_with_day_of_week_and_short_time = "F"
    relative = "R"


def fmt_time(dt: Union[datetime.datetime, datetime.time], tf: DiscordTimeFormat) -> str:
    """Formats time for discord"""
    # TODO: BROKEN AF
    current_tz = datetime.datetime.now().tzinfo
    if isinstance(dt, datetime.time):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.datetime.now().tzinfo)
        ts = datetime.datetime.combine(datetime.date.today(), dt)
    else:
        ts = dt
    return "<t:{0}:{1}>".format(int(ts.utctimetuple()), tf.value)
