import disnake


class SearchDropDown(disnake.ui.Select):
    def __init__(self, options: list[disnake.SelectOption], **kwargs):
        super().__init__(options=options, **kwargs)

    async def callback(self, interaction: disnake.MessageInteraction):
        # get the selected option
        selected_option = self.values[0]
        await interaction.response.send_message(
            f"Selected the option: {selected_option}"
        )


class SearchView(disnake.ui.View):
    """
    View to present to the user when they search for a book in
    the book list.
    """

    message: disnake.Message

    def __init__(self, search_results: list[disnake.SelectOption]):
        super().__init__()
        self.add_item(SearchDropDown(options=search_results))

    async def on_timeout(self):
        await self.message.edit("This is no longer available", view=None)
