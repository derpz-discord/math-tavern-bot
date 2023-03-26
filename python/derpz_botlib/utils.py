import datetime
import enum
from typing import Union

import disnake
from disnake import ApplicationCommandInteraction
from disnake.ext import commands
from disnake.ext.commands import CommandError, Context


def fmt_user(user: Union[disnake.User, disnake.Member]) -> str:
    """Formats a user to username#discriminator"""
    return f"{user.name}#{user.discriminator}"


def fmt_guild_include_id(guild: disnake.Guild) -> str:
    return f"{guild.name} ({guild.id})"


def fmt_user_include_id(user: Union[disnake.User, disnake.Member]) -> str:
    """Formats a user to username#discriminator (id)
    Useful for logging"""
    return f"{fmt_user(user)} ({user.id})"


def fmt_guild_channel_include_id(channel: disnake.abc.GuildChannel) -> str:
    return f"{channel.name} ({channel.id}) in {fmt_guild_include_id(channel.guild)}"


async def reply_feature_wip(
    ctx: Union[commands.Context, ApplicationCommandInteraction]
):
    await ctx.reply("\N{CONSTRUCTION SIGN} This feature is still a work in progress!")


def parse_human_time(human_time: str) -> datetime.timedelta:
    """
    Parses a human time string into a timedelta

    Examples:
    1d2h3m4s
    1d 2h 3m 4s
    1day 2hour 3minute 4second
    1day 2hours 3minutes 4seconds
    1d 2hours 3minute 4s
    1d 2h 3min 4sec

    :throws ValueError: if the string is invalid
    """
    days, hours, minutes, seconds = 0, 0, 0, 0
    # clean up the string first
    human_time = human_time.lower().strip()
    stack = []
    for c in human_time:
        if c.isdigit():
            if stack and stack[-1].isdigit():
                stack[-1] += c
            else:
                stack.append(c)
        elif c.isalpha():
            if stack and stack[-1].isalpha():
                stack[-1] += c
            else:
                stack.append(c)
        elif c.isspace():
            # skip
            pass
        else:
            raise ValueError("Invalid character in human time string")
    # now parse the stack
    # partition the stack into sets of 2
    # the first element is the number, the second is the unit
    partitions = [stack[i : i + 2] for i in range(0, len(stack), 2)]

    # perform a quick check to make sure the partitions are valid
    for i, partition in enumerate(partitions):
        if len(partition) != 2:
            raise ValueError(
                "Invalid partition length at the {0}th partition: {1}".format(
                    i, partition
                )
            )
        if not partition[0].isdigit():
            raise ValueError(
                "First element of partition {0} is not a number: {1}".format(
                    i, partition
                )
            )
        if not partition[1].isalpha():
            raise ValueError(
                "Second element of partition {0} is not alphanumeric: {1}".format(
                    i, partition
                )
            )

    # now parse the partitions
    for i, partition in enumerate(partitions):
        number = int(partition[0])
        unit = partition[1]
        if unit in ("d", "day", "days"):
            days = number
        elif unit in ("h", "hour", "hours"):
            hours = number
        elif unit in ("m", "min", "minute", "minutes"):
            minutes = number
        elif unit in ("s", "sec", "second", "seconds"):
            seconds = number
        else:
            raise ValueError("Invalid unit at partition {0}: {1}".format(i, unit))

    return datetime.timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)


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
