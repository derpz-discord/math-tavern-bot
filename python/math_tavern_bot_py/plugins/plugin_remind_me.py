"""
Plugin for reminding users of things.

Usage:
    /remindme at <time> <reminder>
    /remindme in <duration> <reminder>
    /remindme list
    /remindme delete <id>

    Reminders are sent to DMs


"""
import datetime
from typing import Optional, Sequence

import dateparser
import disnake
from disnake import ApplicationCommandInteraction
from disnake.ext import commands
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import Mapped

from derpz_botlib.bot_classes import DatabasedBot
from derpz_botlib.cog import DatabasedCog
from derpz_botlib.database.db import (
    SqlAlchemyBase,
    intpk,
    required_bigint,
    required_str,
    tz_aware_timestamp,
)
from derpz_botlib.discord_utils.paginator import Menu
from derpz_botlib.utils import fmt_time, DiscordTimeFormat


class Reminder(SqlAlchemyBase):
    __tablename__ = "user_reminders"

    id: Mapped[intpk]
    user_id: Mapped[required_bigint]
    user_reminder_id: Mapped[required_bigint]
    reminder: Mapped[required_str]
    remind_at: Mapped[tz_aware_timestamp]

    def to_embed(self):
        embed = disnake.Embed(title="Reminder set", color=disnake.Color.green())
        embed.add_field(
            name="Reminder ID",
            value=f"{self.user_reminder_id}",
            inline=False,
        )
        embed.add_field(
            name="Reminder",
            value=self.reminder,
            inline=False,
        )
        embed.add_field(
            name="Time",
            value=fmt_time(self.remind_at, DiscordTimeFormat.long_time),
            inline=False,
        )
        embed.set_footer(
            text=f"Delete with /remindme delete {self.user_reminder_id} | gid: {self.id}"
        )
        return embed


class ReminderManager:
    def __init__(self, engine: AsyncEngine):
        self.engine = engine

    async def create_reminder(
        self, user_id: int, remind_time: datetime.datetime, reminder_text: str
    ):
        last_reminder_id = await self.get_last_user_reminder_id(user_id)
        async with AsyncSession(self.engine, expire_on_commit=False) as session:
            reminder = Reminder(
                user_id=user_id,
                remind_at=remind_time,
                reminder=reminder_text,
                user_reminder_id=last_reminder_id + 1,
            )
            session.add(reminder)
            await session.commit()
            return reminder

    async def get_reminder_by_reminder_id(self, reminder_id: int) -> Optional[Reminder]:
        """Fetches a reminder by the reminder id, which is globally unique"""
        async with AsyncSession(self.engine) as session:
            query_stmt = select(Reminder).where(Reminder.id == reminder_id)
            reminder = await session.execute(query_stmt)
            return reminder.scalar_one_or_none()

    async def get_reminder_by_user_reminder_id(
        self, user_id: int, user_reminder_id: int
    ) -> Optional[Reminder]:
        """Fetches a reminder by the user's reminder id, which is unique per user"""
        async with AsyncSession(self.engine) as session:
            query_stmt = (
                select(Reminder)
                .where(Reminder.user_id == user_id)
                .where(Reminder.user_reminder_id == user_reminder_id)
            )
            reminder = await session.execute(query_stmt)
            return reminder.scalar_one_or_none()

    async def get_reminders(self, user_id: int) -> Sequence[Reminder]:
        async with AsyncSession(self.engine) as session:
            query_stmt = select(Reminder).where(Reminder.user_id == user_id)
            reminders = await session.execute(query_stmt)
            return reminders.scalars().all()

    async def count_reminders(self, user_id: int) -> int:
        async with AsyncSession(self.engine) as session:
            # Theoretically this is inefficient,
            # however who even has that many reminders?
            query_stmt = select(Reminder).where(Reminder.user_id == user_id)
            reminders = await session.execute(query_stmt)
            return len(reminders.scalars().all())

    async def get_last_user_reminder_id(self, user_id: int) -> int:
        async with AsyncSession(self.engine) as session:
            query_stmt = (
                select(Reminder.user_reminder_id)
                .where(Reminder.user_id == user_id)
                .order_by(Reminder.user_reminder_id.desc())
                .limit(1)
            )
            last_reminder_id = await session.execute(query_stmt)
            return last_reminder_id.scalar_one_or_none()

    async def delete_reminder_by_reminder_id(self, reminder_id: int):
        async with AsyncSession(self.engine) as session:
            reminder = await self.get_reminder_by_reminder_id(reminder_id)
            await session.delete(reminder)
            await session.commit()


class ReminderPlugin(DatabasedCog):
    def __init__(self, bot: DatabasedBot):
        super().__init__(bot)

    @commands.slash_command(name="remindme")
    async def cmd_remindme(self, ctx: ApplicationCommandInteraction):
        pass

    @cmd_remindme.sub_command(name="at")
    async def cmd_remindme_at(
        self,
        ctx: ApplicationCommandInteraction,
        time: str = commands.Param(
            description="Time to remind you at. Please include your timezone",
            required=True,
        ),
        reminder: str = commands.Param(description="Reminder message", required=True),
    ):
        # parse time with humantime
        reminder_dt = dateparser.parse(time)
        # add reminder to db
        manager = ReminderManager(self.engine)
        out = await manager.create_reminder(
            user_id=ctx.author.id,
            remind_time=reminder_dt,
            reminder_text=reminder,
        )

        # send confirmation
        await ctx.send(
            embed=out.to_embed(),
        )

    @cmd_remindme.sub_command(name="in")
    async def cmd_remindme_in(
        self,
        ctx: ApplicationCommandInteraction,
        time: str = commands.Param(
            description="Time to remind you in. Please include your timezone",
            required=True,
        ),
        reminder: str = commands.Param(description="Reminder message", required=True),
    ):
        # just farm it out, since dateparser can handle this
        await self.cmd_remindme_at(ctx, time, reminder)

    @cmd_remindme.sub_command(name="list")
    async def cmd_remindme_list(self, ctx: ApplicationCommandInteraction):
        manager = ReminderManager(self.engine)
        reminders = await manager.get_reminders(ctx.author.id)
        if not reminders:
            await ctx.send("You have no reminders!")
            return
        embeds = list(map(lambda x: x.to_embed(), reminders))
        paginator = Menu(embeds)
        await ctx.send(view=paginator)

    @cmd_remindme.sub_command(name="delete")
    async def cmd_remindme_delete(
        self,
        ctx: ApplicationCommandInteraction,
        reminder_id: int = commands.Param(
            description="Reminder ID to delete",
            required=True,
        ),
    ):
        manager = ReminderManager(self.engine)
        reminder = await manager.get_reminder_by_user_reminder_id(
            ctx.author.id, reminder_id
        )
        if not reminder:
            await ctx.send("Reminder not found!")
            return
        await manager.delete_reminder_by_reminder_id(reminder_id)
        await ctx.send("Reminder deleted!")


def setup(bot: DatabasedBot):
    bot.add_cog(ReminderPlugin(bot))
