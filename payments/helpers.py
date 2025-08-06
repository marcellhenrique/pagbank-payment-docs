import datetime

import pytz


def convert_timestamp_ms_to_datetime(timestamp_ms: int) -> datetime.datetime:
    timestamp_s = timestamp_ms / 1000.0
    return datetime.datetime.fromtimestamp(timestamp_s, tz=pytz.UTC)
