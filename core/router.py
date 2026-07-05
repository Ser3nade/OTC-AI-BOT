"""
OTC AI Dealer
Router
"""


KEYWORDS = [

    "buy",
    "selling",
    "sell",
    "buying",

    "usdt",
    "usdc",

    "rate",
    "price",
    "quote",

    "php",
    "usd",

]


def route_message(message: str):

    text = message.lower()

    for keyword in KEYWORDS:

        if keyword in text:

            return "PRICE"

    return "IGNORE"