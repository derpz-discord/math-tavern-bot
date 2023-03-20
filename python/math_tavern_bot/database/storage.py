import json
import logging
from typing import Optional

import disnake
import sqlalchemy.dialects
import sqlalchemy.dialects
from disnake.ext.commands import Cog
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncEngine

from math_tavern_bot.database import SqlAlchemyBase
from math_tavern_bot.database.models import CogConfiguration

json_store = sqlalchemy.Table(
    "json_store",
    SqlAlchemyBase.metadata,
    sqlalchemy.Column("id", sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("data", postgresql.JSONB),
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
        async with self.engine.connect() as conn:
            result = await conn.execute(
                json_store.select().where(json_store.c.id == key)
            )
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
        async with self.engine.connect() as conn:
            result = await conn.execute(
                json_store.select().where(json_store.c.id.in_(keys))
            )
            if result.rowcount == 0:
                return None
            return {row[0]: row[1] for row in result}

    async def set(self, key: str, value: dict) -> None:
        """
        Sets a value in the store
        :param key: The key to set
        :param value: The value to set
        """
        async with self.engine.connect() as conn:
            maybe_row = await conn.execute(
                json_store.select().where(json_store.c.id == key)
            )
            if maybe_row.rowcount == 0:
                await conn.execute(json_store.insert().values(id=key, data=value))
            else:
                await conn.execute(
                    json_store.update().where(json_store.c.id == key).values(data=value)
                )
            await conn.commit()

    async def batch_set(self, key_value_map: dict[str, dict]) -> None:
        """
        Batch sets values in the store
        :param key_value_map: A dictionary of keys to values
        """
        async with self.engine.connect() as conn:
            # fetch the row first and see if it exists
            # if it does, update it
            # if it doesn't, insert it
            row = await conn.execute(
                json_store.select().where(json_store.c.id.in_(key_value_map.keys()))
            )
            if row.rowcount() > 0:
                for row in row:
                    key = row[0]
                    value = row[1]
                    if key in key_value_map:
                        await conn.execute(
                            json_store.update()
                            .where(json_store.c.id == key)
                            .values(data=key_value_map[key])
                        )
                        del key_value_map[key]
            # insert the remaining keys
            if len(key_value_map) > 0:
                await conn.execute(
                    json_store.insert(),
                    [dict(id=key, data=value) for key, value in key_value_map.items()],
                )
            await conn.commit()


class CogConfigStore:
    """KV store backed Cog Configuration"""

    def __init__(self, store: SqlAlchemyJsonStore, *, logger: logging.Logger):
        self.store = store
        self.sep = "."
        self.logger = logger

    def build_key(self, parts: list[str]) -> str:
        return self.sep.join(parts)

    def split_key(self, key: str) -> list[str]:
        return key.split(self.sep)

    def build_cog_key(self, guild_id: int, cog: Cog) -> str:
        return self.build_key([str(guild_id), cog.qualified_name])

    def split_cog_key(self, key: str) -> tuple[int, str]:
        parts = self.split_key(key)
        return int(parts[0]), parts[1]

    async def get_cog_config(
        self, guilds: list[int], cog: Cog
    ) -> Optional[dict[int, dict]]:
        """Get the configuration for a cog"""
        desired_configs = list(
            map(lambda guild_id: self.build_cog_key(guild_id, cog), guilds)
        )
        cog_config = await self.store.batch_get(desired_configs)
        self.logger.info("Cog config for %s: %s", cog.qualified_name, cog_config)
        if cog_config is None:
            return None
        # now we need to strip the guild id from the key
        return {self.split_cog_key(key)[0]: value for key, value in cog_config.items()}

    async def set_cog_config(
        self, cog: Cog, guild: disnake.Guild, config: CogConfiguration
    ):
        """Set the configuration for a cog"""
        self.logger.info(
            "updating Cog %s config for guild %s (id: %s)",
            cog.qualified_name,
            guild.name,
            guild.id,
        )
        self.logger.info("%s", config)
        key = self.build_cog_key(guild.id, cog)
        persisted_config = json.loads(config.json())
        self.logger.info("Persisted config: %s", persisted_config)
        await self.store.set(key, persisted_config)
