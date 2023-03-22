import disnake.ui


class PaginatedView(disnake.ui.View):
    """
    A view that allows pagination of embeds
    """


def paginate_embeds(
    embeds: list[disnake.Embed], embeds_per_page: int = 1
) -> PaginatedView:
    # TODO
    pass
