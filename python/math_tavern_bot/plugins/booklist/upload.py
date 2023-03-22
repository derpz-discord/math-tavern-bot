import logging
from typing import TYPE_CHECKING, Optional

import aioboto3
import aiohttp
import disnake
import sqlalchemy
from derpz_botlib.database.db import SqlAlchemyBase
from disnake import ModalInteraction
from math_tavern_bot.plugins.plugin_book_search import \
    query_openlibrary_for_isbn
from pydantic import BaseModel, Field, ValidationError, validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

if TYPE_CHECKING:
    from math_tavern_bot.bot import BookBot


# TODO: This entire file needs to be stuffed into some UploadManager state machine thing


# TODO: Models need to be moved
class BookInDb(SqlAlchemyBase):
    __tablename__ = "books"

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    title = sqlalchemy.Column(sqlalchemy.String)
    author = sqlalchemy.Column(sqlalchemy.String)
    isbn = sqlalchemy.Column(sqlalchemy.String)
    subject = sqlalchemy.Column(sqlalchemy.String)
    s3_key = sqlalchemy.Column(sqlalchemy.String)

    # TODO: Log time uploaded at
    # TODO: Allow admins to modify


def check_isbn10(isbn: str) -> bool:
    """
    Checks if the ISBN is valid
    :param isbn: The ISBN to check
    :return: True if valid, False otherwise
    """
    if len(isbn) != 10:
        return False
    if not isbn.isnumeric():
        return False
    # See Gallian Chapter 0 exercise 45
    mult = list(range(10, 0, -1))
    total = 0
    for i in range(10):
        total += int(isbn[i]) * mult[i]
    return total % 11 == 0


def check_isbn13(isbn: str) -> bool:
    """
    Checks if the ISBN is valid
    :param isbn: The ISBN to check
    :return: True if valid, False otherwise
    """
    if len(isbn) != 13:
        return False
    if not isbn.isnumeric():
        return False
    # check first 3 digits
    if not isbn.startswith("978") and not isbn.startswith("979"):
        return False
    # truncate and check the isbn10
    return check_isbn10(isbn[3:])


class BookMetadata(BaseModel):
    # TODO: Move this into models.py
    download_url: str
    title: str = Field(..., min_length=1)
    author: str = Field(..., min_length=1)
    # TODO: Isbn validation
    # TODO: Convert everything to ISBN13
    isbn: str
    subject: str = Field(..., min_length=1)

    def to_embed(self) -> disnake.Embed:
        embed = disnake.Embed(title="Book Metadata")
        embed.add_field(name="Title", value=self.title, inline=False)
        embed.add_field(name="Author", value=self.author, inline=False)
        embed.add_field(name="ISBN", value=self.isbn, inline=False)
        embed.add_field(name="Subject", value=self.subject, inline=False)
        return embed

    @validator("isbn")
    def isbn_is_valid(cls, isbn: str) -> str:
        isbn = isbn.strip()
        isbn = isbn.replace("-", "")
        if not check_isbn10(isbn) and not check_isbn13(isbn):
            raise ValueError("Invalid ISBN")
        return isbn


