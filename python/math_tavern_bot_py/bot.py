import aioboto3
import disnake
import sqlalchemy
import types_aiobotocore_s3
from derpz_botlib.bot_classes import ConfigurableCogsBot
from derpz_botlib.database.db import SqlAlchemyBase
from disnake.ext import commands
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine


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

    async def _init_db(self):
        """Creates all the database tables"""
        # TODO: Reimport all the stuff we need

        self.engine_logger.info("Initializing database")
        async with self.engine.begin() as conn:
            self.engine.echo = True
            await conn.run_sync(SqlAlchemyBase.metadata.create_all)
            self.engine.echo = False
        self.engine_logger.info("Database initialized")
        # TODO: Do not inline SQL to do this query
        async with AsyncSession(self.engine) as sess:
            tables = await sess.execute(
                sqlalchemy.text(
                    "SELECT tablename, schemaname FROM pg_catalog.pg_tables WHERE schemaname != 'pg_catalog' AND schemaname != 'information_schema';"
                )
            )

            self.engine_logger.info("Tables: %s", tables.fetchall())

    def load_cogs(self):
        # TODO: Dynamic load and unload
        self.logger.info("[bold yellow]Loading cogs[/bold yellow]")
        self.load_extension("math_tavern_bot_py.plugins.plugin_bot_admin")
        self.load_extension("math_tavern_bot_py.plugins.plugin_pin")
        # self.load_extension("math_tavern_bot_py.plugins.plugin_tierlist")
        # self.load_extension("math_tavern_bot_py.plugins.booklist.plugin")
        self.load_extension("math_tavern_bot_py.plugins.plugin_autosully")
        self.load_extension("math_tavern_bot_py.plugins.plugin_moderation")
        self.load_extension("math_tavern_bot_py.plugins.plugin_goal_setting")
        self.load_extension("math_tavern_bot_py.plugins.plugin_auto_purge")
