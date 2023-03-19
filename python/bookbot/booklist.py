import functools
from typing import Optional

import disnake
from disnake import ModalInteraction
from disnake.ext import commands


class EditBookMetaModal(disnake.ui.Modal):
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


class BookList(commands.Cog):
    """
    Cog for managing a book list channel.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
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

    @commands.slash_command(name="booklist")
    async def book_list(self, ctx: disnake.ApplicationCommandInteraction):
        pass

    @book_list.sub_command_group()
    async def config(self, ctx: disnake.ApplicationCommandInteraction):
        pass

    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):
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
        await ctx.send(f"Searching for {query}...")

    @book_list.sub_command(
        description="Get a link to upload your book to the books list."
    )
    async def get_upload_link(self, ctx: disnake.ApplicationCommandInteraction):
        """
        Get a link to upload your book to the books list.
        """
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
