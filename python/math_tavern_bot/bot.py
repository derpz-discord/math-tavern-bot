import logging

import disnake
import sentry_sdk
from disnake.ext import commands
from disnake.ext.commands import errors, Context

from math_tavern_bot.booklist import BookListPlugin
from math_tavern_bot.config.plugin import ConfigPlugin
from math_tavern_bot.plugin_pin import PinMessagePlugin
from math_tavern_bot.tierlist import TierListPlugin


class BotHelp(commands.HelpCommand):
    async def send_bot_help(self, mapping):
        embed = disnake.Embed(title="Help")


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
        self.add_cog(ConfigPlugin(self))

    def configure_logging(self):
        logging.basicConfig(level=logging.INFO)
        self.logger.info("Hello world!")

    def setup_sentry(self, sentry_dsn: str, *, trace_sample_rate: float = 0.4):
        sentry_sdk.init(dsn=sentry_dsn, traces_sample_rate=trace_sample_rate)
        self.logger.info("Sentry configured")

    async def on_ready(self):
        self.logger.info(f"We have logged in as {self.user}")

    async def on_command_error(
        self, context: Context, exception: errors.CommandError
    ) -> None:
        self.logger.warning("Command error: %s", exception)
        if isinstance(exception, errors.CommandError):
            # check if the message is "You do not own this bot"
            if str(exception) == "You do not own this bot.":
                await context.reply(
                    "Only the owner can execute this command. "
                    "This incident has been reported to the owner."
                )
