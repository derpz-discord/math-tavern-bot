import disnake
import sqlalchemy
from derpz_botlib.bot_classes import ConfigurableCogsBot
from derpz_botlib.database.db import SqlAlchemyBase
from disnake.ext import commands
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine


class BookBot(ConfigurableCogsBot):
    def __init__(self, db_url: str, oauth_client_id: str):
        engine = create_async_engine(db_url)
        super().__init__(
            engine=engine,
            command_prefix=".",
            intents=disnake.Intents.all(),
            test_guilds=[1072179290671685753],
            owner_ids=[196556976866459648],
        )

        self._client_id = oauth_client_id

    async def on_ready(self):
        self.logger.info(f"We have logged in as [cyan]{self.user}[/cyan]")
        self.logger.info(f"We are in {len(self.guilds)} servers")

        self.load_cogs()
        await self.change_presence(activity=disnake.Game(name="bot ready"))

    async def _init_db(self):
        """Creates all the database tables"""

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

    @commands.slash_command(description="Get information about the bot")
    async def about(self, ctx: disnake.ApplicationCommandInteraction):
        embed = disnake.Embed(title="About")
        embed.add_field(
            name="Source", value="https://github.com/derpz-discord/math-tavern-bot"
        )
        embed.add_field(
            name="Invite",
            value=disnake.utils.oauth_url(
                self._client_id, permissions=disnake.Permissions.administrator()
            ),
        )

    def load_cogs(self):
        # TODO: Dynamic load and unload
        self.logger.info("[bold yellow]Loading cogs[/bold yellow]")
        self.load_extension("math_tavern_bot_py.plugins.plugin_bot_admin")
        self.load_extension("math_tavern_bot_py.plugins.plugin_pin")
        self.load_extension("math_tavern_bot_py.plugins.plugin_autosully")
        self.load_extension("math_tavern_bot_py.plugins.plugin_moderation")
        self.load_extension("math_tavern_bot_py.plugins.plugin_goal_setting")
        self.load_extension("math_tavern_bot_py.plugins.plugin_auto_purge")
        self.load_extension("math_tavern_bot_py.plugins.plugin_tierlist")
        self.load_extension("math_tavern_bot_py.plugins.plugin_sticky_roles")
