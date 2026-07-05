from inquiry.model import Inquiry, InquiryStatus


def build_inquiry_card(inquiry: Inquiry) -> str:

    amount = (
        f"{inquiry.trade.amount:g}"
        if inquiry.trade.amount is not None
        else "Not specified"
    )

    status_icon = {
        InquiryStatus.NEW: "🟢",
        InquiryStatus.CLAIMED: "🟡",
        InquiryStatus.QUOTE_READY: "🟣",
        InquiryStatus.QUOTE_SENT: "🔵",
        InquiryStatus.LOCKED: "🔒",
        InquiryStatus.LOGGED: "📝",
        InquiryStatus.COMPLETED: "✅",
        InquiryStatus.CANCELLED: "❌",
    }.get(inquiry.status, "⚪")

    claimed_by = (
        inquiry.ownership.claimed_by_name
        if inquiry.ownership.claimed_by_name
        else "Nobody"
    )

    return f"""
{status_icon} <b>OTC INQUIRY</b>

👤 <b>Client</b>
{inquiry.customer.telegram_name}

💱 <b>Trade</b>
{inquiry.trade.action.upper()} {amount} {inquiry.trade.asset}

💵 <b>Pair</b>
{inquiry.trade.currency_pair}

📌 <b>Status</b>
{inquiry.status.value}

🙋 <b>Claimed By</b>
{claimed_by}

🎯 <b>Confidence</b>
{inquiry.confidence:.0%}

🆔 <code>{inquiry.inquiry_id}</code>
"""