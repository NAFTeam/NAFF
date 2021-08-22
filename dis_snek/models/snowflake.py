from contextlib import suppress
from typing import Union

import attr

from dis_snek.models.timestamp import Timestamp

Snowflake_Type = Union[str, int]


@attr.s(cmp=False, hash=False, slots=True)
class Snowflake:
    """A base object for anything with a snowflake
    Holds several methods that are likely to be used by them"""

    id: Snowflake_Type = attr.ib()

    def __eq__(self, other):
        if hasattr(other, "id"):
            return self.id == other.id
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return int(self.id) << 32

    @property
    def created_at(self) -> Timestamp:
        """
        Returns a timestamp representing the date-time this discord object was created
        :return:
        """
        return Timestamp.fromsnowflake(self.id)


def to_snowflake(snowflake: Snowflake_Type) -> int:
    if not isinstance(snowflake, (int, str)):
        raise TypeError("ID (snowflake) should be instance of int or str!")

    with suppress(ValueError):
        snowflake = int(snowflake)

    if 22 > snowflake.bit_length() > 64:
        raise ValueError("ID (snowflake) is not in correct discord format!")

    return snowflake
