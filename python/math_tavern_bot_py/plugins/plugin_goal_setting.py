"""
A goal setting plugin.

Creates a goal and tracks progress towards it. If a "study role" is set up, it will
also apply the role such that you cannot access social channels until you have
completed your goal.
/goal create <goal name> <goal description> <end date> <end time>

/goal set_study_role <role name>

Indicates that you have completed the goal. If a study role is set up, it will
remove the role from you.
/goal complete <goal name>

TODO:
- Have the bot dynamically manage the study role
"""
from datetime import datetime
from typing import Optional, Sequence

import disnake
import sqlalchemy.exc
from sqlalchemy import select

from derpz_botlib.bot_classes import ConfigurableCogsBot
from derpz_botlib.cog import DatabaseConfigurableCog
from derpz_botlib.database.db import (SqlAlchemyBase, intpk, required_int,
                                      required_str, tz_aware_timestamp, required_bigint)
from derpz_botlib.database.storage import CogConfiguration
from derpz_botlib.discord_utils.view import (DatePickerView,
                                             MessageAndBotAwareView)
from derpz_botlib.utils import parse_human_time, reply_feature_wip
from disnake import ApplicationCommandInteraction
from disnake.ext import commands
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from sqlalchemy.orm import Mapped


class GoalSettingPluginConfig(CogConfiguration):
    study_role: Optional[int] = None


class Goal(SqlAlchemyBase):
    __tablename__ = "user_goals"

    id: Mapped[intpk]
    user_id: Mapped[required_bigint]
    goal_name: Mapped[required_str]
    goal_description: Mapped[required_str]
    end_dt: Mapped[tz_aware_timestamp]


class GoalManager:
    def __init__(self, engine: AsyncEngine):
        self.engine = engine

    async def create_goal(
            self, user_id: int, goal_name: str, goal_description: str, end_dt: datetime
    ):
        async with AsyncSession(self.engine, expire_on_commit=False) as session:
            goal = Goal(
                user_id=user_id,
                goal_name=goal_name,
                goal_description=goal_description,
                end_dt=end_dt,
            )
            session.add(goal)
            await session.commit()
            return goal

    async def get_goal(self, user_id: int, goal_name: str) -> Optional[Goal]:
        async with AsyncSession(self.engine) as session:
            query_stmt = (
                select(Goal)
                .where(Goal.user_id == user_id)
                .where(Goal.goal_name == goal_name)
            )
            goal = await session.execute(query_stmt)
            return goal.scalar_one_or_none()

    async def get_goals(self, user_id: int) -> Sequence[Goal]:
        async with AsyncSession(self.engine) as session:
            query_stmt = select(Goal).where(Goal.user_id == user_id)
            goals = await session.execute(query_stmt)

            return goals.scalars().all()

    async def delete_goal(self, user_id: int, goal_name: str):
        async with AsyncSession(self.engine) as session:
            goal = (
                session.query(Goal)
                .filter(Goal.user_id == user_id)
                .filter(Goal.goal_name == goal_name)
                .first()
            )
            await session.delete(goal)
            await session.commit()


class GoalSettingView(MessageAndBotAwareView):
    def __init__(self, message: disnake.Message, bot: commands.Bot):
        super().__init__(message, bot)


class GoalSettingPlugin(DatabaseConfigurableCog[GoalSettingPluginConfig]):
    """
    A plugin for setting goals and tracking progress towards them.
    """

    def __init__(self, bot: ConfigurableCogsBot):
        super().__init__(bot, GoalSettingPluginConfig)

    @commands.slash_command(name="goal")
    async def cmd_goal(self, ctx: ApplicationCommandInteraction):
        pass

    @commands.slash_command(name="goal_plugin_config")
    async def cmd_goal_plugin_config(self, ctx: ApplicationCommandInteraction):
        pass

    @cmd_goal.sub_command(description="Creates a goal")
    async def create(
            self,
            ctx: ApplicationCommandInteraction,
            name: str = commands.Param(description="The name of the goal"),
            description: str = commands.Param(
                description="The description of the goal"),
            end_in: str = commands.Param(description="The end time delta of the goal"),
    ):
        try:
            parse_human_time(end_in)
        except ValueError as e:
            raise commands.BadArgument(str(e))
        await ctx.send("Creating goal...", ephemeral=True)
        manager = GoalManager(self.bot.engine)
        goal = await manager.create_goal(
            ctx.author.id,
            name,
            description,
            (datetime.now() + parse_human_time(end_in)).replace(microsecond=0),
        )
        await ctx.edit_original_response(f"Goal created! Goal ID: {goal.id}")

    @cmd_goal.sub_command(description="See what goals you have currently set")
    async def list(self, ctx: ApplicationCommandInteraction):
        goals = await GoalManager(self.bot.engine).get_goals(ctx.author.id)
        await ctx.send(
            embed=disnake.Embed(
                title="Your Goals",
                description="\n".join(
                    f"{goal.id}: {goal.goal_name} - {goal.goal_description}"
                    for goal in goals
                ),
            )
        )

    @cmd_goal.sub_command(description="Goal creation UI")
    async def create_ui(self, ctx: ApplicationCommandInteraction):
        await ctx.send("Loading...")
        await ctx.edit_original_response(
            view=DatePickerView(await ctx.original_response())
        )

    @cmd_goal_plugin_config.sub_command(description="Sets the study role")
    @commands.has_permissions(manage_roles=True)
    @commands.guild_only()
    async def set_study_role(
            self,
            ctx: ApplicationCommandInteraction,
            *,
            role: disnake.Role = commands.Param(
                description="The role to set as the study role"
            ),
    ):
        guild_config = self.get_guild_config(ctx.guild)
        guild_config.study_role = role.id
        await self.save_guild_config(ctx.guild, guild_config)
        await ctx.send(
            f"Set study role to {role.mention}",
            allowed_mentions=disnake.AllowedMentions.none(),
        )

    @cmd_goal_plugin_config.sub_command(description="Dumps the config")
    @commands.has_permissions(manage_roles=True)
    @commands.guild_only()
    async def dump_config(
            self,
            ctx: ApplicationCommandInteraction,
    ):
        guild_config = self.get_guild_config(ctx.guild)
        await ctx.send(embed=guild_config.to_embed())


def setup(bot: ConfigurableCogsBot):
    bot.add_cog(GoalSettingPlugin(bot))
