from collections import OrderedDict
from typing import Optional, Sequence

import disnake
import sqlalchemy.dialects.postgresql
from derpz_botlib.bot_classes import ConfigurableCogsBot
from derpz_botlib.cog import DatabaseConfigurableCog
from derpz_botlib.database.db import (SqlAlchemyBase, intpk, required_bigint,
                                      required_int, required_str)
from derpz_botlib.database.storage import CogConfiguration
from derpz_botlib.utils import (fmt_guild_include_id, fmt_user,
                                fmt_user_include_id)
from disnake import ApplicationCommandInteraction
from disnake.ext import commands
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import Mapped, mapped_column


class UserRoleCache(SqlAlchemyBase):
    __tablename__ = "user_role_cache"

    id: Mapped[intpk]
    user_id: Mapped[required_bigint]
    user_name: Mapped[required_str]
    server_id: Mapped[required_bigint]
    server_name: Mapped[required_str]
    role_ids: Mapped[list[int]] = mapped_column(
        sqlalchemy.dialects.postgresql.ARRAY(sqlalchemy.BigInteger)
    )
    role_names: Mapped[list[str]] = mapped_column(
        sqlalchemy.dialects.postgresql.ARRAY(sqlalchemy.String)
    )


class UserRoleCacheManager:
    def __init__(self, engine: AsyncEngine):
        self.engine = engine

    async def upsert_member(self, member: disnake.Member):
        """
        Attempts to upsert a member into the role cache.
        If the member is a bot, it will not be cached.
        We ignore the @everyone role.

        TODO: Batch upserts
        """
        async with AsyncSession(self.engine, expire_on_commit=False) as sess:
            if member.bot:
                return
            # Try to find the user in the cache first
            stmt = (
                sqlalchemy.select(UserRoleCache)
                .where(UserRoleCache.user_id == member.id)
                .where(UserRoleCache.server_id == member.guild.id)
            )
            result = await sess.execute(stmt)
            rows = result.scalars().all()
            if len(rows) == 0:
                # insert
                id_name_map = OrderedDict({r.id: r.name for r in member.roles})
                # remove the @everyone role
                id_name_map.pop(member.guild.default_role.id)
                urc = UserRoleCache(
                    user_id=member.id,
                    user_name=fmt_user(member),
                    server_id=member.guild.id,
                    server_name=member.guild.name,
                    role_ids=id_name_map.keys(),
                    role_names=id_name_map.values(),
                )
                sess.add(urc)
            elif len(rows) == 1:
                # update
                urc = rows[0]
                id_name_map = OrderedDict({r.id: r.name for r in member.roles})
                # remove the @everyone role
                id_name_map.pop(member.guild.default_role.id)
                urc.role_ids = id_name_map.keys()
                urc.role_names = id_name_map.values()

            else:
                raise ValueError("Multiple rows for user?")
            await sess.commit()

    async def get_all_cached_members(self, guild_id: int) -> Sequence[UserRoleCache]:
        async with AsyncSession(self.engine, expire_on_commit=False) as sess:
            stmt = sqlalchemy.select(UserRoleCache).where(
                UserRoleCache.server_id == guild_id
            )
            result = await sess.execute(stmt)
            rows = result.scalars().all()
            return rows

    async def get_member(
        self, member_id: int, server_id: int
    ) -> Optional[UserRoleCache]:
        with AsyncSession(self.engine) as sess:
            stmt = (
                sqlalchemy.select(UserRoleCache)
                .where(UserRoleCache.user_id == member_id)
                .where(UserRoleCache.server_id == server_id)
            )
            result = await sess.execute(stmt)
            rows = result.scalars().all()
            if len(rows) == 0:
                return None
            if len(rows) > 1:
                raise ValueError("More than one row for a member?")
            return rows[0]


def setup(bot: ConfigurableCogsBot):
    bot.add_cog(StickyRolesPlugin(bot))


class StickyRolesConfig(CogConfiguration):
    enabled: bool = True


class StickyRolesPlugin(DatabaseConfigurableCog[StickyRolesConfig]):
    def __init__(self, bot: ConfigurableCogsBot):
        super().__init__(bot, StickyRolesConfig)
        self.manager = UserRoleCacheManager(self.bot.engine)

    async def cog_load(self):
        """
        Checks what servers we are in for which we haven't cached the members.
        If the server has the plugin enabled, we cache the members.
        """
        await super().cog_load()
        # create the table if it doesn't exist
        async with self.bot.engine.begin() as conn:
            self.logger.info("Attempting to create table if it doesn't exist")
            await conn.run_sync(SqlAlchemyBase.metadata.create_all)

        for guild in self.bot.guilds:
            guild_config = self.get_guild_config(guild)
            if not guild_config.enabled:
                continue
            self.logger.info("Caching roles for %s", fmt_guild_include_id(guild))
            all_guild_members = guild.fetch_members(limit=None)

            members_we_know_about = await self.manager.get_all_cached_members(guild.id)
            async for member in all_guild_members:
                if member.id not in members_we_know_about:
                    await self.manager.upsert_member(member)

    @commands.Cog.listener(disnake.Event.member_update)
    async def on_member_update(self, before: disnake.Member, after: disnake.Member):
        """
        Performs the caching of roles for a member.
        """
        guild_config = self.get_guild_config(after.guild)
        if not guild_config.enabled:
            return

        if before.id != after.id:
            raise ValueError("Member ID changed?")

        if before.roles != after.roles:
            self.logger.info(f"Roles changes for %s", fmt_user(after))
            self.logger.info("Before: %s", [r.name for r in before.roles])
            self.logger.info("After: %s", [r.name for r in after.roles])
            await self.manager.upsert_member(after)

    @commands.Cog.listener(disnake.Event.member_join)
    async def on_member_join(self, member: disnake.Member):
        """
        Restore roles for a member when they join.
        """
        guild_config = self.get_guild_config(member.guild)
        if not guild_config.enabled:
            return

        member_info = await self.manager.get_member(member.id, member.guild.id)
        if member_info is None:
            return
        self.logger.info(
            "Restoring roles for %s in %s",
            fmt_user_include_id(member),
            fmt_guild_include_id(member.guild),
        )
        roles = list(
            filter(
                lambda r: r is not None,
                map(member.guild.get_role, member_info.role_ids),
            )
        )
        await member.edit(roles=roles)

    @commands.slash_command()
    @commands.is_owner()
    async def cmd_role_cache(self, ctx: ApplicationCommandInteraction):
        pass

    @cmd_role_cache.sub_command(description="Syncs roles to the role cache")
    async def cache_sync(self, ctx: ApplicationCommandInteraction):
        await ctx.send("Syncing roles...")
        # TODO: Move into manager
        async with AsyncSession(self.bot.engine.connect()) as sess:
            stmt = sqlalchemy.select(UserRoleCache).where(
                UserRoleCache.server_id == ctx.guild.id
            )
            result = await sess.execute(stmt)
            rows = result.scalars().all()
            for urc in rows:
                member = ctx.guild.get_member(urc.user_id)
                if member is None:
                    continue
                roles = [ctx.guild.get_role(r) for r in urc.role_ids]
                await member.edit(roles=roles)

    @cmd_role_cache.sub_command(
        description="Forces caching of all members in the server"
    )
    async def cache_all(self, ctx: ApplicationCommandInteraction):
        await ctx.send("Caching roles...")
        async for member in ctx.guild.fetch_members(limit=None):
            await self.manager.upsert_member(member)
