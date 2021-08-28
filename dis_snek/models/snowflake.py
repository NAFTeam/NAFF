from contextlib import suppress
from typing import Union

import attr

from dis_snek.models.timestamp import Timestamp

Snowflake_Type = Union[str, int]


def to_snowflake(snowflake: Snowflake_Type) -> int:
    if not isinstance(snowflake, (int, str)):
        raise TypeError("ID (snowflake) should be instance of int or str!")

    with suppress(ValueError):
        snowflake = int(snowflake)

    if 22 > snowflake.bit_length() > 64:
        raise ValueError("ID (snowflake) is not in correct discord format!")

    return snowflake

