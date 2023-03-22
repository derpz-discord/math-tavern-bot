"""
Provides functionality for managing tier lists.
We call a tier list a discord channel where users can rate
the difficulty of exercises in textbooks.

For a demonstration, visit the Math Tavern: https://discord.gg/EK5p2KUTxR
"""
import logging

import disnake
from derpz_botlib.utils import fmt_user
from disnake.ext import commands
from pydantic import BaseModel


class TierList(BaseModel):
    owner: int
    name: str


def setup(bot: commands.Bot):
    bot.add_cog(TierListPlugin(bot))


class TierListPlugin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        self.config_logger = self.logger.getChild("config")
        self._documentation = {
            self.tier_list_category: disnake.Embed(
                title="tier_list_category",
                description="Sets the category for which tier "
                "list channels will be created in. Note that the bot will "
                "fully manage the channels in this category and any "
                "channels that are not created by the bot will be "
                "instantly vaporized.",
            )
        }

    async def cog_load(self):
        self.logger.info("TierList plugin loaded")

    @commands.slash_command(name="tierlist")
    async def tier_list(self, ctx: disnake.ApplicationCommandInteraction):
        pass

    @tier_list.sub_command_group()
    async def config(self, ctx: disnake.ApplicationCommandInteraction):
        pass

    @config.sub_command(
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
        self.config_logger.info(
            "User %s (id: %s) set tier list category to %s (id: %s)",
            fmt_user(ctx.user),
            ctx.user.id,
            category.name,
            category.id,
        )
        await ctx.send(f"Setting tier list category to {category.mention}")
        # TODO: Persist to DB

    @config.sub_command()
    async def documentation(self, ctx: disnake.ApplicationCommandInteraction):
        """
        Documentation for config options
        """
        await ctx.send(
            "Documentation for config options",
            embeds=list(self._documentation.values()),
        )

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
        # TODO: actually do it

    # handler for no permission
    @create.error
    async def create_error(self, ctx: disnake.ApplicationCommandInteraction, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(
                "You do not have the required permissions to create a tier list"
            )
        else:
            raise error
