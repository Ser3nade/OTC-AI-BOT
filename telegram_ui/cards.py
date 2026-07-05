from inquiry.model import Inquiry


def build_inquiry_card(inquiry: Inquiry) -> str:
    """
    Returns the formatted Telegram message
    shown to OTC traders.
    """

    return f"""
🟢 <b>NEW OTC INQUIRY</b>

👤 <b>Client</b>
{inquiry.customer_name}

💱 <b>Trade</b>
{inquiry.action.upper()} {inquiry.amount} {inquiry.asset}

💵 <b>Pair</b>
{inquiry.currency_pair}

📌 <b>Status</b>
🟡 Waiting for dealer

🆔 <code>{inquiry.id}</code>
"""