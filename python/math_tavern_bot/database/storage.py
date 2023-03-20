import logging
from typing import Optional

import disnake
from disnake.ext.commands import Cog
from sqlalchemy.ext.asyncio import AsyncEngine
import sqlalchemy.dialects

from math_tavern_bot.config.models import CogConfiguration
from math_tavern_bot.database import SqlAlchemyBase
import logging
from typing import Optional

import disnake
import sqlalchemy.dialects
from disnake.ext.commands import Cog
from sqlalchemy.ext.asyncio import AsyncEngine

from math_tavern_bot.config.models import CogConfiguration
from math_tavern_bot.database import SqlAlchemyBase

json_store = sqlalchemy.Table(
    "json_store",
    SqlAlchemyBase.metadata,
    sqlalchemy.Column("id", sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("data", sqlalchemy.dialects.postgresql.JSONB)
)


class SqlAlchemyJsonStore:
    def __init__(self, engine: AsyncEngine):
        self.engine = engine

    async def get(self, key: str) -> Optional[dict]:
        """
        Retrieves a value from the store
        :param key: The key to retrieve
        :return: The value or None if not found
        """
        with self.engine.begin() as conn:
            result = await conn.execute(
                json_store.select().where(json_store.c.id == key))
            row = result.first()
            if row is None:
                return None
            return row[1]

    async def batch_get(self, keys: list[str]) -> Optional[dict[str, dict]]:
        """
        Batch retrieves values from the store
        :param keys: The keys to retrieve
        :return: A dictionary of keys to values or None if no keys were found
        """
        with self.engine.begin() as conn:
            result = await conn.execute(
                json_store.select().where(json_store.c.id.in_(keys)))
            if len(result) == 0:
                return None
            return {
                row[0]: row[1]
                for row in result
            }

    async def set(self, key: str, value: dict) -> None:
        """
        Sets a value in the store
        :param key: The key to set
        :param value: The value to set
        """
        with self.engine.begin() as conn:
            await conn.execute(
                json_store.insert().values(id=key, data=value)
                .on_conflict_do_update(
                    index_elements=[json_store.c.id],
                    set_=dict(data=value)
                )
            )

    async def batch_set(self, key_value_map: dict[str, dict]) -> None:
        """
        Batch sets values in the store
        :param key_value_map: A dictionary of keys to values
        """
        with self.engine.begin() as conn:
            # TODO: If this doesn't work just try except it
            await conn.execute(
                json_store.insert().values(
                    [
                        dict(id=key, data=value)
                        for key, value in key_value_map.items()
                    ]
                ).on_conflict_do_update(
                    index_elements=[json_store.c.id],
                    set_=dict(data=sqlalchemy.dialects.postgresql.JSONB.excluded.data)
                )
            )


class CogConfigStore:
    """KV store backed Cog Configuration"""

    def __init__(
            self, store: SqlAlchemyJsonStore, guilds: list[disnake.Guild], *,
            logger: logging.Logger
    ):
        self.store = store
        self.sep = "."
        self.logger = logger
        self.guilds = guilds
        self._guild_ids = list(map(lambda g: g.id, guilds))

    def build_key(self, parts: list[str]) -> str:
        return self.sep.join(parts)

    def split_key(self, key: str) -> list[str]:
        return key.split(self.sep)

    def build_cog_key(self, guild_id: int, cog: Cog) -> str:
        return self.build_key([str(guild_id), cog.qualified_name])

    def split_cog_key(self, key: str) -> tuple[int, str]:
        parts = self.split_key(key)
        return int(parts[0]), parts[1]

    async def get_cog_config(self, cog: Cog) -> Optional[dict[int, dict]]:
        """Get the configuration for a cog"""
        desired_configs = list(map(
            lambda guild_id: self.build_cog_key(guild_id, cog),
            self._guild_ids
        ))
        cog_config = await self.store.batch_get(desired_configs)
        self.logger.info("Cog config for %s: %s", cog.qualified_name, cog_config)
        if cog_config is None:
            return None
        # now we need to strip the guild id from the key
        return {
            self.split_cog_key(key)[0]: value
            for key, value in cog_config.items()
        }

    async def set_cog_config(self, cog: Cog, guild: disnake.Guild,
                             config: CogConfiguration):
        """Set the configuration for a cog"""
        self.logger.info("updating Cog %s config for guild %s (id: %s)",
                         cog.qualified_name, guild.name, guild.id)
        self.logger.info("Config: %s", config)
        key = self.build_cog_key(guild.id, cog)
        persisted_config = config.dict()
        self.logger.info("Guild %s (id: %s) has modified config", guild.name, guild.id)
        self.logger.info("Persisted config: %s", persisted_config)
        await self.store.set(key, persisted_config)
