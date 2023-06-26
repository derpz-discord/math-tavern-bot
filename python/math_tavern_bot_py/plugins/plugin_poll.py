from typing import Optional

import disnake
from derpz_botlib.bot_classes import LoggedBot
from derpz_botlib.cog import LoggedCog
from disnake.ext import commands


class PollPlugin(LoggedCog):
    def __init__(self, bot: LoggedBot):
        super().__init__(bot)

    @commands.slash_command(name="poll")
    async def poll_command(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @poll_command.sub_command()
    @commands.has_permissions(manage_messages=True)
    async def create(
        self,
        inter: disnake.ApplicationCommandInteraction,
        *,
        question: str = commands.Param(description="Question you want to ask"),
        channel: Optional[disnake.TextChannel] = commands.Param(
            description="Channel to post the poll in. Defaults to the current channel."
        ),
    ):
        if channel is None:
            channel = inter.channel
        msg = await channel.send(
            embed=disnake.Embed(
                title=question, description=f"Poll created by {inter.author.mention}"
            )
        )
        await msg.add_reaction("\N{THUMBS UP SIGN}")
        await msg.add_reaction("\N{THUMBS DOWN SIGN}")



def setup(bot: LoggedBot):
    bot.add_cog(PollPlugin(bot))
