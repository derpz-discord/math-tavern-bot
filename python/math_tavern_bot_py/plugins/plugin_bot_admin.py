import logging
import pprint
from datetime import datetime, timedelta
from typing import Optional

import disnake
from derpz_botlib.bot_classes import ConfigurableCogsBot
from disnake.ext import commands
from sqlalchemy import text


def setup(bot: ConfigurableCogsBot):
    bot.add_cog(BotAdminPlugin(bot))


class BotAdminPlugin(commands.Cog):
    """
    Cog for managing the bot configuration
    (also allows for arbitrary SQL execution)
    """

    def __init__(self, bot: ConfigurableCogsBot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)

    async def cog_load(self) -> None:
        self.logger.info("BotAdmin plugin loaded")

    @commands.slash_command(name="config")
    async def config(self, ctx: disnake.ApplicationCommandInteraction):
        pass

    @commands.command(aliases=["sqlexec"])
    @commands.is_owner()
    async def sql_exec(self, ctx: commands.Context):
        """
        Execute arbitrary SQL
        """
        await ctx.send("Please send the SQL query in the next message")
        msg = await self.bot.wait_for(
            "message",
            check=lambda m: m.author == ctx.author and m.channel == ctx.channel,
            timeout=20,
        )
        if not msg:
            await ctx.send("Timed out waiting for SQL query")
            return
        # check if the message begins with ```sql and ends with ```
        if not msg.content.startswith("```sql") or not msg.content.endswith("```"):
            await ctx.send("SQL query must be wrapped in ```sql and ```")
            return

        # remove the ```sql and ``` from the message
        query = msg.content[6:-3]
        # strip the query of any whitespace
        query = query.strip()

        # execute with the database connection
        orig = await ctx.send(f"Executing SQL query, please wait.")
        async with self.bot.engine.connect() as conn:
            try:
                result = await conn.execute(text(query))
                result = result.fetchall()
            except Exception as e:
                await orig.edit(
                    f"There was an error executing your query. "
                    f"I have DMed you the error"
                )
                await ctx.author.send(pprint.pformat(e))
                raise e
            await orig.edit(f"Result: \n```\n{pprint.pformat(result)}\n```")

    @commands.command(name="sendraw")
    @commands.is_owner()
    async def send_raw_message(self, ctx: commands.Context, *, message: str):
        """
        Send a raw message
        """
        await ctx.send(message)

    @commands.command(name="eval")
    @commands.is_owner()
    async def eval_code(self, ctx: commands.Context):
        """
        Execute arbitrary Python code
        """
        await ctx.send("Please send the Python code in the next message")
        msg = await self.bot.wait_for(
            "message",
            check=lambda m: m.author == ctx.author and m.channel == ctx.channel,
            timeout=120,
        )
        if not msg:
            await ctx.send("Timed out waiting for Python code")
            return
        # check if the message begins with ```python and ends with ```
        if not msg.content.startswith("```python") or not msg.content.endswith("```"):
            await ctx.send("Python code must be wrapped in ```python and ```")
            return

        # remove the ```python and ``` from the message
        code = msg.content[9:-3]
        orig = await ctx.send(f"Executing Python code")
        try:
            result = exec(code)
        except Exception as e:
            await orig.edit(
                f"There was an error executing your code. " f"I have DMed you the error"
            )
            await ctx.author.send(pprint.pformat(e))

            raise e
        await orig.edit(f"Result: \n```\n{result}\n```")
