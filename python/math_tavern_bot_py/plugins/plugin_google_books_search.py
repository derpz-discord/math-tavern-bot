import os

import aiohttp
import disnake
from disnake import ApplicationCommandInteraction
from disnake.ext import commands

from derpz_botlib.bot_classes import LoggedBot
from derpz_botlib.cog import LoggedCog
from derpz_botlib.discord_utils.paginator import Menu


def make_embed(gbook_item: dict) -> disnake.Embed:
    """
    Beautifully formats a Google Books result

    Args:
        gbook_item: Google book result

    Returns:

    """
    embed = disnake.Embed(
        title=gbook_item["volumeInfo"]["title"],
        description=gbook_item["volumeInfo"]["description"],
        url=f"https://www.amazon.com/s?k={gbook_item['volumeInfo']['industryIdentifiers'][0]['identifier']}",
    )
    embed.set_author(name=", ".join(gbook_item["volumeInfo"]["authors"]))
    embed.add_field(
        name="ISBN",
        value=gbook_item["volumeInfo"]["industryIdentifiers"][0]["identifier"],
    )
    embed.add_field(name="Publisher", value=gbook_item["volumeInfo"]["publisher"])
    embed.add_field(name="Page count", value=gbook_item["volumeInfo"]["pageCount"])
    embed.add_field(
        name="Categories", value=", ".join(gbook_item["volumeInfo"]["categories"])
    )
    embed.set_image(url=gbook_item["volumeInfo"]["imageLinks"]["thumbnail"])
    return embed


class PluginGoogleBooksSearch(LoggedCog):
    def __init__(self, bot: LoggedBot):
        super().__init__(bot)
        self.aiohttp_sess = aiohttp.ClientSession()
        self.google_api_key = os.getenv("GOOGLE_API_KEY")

    @commands.slash_command(name="gbooks")
    async def cmd_gbooks(self, ctx: ApplicationCommandInteraction):
        pass

    @cmd_gbooks.sub_command(name="search", description="Searches Google books")
    async def search_gbooks(
        self,
        ctx: ApplicationCommandInteraction,
        *,
        query: str = commands.Param(description="Query to search"),
    ):
        # https://developers.google.com/books/docs/v1/using#PerformingSearch
        params = {
            "key": self.google_api_key,
            "q": query,
        }
        async with self.aiohttp_sess.get(
            "https://www.googleapis.com/books/v1/volumes", params=params
        ) as resp:
            resp.raise_for_status()
            resp_json = await resp.json()
            if resp_json["totalItems"] == 0:
                await ctx.response.send_message("No results found")
                return
            embeds = list(
                map(
                    make_embed,
                    resp_json["items"],
                )
            )
            paginator = Menu(embeds)
            await ctx.send(
                embed=embeds[0],
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
    bot.add_cog(PluginGoogleBooksSearch(bot))
