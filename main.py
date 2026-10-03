from app.bot import bot
from app.config import DISCORD_TOKEN


def run():
    if not DISCORD_TOKEN:
        raise SystemExit("DISCORD_TOKEN not found. Check that your .env file is in this folder.")
    bot.run(DISCORD_TOKEN)


if __name__ == "__main__":
    run()
