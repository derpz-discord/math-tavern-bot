from os import getenv

from dotenv import load_dotenv
from math_tavern_bot_py.bot import TavernBot

if __name__ == "__main__":
    load_dotenv()
    db_url = getenv("DATABASE_URL")
    discord_token = getenv("DISCORD_TOKEN")
    client_id = getenv("OAUTH_CLIENT_ID")
    if not db_url:
        raise ValueError("No DATABASE_URL found in environment variables.")
    if not discord_token:
        raise ValueError("No DISCORD_TOKEN found in environment variables.")
    bot = TavernBot(db_url=db_url, oauth_client_id=client_id)
    bot.run(discord_token)
