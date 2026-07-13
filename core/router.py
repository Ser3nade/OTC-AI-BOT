"""
OTC AI Dealer
Router
"""

import re


ASSET_PATTERN = re.compile(r"\b(usdt|usdc)\b", re.IGNORECASE)
FIAT_PATTERN = re.compile(r"\b(php|usd)\b", re.IGNORECASE)
TRADE_PATTERN = re.compile(r"\b(buy|buying|sell|selling)\b", re.IGNORECASE)
QUOTE_PATTERN = re.compile(r"\b(rate|rates|price|quote|quotes)\b", re.IGNORECASE)
REFRESH_PATTERN = re.compile(r"\b(refresh|efresh|update|current|latest)\b", re.IGNORECASE)
QUESTION_PATTERN = re.compile(r"\b(what'?s|whats|what is|how much|hm|magkano)\b", re.IGNORECASE)
QUOTE_ONLY_PATTERN = re.compile(
    r"^(\.*)?\s*(refresh\s+)?(rate|rates|price|quote)(\s+(again|now|please|pls|po|sir|maam|ma'am|today))*\??$",
    re.IGNORECASE,
)
AMOUNT_PATTERN = re.compile(
    r"\b\d[\d,]*(\.\d+)?\s*(k|m|usd|php|usdt|usdc)?\b",
    re.IGNORECASE,
)


def route_message(message: str):
    text = message.strip()

    if not text:
        return "IGNORE"

    if QUOTE_ONLY_PATTERN.search(text):
        return "PRICE"

    has_asset = bool(ASSET_PATTERN.search(text))
    has_fiat = bool(FIAT_PATTERN.search(text))
    has_trade = bool(TRADE_PATTERN.search(text))
    has_quote = bool(QUOTE_PATTERN.search(text))
    has_refresh = bool(REFRESH_PATTERN.search(text))
    has_question = bool(QUESTION_PATTERN.search(text))
    has_amount = bool(AMOUNT_PATTERN.search(text))

    if has_refresh and text.lower().strip(".?! ") in {"refresh", "efresh", "update", "current", "latest"}:
        return "PRICE"

    if has_quote and (has_refresh or has_question):
        return "PRICE"

    if has_refresh and has_quote:
        return "PRICE"

    if has_question and has_asset:
        return "PRICE"

    if has_asset and (has_trade or has_quote or has_amount):
        return "PRICE"

    if has_quote and (has_asset or has_fiat):
        return "PRICE"

    if has_trade and has_fiat and has_amount:
        return "PRICE"

    if text.lower() in {"rate?", "rates?", "price?", "quote?"}:
        return "PRICE"

    return "IGNORE"
