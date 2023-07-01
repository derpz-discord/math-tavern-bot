"""
Plugin for searching Libgen for books.
"""
import disnake
from derpz_botlib.bot_classes import LoggedBot
from derpz_botlib.cog import LoggedCog
from derpz_botlib.discord_utils.paginator import Menu
from disnake import ApplicationCommandInteraction
from disnake.ext import commands
from libgen_api import LibgenSearch


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
                lambda r: disnake.Embed(
                    title=r["Title"],
                    description=f"Author: {r['Author']}\n"
                    f"Year: {r['Year']}\n"
                    f"Pages: {r['Pages']}\n"
                    f"Size: {r['Size']}\n"
                    f"Extension: {r['Extension']}\n"
                    f"Mirror: {r['Mirror_1']}",
                ),
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
