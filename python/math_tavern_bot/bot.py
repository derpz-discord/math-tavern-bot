import aioboto3
import disnake
import sentry_sdk
import types_aiobotocore_s3
from disnake.ext import commands
from disnake.ext.commands import errors, Context
from sqlalchemy.ext.asyncio import create_async_engine

from math_tavern_bot.book_search import BookSearchPlugin
from math_tavern_bot.booklist import BookListPlugin
from math_tavern_bot.library.bot_classes import KvStoredBot
from math_tavern_bot.plugins_bot_admin import BotAdminPlugin
from math_tavern_bot.plugin_autosully import AutoSullyPlugin
from math_tavern_bot.plugin_pin import PinMessagePlugin
from math_tavern_bot.tierlist import TierListPlugin


# TODO:
class BotHelp(commands.HelpCommand):
    async def send_bot_help(self, mapping):
        embed = disnake.Embed(title="Help")


class BookBot(KvStoredBot):
    def __init__(self, *args, db_url: str, **options):
        engine = create_async_engine(db_url)
        super().__init__(
            database=engine,
            command_prefix=".",
            intents=disnake.Intents.all(),
            reload=True,
            test_guilds=[1072179290671685753, 1073267404110561353],
        )
        # TODO: Make this configurable
        self.s3 = aioboto3.Session(
            aws_access_key_id="minioadmin", aws_secret_access_key="minioadmin"
        )

    def setup_sentry(self, sentry_dsn: str, *, trace_sample_rate: float = 0.4):
        sentry_sdk.init(dsn=sentry_dsn, traces_sample_rate=trace_sample_rate)
        self.logger.info("Sentry configured")

    async def on_ready(self):
        self.logger.info(f"We have logged in as {self.user}")
        self.logger.info(f"We are in {len(self.guilds)} servers")

        # TODO: Hardcoded
        try:
            # TODO: Hardcoded
            async with self.s3.resource(
                "s3", endpoint_url="http://localhost:9090"
            ) as s3:
                s3: types_aiobotocore_s3.S3ServiceResource
                bucket = await s3.Bucket("bookbot")
                resp = bucket.get_available_subresources()
                self.logger.info("S3 connection successful. Response: %s", resp)
        except Exception as e:
            self.logger.error("S3 connection failed: %s", e)
            self.logger.exception(e)
            await self.close()

        # TODO: Better system of doing this
        self.add_cog(BookListPlugin(self))
        self.add_cog(TierListPlugin(self))
        self.add_cog(AutoSullyPlugin(self))
        self.add_cog(PinMessagePlugin(self))
        self.add_cog(BotAdminPlugin(self))
        self.add_cog(BookSearchPlugin(self))

        await self.change_presence(activity=disnake.Game(name="bot ready"))

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
