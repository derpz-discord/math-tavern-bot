import logging

import disnake
from disnake.ext import commands

from math_tavern_bot import KvStoredBot
from math_tavern_bot.config.models import CogConfiguration
from math_tavern_bot.utils import fmt_user


class PinConfig(CogConfiguration):
    who_can_pin: set[int] = set()


class PinMessagePlugin(commands.Cog):
    def __init__(self, bot: KvStoredBot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        self.config: PinConfig = PinConfig()

    async def cog_load(self) -> None:
        self.logger.info("PinMessage plugin loaded")
        # load config from DB
        config = await self.bot.cog_config_store.get_cog_config(self)
        if config:
            self.config = PinConfig.parse_obj(config)
        else:
            await self.bot.cog_config_store.set_cog_config(self, self.config)

    async def cog_command_error(self, ctx: commands.Context, error: Exception):
        if isinstance(error, commands.CommandInvokeError):
            error = error.original
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You do not have permission to use this command")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Missing required argument")
        else:
            await ctx.send("An error occurred")
            raise error

    # TODO: Change to slash command
    @commands.command("add_pin_role")
    @commands.has_permissions(manage_roles=True)
    async def add_pin_role(
        self,
        ctx: commands.Context,
        *,
        role: disnake.Role = commands.Param(description="The role to add"),
    ):
        if not ctx.guild:
            await ctx.send("This command can only be used in a guild")
            return
        self.config.who_can_pin.add(role.id)
        await self.bot.cog_config_store.set_cog_config(self, self.config)
        await ctx.send(
            f"+ Added {role.name} to the list of roles that can pin messages"
        )

    # TODO: Change to slash command
    @commands.command("remove_pin_role")
    @commands.has_permissions(manage_roles=True)
    async def remove_pin_role(
        self,
        ctx: commands.Context,
        *,
        role: disnake.Role = commands.Param(description="The role to remove"),
    ):
        if not ctx.guild:
            await ctx.send("This command can only be used in a guild")
            return
        if role.id not in self.config.who_can_pin:
            await ctx.send("That role cannot pin messages")
            return
        self.config.who_can_pin.remove(role.id)
        await self.bot.cog_config_store.set_cog_config(self, self.config)
        await ctx.send(
            f"- Removed {role.name} from the list of roles that can pin messages"
        )

    @commands.command("pin")
    async def pin_message(self, ctx: commands.Context):
        if not ctx.guild:
            await ctx.send("This command can only be used in a guild")
            return
        if not (
            any(role in ctx.author.roles for role in self.config.who_can_pin)
            or ctx.author.guild_permissions.manage_messages
        ):
            await ctx.send("You do not have permission to pin messages")
            return
        # check what message the user is replying to and pin that
        if ctx.message.reference:
            to_pin = ctx.message.reference.resolved
            await to_pin.pin(
                reason=f"Pinned on behalf of {fmt_user(ctx.author)} (id: "
                f"{ctx.author.id})"
            )
            # react to the message with a checkmark
            await ctx.message.add_reaction("\N{WHITE HEAVY CHECK MARK}")
        else:
            await ctx.message.add_reaction("\N{CROSS MARK}")
