"""
Provides functionality for managing tier lists.
We call a tier list a discord channel where users can rate
the difficulty of exercises in textbooks.

For a demonstration, visit the Math Tavern: https://discord.gg/EK5p2KUTxR
"""
import logging
from collections import deque
from typing import Optional

import disnake
from derpz_botlib.bot_classes import ConfigurableCogsBot
from derpz_botlib.cog import DatabaseConfigurableCog
from derpz_botlib.database.storage import CogConfiguration
from derpz_botlib.utils import fmt_guild_include_id, fmt_user
from disnake.ext import commands
from pydantic import BaseModel


class TierListChannelDetails(BaseModel):
    name: str = "Untitled"
    owners: list[int]

    def generate_bot_pin_embed(self) -> disnake.Embed:
        embed = disnake.Embed(title=f"Tier List: {self.name}")
        embed.add_field(
            name="Owners",
            value="\n".join(
                map(
                    lambda j: f"- <@!{j}>",
                    self.owners,
                )
            ),
        )
        return embed


class TierListPluginConfiguration(CogConfiguration):
    tier_list_category: Optional[int] = None
    tier_lists: dict[int, TierListChannelDetails] = {}


def setup(bot: ConfigurableCogsBot):
    bot.add_cog(TierListPlugin(bot))


