"""
Plugin that allows users with a certain role to pin and unpin messages.

TODO:
- Do not allow people to unpin messages they did not pin
- Add maximum number of pins per user per channel (configurable)

"""
import disnake
from derpz_botlib.bot_classes import ConfigurableCogsBot
from derpz_botlib.cog import CogConfiguration, DatabaseConfigurableCog
from derpz_botlib.utils import check_in_guild, fmt_user
from disnake.ext import commands


class PinConfig(CogConfiguration):
    roles_that_can_pin: set[int] = set()


def setup(bot: ConfigurableCogsBot):
    bot.add_cog(PinMessagePlugin(bot))


class PinMessagePlugin(DatabaseConfigurableCog[PinConfig]):
    def __init__(self, bot: ConfigurableCogsBot):
        super().__init__(bot, PinConfig)

    @commands.slash_command()
    async def pin_config(self, ctx: disnake.ApplicationCommandInteraction):
        pass

    @pin_config.sub_command(description="Adds a role which can pin messages")
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
        """Add a role which can pin messages"""
        guild_config = self.get_guild_config(ctx.guild)
        guild_config.roles_that_can_pin.add(role.id)
        self.config[ctx.guild] = guild_config
        await self.bot.cog_config_store.set_cog_config(self, ctx.guild, guild_config)
        await ctx.send(
            f"+ Added {role.name} to the list of roles that can pin messages"
        )

    @pin_config.sub_command(
        description="Removes role from list of roles which can pin messages"
    )
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
        if role.id not in guild_config.roles_that_can_pin:
            await ctx.send("That role cannot pin messages")
            return
        guild_config.roles_that_can_pin.remove(role.id)
        self.config[ctx.guild] = guild_config
        await self.bot.cog_config_store.set_cog_config(self, ctx.guild, guild_config)
        await ctx.send(
            f"- Removed {role.name} from the list of roles that can pin messages"
        )

    @commands.command("pinroles")
    @commands.check(check_in_guild)
    async def list_pin_roles(self, ctx: commands.Context):
        """
        List the roles that can pin messages.
        Note that by default, users with the Manage Messages permission can pin.
        (Of course, they could already do this from the discord UI)
        """
        guild_config = self.config.get(ctx.guild, PinConfig())
        pin_roles = list(
            map(
                lambda role_id: ctx.guild.get_role(role_id),
                guild_config.roles_that_can_pin,
            )
        )
        await ctx.send(
            embed=disnake.Embed(
                title="Roles that can pin messages",
                description="\n".join(f"- {role.mention}" for role in pin_roles),
            ),
            allowed_mentions=disnake.AllowedMentions.none(),
        )

    @commands.command("pin")
    @commands.check(check_in_guild)
    async def pin_message(self, ctx: commands.Context):
        """
        Pins the message you are replying to.
        """
        guild_config = self.config.get(ctx.guild, PinConfig())
        if not (
            any(role in ctx.author.roles for role in guild_config.roles_that_can_pin)
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
        """
        Unpins the message you are replying to.
        """
        guild_config = self.config.get(ctx.guild, PinConfig())
        if not (
            any(role in ctx.author.roles for role in guild_config.roles_that_can_pin)
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
