import pkgutil
from collections import deque
from os import getenv

import disnake
import sqlalchemy
from derpz_botlib.bot_classes import ConfigurableCogsBot
from derpz_botlib.database.db import SqlAlchemyBase
from disnake.ext import commands
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine


class TavernBot(ConfigurableCogsBot):
    def __init__(self, db_url: str, oauth_client_id: str):
        engine = create_async_engine(db_url)
        super().__init__(
            engine=engine,
            command_prefix=".",
            intents=disnake.Intents.all(),
            test_guilds=list(map(int, getenv("DEBUG_GUILDS").split(","))),
            owner_ids=[196556976866459648],
        )

        self.client_id = oauth_client_id

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

    def load_cogs(self):
        self.logger.info("[bold yellow]Loading cogs[/bold yellow]")
        extension_list = list(
            map(lambda x: x.name, pkgutil.iter_modules(["math_tavern_bot_py/plugins"]))
        )
        do_not_load = getenv("DISABLED_PLUGINS").split(",")
        to_load = list(filter(lambda x: x not in do_not_load, extension_list))

        deque(
            map(
                self.load_extension,
                map(lambda x: f"math_tavern_bot_py.plugins.{x}", to_load),
            )
        )
