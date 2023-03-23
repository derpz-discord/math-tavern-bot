import logging
from typing import TYPE_CHECKING, Optional, Union

import aioboto3
import aiohttp
import disnake
from disnake.ext import commands
from math_tavern_bot.plugins.booklist.models import BookInDb, BookMetadata
from math_tavern_bot.plugins.booklist.upload_views import UploadView
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

if TYPE_CHECKING:
    from math_tavern_bot.bot import BookBot


# TODO: This entire file needs to be stuffed into some UploadManager state machine thing


class UploadManager:
    """
    Manages the process of uploading a book.
    """

    def __init__(self, bot: "BookBot"):
        self.bot = bot
        self.logger = self.bot.logger.getChild(self.__class__.__name__)
        self._book_meta: Optional[BookMetadata] = None
        self._download_url: Optional[str] = None
        self._ctx: Optional[
            Union[commands.Context, disnake.ApplicationCommandInteraction]
        ] = None

    async def start_upload_process(
        self,
        url: str,
        ctx: Union[commands.Context, disnake.ApplicationCommandInteraction],
    ):
        """
        Starts the upload process for a book.
        :param url: The URL of the book to upload
        :param ctx: The context of the command
        :return:
        """
        self.logger.info("Starting upload lmrocess for %s", url)
        self._download_url = url
        self._ctx = ctx

    @staticmethod
    async def test_download_uploaded_book(url: str):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    raise RuntimeError("Could not download book")
                return await resp.read()

    async def _display_edit_meta_message(self, msg: disnake.Message):
        view = UploadView(file_url=self._download_url, bot=self.bot, message=msg)
        await msg.edit(
            content="Please enter the metadata for the book",
            view=view,
        )


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
