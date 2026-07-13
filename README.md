# OTC AI Bot

Telegram bot for triaging OTC crypto price inquiries. It detects likely buy/sell messages, asks Gemini to extract structured trade details, creates an inquiry card, and lets traders claim or cancel the inquiry.

## Current Scope

- Validates required configuration at startup.
- Uses structured logging instead of raw prints.
- Routes only likely OTC price inquiries.
- Handles Gemini and Telegram send failures cleanly.
- Reads quote rates from a configured Google Sheet.
- Keeps inquiries in memory for now.
- Supports the inquiry lifecycle: claim, quote ready, send quote, edit, lock trade, complete, and no deal with reason.
- Sends inquiry cards only to the internal trader group.
- Sends client-facing quote and trade-lock confirmation messages back to the original Telegram thread.
- Suppresses duplicate active inquiries from the same user in the same chat.
- Collapses completed and cancelled cards to reduce trader-group noise.

## Setup

1. Create a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env`.
4. Fill in:

```text
BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
GOOGLE_SERVICE_ACCOUNT_FILE=service_account.json
PRICE_SHEET_ID=YOUR_GOOGLE_SHEET_ID
PRICE_WORKSHEET_NAME=Prices
TRADER_GROUP_CHAT_ID=-1001234567890
TRADER_USER_IDS=123456789,987654321
TRADE_LOG_SHEET_ID=YOUR_TRADE_LOG_SHEET_ID
TRADE_LOG_WORKSHEET_TEMPLATE=%Y-%m
```

5. Place the Google service account JSON file at the path configured by `GOOGLE_SERVICE_ACCOUNT_FILE`.
6. Share the Google Sheet with the service account email.
7. If you do not know the trader group ID yet, temporarily set `TRADER_GROUP_CHAT_ID=0`.
8. Run the bot, add it to your internal trader group, and type `/chatid` in that group.
9. Copy the returned number into `TRADER_GROUP_CHAT_ID`.
10. Ask each trader to type `/whoami`, then add their user IDs to `TRADER_USER_IDS`.
11. Restart the bot.

`TRADER_USER_IDS` prevents trader replies in client groups from being detected as new client inquiries.

## Price Sheet Format

The pricing engine accepts flexible column names.

Pair columns can be named:

- `currency_pair`
- `pair`
- `symbol`
- `market`

Or split columns can be named:

- `asset`, `token`, `coin`, or `stablecoin`
- `fiat`, `currency`, or `quote`

Rate columns for client buys can be named:

- `client_buy_rate`
- `buy_rate`
- `ask`
- `ask_rate`
- `sell`
- `sell_rate`
- `offer`
- `offer_rate`

Rate columns for client sells can be named:

- `client_sell_rate`
- `sell_rate`
- `bid`
- `bid_rate`
- `buy`
- `buy_rate`

## Run

```bash
python main.py
```

## Trade Log Sheet

When `Lock Trade` succeeds, the bot can append the locked deal to a separate Google Sheet.

Add this to `.env`:

```text
TRADE_LOG_SHEET_ID=YOUR_TRADE_LOG_SHEET_ID
TRADE_LOG_WORKSHEET_TEMPLATE=%Y-%m
```

Default behavior:

- The spreadsheet is controlled by `TRADE_LOG_SHEET_ID`.
- The bot logs into a monthly worksheet tab like `2026-07`, based on PH time.
- If that month tab does not exist, the bot creates it and writes headers.
- If your company uses a brand-new spreadsheet file every month, update only `TRADE_LOG_SHEET_ID` at the start of the month.
- If you want one fixed worksheet tab instead, set `TRADE_LOG_WORKSHEET_NAME=Sheet1`.

Share the trade log Google Sheet with the same service account email used for the price sheet.

## Known Gaps

- Inquiries are not persisted after restart.
- Trade logging files are placeholders.
- There are no automated tests yet.

## Edit Format

After pressing `Edit`, send a message like:

```text
amount=122000 rate=61.42 pair=USDT/PHP sell
```

Supported fields:

- `amount`
- `rate`
- `pair`
- `buy` or `sell`

## Trade Lock Confirmation

`Lock Trade` sends a confirmation to the original chat in this format:

```text
1.

Rate is 61.4200 USDT/PHP. You sold a total of 122,000.00 USDT for 7,493,240.00 PHP
```
