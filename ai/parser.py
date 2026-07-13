"""
OTC AI Dealer
Gemini Parser v3
"""

from enum import Enum
from typing import Optional

from google import genai
from pydantic import BaseModel, Field

from config import GEMINI_API_KEY


client = None


# =====================================================
# ENUMS
# =====================================================

class Intent(str, Enum):
    PRICE_INQUIRY = "price_inquiry"
    OTHER = "other"


class Action(str, Enum):
    BUY = "buy"
    SELL = "sell"
    UNKNOWN = "unknown"


# =====================================================
# AI OUTPUT MODEL
# =====================================================

class ParsedTrade(BaseModel):

    # Intent
    intent: Intent = Intent.OTHER

    # Buy / Sell
    action: Action = Action.UNKNOWN

    # Assets
    asset: str = "UNKNOWN"

    fiat: str = "UNKNOWN"

    currency_pair: str = "UNKNOWN"

    # Trade values
    amount: Optional[float] = None

    mentioned_rate: Optional[float] = None

    # Future conversation memory
    client_name: Optional[str] = None

    reply_context: Optional[str] = None

    # Confidence
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


# =====================================================
# SYSTEM PROMPT
# =====================================================

SYSTEM_PROMPT = """
You are an OTC cryptocurrency trading assistant.

Your ONLY job is to extract structured trading information.

Short vague messages like "rate now?", "rate please?", "rates?", "price?", and "quote please"
are price inquiries even when asset, fiat, action, and amount are not specified.

Never explain.

Never chat.

Never answer the customer.

Return ONLY JSON.

----------------------------------

intent

Allowed values:

price_inquiry
other

----------------------------------

action

Allowed values:

buy
sell
unknown

----------------------------------

asset

Allowed values:

USDT
USDC
UNKNOWN

----------------------------------

fiat

Allowed values:

PHP
USD
UNKNOWN

----------------------------------

currency_pair

Examples:

USDT/PHP
USDC/PHP
USDT/USD
USDC/USD

If unknown:

UNKNOWN

----------------------------------

amount

Numeric only.

If absent:

null

----------------------------------

mentioned_rate

If customer mentions a rate:

58.25

Otherwise:

null

----------------------------------

client_name

If explicitly mentioned.

Otherwise null.

----------------------------------

reply_context

If the customer is replying to or modifying a previous inquiry.

Otherwise null.

----------------------------------

confidence

Between 0 and 1.

----------------------------------

Return ONLY valid JSON.
"""


# =====================================================
# PARSER
# =====================================================

def parse_message(message: str) -> ParsedTrade:
    global client

    if client is None:
        client = genai.Client(api_key=GEMINI_API_KEY)

    response = client.models.generate_content(

        model="gemini-2.5-flash",

        contents=f"""
{SYSTEM_PROMPT}

Customer Message:

{message}
""",

        config={
            "response_mime_type": "application/json",
            "response_schema": ParsedTrade,
        },
    )

    # If Gemini successfully parsed into our schema
    if response.parsed is not None:
        return response.parsed

    # Fallback (extremely rare)
    return ParsedTrade()
