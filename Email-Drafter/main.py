import logging
import sys

from config import get_env
from discord_bot import create_bot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)


def main():
    try:
        token = get_env("DISCORD_BOT_TOKEN")
        get_env("DISCORD_CHANNEL_ID")
        get_env("OPENAI_API_KEY")
        get_env("GMAIL_ADDRESS")
        get_env("GMAIL_APP_PASSWORD")
    except EnvironmentError as exc:
        log.error(str(exc))
        sys.exit(1)

    bot = create_bot()
    log.info("Starting bot...")
    bot.run(token, log_handler=None)


if __name__ == "__main__":
    main()
