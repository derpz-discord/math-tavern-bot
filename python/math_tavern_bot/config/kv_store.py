import abc
import logging
from typing import Optional

import sqlalchemy
from disnake.ext.commands import Cog
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine

from math_tavern_bot.config.models import CogConfiguration
from math_tavern_bot.database import SqlAlchemyBase


class KvStore(abc.ABC):
    """An abstract key-value store"""

    def get(self, key: str, default=None) -> str:
        """Get a value from the store"""
        raise NotImplementedError

    def batch_get(self, keys: list[str], default=None) -> dict[str, str]:
        """Get a value from the store"""
        raise NotImplementedError

    def get_all_that_starts_with(self, prefix: str, default=None) -> dict[str, str]:
        """Get multiple values from the store that start with a prefix"""
        raise NotImplementedError

    def set(self, key: str, value: str):
        """Set a value in the store"""
        raise NotImplementedError

    def batch_set(self, key_value_pairs: dict[str, str]):
        """Set multiple values in the store"""
        raise NotImplementedError

    def delete(self, key) -> Optional[str]:
        """
        Delete a key from the store

        :param key: The key to delete
        :return: The value of the deleted key
        """
        raise NotImplementedError


class AsyncKvStore(KvStore, abc.ABC):
    """An abstract async key-value store"""

    async def get(self, key: str, default=None) -> str:
        """Get a value from the store"""
        raise NotImplementedError

    async def batch_get(self, keys: list[str], default=None) -> dict[str, str]:
        """Get a value from the store"""
        raise NotImplementedError

    async def get_all_that_starts_with(
        self, prefix: str, default=None
    ) -> dict[str, str]:
        """Get a value from the store"""
        raise NotImplementedError

    async def set(self, key: str, value: str):
        """Set a value in the store"""
        raise NotImplementedError

    async def batch_set(self, key_value_pairs: dict[str, str]):
        """Set multiple values in the store"""
        raise NotImplementedError

    async def delete(self, key):
        """
        Delete a key from the store

        :param key: The key to delete
        :return: The value of the deleted key
        """
        raise NotImplementedError


class MemoryKvStore(KvStore):
    """A memory backed key-value store"""

    def __init__(self):
        self.store = {}

    def get(self, key: str, default=None):
        return self.store.get(key, default)

    def batch_get(self, keys: list[str], default=None):
        return {key: self.store.get(key, default) for key in keys}

    def batch_set(self, key_value_pairs: dict[str, str]):
        self.store.update(key_value_pairs)

    def get_all_that_starts_with(self, prefix: str, default=None):
        return {
            key: value for key, value in self.store.items() if key.startswith(prefix)
        }

    def set(self, key: str, value: str):
        self.store[key] = value

    def delete(self, key):
        """
        Delete a key from the store

        :param key: The key to delete
        :return: The value of the deleted key
        """
        return self.store.pop(key)


class MemoryAsyncKvStore(AsyncKvStore):
    """An async memory backed key-value store"""

    async def batch_set(self, key_value_pairs: dict[str, str]):
        self.store.update(key_value_pairs)

    def __init__(self):
        self.store = {}

    async def get(self, key: str, default=None):
        return self.store.get(key, default)

    async def batch_get(self, keys: list[str], default=None):
        return {key: self.store.get(key, default) for key in keys}

    async def get_all_that_starts_with(self, prefix: str, default=None):
        return {
            key: value for key, value in self.store.items() if key.startswith(prefix)
        }

    async def set(self, key: str, value: str):
        self.store[key] = value

    async def delete(self, key):
        """
        Delete a key from the store

        :param key: The key to delete
        :return: The value of the deleted key
        """
        return self.store.pop(key)


# TODO: This only works for a single server
kv_store_table = sqlalchemy.Table(
    "kv_store",
    SqlAlchemyBase.metadata,
    sqlalchemy.Column("key", sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("value", sqlalchemy.String),
)


class AsyncSqlAlchemyKvStore(AsyncKvStore):
    """An async SQLAlchemy backed key-value store"""

    async def batch_set(self, key_value_pairs: dict[str, str]):
        async with self.engine.begin() as conn:
            try:
                stmt = kv_store_table.insert().values(
                    [
                        {"key": key, "value": value}
                        for key, value in key_value_pairs.items()
                    ]
                )

                await conn.execute(stmt)
            except IntegrityError:
                for key, value in key_value_pairs.items():
                    await conn.execute(
                        kv_store_table.update()
                        .where(kv_store_table.c.key == key)
                        .values(value=value)
                    )

    async def get(self, key: str, default=None):
        async with self.engine.begin() as conn:
            result = await conn.execute(
                kv_store_table.select().where(kv_store_table.c.key == key)
            )
            row = await result.fetchone()
            if row is None:
                return default
            return row.value

    async def batch_get(self, keys: list[str], default=None):
        async with self.engine.begin() as conn:
            result = await conn.execute(
                kv_store_table.select().where(kv_store_table.c.key.in_(keys))
            )
            rows = await result.fetchall()
            return {row.key: row.value for row in rows}

    async def get_all_that_starts_with(self, prefix: str, default=None):
        async with self.engine.begin() as conn:
            result = await conn.execute(
                kv_store_table.select().where(kv_store_table.c.key.startswith(prefix))
            )
            rows = result.fetchall()
            if len(rows) == 0:
                return default
            return {row.key: row.value for row in rows}

    async def set(self, key: str, value: str):
        async with self.engine.begin() as conn:
            try:
                stmt = kv_store_table.insert().values(key=key, value=value)
                await conn.execute(stmt)
            except IntegrityError:
                await conn.execute(
                    kv_store_table.update()
                    .where(kv_store_table.c.key == key)
                    .values(value=value)
                )

    async def delete(self, key):
        """
        Delete a key from the store

        :param key: The key to delete
        :return: The value of the deleted key
        """
        async with self.engine.begin() as conn:
            result = await conn.execute(
                kv_store_table.select().where(kv_store_table.c.key == key)
            )
            row = await result.fetchone()
            if row is None:
                return None
            await conn.execute(
                kv_store_table.delete().where(kv_store_table.c.key == key)
            )
            return row.value

    def __init__(self, engine: AsyncEngine):
        self.engine = engine


class CogConfigStore:
    """KV store backed Cog Configuration"""

    def __init__(self, store: AsyncKvStore, *, logger: logging.Logger):
        self.store = store
        self.sep = "."
        self.logger = logger

    def build_key(self, parts: list[str]) -> str:
        return self.sep.join(parts)

    async def get_cog_config(self, cog: Cog) -> Optional[CogConfiguration]:
        """Get the configuration for a cog"""
        # Note: can be prone to breaking if the cog name contains a dot
        # TODO: Investigate
        cog_config = await self.store.get_all_that_starts_with(
            cog.qualified_name + self.sep
        )
        self.logger.info("Cog config for %s: %s", cog.qualified_name, cog_config)
        if cog_config is None:
            return None
        return CogConfiguration.parse_obj(cog_config)

    async def set_cog_config(self, cog: Cog, config: CogConfiguration):
        """Set the configuration for a cog"""
        self.logger.info("Setting cog config for %s", cog.qualified_name)
        self.logger.info("Config: %s", config)
        persisted_config = dict(
            map(
                lambda item: (
                    self.build_key([cog.qualified_name, item[0]]),
                    str(item[1]),
                ),
                config.dict().items(),
            )
        )
        self.logger.info("Persisted config: %s", persisted_config)
        await self.store.batch_set(persisted_config)
