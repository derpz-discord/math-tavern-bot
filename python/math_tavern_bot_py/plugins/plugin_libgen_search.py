"""
Plugin for searching Libgen for books.
"""
from collections import deque

import disnake
from derpz_botlib.bot_classes import LoggedBot
from derpz_botlib.cog import LoggedCog
from derpz_botlib.discord_utils.paginator import Menu
from disnake import ApplicationCommandInteraction
from disnake.ext import commands
from libgen_api import LibgenSearch


def extract_all_mirrors(lg_item: dict) -> list[str]:
    """
    Extracts all the mirrors from a libgen item

    References:
        https://github.com/harrison-broadbent/libgen-api#results-layout
    """
    return list(
        map(
            lambda k: lg_item[k],
            filter(lambda k: k.startswith("Mirror_"), lg_item.keys()),
        )
    )


def make_embed(lg_item: dict) -> disnake.Embed:
    """
    Formats libgen return items nicely

    Args:
        lg_item: See above
    Returns:
        Nice embed
    """
    embed = disnake.Embed(
        title=lg_item["Title"],
        description=f"Author: {lg_item['Author']}\n"
        f"Year: {lg_item['Year']}\n"
        f"Pages: {lg_item['Pages']}\n"
        f"Size: {lg_item['Size']}\n"
        f"Extension: {lg_item['Extension']}\n",
    )
    mirrors = extract_all_mirrors(lg_item)
    deque(
        map(
            lambda i_m: embed.add_field(
                name=f"Mirror #{i_m[0]+1}", value=i_m[1], inline=False
            ),
            enumerate(mirrors),
        )
    )
    return embed


class PluginLibgenSearch(LoggedCog):
    def __init__(self, bot: LoggedBot):
        super().__init__(bot)
        self.lg_search = LibgenSearch()

    @commands.slash_command(name="libgen")
    async def cmd_libgen(self, ctx: ApplicationCommandInteraction):
        pass

    @cmd_libgen.sub_command(name="search", description="Search libgen by book title.")
    async def cmd_libgen_search(
        self,
        ctx: ApplicationCommandInteraction,
        *,
        title: str = commands.Param(description="Title of book", min_length=3),
    ):
        results = self.lg_search.search_title(title)
        if len(results) == 0:
            await ctx.send("No results found.")
            return
        embeds = list(
            map(
                make_embed,
                results,
            )
        )
        paginator = Menu(embeds)
        await ctx.send(
            view=paginator,
        )

    async def cog_slash_command_error(
        self, inter: disnake.ApplicationCommandInteraction, error: Exception
    ) -> None:
        await inter.response.send_message(
            f":octagonal_sign: Internal error",
            ephemeral=True,
        )
        await super().cog_slash_command_error(inter, error)


def setup(bot: LoggedBot):
    bot.add_cog(PluginLibgenSearch(bot))