class EditBookMetaModal(disnake.ui.Modal):
    """
    Modal that allows the user to input the metadata of a book
    after they upload it.
    Specifically, we are taking in the:
    - title
    - author
    - isbn

    It is intuitively obvious to even the most casual observer that
    the ISBN is a hash for a book object and thus uniquely identifies
    a book.
    """

    def __init__(
        self,
        *,
        file_url: str,
        bot: "BookBot",
        meta: Optional[BookMetadata] = None,
        **kwargs,
    ):
        """

        :param file_url: The URL of the file that was uploaded
        :param meta: The metadata of the book. Used for editing mistakes
        :param kwargs:
        """
        self.file_url = file_url
        # TODO: Fix logging
        self.logger = logging.getLogger(__name__)
        self.bot = bot
        if meta:
            title = meta.title
            author = meta.author
            isbn = meta.isbn
            subject = meta.subject
        else:
            title = ""
            author = ""
            isbn = ""
            subject = ""
        components = [
            disnake.ui.TextInput(
                label="Title",
                placeholder="The title of the book",
                custom_id="book_title",
                style=disnake.TextInputStyle.single_line,
                value=title,
            ),
            disnake.ui.TextInput(
                label="Author",
                placeholder="The author of the book",
                custom_id="book_author",
                style=disnake.TextInputStyle.single_line,
                value=author,
            ),
            disnake.ui.TextInput(
                label="ISBN",
                placeholder="The ISBN of the book",
                custom_id="book_isbn",
                style=disnake.TextInputStyle.single_line,
                value=isbn,
            ),
            disnake.ui.TextInput(
                label="Subject",
                placeholder="The subject of the book (e.g. Analysis)",
                custom_id="book_subject",
                style=disnake.TextInputStyle.single_line,
                value=subject,
            ),
        ]
        super().__init__(title="Book Metadata", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        data = inter.text_values
        try:
            meta = BookMetadata(
                download_url=self.file_url,
                title=data["book_title"],
                author=data["book_author"],
                isbn=data["book_isbn"],
                subject=data["book_subject"],
            )
            await inter.response.send_message(
                embed=meta.to_embed(),
                view=ConfirmBookMetaView(meta, inter.message, self.bot),
            )
        except ValidationError as e:
            self.logger.warning("Invalid metadata: %s", e.errors())
            self.logger.exception(e)
            await inter.response.send_message(
                f"Invalid metadata: {e.errors()}", ephemeral=True
            )

    async def on_timeout(self):
        # TODO: Handle
        pass

    async def on_error(self, error: Exception, interaction: ModalInteraction) -> None:
        self.logger.exception(error)
        await interaction.send(
            "An error occurred while processing this modal", ephemeral=True
        )

    async def on_close(self, interaction):
        await interaction.response.send_message("Cancelled", ephemeral=True)


async def search_book_in_db(
    query: str, engine: AsyncEngine
) -> Optional[list[BookInDb]]:
    """
    Searches for a book in the database
    :param query: The query to search for
    :param engine: The sqlalchemy engine
    :return: The list of books that match the query
    """

    async with AsyncSession(engine) as session:
        stmt = select(BookInDb).where(
            BookInDb.title.ilike(f"%{query}%")
            | BookInDb.author.ilike(f"%{query}%")
            | BookInDb.subject.ilike(f"%{query}%")
        )
        result = await session.execute(stmt)
        things = result.scalars().all()
        if len(things) == 0:
            return None
        return things


# TODO: Stream download instead of reading into memory
async def download_book_from_db(
    s3_key: str, boto3_sess: aioboto3.Session
) -> Optional[bytes]:
    """
    Downloads a book from the database
    :param s3_key: The key of the book in the database
    :param boto3_sess: The boto3 session
    :return: The bytes of the book
    """
    # TODO: This should be offloaded to the rust portion of the bot
    # TODO: Better logging
    logger = logging.getLogger("booklist.download.download_book_from_db")
    # TODO: Hardcoded
    async with boto3_sess.resource("s3", endpoint_url="http://localhost:9000") as s3:
        bucket = await s3.Bucket("bookbot")
        logger.info("Got bucket")
        try:
            obj = await bucket.Object(s3_key)
            obj = await obj.get()
            book_body = await obj["Body"].read()
            logger.info("Got object")
            return book_body
        except Exception as e:
            # TODO: We should probably handle this better
            logger.warning("Failed to download file")
            logger.exception(e)
            return None


async def upload_book_and_insert_to_db(
    meta: BookMetadata, engine: AsyncEngine, boto3_sess: aioboto3.Session
):
    # TODO: Better logging
    logger = logging.getLogger("booklist.upload.insert_book_to_db")
    aiohttp_sess = aiohttp.ClientSession()
    # TODO: Hardcoded
    async with boto3_sess.resource("s3", endpoint_url="http://localhost:9000") as s3:
        bucket = await s3.Bucket("bookbot")
        logger.info("Got bucket")
        # download file to memory
        async with aiohttp_sess.get(meta.download_url) as resp:
            if resp.status != 200:
                logger.warning("Failed to download file")
                return
            logger.info("Got file of length %s", resp.content_length)
            file_bytes = await resp.read()
        await aiohttp_sess.close()
        # upload file to minio
        # TODO: Potential key collision if diff servers upload same book
        # TODO: Content type checking
        try:
            returned = await bucket.put_object(
                Key=meta.isbn, Body=file_bytes, ContentType="application/pdf"
            )
            logger.info(f"Uploaded file to minio: {returned}")
        except Exception as e:
            logger.exception(e)
            return

        try:
            # TODO: redundant connect, just create session on engine directly
            async with engine.connect() as conn:
                async with AsyncSession(conn) as session:
                    # insert into db
                    book = BookInDb(
                        title=meta.title,
                        author=meta.author,
                        isbn=meta.isbn,
                        subject=meta.subject,
                        s3_key=returned.key,
                    )
                    session.add(book)
                    await session.commit()

        except Exception as e:
            logger.exception(e)
            # TODO: Delete file from minio if DB insert fails to guarantee atomicity
            return


class ConfirmBookMetaView(disnake.ui.View):
    def __init__(
        self, book_meta: BookMetadata, message: disnake.Message, bot: "BookBot"
    ):
        super().__init__()
        self.book_meta = book_meta
        self.message = message
        self.bot = bot

    @disnake.ui.button(label="Confirm", style=disnake.ButtonStyle.green)
    async def confirm(
        self, button: disnake.ui.Button, interaction: disnake.MessageInteraction
    ):
        await interaction.response.send_message("Uploading now... please wait")
        await upload_book_and_insert_to_db(
            self.book_meta, self.bot.engine, self.bot.boto3_sess
        )
        await interaction.followup.send("Uploaded successfully", ephemeral=True)

    @disnake.ui.button(label="Correct Mistakes", style=disnake.ButtonStyle.red)
    async def correct(
        self, button: disnake.ui.Button, interaction: disnake.MessageInteraction
    ):
        await interaction.response.send_modal(
            view=EditBookMetaModal(
                file_url=self.book_meta.download_url, bot=self.bot, meta=self.book_meta
            )
        )

    async def on_timeout(self):
        await self.message.edit("Timed out waiting for input", view=None)


class InputIsbnModal(disnake.ui.Modal):
    def __init__(self):
        components = [
            disnake.ui.TextInput(
                label="ISBN",
                placeholder="The ISBN of the book",
                custom_id="book_isbn",
                style=disnake.TextInputStyle.single_line,
            ),
        ]
        super().__init__(title="Input ISBN for autofill", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        isbn: str = inter.text_values["book_isbn"]
        isbn = isbn.strip()
        if not isbn:
            await inter.response.send_message(
                "ERROR: ISBN cannot be empty", ephemeral=True
            )
            return
        # ensure isbn is valid
        isbn = isbn.replace("-", "")
        if not isbn.isnumeric():
            await inter.response.send_message(
                "ERROR: ISBNs are numeric.", ephemeral=True
            )
            return
        # check length, should be either 10 or 13 now
        if len(isbn) != 10 and len(isbn) != 13:
            await inter.response.send_message(
                "ERROR: Length of ISBN should be 10 or 13", ephemeral=True
            )
            return
        await inter.response.send_message(f"Searching for {isbn}...")
        books_found = await query_openlibrary_for_isbn(isbn)
        if not books_found:
            await inter.edit_original_response(content=f"No books found for {isbn}")
            return
        if books_found.num_found > 1:
            await inter.edit_original_response(
                content=f"Multiple books found for {isbn}. This should be impossible"
            )
            return
        book = books_found.docs[0]
        embed = disnake.Embed(title="Book Metadata")
        # TODO: using magic string schema. model properly
        embed.add_field(name="Title", value=book["title"], inline=False)
        embed.add_field(name="Author", value=book["author_name"], inline=False)
        embed.add_field(name="ISBN", value=book["isbn"], inline=False)
        embed.add_field(
            name="Pages", value=book["number_of_pages_median"], inline=False
        )
        embed.add_field(name="Publisher", value=book["publisher"], inline=False)
        await inter.edit_original_response(
            "\N{WHITE HEAVY CHECK MARK} Search completed", embed=embed
        )

    async def on_timeout(self):
        pass

    async def on_close(self, interaction):
        await interaction.response.send_message("Cancelled", ephemeral=True)


class UploadView(disnake.ui.View):
    def __init__(
        self, file_url: str, message: disnake.Message, bot: "BookBot", **kwargs
    ):
        self.message = message
        self.file_url = file_url
        self.bot = bot
        super().__init__(**kwargs)

    @disnake.ui.button(label="Edit Book Metadata", style=disnake.ButtonStyle.primary)
    async def upload(
        self, button: disnake.ui.Button, interaction: disnake.MessageInteraction
    ):
        await interaction.response.send_modal(
            EditBookMetaModal(file_url=self.file_url, bot=self.bot)
        )

    @disnake.ui.button(label="Cancel", style=disnake.ButtonStyle.danger)
    async def cancel(
        self, button: disnake.ui.Button, interaction: disnake.MessageInteraction
    ):
        await interaction.response.send_message("Cancelled", ephemeral=True)
        self.stop()

    async def on_timeout(self):
        await self.message.edit("Timed out waiting for input", view=None)
