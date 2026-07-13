from datetime import datetime, timedelta, timezone


PH_TZ = timezone(timedelta(hours=8))


def select_trade_log_worksheet_name(
    value: datetime,
    fixed_name=None,
    template="%Y-%m",
):
    if fixed_name:
        return str(fixed_name).strip()

    if value is None:
        value = datetime.utcnow()

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)

    ph_time = value.astimezone(PH_TZ)
    return ph_time.strftime(template or "%Y-%m")
