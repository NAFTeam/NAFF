from datetime import datetime
from typing import Union

from dis_snek.models.timestamp import Timestamp


def timestamp_converter(value: Union[datetime, int, float]) -> Timestamp:
    if isinstance(value, (float, int)):
        return Timestamp.fromtimestamp(float(value))
    elif isinstance(value, datetime):
        return Timestamp.fromdatetime(value)
    raise TypeError("Timestamp must be one of: datetime, int, float")
