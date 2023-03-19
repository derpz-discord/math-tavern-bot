import logging

import disnake
from disnake.ext import commands


class ConfigPlugin(commands.Cog):
    """
    Cog for managing the bot configuration
    (also allows for arbitrary SQL execution)
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)

        self.logger.info("Config plugin loaded")

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

    @commands.command()
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
        await ctx.send(f"Executing SQL query")

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
        await ctx.send(f"Executing Python code")
        result = eval(code)
        await ctx.send(f"Result: \n```\n{result}\n```")
