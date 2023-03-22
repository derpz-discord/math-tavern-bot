import aioboto3
import disnake
import types_aiobotocore_s3
from derpz_botlib.bot_classes import ConfigurableCogsBot
from disnake.ext import commands
from sqlalchemy.ext.asyncio import create_async_engine


# TODO:
class BotHelp(commands.HelpCommand):
    async def send_bot_help(self, mapping):
        embed = disnake.Embed(title="Help")


class BookBot(ConfigurableCogsBot):
    def __init__(self, db_url: str):
        engine = create_async_engine(db_url)
        super().__init__(
            engine=engine,
            command_prefix=".",
            intents=disnake.Intents.all(),
            reload=True,
            test_guilds=[1072179290671685753, 1073267404110561353],
        )
        # TODO: Make this configurable
        self.boto3_sess = aioboto3.Session(
            aws_access_key_id="minioadmin", aws_secret_access_key="minioadmin"
        )

    async def on_ready(self):
        self.logger.info(f"We have logged in as [cyan]{self.user}[/cyan]")
        self.logger.info(f"We are in {len(self.guilds)} servers")

        # TODO: Hardcoded
        try:
            # TODO: Hardcoded
            async with self.boto3_sess.resource(
                "s3", endpoint_url="http://localhost:9090"
            ) as s3:
                s3: types_aiobotocore_s3.S3ServiceResource
                bucket = await s3.Bucket("bookbot")
                self.logger.info("S3 connection successful. Bucket: %s", vars(bucket))
        except Exception as e:
            self.logger.error("S3 connection failed: %s", e)
            self.logger.exception(e)
            await self.close()
        self.load_cogs()
        await self.change_presence(activity=disnake.Game(name="bot ready"))

    def load_cogs(self):
        self.logger.info("[bold yellow]Loading cogs[/bold yellow]")
        self.load_extension("math_tavern_bot.plugins.plugin_bot_admin")
        self.load_extension("math_tavern_bot.plugins.plugin_pin")
        self.load_extension("math_tavern_bot.plugins.plugin_tierlist")
        self.load_extension("math_tavern_bot.plugins.plugin_autosully")
