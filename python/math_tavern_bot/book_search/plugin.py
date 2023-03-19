import logging

import aiohttp
import disnake
from disnake.ext import commands

from math_tavern_bot.book_search.models import OpenLibraryResponse


# TODO: Finish
async def query_openlibrary(
    sess: aiohttp.ClientSession, query: str
) -> OpenLibraryResponse:
    async with sess as session:
        async with session.get(
            "http://openlibrary.org/search.json",
            params={"q": query},
        ) as resp:
            resp.raise_for_status()
            content = await resp.json()
            parsed = OpenLibraryResponse.parse_obj(content)
            return parsed


class BookSearchPlugin(commands.Cog):
    """
    Cog that provides an API which allows you to search for books
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)

        self._aiohttp_sess = aiohttp.ClientSession()

    async def cog_load(self) -> None:
        self.logger.info("BookSearch plugin loaded")

    @commands.slash_command(
        name="booksearch", description="Uses the OpenLibrary API to search for books"
    )
    async def book_search(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        *,
        query: str = commands.Param(description="Your query"),
    ):
        books_found = await query_openlibrary(self._aiohttp_sess, query)
        await ctx.send(f"Found {books_found.num_found} books")
