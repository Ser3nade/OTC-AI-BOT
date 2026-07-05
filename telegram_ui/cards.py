from inquiry.model import Inquiry, InquiryStatus


def render_inquiry_card(inquiry: Inquiry) -> str:

    trade = inquiry.trade
    customer = inquiry.customer
    owner = inquiry.ownership

    lines = []

    lines.append("━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"🆔 {inquiry.inquiry_id}")
    lines.append("")

    # Status
    status_icons = {
        InquiryStatus.NEW: "🟢",
        InquiryStatus.CLAIMED: "🟡",
        InquiryStatus.QUOTE_SENT: "🔵",
        InquiryStatus.LOCKED: "🟣",
        InquiryStatus.LOGGED: "⚫",
        InquiryStatus.COMPLETED: "✅",
        InquiryStatus.CANCELLED: "❌",
    }

    icon = status_icons.get(inquiry.status, "⚪")

    lines.append(f"{icon} Status")
    lines.append(inquiry.status.value)
    lines.append("")

    # Customer
    lines.append("👤 Customer")
    lines.append(customer.telegram_name)
    lines.append("")

    # Trade
    lines.append("💱 Trade")

    direction = (
        "BUY"
        if trade.action.upper() == "BUY"
        else "SELL"
    )

    amount = (
        f"{trade.amount:,.2f}"
        if trade.amount is not None
        else "Unknown"
    )

    lines.append(
        f"{direction} {amount} {trade.asset}"
    )

    lines.append(trade.currency_pair)

    if trade.mentioned_rate:
        lines.append(
            f"Requested Rate: {trade.mentioned_rate}"
        )

    lines.append("")

    # Owner
    if owner.claimed_by_name:

        lines.append("👨‍💼 Claimed By")
        lines.append(owner.claimed_by_name)

    else:

        lines.append("👨‍💼 Claimed By")
        lines.append("Nobody")

    lines.append("")

    # Quote Preview
    if trade.quoted_rate:

        lines.append("━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("📨 Quote Preview")
        lines.append("")
        lines.append(
            f"Buying {amount} {trade.asset}"
        )
        lines.append(
            f"Rate: {trade.quoted_rate}"
        )
        lines.append("")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━")

    return "\n".join(lines)