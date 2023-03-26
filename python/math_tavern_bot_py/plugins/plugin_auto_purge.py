"""
Plugin that configures channels to automatically purge all messages
(except pinned ones) on a regular basis.

"""
from collections import deque

import disnake
from derpz_botlib.bot_classes import ConfigurableCogsBot
from derpz_botlib.cog import DatabaseConfigurableCog
from derpz_botlib.database.storage import CogConfiguration
from derpz_botlib.utils import (DiscordTimeFormat,
                                fmt_guild_channel_include_id,
                                fmt_guild_include_id, fmt_time)
from disnake import ApplicationCommandInteraction
from disnake.ext import commands, tasks
from disnake.ext.tasks import Loop


class AutoPurgeConfig(CogConfiguration):
    channel_purge_interval: dict[int, int] = {}


class AutoPurgePlugin(DatabaseConfigurableCog[AutoPurgeConfig]):
    def __init__(self, bot: ConfigurableCogsBot):
        super().__init__(bot, AutoPurgeConfig)
        self._loops: dict[int, Loop] = {}

    async def cog_load(self):
        """
        Adds all the auto purge tasks to the event loop
        """
        await super().cog_load()
        # iterate over config and register all channels

        for guild, config in self.config.items():
            cleanup_list = []
            for channel_id, interval in config.channel_purge_interval.items():
                channel = guild.get_channel(channel_id)
                if channel is None:
                    self.logger.error(
                        "Channel %s not found in guild %s", channel_id, guild.id
                    )
                    # remove it from the config
                    cleanup_list.append(channel_id)
                    continue
                self.register_channel_for_auto_purge(channel, interval)
            # remove any invalid channels from the config
            for ch in cleanup_list:
                del config.channel_purge_interval[ch]
            self.logger.info(
                "Cleaning up %s invalid channels in %s",
                len(cleanup_list),
                fmt_guild_include_id(guild),
            )
            await self.save_guild_config(guild, config)

    def cog_unload(self):
        """
        Cancels all the auto purge tasks
        """
        super().cog_unload()
        deque(map(self.unregister_channel_for_auto_purge, self._loops.keys()))

    @commands.Cog.listener(name="on_guild_channel_delete")
    async def on_channel_delete(self, channel: disnake.abc.GuildChannel):
        """
        If a channel is deleted, we remove it from the auto purge list
        """
        self.logger.info(
            "Channel %s deleted, removing from auto purge list",
            fmt_guild_channel_include_id(channel),
        )
        self.unregister_channel_for_auto_purge(channel.id)
        # we go ahead and remove it from the config
        guild_config = self.get_guild_config(channel.guild)
        if channel.id in guild_config.channel_purge_interval:
            del guild_config.channel_purge_interval[channel.id]
            await self.save_guild_config(channel.guild, guild_config)

    @commands.slash_command(name="autopurge")
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    async def cmd_auto_purge(self, ctx: ApplicationCommandInteraction):
        pass

    @commands.command()
    @commands.guild_only()
    async def channel_info(self, ctx: commands.GuildContext):
        """
        Retrieves information about the auto-purge status of the channel
        """
        guild_config = self.get_guild_config(ctx.guild)

        if ctx.channel.id in guild_config.channel_purge_interval:
            loop = self._loops.get(ctx.channel.id)
            if loop is None:
                # TODO: Handle
                await ctx.send("Error occured, contact dev")
                return
            next_run = loop.next_iteration
            if next_run is not None:
                next_run = fmt_time(next_run, DiscordTimeFormat.relative)
            else:
                next_run = "idk"
            await ctx.send(
                f"This channel is set to purge messages every "
                f"{guild_config.channel_purge_interval[ctx.channel.id]} seconds."
                f"This will occur at {next_run}",
                mention_author=True,
            )
        else:
            await ctx.send("This channel is not set to purge messages at intervals.")

    @cmd_auto_purge.sub_command(description="Adds a channel to the auto purge list")
    async def add_channel(
        self,
        ctx: ApplicationCommandInteraction,
        channel: disnake.TextChannel,
        interval: int = commands.Param(
            description="Interval to purge messages at in seconds", gt=5
        ),
    ):
        guild_config = self.get_guild_config(ctx.guild)
        guild_config.channel_purge_interval[channel.id] = interval
        await self.save_guild_config(ctx.guild, guild_config)
        await ctx.send(
            f"Added {channel.mention} to the list of channels to "
            f"purge messages at {interval} seconds."
        )
        self.register_channel_for_auto_purge(channel, interval)

    @cmd_auto_purge.sub_command(description="Removes a channel from auto purge")
    async def remove_channel(
        self,
        ctx: ApplicationCommandInteraction,
        channel: disnake.TextChannel,
    ):
        guild_config = self.get_guild_config(ctx.guild)
        if channel.id not in guild_config.channel_purge_interval:
            await ctx.send(
                f"{channel.mention} is not in the list of channels to "
                f"purge messages at intervals."
            )
            return
        del guild_config.channel_purge_interval[channel.id]
        await self.save_guild_config(ctx.guild, guild_config)
        self.unregister_channel_for_auto_purge(channel.id)
        await channel.edit(topic=None, reason="Auto purge interval removed")
        await ctx.send(
            f"Removed {channel.mention} from the list of channels to purge messages "
            f"at intervals."
        )

    @cmd_auto_purge.sub_command(
        description="Modifies the interval at which a channel is purged."
    )
    async def modify_interval(
        self,
        ctx: ApplicationCommandInteraction,
        channel: disnake.TextChannel,
        interval: int = commands.Param(
            description="Interval to purge messages at in seconds", gt=5
        ),
    ):
        guild_config = self.get_guild_config(ctx.guild)
        if channel.id not in guild_config.channel_purge_interval:
            await ctx.send(
                f"{channel.mention} is not in the list of channels to "
                f"purge messages at intervals."
            )
            return
        guild_config.channel_purge_interval[channel.id] = interval
        await self.save_guild_config(ctx.guild, guild_config)
        self.edit_purge_interval(channel, interval)
        # TODO: What if someone changes the topic after this?
        await channel.edit(
            topic=f"Auto purge interval: {interval} seconds",
            reason="Auto purge interval set",
        )
        await ctx.send(
            f"Modified the interval at which {channel.mention} is purged to "
            f"{interval} seconds."
        )

    @cmd_auto_purge.sub_command(
        description="Gets the list of channels that have auto-purge enabled."
    )
    async def get_channels(self, ctx: ApplicationCommandInteraction):
        guild_config = self.get_guild_config(ctx.guild)
        channel_lookup = {channel.id: channel for channel in ctx.guild.channels}
        await ctx.send(
            "Channels to purge messages at intervals:\n"
            + "\n".join(
                f"- {channel_lookup[channel].mention} - every {interval} seconds"
                for channel, interval in guild_config.channel_purge_interval.items()
            )
        )

    def register_channel_for_auto_purge(
        self, channel: disnake.TextChannel, interval: int
    ):
        loop = tasks.loop(seconds=interval)(self.purge_channel)
        loop.start(channel)
        self._loops[channel.id] = loop

    def edit_purge_interval(self, channel: disnake.TextChannel, interval: int):
        loop = self._loops.get(channel.id)
        if loop is None:
            raise ValueError("Channel is not registered for auto purge")
        loop.change_interval(seconds=interval)
        self._loops[channel.id] = loop

    def unregister_channel_for_auto_purge(self, channel_id: int):
        loop = self._loops.pop(channel_id)
        if loop:
            loop.cancel()

    @staticmethod
    async def purge_channel(channel: disnake.TextChannel, include_pinned: bool = False):
        """
        Purges all messages in a channel except pinned ones.
        """
        await channel.send("\N{WARNING SIGN} Auto purge is purging messages...")

        def purgeable_msg(m: disnake.Message):
            if not include_pinned:
                return not m.pinned
            return True

        await channel.purge(
            limit=None,
            check=purgeable_msg,
        )


def setup(bot: ConfigurableCogsBot):
    bot.add_cog(AutoPurgePlugin(bot))
