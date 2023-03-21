import logging
import pprint
from datetime import timedelta, datetime
from typing import Optional

import disnake
from disnake.ext import commands
from sqlalchemy import text

from math_tavern_bot.library.bot_classes import KvStoredBot


class BotAdminPlugin(commands.Cog):
    """
    Cog for managing the bot configuration
    (also allows for arbitrary SQL execution)
    """

    def __init__(self, bot: KvStoredBot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)

    async def cog_load(self) -> None:
        self.logger.info("BotAdmin plugin loaded")

    @commands.command(name="plugins")
    @commands.is_owner()
    async def plugin_list(self, ctx: commands.Context):
        await ctx.send("Loaded Plugins: " + ", ".join(self.bot.cogs.keys()))

    @commands.slash_command(name="config")
    async def config(self, ctx: disnake.ApplicationCommandInteraction):
        pass

    @config.sub_command()
    async def unload_plugin(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        plugin: str = commands.Param(description="The plugin to unload"),
    ):
        if plugin in self.bot.cogs:
            self.bot.remove_cog(plugin)
            await ctx.send(f"Unloaded plugin {plugin}")
        else:
            await ctx.send(f"Plugin {plugin} not loaded")

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
        async with self.bot.db.connect() as conn:
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

    @commands.slash_command(name="sudo_timeout")
    @commands.is_owner()
    async def sudo_timeout(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        *,
        user: disnake.Member = commands.Param(description="The user to timeout"),
        duration: int = commands.Param(
            description="The duration of the timeout in seconds"
        ),
        reason: Optional[str] = commands.Param(
            description="The reason for the timeout", default="Sudo timeout"
        ),
    ):
        """
        Timeout a user
        """
        human_readable_time = timedelta(seconds=duration)
        await ctx.send(
            f"Timeout {user} for {human_readable_time} seconds", ephemeral=True
        )

        await user.timeout(duration=human_readable_time, reason=reason)

    @commands.slash_command(name="sudo_remove_timeout")
    @commands.is_owner()
    async def sudo_remove_timeout(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        *,
        user: disnake.Member = commands.Param(
            description="The user to remove the timeout from"
        ),
    ):
        """
        Remove a timeout from a user
        """
        expires_at = user.current_timeout
        if expires_at is None:
            await ctx.send(f"{user} is not timed out", ephemeral=True)
            return
        how_much_longer = expires_at - datetime.utcnow()
        await ctx.send(
            f"Remove timeout from {user} (Remains: {how_much_longer})", ephemeral=True
        )
        await user.remove_timeout()

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
