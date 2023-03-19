import disnake
from disnake import ModalInteraction


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

    def __init__(self, **kwargs):
        components = [
            disnake.ui.TextInput(
                label="Title",
                placeholder="The title of the book",
                custom_id="book_title",
                style=disnake.TextInputStyle.single_line,
            ),
            disnake.ui.TextInput(
                label="Author",
                placeholder="The author of the book",
                custom_id="book_author",
                style=disnake.TextInputStyle.single_line,
            ),
            disnake.ui.TextInput(
                label="ISBN",
                placeholder="The ISBN of the book",
                custom_id="book_isbn",
                style=disnake.TextInputStyle.single_line,
            ),
        ]
        super().__init__(title="Book Metadata", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        embed = disnake.Embed(title="Book Metadata")
        for key, value in inter.text_values.items():
            embed.add_field(
                name=key,
                value=value[:1024],
                inline=False,
            )
        await inter.response.send_message(embed=embed)

    async def on_timeout(self):
        pass

    async def on_error(self, error: Exception, interaction: ModalInteraction) -> None:
        await interaction.send(
            "An error occurred while processing this modal", ephemeral=True
        )

    async def on_close(self, interaction):
        await interaction.response.send_message("Closed", ephemeral=True)


class UploadView(disnake.ui.View):
    message: disnake.Message

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @disnake.ui.button(label="Edit Book Metadata", style=disnake.ButtonStyle.primary)
    async def upload(
        self, button: disnake.ui.Button, interaction: disnake.MessageInteraction
    ):
        await interaction.response.send_modal(EditBookMetaModal())

    @disnake.ui.button(label="Cancel", style=disnake.ButtonStyle.danger)
    async def cancel(
        self, button: disnake.ui.Button, interaction: disnake.MessageInteraction
    ):
        await interaction.response.send_message("Cancelled", ephemeral=True)
        self.stop()

    async def on_timeout(self):
        await self.message.edit(view=None)
