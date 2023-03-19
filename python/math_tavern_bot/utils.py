import disnake


def fmt_user(user: disnake.User) -> str:
    return f"{user.name}#{user.discriminator}"
