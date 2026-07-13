from inquiry.model import (
    Inquiry,
    TelegramInfo,
    CustomerInfo,
    TradeInfo,
)

from inquiry.repository import repository


def create_inquiry(
    customer_name,
    customer_id,
    customer_group,
    chat_id,
    message_id,
    chat_username,
    original_message,
    parsed,
):

    inquiry = Inquiry(

        inquiry_id=repository.next_id(),

        telegram=TelegramInfo(
            chat_id=chat_id,
            message_id=message_id,
            group_name=customer_group,
            source_message_id=message_id,
            chat_username=chat_username,
        ),

        customer=CustomerInfo(
            telegram_name=customer_name,
            telegram_id=customer_id,
            resolved_name=parsed.client_name,
        ),

        trade=TradeInfo(
            action=parsed.action.value,
            asset=parsed.asset,
            fiat=parsed.fiat,
            currency_pair=parsed.currency_pair,
            amount=parsed.amount,
            mentioned_rate=parsed.mentioned_rate,
        ),

        original_message=original_message,

        confidence=parsed.confidence,
    )

    repository.save(inquiry)

    return inquiry
