import logging
from typing import Optional

import disnake
from disnake.ext import commands

from math_tavern_bot.bot_classes import DatabasedBot
from math_tavern_bot.booklist.search import SearchView
from math_tavern_bot.booklist.upload import UploadView


class BookListPlugin(commands.Cog):
    """
    Cog for managing a book list channel.
    """

    def __init__(self, bot: DatabasedBot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        # TODO: Surely there's a better way to do this
        self._documentation = {
            self.book_list_channel: disnake.Embed(
                title="book_list_channel",
                description="Sets the book list channel. This is the channel where "
                "the bot will manage the book list."
                "Note that the channel is fully managed by the bot "
                "and any messages that are not from the bot will "
                "be instantly vaporized.",
            )
        }
        # TODO: Add a database to store the book list channel
        self._book_list_channel: Optional[disnake.TextChannel] = None

    async def cog_load(self):
        self.logger.info("BookList plugin loaded")

    @commands.slash_command(name="booklist")
    async def book_list(self, ctx: disnake.ApplicationCommandInteraction):
        pass

    @book_list.sub_command_group()
    async def config(self, ctx: disnake.ApplicationCommandInteraction):
        pass

    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):
        """Keeps the book list channel clean by deleting any non-bot messages"""
        if (
            self._book_list_channel
            and message.channel == self._book_list_channel
            and message.author != self.bot.user
        ):
            replied = await message.reply("Your message is being vaporized...")
            await message.delete()
            await replied.delete()

    @config.sub_command(description="Sets the book list channel")
    async def book_list_channel(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        *,
        channel: disnake.TextChannel = commands.Param(
            description="The channel which will be managed by the book list bot"
        ),
    ):
        """
        Sets the book list channel

        :param ctx: :class:`disnake.ApplicationCommandInteraction` context
        :param channel: The channel which will be managed by the book list bot
        :return:
        """
        await ctx.send(f"Setting the book list channel to {channel.mention}")
        self._book_list_channel = channel

    @config.sub_command()
    async def documentation(self, ctx: disnake.ApplicationCommandInteraction):
        """
        Documentation for config options
        """
        await ctx.send(
            "Documentation for config options",
            embeds=list(self._documentation.values()),
        )

    @book_list.sub_command(description="Search for a book in the book list.")
    async def search(self, ctx: disnake.ApplicationCommandInteraction, *, query: str):
        """
        Search for a book in the book list.
        """
        # TODO: Implement this
        await ctx.send(f"Searching for {query}...")
        view = SearchView(
            [
                disnake.SelectOption(
                    label=f"Book {query}", value=query, description=f"Search {query}"
                )
            ]
        )
        view.message = await ctx.original_response()
        await view.message.edit(f"Search results for {query}", view=view)

    @book_list.sub_command(
        description="Get a link to upload your book to the books list."
    )
    async def get_upload_link(self, ctx: disnake.ApplicationCommandInteraction):
        """
        Get a link to upload your book to the books list.
        """
        # TODO: Implement this
        await ctx.send("This feature has yet to be implemented")

    @book_list.sub_command(description="Uploads your book to the book list.")
    async def upload(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        *,
        url: str = commands.Param(description="The EXACT DOWNLOAD url of your book"),
    ):
        """
        Uploads your book to the book list.
        """
        view = UploadView()
        await ctx.send("Processing...")
        view.message = await ctx.original_response()
        await view.message.edit(f"Configure your upload of {url}", view=view)
