import logging

import disnake
import sentry_sdk
from disnake.ext import commands

from bookbot.booklist import BookList


class BookBot(commands.Bot):
    def __init__(self, *args, **options):
        super().__init__(
            command_prefix="!",
            intents=disnake.Intents.all(),
            test_guilds=[1072179290671685753, 1073267404110561353],
        )
        self.logger = logging.getLogger(__name__)
        self.configure_logging()
        self.add_cog(BookList(self))

    def configure_logging(self):
        logging.basicConfig(level=logging.INFO)
        self.logger.info("Logging configured.")

    @staticmethod
    def setup_sentry(sentry_dsn: str, *, trace_sample_rate: float = 0.4):
        sentry_sdk.init(dsn=sentry_dsn, traces_sample_rate=trace_sample_rate)

    async def on_ready(self):
        logging.info(f"We have logged in as {self.user}")
