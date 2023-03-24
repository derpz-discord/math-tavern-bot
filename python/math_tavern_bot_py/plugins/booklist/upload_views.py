import logging
from typing import Optional

import disnake
from derpz_botlib.discord_utils.view import MessageAndBotAwareView
from disnake import ModalInteraction
from math_tavern_bot_py.bot import BookBot
from math_tavern_bot_py.plugins.booklist.models import BookMetadata
from math_tavern_bot_py.plugins.booklist.upload import \
    upload_book_and_insert_to_db
from math_tavern_bot_py.plugins.plugin_book_search import \
    query_openlibrary_for_isbn
from pydantic import ValidationError


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


class ConfirmBookMetaView(MessageAndBotAwareView):
    bot: "BookBot"

    def __init__(
        self, book_meta: BookMetadata, message: disnake.Message, bot: "BookBot"
    ):
        super().__init__(message, bot)
        self.book_meta = book_meta

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


class UploadView(MessageAndBotAwareView):
    bot: "BookBot"

    def __init__(self, file_url: str, *, message: disnake.Message, bot: "BookBot"):
        super().__init__(message, bot)
        self.file_url = file_url

    @disnake.ui.button(label="Edit Book Metadata", style=disnake.ButtonStyle.primary)
    async def edit_book_metadata(
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
