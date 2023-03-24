import datetime

import disnake
from disnake.ext import commands


def numerical_select(iterator: range) -> list[disnake.SelectOption]:
    return list(map(lambda x: disnake.SelectOption(label=x, value=x), iterator))


class MessageAwareView(disnake.ui.View):
    """
    A view that is aware of the message it is attached to.
    """

    message: disnake.Message

    def __init__(self, message: disnake.Message):
        super().__init__()
        self.message = message

    async def on_timeout(self):
        await self.message.edit("This is no longer available", view=None)


class BotAwareView(disnake.ui.View):
    """
    A view that is aware of the bot that is using it.
    """

    bot: commands.Bot

    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot


class MessageAndBotAwareView(MessageAwareView):
    """
    A view that is aware of the message and the bot that is using it.
    """

    bot: commands.Bot

    def __init__(self, message: disnake.Message, bot: commands.Bot):
        super().__init__(message)
        self.bot = bot


def date_display_embed(dt: datetime.datetime) -> disnake.Embed:
    embed = disnake.Embed(
        title="Date Display",
        description=f"{dt.day}/{dt.month}/{dt.year}",
    )
    embed.add_field(name="Day", value=dt.strftime("%A"))
    embed.add_field(name="Month", value=dt.strftime("%B"))
    embed.add_field(name="Year", value=dt.strftime("%Y"))
    return embed


class DatePickerView(MessageAwareView):
    """
    A date picker view
    """

    def __init__(self, message: disnake.Message):
        super().__init__(message)

    @disnake.ui.select(
        options=numerical_select(range(1, 4)),
        placeholder="Day first digit",
        min_values=1,
        max_values=1,
    )
    async def day_first_digit(
        self, select: disnake.ui.Select, interaction: disnake.Interaction
    ):
        await self.message.edit(embed=date_display_embed(datetime.datetime.now()))
        await interaction.response.send_message(
            f"Selected day first digit: {select.values[0]}"
        )

    @disnake.ui.select(
        options=numerical_select(range(1, 10)),
        placeholder="Day second digit",
        min_values=1,
        max_values=1,
    )
    async def day_second_digit(
        self, select: disnake.ui.Select, interaction: disnake.Interaction
    ):
        await interaction.response.send_message(
            f"Selected day second digit: {select.values[0]}"
        )

    @disnake.ui.select(
        options=numerical_select(range(1, 13)),
        placeholder="Month",
        min_values=1,
        max_values=1,
    )
    async def month(self, select: disnake.ui.Select, interaction: disnake.Interaction):
        await interaction.response.send_message(f"Selected month: {select.values[0]}")

    @disnake.ui.select(
        options=numerical_select(range(2021, 2026)),
        placeholder="Year",
        min_values=1,
        max_values=1,
    )
    async def year(self, select: disnake.ui.Select, interaction: disnake.Interaction):
        await interaction.response.send_message(f"Selected year: {select.values[0]}")
