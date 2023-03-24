from os import getenv

from dotenv import load_dotenv
from math_tavern_bot_py.bot import BookBot

if __name__ == "__main__":
    load_dotenv()
    db_url = getenv("DATABASE_URL")
    discord_token = getenv("DISCORD_TOKEN")
    if not db_url:
        raise ValueError("No DATABASE_URL found in environment variables.")
    if not discord_token:
        raise ValueError("No DISCORD_TOKEN found in environment variables.")
    bot = BookBot(db_url=db_url)
    bot.run(discord_token)
