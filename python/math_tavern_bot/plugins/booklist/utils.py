import disnake
from derpz_botlib.discord_utils.view import MessageAwareView


class BookPaginator(MessageAwareView):
    def __init__(self, message: disnake.Message):
        super().__init__(message)
