from datetime import datetime, timedelta
from io import BytesIO
from typing import Optional, TYPE_CHECKING

import disnake
import sqlalchemy
from disnake.ext import commands
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from math_tavern_bot.booklist.search import SearchView
from math_tavern_bot.booklist.upload import (
    UploadView,
    BookInDb,
    download_book_from_db,
    search_book_in_db,
)

if TYPE_CHECKING:
    from math_tavern_bot.bot import BookBot
from math_tavern_bot.database.models import CogConfiguration
from math_tavern_bot.library.cog import DatabaseConfiguredCog
from math_tavern_bot.library.utils import check_in_guild


class BookListPluginConfig(CogConfiguration):
    book_list_channel: Optional[int] = None


class BookListPlugin(DatabaseConfiguredCog):
    """
    Cog for managing a book list channel.
    """

    config: dict[disnake.Guild, BookListPluginConfig]
    bot: "BookBot"

    def __init__(self, bot: "BookBot"):
        super().__init__(bot, BookListPluginConfig)
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

    async def cog_load(self):
        self.logger.info("BookList plugin loaded")

    @commands.slash_command()
    async def book_list(self, ctx: disnake.ApplicationCommandInteraction):
        pass

    @book_list.sub_command(
        name="list", description="Prints out the list of books in the DB"
    )
    async def list_books(self, ctx: disnake.ApplicationCommandInteraction):
        """
        Prints out the list of books in the DB.
        TODO: Add pagination
        TODO: Should really be printing out books in book list instead.
        :param ctx:
        :return:
        """
        # TODO: Logic should be separated
        guild_config = self.config.get(ctx.guild, BookListPluginConfig())
        # TODO: Not guild specific

        async with AsyncSession(self.bot.db) as sess:
            stmt = sqlalchemy.select(BookInDb).order_by(BookInDb.title)

            # TODO: Do not loop, do pagination instead
            res = await sess.scalars(stmt)
            books = res.fetchall()
            await ctx.send(f"Obtained {len(books)} books from the database")
            for book in books:
                book: BookInDb
                embed = disnake.Embed(title=book.title)
                # TODO: Hardcoded
                embed.set_footer(text="Generated by Math Tavern Bot")
                embed.add_field(name="Author", value=book.author, inline=False)
                embed.add_field(name="ISBN", value=book.isbn, inline=False)
                embed.add_field(name="Subject", value=book.subject, inline=False)
                # TODO: Make this a link
                embed.add_field(name="S3 Key", value=book.s3_key, inline=False)
                await ctx.send(embed=embed)

    @book_list.sub_command_group()
    async def config(self, ctx: disnake.ApplicationCommandInteraction):
        pass

    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):
        """Keeps the book list channel clean by deleting any non-bot messages"""
        book_list_channel = self.config.get(
            message.guild, BookListPluginConfig()
        ).book_list_channel
        if (
            book_list_channel
            and message.channel == book_list_channel
            and message.author != self.bot.user
        ):
            replied = await message.reply("Your message is being vaporized...")
            await message.delete()
            await replied.delete()

    @config.sub_command(description="Sets the book list channel")
    @commands.check(check_in_guild)
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
        guild_config = self.config.get(ctx.guild, BookListPluginConfig())
        guild_config.book_list_channel = channel.id
        self.config[ctx.guild] = guild_config
        await self.bot.cog_config_store.set_cog_config(self, ctx.guild, guild_config)
        await ctx.send(f"Setting the book list channel to {channel.mention}")

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

        await ctx.send(f"Searching for {query}...")
        books = await search_book_in_db(query, self.bot.db)
        if not books:
            await ctx.send("No books found")
            return
        await ctx.edit_original_response(content=f"Found {len(books)} books")
        for book in books:
            # TODO: Extract to function
            embed = disnake.Embed(title=book.title)
            embed.add_field(name="Author", value=book.author, inline=False)
            embed.add_field(name="ISBN", value=book.isbn, inline=False)
            embed.add_field(name="Subject", value=book.subject, inline=False)
            embed.add_field(name="S3 Key", value=book.s3_key, inline=False)
            await ctx.send(embed=embed)

    @book_list.sub_command(
        description="Get a link to upload your book to the books list."
    )
    async def get_upload_link(self, ctx: disnake.ApplicationCommandInteraction):
        """
        Get a link to upload your book to the books list.
        """
        # TODO: Implement this
        await ctx.send("This feature has yet to be implemented")

    @commands.command(name="upload_book_file")
    async def file_upload(self, ctx: commands.Context):
        """
        Uploads a book file to the book list.
        """
        if not ctx.message.attachments:
            wait_timeout = 60

            timestamp = f"<t:{int((datetime.utcnow() + timedelta(seconds=wait_timeout)).timestamp())}:T>"

            orig_msg = await ctx.send(
                f"Please upload your book file before {timestamp}"
            )

            message = await self.bot.wait_for(
                "message",
                check=lambda m: m.author == ctx.author and m.channel == ctx.channel,
                timeout=wait_timeout,
            )
            if not message.attachments:
                await orig_msg.edit("No file attached. Aborting")
                return
            if len(message.attachments) > 1:
                await orig_msg.edit(
                    "More than one file attached. Please only attach one file."
                )
                return
        else:
            message = ctx.message
        book_file: disnake.Attachment = message.attachments[0]
        msg = await ctx.send("Processing")
        if not book_file.filename.endswith(".pdf"):
            await msg.edit("Only PDF files are allowed.")
            return
        await ctx.send(
            f"Configure your upload of {message.attachments[0].url}",
            view=UploadView(message.attachments[0].url, msg, self.bot),
        )

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
        # TODO: We should try to download the file here to check if it's valid
        await ctx.send("Processing...")
        view = UploadView(url, await ctx.original_response(), self.bot)
        await view.message.edit(f"Configure your upload of {url}", view=view)

    @book_list.sub_command(description="Download the book from the database")
    async def download_book(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        *,
        isbn: str = commands.Param(description="The ISBN of the book to download"),
    ):
        """
        Download the book from the database
        """
        # TODO: This will fail if the book is larger than 8MB (Discord's limit)
        async with AsyncSession(self.bot.db) as sess:
            stmt = select(BookInDb).where(BookInDb.isbn == isbn)
            result = await sess.scalars(stmt)
            books = result.fetchall()
            if not books:
                await ctx.send("No book found with that ISBN")
                return
            if len(books) > 1:
                # TODO: This should not happen
                await ctx.send("More than one book found with that ISBN")
                return
            book: BookInDb = books[0]
            await ctx.send(f"Downloading {book.title}...")
            book_file = await download_book_from_db(book.s3_key, self.bot.boto3_sess)
            if book_file is None:
                await ctx.send("Failed to download book")
                return
            bio = BytesIO()
            bio.write(book_file)
            bio.seek(0)

            # TODO: Filename should be sanitized. Actually, we should do that
            #  before uploading the book
            await ctx.send(
                f"Your file {book.title} by {book.author} is ready",
                file=disnake.File(bio, filename=book.title + ".pdf"),
            )
