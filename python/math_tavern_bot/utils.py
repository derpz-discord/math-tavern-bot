import disnake
from disnake.ext.commands import CommandError, Context


def fmt_user(user: disnake.User) -> str:
    return f"{user.name}#{user.discriminator}"


def check_in_guild(ctx: Context):
    if not ctx.guild:
        raise CommandError("This command can only be used in a guild")
    return True
