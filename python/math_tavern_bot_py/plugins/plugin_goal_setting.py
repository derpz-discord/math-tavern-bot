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
from typing import Optional

import disnake
from derpz_botlib.bot_classes import ConfigurableCogsBot
from derpz_botlib.cog import DatabaseConfigurableCog
from derpz_botlib.database.db import (SqlAlchemyBase, intpk, required_int,
                                      required_str, tz_aware_timestamp)
from derpz_botlib.database.storage import CogConfiguration
from derpz_botlib.discord_utils.view import (DatePickerView,
                                             MessageAndBotAwareView)
from derpz_botlib.utils import reply_feature_wip
from disnake import ApplicationCommandInteraction
from disnake.ext import commands
from sqlalchemy.orm import Mapped


class GoalSettingPluginConfig(CogConfiguration):
    study_role: Optional[int] = None


class Goal(SqlAlchemyBase):
    __tablename__ = "user_goals"

    id: Mapped[intpk]
    user_id: Mapped[required_int]
    goal_name: Mapped[required_str]
    goal_description: Mapped[required_str]
    end_dt: Mapped[tz_aware_timestamp]


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
        description: str = commands.Param(description="The description of the goal"),
        end_date: str = commands.Param(description="The end date of the goal"),
        end_time: str = commands.Param(description="The end time of the goal"),
        end_tz: int = commands.Param(description="The end timezone of the goal"),
    ):
        # TODO
        await reply_feature_wip(ctx)

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
