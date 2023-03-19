import logging

import disnake
import sentry_sdk
from disnake import ApplicationCommandInteraction
from disnake.ext import commands

from math_tavern_bot.booklist import BookListPlugin
from math_tavern_bot.plugin_autosully import AutoSullyPlugin
from math_tavern_bot.plugin_pin import PinMessagePlugin
from math_tavern_bot.tierlist import TierListPlugin
from math_tavern_bot.utils import fmt_user


class BookBot(commands.Bot):
    def __init__(self, *args, **options):
        super().__init__(
            command_prefix=".",
            intents=disnake.Intents.all(),
            test_guilds=[1072179290671685753, 1073267404110561353],
        )
        self.logger = logging.getLogger(__name__)
        # TODO: Do not hardcode
        logging.getLogger("disnake").setLevel(logging.WARNING)
        self.configure_logging()
        self.add_cog(BookListPlugin(self))
        self.add_cog(TierListPlugin(self))
        # self.add_cog(AutoSullyPlugin(self))
        self.add_cog(PinMessagePlugin(self))

    def configure_logging(self):
        logging.basicConfig(level=logging.INFO)
        self.logger.info("Hello world!")

    @staticmethod
    def setup_sentry(sentry_dsn: str, *, trace_sample_rate: float = 0.4):
        sentry_sdk.init(dsn=sentry_dsn, traces_sample_rate=trace_sample_rate)

    async def on_ready(self):
        self.logger.info(f"We have logged in as {self.user}")
