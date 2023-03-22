import disnake
from disnake.ext import commands


class MessageAwareView(disnake.ui.View):
    """
    A view that is aware of the message it is attached to.
    """

    message: disnake.Message

    def __init__(self, message: disnake.Message):
        super().__init__()
        self.message = message

    async def on_timeout(self):
        await self.message.edit("This is no longer available", view=None)


class BotAwareView(disnake.ui.View):
    """
    A view that is aware of the bot that is using it.
    """

    bot: commands.Bot

    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot
