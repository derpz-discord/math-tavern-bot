import logging

from disnake.ext import commands
from sqlalchemy.ext.asyncio import AsyncEngine

from math_tavern_bot.database import SqlAlchemyBase
from math_tavern_bot.database.storage import SqlAlchemyJsonStore, CogConfigStore


class LoggedBot(commands.Bot):
    def __init__(self, *args, **options):
        super().__init__(*args, **options)
        self.logger = logging.getLogger(__name__)
        # TODO: Do not hardcode
        logging.getLogger("disnake").setLevel(logging.WARNING)
        self.configure_logging()

    def configure_logging(self):
        logging.basicConfig(level=logging.INFO)
        self.logger.info("Hello world!")


class DatabasedBot(LoggedBot):
    def __init__(self, *args, database: AsyncEngine, **options):
        super().__init__(*args, **options)
        self.db = database
        self.db_logger = self.logger.getChild("database")

    async def start(self, *args, **kwargs):
        await self._init_db()
        await super().start(*args, **kwargs)

    async def _init_db(self):
        self.db_logger.info("Initializing database")
        async with self.db.begin() as conn:
            await conn.run_sync(SqlAlchemyBase.metadata.create_all)
        self.db_logger.info("Database initialized")


class KvStoredBot(DatabasedBot):
    def __init__(self, *args, database: AsyncEngine, **options):
        super().__init__(*args, database=database, **options)
        self.kv_store = SqlAlchemyJsonStore(self.db)
        self.cog_config_store = CogConfigStore(
            self.kv_store, logger=self.logger.getChild("cog_config_store")
        )
