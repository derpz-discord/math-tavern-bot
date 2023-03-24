import disnake
from derpz_botlib.bot_classes import ConfigurableCogsBot
from derpz_botlib.cog import DatabaseConfigurableCog
from derpz_botlib.database.storage import CogConfiguration
from derpz_botlib.utils import fmt_user_include_id
from disnake import AllowedMentions, ApplicationCommandInteraction
from disnake.ext import commands


class ModerationPluginConfig(CogConfiguration):
    psuedo_muted_users: set[int] = set()


class ModerationPlugin(DatabaseConfigurableCog[ModerationPluginConfig]):
    """
    Cog for performing moderation tasks with the bot

    TODO:
    - Finer grained permissions
    """

    def __init__(self, bot: ConfigurableCogsBot):
        super().__init__(bot, ModerationPluginConfig)

    async def cog_after_slash_command_invoke(
        self, inter: ApplicationCommandInteraction
    ) -> None:
        """Logs the invocation of a slash command."""
        self.logger.info(
            f"Command {inter.application_command.name} invoked by "
            f"{fmt_user_include_id(inter.author)} with options {inter.filled_options}",
        )

    @commands.slash_command()
    async def moderation(self, ctx: ApplicationCommandInteraction):
        pass

    @moderation.sub_command()
    @commands.guild_only()
    async def get_role_position(
        self, ctx: ApplicationCommandInteraction, *, role: disnake.Role
    ):
        """
        Gets the position of a role
        """
        await ctx.send(
            f"Position of {role.mention} is {role.position}",
            allowed_mentions=AllowedMentions.none(),
        )

    @moderation.sub_command()
    @commands.guild_only()
    async def list_roles_and_positions(self, ctx: ApplicationCommandInteraction):
        """
        Lists all roles and their positions
        """
        await ctx.send(
            "\n".join(
                map(
                    lambda r: f"- {r.mention} | pos: {r.position}",
                    sorted(ctx.guild.roles, key=lambda r: r.position, reverse=True),
                )
            ),
            allowed_mentions=AllowedMentions.none(),
        )

    @moderation.sub_command()
    @commands.has_permissions(manage_roles=True)
    @commands.is_owner()
    @commands.guild_only()
    async def move_role(
        self,
        ctx: ApplicationCommandInteraction,
        *,
        role: disnake.Role,
        delta: int = commands.Param(
            description="The delta to move the role by", default=1
        ),
    ):
        """
        Adjusts the position of a role by a given delta
        """
        await role.edit(
            position=role.position + delta,
            reason=f"Requested by {fmt_user_include_id(ctx.author)}",
        )
        await ctx.send(
            f"Moved {role.mention} by {delta} positions",
            allowed_mentions=AllowedMentions.none(),
        )

    @moderation.sub_command()
    @commands.has_permissions(manage_roles=True)
    @commands.is_owner()
    @commands.guild_only()
    async def set_role_position(
        self, ctx: ApplicationCommandInteraction, *, role: disnake.Role, position: int
    ):
        """
        Sets the position of a role
        """
        await role.edit(
            position=position, reason=f"Requested by {fmt_user_include_id(ctx.author)}"
        )
        await ctx.send(
            f"Set position of {role.mention} to {position}",
            allowed_mentions=AllowedMentions.none(),
        )

    @moderation.sub_command()
    @commands.has_permissions(manage_roles=True)
    @commands.is_owner()
    @commands.guild_only()
    async def remove_role(
        self,
        ctx: ApplicationCommandInteraction,
        *,
        user: disnake.Member,
        role: disnake.Role,
    ):
        """
        Removes a role from a user
        """
        await user.remove_roles(
            role, reason=f"Requested by " f"{fmt_user_include_id(ctx.author)}"
        )
        await ctx.send(
            f"Removed {role.mention} from {user.mention}",
            allowed_mentions=AllowedMentions.none(),
        )

    @moderation.sub_command()
    @commands.has_permissions(manage_roles=True)
    @commands.is_owner()
    @commands.guild_only()
    async def add_role(
        self,
        ctx: ApplicationCommandInteraction,
        *,
        user: disnake.Member,
        role: disnake.Role,
    ):
        """
        Adds a role to a user
        """
        await user.add_roles(
            role, reason=f"Requested by {fmt_user_include_id(ctx.author)}"
        )
        await ctx.send(
            f"Added {role.mention} to {user.mention}",
            allowed_mentions=AllowedMentions.none(),
        )


def setup(bot: ConfigurableCogsBot):
    bot.add_cog(ModerationPlugin(bot))
