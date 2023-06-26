import subprocess

import pkg_resources
from disnake.ext import commands

from derpz_botlib.bot_classes import LoggedBot
from derpz_botlib.cog import LoggedCog
from math_tavern_bot_py.bot import TavernBot


def get_git_revision_short_hash() -> str:
    return (
        subprocess.check_output(["git", "rev-parse", "--short", "HEAD"])
        .decode("ascii")
        .strip()
    )


class BotInfoPlugin(LoggedCog):
    def __init__(self, bot: TavernBot):
        super().__init__(bot)
        self.bot: TavernBot = bot

    @commands.command(name="ping")
    async def ping_command(self, ctx: commands.Context):
        """
        Checks the bot's latency to the discord API
        """
        await ctx.send(
            f"Pong! Latency to discord API is: **{round(self.bot.latency * 1000)}ms**"
        )

    @commands.command(name="about")
    async def about_command(self, ctx: commands.Context):
        """
        Shows information about the bot such as the version and git hash
        """
        version = pkg_resources.get_distribution("math-tavern-bot").version
        git_hash = get_git_revision_short_hash()
        await ctx.send(f"Math Tavern Bot v**{version}**\n" f"Git: {git_hash}")

    @commands.command(name="source")
    async def source_command(self, ctx: commands.Context):
        await ctx.send(
            "https://github.com/derpz-discord/math-tavern-bot", suppress_embeds=True
        )

    @commands.command(name="reload")
    @commands.is_owner()
    async def reload_command(self, ctx: commands.Context):
        """
        Reloads all the extensions currently loaded.
        Currently, disabled due to issues
        """
        await ctx.send("This command is currently disabled")
        # self.bot.reload_all_extensions()
        # await ctx.send("Reloaded cogs")


def setup(bot: TavernBot):
    bot.add_cog(BotInfoPlugin(bot))
