import os
import re

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv():
        return False


load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
PRICE_SHEET_ID = os.getenv("PRICE_SHEET_ID")
PRICE_WORKSHEET_NAME = os.getenv("PRICE_WORKSHEET_NAME", "Prices")
TRADER_GROUP_CHAT_ID = os.getenv("TRADER_GROUP_CHAT_ID")
TRADER_USER_IDS = os.getenv("TRADER_USER_IDS", "")
TRADE_LOG_SHEET_ID = os.getenv("TRADE_LOG_SHEET_ID")
TRADE_LOG_WORKSHEET_NAME = os.getenv("TRADE_LOG_WORKSHEET_NAME")
TRADE_LOG_WORKSHEET_TEMPLATE = os.getenv("TRADE_LOG_WORKSHEET_TEMPLATE", "%Y-%m")


REQUIRED_SETTINGS = {
    "BOT_TOKEN": BOT_TOKEN,
    "GEMINI_API_KEY": GEMINI_API_KEY,
    "GOOGLE_SERVICE_ACCOUNT_FILE": GOOGLE_SERVICE_ACCOUNT_FILE,
    "PRICE_SHEET_ID": PRICE_SHEET_ID,
    "TRADER_GROUP_CHAT_ID": TRADER_GROUP_CHAT_ID,
}


class ConfigError(RuntimeError):
    pass


def get_trader_user_ids():
    trader_ids = set()

    for raw_value in str(TRADER_USER_IDS or "").split(","):
        value = raw_value.strip()

        if not value:
            continue

        if re.fullmatch(r"\d+", value):
            trader_ids.add(int(value))

    return trader_ids


def validate_required_settings():
    missing = [
        name
        for name, value in REQUIRED_SETTINGS.items()
        if not value
    ]

    if missing:
        formatted = ", ".join(missing)
        raise ConfigError(f"Missing required environment variables: {formatted}")

    if not re.fullmatch(r"\d+:[A-Za-z0-9_-]{30,}", BOT_TOKEN):
        raise ConfigError(
            "BOT_TOKEN is not a valid Telegram bot token. "
            "Get the full token from BotFather; it should look like 123456789:ABC..."
        )

    if not re.fullmatch(r"-?\d+", TRADER_GROUP_CHAT_ID):
        raise ConfigError(
            "TRADER_GROUP_CHAT_ID must be a Telegram chat ID number, "
            "for example -1001234567890."
        )
