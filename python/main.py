from dotenv import load_dotenv
from os import getenv

from math_tavern_bot.bot import BookBot

if __name__ == "__main__":
    load_dotenv()
    bot = BookBot()
    if getenv("DISCORD_TOKEN"):
        bot.run(getenv("DISCORD_TOKEN"))
    else:
        bot.logger.error("No DISCORD_TOKEN found in environment variables.")
        exit(1)
