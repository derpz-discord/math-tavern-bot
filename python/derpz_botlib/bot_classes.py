import logging
import os
from collections import deque

import rich
from derpz_botlib.database.db import SqlAlchemyBase
from derpz_botlib.database.storage import (AsyncSqlAlchemyKvJsonStore,
                                           CogConfigStore)
from disnake import ApplicationCommandInteraction
from disnake.ext import commands
from disnake.ext.commands import errors
from rich.logging import RichHandler
from sqlalchemy.ext.asyncio import AsyncEngine


def get_log_level_from_env() -> int:
    """
    Gets the log level from the environment.
    Defaults to INFO if not set
    """

    log_level = os.getenv("LOG_LEVEL", "INFO")
    return getattr(logging, log_level.upper(), logging.INFO)


class LoggedBot(commands.Bot):
    """A bot with logging and sentry configured"""

    def __init__(self, *args, **options):
        super().__init__(*args, **options)
        # This gets the name of the inherited class so the logger name is correct
        self.logger = logging.getLogger(self.__class__.__name__)
        self._configure_logging()
        self._configure_sentry()

    def _configure_logging(self):
        # TODO: Allow user configuration for this
        logging.getLogger("disnake").setLevel(logging.WARNING)

        self.logger.setLevel(get_log_level_from_env())
        rh = RichHandler(markup=True, rich_tracebacks=True)
        rh.setFormatter(logging.Formatter("[%(name)s] %(message)s"))
        # TODO: Add logstash handler
        self.logger.addHandler(rh)

    def _configure_sentry(self):
        sentry_dsn = os.getenv("SENTRY_DSN")
        if sentry_dsn is None:
            return
        trace_sample_rate = float(os.getenv("SENTRY_TRACE_SAMPLE_RATE", 0.4))
        import sentry_sdk

        sentry_sdk.init(dsn=sentry_dsn, traces_sample_rate=trace_sample_rate)
        self.logger.info(f"Sentry configured. Sampling rate: {trace_sample_rate}")

    async def on_command_error(
        self, context: commands.Context, exception: commands.errors.CommandError
    ) -> None:
        if self.extra_events.get("on_command_error", None):
            return

        command = context.command
        if command and command.has_error_handler():
            return

        cog = context.cog
        if cog and cog.has_error_handler():
            return

        if isinstance(exception, commands.errors.CommandNotFound):
            return
        if isinstance(
            exception,
            (
                commands.errors.NotOwner,
                commands.errors.MissingPermissions,
                commands.errors.MissingRole,
            ),
        ):
            await context.reply("You cannot use this command.")
            self.logger.warning(
                "%s tried to use a command they are not" " allowed to use: %s",
                context.author,
                context.message.content,
            )

        if isinstance(
            exception,
            (
                commands.errors.BotMissingRole,
                commands.errors.BotMissingPermissions,
                commands.errors.BotMissingAnyRole,
            ),
        ):
            self.logger.warning(
                "Bot is missing permissions to run command: %s", context.message.content
            )

        self.logger.exception(exception, exc_info=exception)

    async def on_slash_command_error(
        self,
        interaction: ApplicationCommandInteraction,
        exception: commands.errors.CommandError,
    ) -> None:
        if self.extra_events.get("on_slash_command_error", None):
            return

        command = interaction.application_command
        if command and command.has_error_handler():
            return

        cog = command.cog
        if cog and cog.has_slash_error_handler():
            return
        await interaction.send(
            "\N{CROSS MARK} An error occurred while running this command",
            ephemeral=True,
        )
        self.logger.exception(exception, exc_info=exception)


class DatabasedBot(LoggedBot):
    """A bot with a database connection attached"""

    def __init__(self, *args, engine: AsyncEngine, **options):
        super().__init__(*args, **options)
        # TODO: Create a sync engine too
        self.engine = engine
        self.engine_logger = self.logger.getChild("database")

    async def start(self, *args, **kwargs):
        await self._init_db()
        await super().start(*args, **kwargs)

    async def _init_db(self):
        """Creates all the database tables"""
        self.engine_logger.info("Initializing database")
        async with self.engine.begin() as conn:
            self.engine.echo = True
            await conn.run_sync(SqlAlchemyBase.metadata.create_all)
            self.engine.echo = False
        self.engine_logger.info("Database initialized")


class ConfigurableCogsBot(DatabasedBot):
    def __init__(self, *args, engine: AsyncEngine, **options):
        super().__init__(*args, engine=engine, **options)
        self.kv_store = AsyncSqlAlchemyKvJsonStore(self.engine)
        self.cog_config_store = CogConfigStore(
            self.kv_store, logger=self.logger.getChild("cog_config_store")
        )
