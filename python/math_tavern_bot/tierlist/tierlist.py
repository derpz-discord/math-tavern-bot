"""
Provides functionality for managing tier lists.
We call a tier list a discord channel where users can rate
the difficulty of exercises in textbooks.

For a demonstration, visit the Math Tavern: https://discord.gg/EK5p2KUTxR
"""
import logging

import disnake
from disnake.ext import commands


class TierListPlugin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        self.logger.info("TierList plugin loaded")

    @commands.slash_command(name="tierlist")
    async def tier_list(self, ctx: disnake.ApplicationCommandInteraction):
        pass
