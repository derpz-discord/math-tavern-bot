"""
Provides functionality for managing tier lists.
We call a tier list a discord channel where users can rate
the difficulty of exercises in textbooks.

For a demonstration, visit the Math Tavern: https://discord.gg/EK5p2KUTxR
"""
import logging
from typing import Optional

import disnake
from derpz_botlib.bot_classes import ConfigurableCogsBot
from derpz_botlib.cog import DatabaseConfigurableCog
from derpz_botlib.database.storage import CogConfiguration
from derpz_botlib.utils import fmt_user
from disnake.ext import commands
from pydantic import BaseModel


class TierListPluginConfiguration(CogConfiguration):
    tier_list_category: Optional[int] = None


def setup(bot: ConfigurableCogsBot):
    bot.add_cog(TierListPlugin(bot))


class TierListPlugin(DatabaseConfigurableCog[TierListPluginConfiguration]):
    def __init__(self, bot: ConfigurableCogsBot):
        super().__init__(bot, TierListPluginConfiguration)

    @commands.slash_command(name="tierlist")
    async def tier_list(self, ctx: disnake.ApplicationCommandInteraction):
        pass

    @tier_list.sub_command_group(name="config")
    async def cmd_config(self, ctx: disnake.ApplicationCommandInteraction):
        pass

    @cmd_config.sub_command(description="Dumps the config")
    async def dump_config(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.send(embed=self.get_guild_config(ctx.guild).to_embed())

    @cmd_config.sub_command(
        description="Configures the category for which"
        " tier list channels will be created in"
    )
    async def tier_list_category(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        *,
        category: disnake.CategoryChannel = commands.Param(
            description="Category to create tier list channels in"
        ),
    ):
        await ctx.send(f"Setting tier list category to {category.mention}")
        guild_config = self.get_guild_config(ctx.guild)
        guild_config.tier_list_category = category.id
        await self.save_guild_config(ctx.guild, guild_config)

    @tier_list.sub_command(description="Requests a tier list")
    async def request(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        *,
        name: str = commands.Param(description="Name of the tier list"),
    ):
        await ctx.send(f"Requesting the tier list: {name}")

    @tier_list.sub_command(description="Creates a new tier list")
    @commands.has_permissions(manage_channels=True)
    async def create(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        *,
        name: str = commands.Param(description="Name of the tier list"),
    ):
        # TODO: This really should be REQUEST for a tier list.
        channel_name = name.strip().replace(" ", "-")
        self.logger.info(
            "User %s (id: %s) has requested for tier list %s to be made",
            fmt_user(ctx.user),
            ctx.user.id,
            channel_name,
        )
        await ctx.send(f"Creating the tier list: #{channel_name}")
        # TODO: WIP