class TierListPlugin(DatabaseConfigurableCog[TierListPluginConfiguration]):
    def __init__(self, bot: ConfigurableCogsBot):
        super().__init__(bot, TierListPluginConfiguration)
        self._not_owner_perms = disnake.PermissionOverwrite(
            send_messages=False,
            create_public_threads=False,
            create_private_threads=False,
            read_message_history=True,
        )
        self._owner_perms = disnake.PermissionOverwrite(
            send_messages=True,
            create_public_threads=True,
            create_private_threads=True,
            manage_messages=True,
        )

    @commands.slash_command(name="tierlist")
    async def tier_list(self, ctx: disnake.ApplicationCommandInteraction):
        pass

    @tier_list.sub_command_group(name="config")
    async def cmd_config(self, ctx: disnake.ApplicationCommandInteraction):
        pass

    @tier_list.sub_command_group(name="maintenance")
    async def cmd_maintenance(self, ctx: disnake.ApplicationCommandInteraction):
        pass

    @cmd_maintenance.sub_command(description="Re-syncs all tier lists")
    async def resync_all(self, ctx: disnake.ApplicationCommandInteraction):
        guild_config = self.get_guild_config(ctx.guild)
        tier_list_category = ctx.guild.get_channel(guild_config.tier_list_category)
        if tier_list_category is None:
            await ctx.send("Tier list category not set")
            return
        for channel in tier_list_category.text_channels:
            # fetch the details for this channel
            details = guild_config.tier_lists.get(channel.id)
            if details is None:
                await ctx.send(f"Channel {channel.mention} is not a tier list channel")
                continue
            await self._resync_tier_list(channel, details)
        await ctx.send("Done")

    async def _resync_tier_list(
        self, channel: disnake.TextChannel, details: TierListChannelDetails
    ):
        """
        Fixes up permissions and the topic for a tier list channel
        """

        # fix up the topic
        topic = channel.topic
        if topic is None or not topic.startswith("Tier list for "):
            await channel.edit(topic=f"Tier list for {channel.name}")

        # fix up the permissions
        await channel.set_permissions(overwrite=None)
        new_overwrites = {channel.guild.default_role: self._not_owner_perms}
        for owner_id in details.owners:
            owner = channel.guild.get_member(owner_id)
            if owner is None:
                self.logger.warning(
                    "Owner %s not found in guild %s",
                    owner_id,
                    fmt_guild_include_id(channel.guild),
                )
                continue
            new_overwrites[owner] = self._owner_perms

        await channel.edit(overwrites=new_overwrites)

    @cmd_config.sub_command(description="Dumps the config")
    async def dump_config(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.send(embed=self.get_guild_config(ctx.guild).to_embed())

    @cmd_config.sub_command(
        description="Configures the category where tier list channels will be created"
    )
    async def tier_list_category(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        *,
        category: disnake.CategoryChannel = commands.Param(
            description="Category to create tier list channels in"
        ),
    ):
        await ctx.send(f"Setting tier list category to {category.mention}")
        guild_config = self.get_guild_config(ctx.guild)
        guild_config.tier_list_category = category.id
        await self.save_guild_config(ctx.guild, guild_config)

    @tier_list.sub_command(description="Requests a tier list")
    async def request(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        *,
        name: str = commands.Param(description="Name of the tier list"),
    ):
        await ctx.send(f"Requesting the tier list: {name}")
        # TODO: Implement

    @tier_list.sub_command(description="Creates a new tier list")
    @commands.has_permissions(manage_channels=True)
    @commands.guild_only()
    async def create(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        *,
        name: str = commands.Param(description="Name of the tier list"),
        user: disnake.Member = commands.Param(
            description="User who will own the tier list"
        ),
    ):
        channel_name = name.strip().replace(" ", "-")
        await ctx.send(f"Creating the tier list: #{channel_name}")
        guild_config = self.get_guild_config(ctx.guild)
        if guild_config.tier_list_category is None:
            raise commands.BadArgument(
                "You must first configure the tier list category"
            )
        category = ctx.guild.get_channel(guild_config.tier_list_category)
        if category is None:
            raise commands.ChannelNotFound("Tier list category not found")
        channel = await ctx.guild.create_text_channel(
            name=channel_name,
            category=category,
            topic=f"Tier list for {name}",
            overwrites={
                ctx.guild.default_role: self._not_owner_perms,
                user: self._owner_perms,
            },
        )
        await channel.send(f"Tier list created for {user.mention}")
        guild_config.tier_lists[channel.id] = TierListChannelDetails(
            name=name, owners=[user.id]
        )
        await self.save_guild_config(ctx.guild, guild_config)

    @tier_list.sub_command(description="Lists all the tier lists")
    @commands.guild_only()
    async def list(self, ctx: disnake.ApplicationCommandInteraction):
        guild_config = self.get_guild_config(ctx.guild)
        tier_list_channels = list(
            filter(
                lambda c: c is not None,
                map(lambda c: ctx.guild.get_channel(c), guild_config.tier_lists.keys()),
            )
        )
        if len(tier_list_channels) == 0:
            await ctx.send("No tier lists found")
            return
        # TODO: Nicer embed
        embed = disnake.Embed(
            title="Tier lists",
            description="\n".join(
                map(lambda c: f"{c.mention} - {c.topic}", tier_list_channels)
            ),
        )
        await ctx.send(embed=embed)

    @tier_list.sub_command(description="Fetches information about a tier list")
    @commands.guild_only()
    async def info(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        *,
        channel: disnake.TextChannel = commands.Param(
            description="Channel to get information about"
        ),
    ):
        guild_config = self.get_guild_config(ctx.guild)
        details = guild_config.tier_lists.get(channel.id)
        if details is None:
            raise commands.BadArgument("Channel is not a tier list")

        await ctx.send(embed=details.generate_bot_pin_embed())

    @tier_list.sub_command(description="Sets up an existing channel as a tier list")
    @commands.has_permissions(manage_channels=True)
    @commands.guild_only()
    async def setup(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        *,
        channel: disnake.TextChannel = commands.Param(description="Channel to setup"),
        owner: disnake.Member = commands.Param(
            description="User who will own the tier list"
        ),
    ):
        guild_config = self.get_guild_config(ctx.guild)
        # We intentionally do not care if the tier list category is none.
        if guild_config.tier_lists.get(channel.id) is not None:
            raise commands.BadArgument("Channel is already a tier list")
        await ctx.send(f"Setting up the tier list: {channel.mention}")
        guild_config.tier_lists[channel.id] = TierListChannelDetails(
            name=channel.name, owners=[owner.id]
        )
        await self.save_guild_config(ctx.guild, guild_config)
        await channel.edit(
            topic=f"Tier list for {channel.name}",
            overwrites={
                ctx.guild.default_role: self._not_owner_perms,
                owner: self._owner_perms,
            },
        )

    @tier_list.sub_command(description="Adds an owner to a tier list")
    @commands.has_permissions(manage_channels=True)
    @commands.guild_only()
    async def add_owner(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        *,
        channel: disnake.TextChannel = commands.Param(
            description="Channel to add an owner to"
        ),
        owner: disnake.Member = commands.Param(
            description="User who will own the tier list"
        ),
    ):
        guild_config = self.get_guild_config(ctx.guild)
        tier_list = guild_config.tier_lists.get(channel.id)
        if tier_list is None:
            raise commands.BadArgument("Channel is not a tier list")
        if owner.id in tier_list.owners:
            raise commands.BadArgument("User is already an owner")
        await ctx.send(
            f"Adding {owner.mention} as an owner of {channel.mention}",
            allowed_mentions=disnake.AllowedMentions.none(),
        )
        tier_list.owners.append(owner.id)
        await self.save_guild_config(ctx.guild, guild_config)
        await channel.set_permissions(
            owner,
            overwrite=self._owner_perms,
            reason=f"Tier list owner added by {fmt_user(ctx.user)}",
        )

    @tier_list.sub_command(description="Removes an owner from a tier list")
    @commands.has_permissions(manage_channels=True)
    @commands.guild_only()
    async def remove_owner(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        *,
        channel: disnake.TextChannel = commands.Param(
            description="Channel to remove an owner from"
        ),
        owner: disnake.Member = commands.Param(
            description="User who will no longer own the tier list"
        ),
    ):
        guild_config = self.get_guild_config(ctx.guild)
        tier_list = guild_config.tier_lists.get(channel.id)
        if tier_list is None:
            raise commands.BadArgument("Channel is not a tier list")
        if owner.id not in tier_list.owners:
            raise commands.BadArgument("User is not an owner")
        await ctx.send(
            f"Removing {owner.mention} as an owner of {channel.mention}",
            allowed_mentions=disnake.AllowedMentions.none(),
        )
        tier_list.owners.remove(owner.id)
        await self.save_guild_config(ctx.guild, guild_config)
        await channel.set_permissions(
            owner,
            overwrite=None,
            reason=f"Tier list owner removed by {fmt_user(ctx.user)}",
        )

    @tier_list.sub_command(description="Deletes a tier list")
    @commands.has_permissions(manage_channels=True)
    @commands.guild_only()
    async def delete(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        *,
        channel: disnake.TextChannel = commands.Param(description="Channel to delete"),
    ):
        # TODO: Check if it is a tier list channel we manage
        await ctx.send(f"Deleting the tier list: {channel.mention}")
        guild_config = self.get_guild_config(ctx.guild)
        guild_config.tier_lists.pop(channel.id, None)
        await self.save_guild_config(ctx.guild, guild_config)

        await channel.delete(
            reason=f"Tier list delete requested by {fmt_user(ctx.user)}"
        )
