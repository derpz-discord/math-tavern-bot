import logging

import disnake
from disnake.ext import commands

from math_tavern_bot.bot_classes import KvStoredBot
from math_tavern_bot.config.models import CogConfiguration
from math_tavern_bot.utils import fmt_user, check_in_guild


class PinConfig(CogConfiguration):
    who_can_pin: set[int] = set()


class PinMessagePlugin(commands.Cog):
    config: dict[disnake.Guild, PinConfig]

    def __init__(self, bot: KvStoredBot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)

    async def cog_load(self) -> None:
        self.logger.info("PinMessage plugin loaded")
        # load config from DB
        config = await self.bot.cog_config_store.get_cog_config(self)
        if config:
            self.config = dict(
                map(
                    lambda x: (self.bot.get_guild(x[0]), PinConfig.parse_obj(x[1])),
                    config.items(),
                )
            )
        else:
            self.logger.warning("No config found in DB")

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

    @commands.slash_command()
    @commands.has_permissions(manage_roles=True)
    @commands.check(check_in_guild)
    async def add_pin_role(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        *,
        role: disnake.Role = commands.Param(
            description="The role to give pin permissions to"
        ),
    ):
        guild_config = self.config.get(ctx.guild, PinConfig())
        guild_config.who_can_pin.add(role.id)
        self.config[ctx.guild] = guild_config
        await self.bot.cog_config_store.set_cog_config(self, ctx.guild, guild_config)
        await ctx.send(
            f"+ Added {role.name} to the list of roles that can pin messages"
        )

    # TODO: Change to slash command
    @commands.slash_command()
    @commands.has_permissions(manage_roles=True)
    @commands.check(check_in_guild)
    async def remove_pin_role(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        *,
        role: disnake.Role = commands.Param(
            description="The role to remove pin permissions from"
        ),
    ):
        guild_config = self.config.get(ctx.guild, PinConfig())
        if role.id not in guild_config.who_can_pin:
            await ctx.send("That role cannot pin messages")
            return
        guild_config.who_can_pin.remove(role.id)
        self.config[ctx.guild] = guild_config
        await self.bot.cog_config_store.set_cog_config(self, ctx.guild, guild_config)
        await ctx.send(
            f"- Removed {role.name} from the list of roles that can pin messages"
        )

    @commands.command("pinroles")
    @commands.check(check_in_guild)
    async def list_pin_roles(self, ctx: commands.Context):
        guild_config = self.config.get(ctx.guild, PinConfig())
        pin_roles = list(
            map(
                lambda role_id: ctx.guild.get_role(role_id),
                guild_config.who_can_pin,
            )
        )
        await ctx.send(
            embed=disnake.Embed(
                title="Roles that can pin messages",
                description="\n".join(f"- {role.name}" for role in pin_roles),
            )
        )

    @commands.command("pin")
    @commands.check(check_in_guild)
    async def pin_message(self, ctx: commands.Context):
        guild_config = self.config.get(ctx.guild, PinConfig())
        if not (
            any(role in ctx.author.roles for role in guild_config.who_can_pin)
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

    @commands.command("unpin")
    @commands.check(check_in_guild)
    async def unpin_message(self, ctx: commands.Context):
        guild_config = self.config.get(ctx.guild, PinConfig())
        if not (
            any(role in ctx.author.roles for role in guild_config.who_can_pin)
            or ctx.author.guild_permissions.manage_messages
        ):
            await ctx.send("You do not have permission to unpin messages")
            return
        # check what message the user is replying to and unpin that
        if ctx.message.reference:
            to_unpin = ctx.message.reference.resolved
            await to_unpin.unpin(
                reason=f"Unpinned on behalf of {fmt_user(ctx.author)} (id: "
                f"{ctx.author.id})"
            )
            # react to the message with a checkmark
            await ctx.message.add_reaction("\N{WHITE HEAVY CHECK MARK}")
        else:
            await ctx.message.add_reaction("\N{CROSS MARK}")
