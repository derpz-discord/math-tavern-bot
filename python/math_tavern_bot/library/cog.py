import logging
import typing

import disnake
from disnake.ext import commands

from math_tavern_bot.database.models import CogConfiguration
from math_tavern_bot.library.bot_classes import KvStoredBot

T = typing.TypeVar("T", bound=CogConfiguration)


class DatabaseConfiguredCog(commands.Cog):
    config: dict[disnake.Guild, T]

    def __init__(self, bot: KvStoredBot, configclass: typing.Type[T]):
        self.bot = bot
        self.logger = logging.getLogger(self.__class__.__cog_name__)
        self.config = {}
        self._configclass = configclass

    async def cog_load(self):
        self.logger.info(f"{self.__class__.__cog_name__} loaded")
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
