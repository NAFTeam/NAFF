from datetime import datetime
from typing import Union

from dis_snek.models.timestamp import Timestamp


def timestamp_converter(value: Union[datetime, int, float, str]) -> Timestamp:
    if isinstance(value, str):
        return Timestamp.fromisoformat(value)
    elif isinstance(value, (float, int)):
        return Timestamp.fromtimestamp(float(value))
    elif isinstance(value, datetime):
        return Timestamp.fromdatetime(value)
    raise TypeError("Timestamp must be one of: datetime, int, float, ISO8601 str")


def list_converter(converter):
    def convert_action(value):
        return [
            converter(element) if not hasattr(element, "to_dict") else converter(**element.to_dict())
            for element in value
        ]

    return convert_action
