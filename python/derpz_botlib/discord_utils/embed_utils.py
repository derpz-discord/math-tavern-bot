import disnake


def listing_embed(
    things_to_list: list[str], title: str, description: str = ""
) -> disnake.Embed:
    """
    Creates an embed with a list of things in it
    """
    embed = disnake.Embed(title=title, description=description)
    embed.add_field(
        name="Things", value="\n".join(map(lambda t: f"- {t}", things_to_list))
    )
    return embed
