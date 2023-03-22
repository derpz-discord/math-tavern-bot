import typing

import disnake
from derpz_botlib.bot_classes import (ConfigurableCogsBot, DatabasedBot,
                                      LoggedBot)
from derpz_botlib.database.storage import CogConfiguration
from disnake.ext import commands

T = typing.TypeVar("T", bound=CogConfiguration)


class LoggedCog(commands.Cog):
    """
    A cog which can utilize the logger.
    """

    def __init__(self, bot: LoggedBot):
        self.bot = bot
        self.logger = self.bot.logger.getChild(self.__class__.__cog_name__)


class DatabasedCog(LoggedCog):
    """
    A cog which can utilize the database.
    """

    bot: DatabasedBot

    def __init__(self, bot: DatabasedBot):
        super().__init__(bot)
        self.engine = bot.engine


class DatabaseConfigurableCog(typing.Generic[T], LoggedCog):
    """
    A cog which can be configured on a per-guild basis.
    Loads and saves configuration from the database.

    Author's Notes:
    This will load the configuration of all the guilds the bot is in
    when the cog is loaded.
    """

    config: dict[disnake.Guild, T]
    bot: ConfigurableCogsBot

    def __init__(self, bot: ConfigurableCogsBot, configclass: typing.Type[T]):
        super().__init__(bot)
        self.config = {}
        self._configclass = configclass

    def get_guild_config(self, guild: disnake.Guild) -> T:
        """
        Get the configuration for a guild.
        If no configuration exists, a new one is created.
        """
        return self.config.get(guild, self._configclass())

    async def save_guild_config(self, guild: disnake.Guild, config: T):
        """
        Save the configuration for a guild to the database.
        This will also update the in-memory configuration.
        """
        self.config[guild] = config
        await self.bot.cog_config_store.set_cog_config(self, guild, self.config[guild])

    async def cog_load(self):
        self.logger.info(f"Initializing {self.__class__.__cog_name__}")
        if len(self.bot.guilds) == 0:
            self.logger.warning("No guilds found. Skipping config load.")
            if not self.bot.is_ready():
                self.logger.warning(
                    "Note: This may occur if you load the cog outside of on_ready. "
                    "Make sure you load the cog in on_ready"
                )
            return
        # load config from DB
        guilds = list(map(lambda x: x.id, self.bot.guilds))
        config = await self.bot.cog_config_store.get_cog_config(guilds, self)
        if config:
            self.config = dict(
                map(
                    lambda x: (
                        self.bot.get_guild(x[0]),
                        self._configclass.parse_obj(x[1]),
                    ),
                    config.items(),
                )
            )
        else:
            self.logger.warning("No config found in DB")
        self.logger.info(f"Initialized {self.__class__.__cog_name__}")

    def cog_unload(self):
        # TODO: Flush config to DB
        pass
