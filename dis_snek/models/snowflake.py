from contextlib import suppress
from typing import Union, List, Optional

from dis_snek.const import MISSING
from dis_snek.models.timestamp import Timestamp
from dis_snek.utils.attr_utils import define, field

Snowflake_Type = Union[str, int]


def to_snowflake(snowflake: Union[Snowflake_Type, "SnowflakeObject"]) -> int:
    if isinstance(snowflake, SnowflakeObject):
        snowflake = snowflake.id

    if not isinstance(snowflake, (int, str)):
        raise TypeError(
            f"ID (snowflake) should be instance of int, str or SnowflakeObject. Got '{snowflake}' ({type(snowflake)}) "
            f"instead."
        )

    with suppress(ValueError):
        snowflake = int(snowflake)

    if 22 > snowflake.bit_length() > 64:
        raise ValueError("ID (snowflake) is not in correct discord format!")

    return snowflake


def to_optional_snowflake(snowflake: Optional[Union[Snowflake_Type, "SnowflakeObject"]] = MISSING) -> Optional[int]:
    if snowflake is MISSING:
        return MISSING
    if snowflake is None:
        return None
    return to_snowflake(snowflake)


def to_snowflake_list(snowflakes: List[Union[Snowflake_Type, "SnowflakeObject"]]) -> List[int]:
    return [to_snowflake(c) for c in snowflakes]


@define()
class SnowflakeObject:
    id: "Snowflake_Type" = field(repr=True, converter=to_snowflake)

    def __eq__(self, other):
        return self.id == other.id

    def __ne__(self, other):
        return self.id != other.id

    def __hash__(self):
        return int(self.id) << 32

    @property
    def created_at(self) -> "Timestamp":
        """
        Returns a timestamp representing the date-time this discord object was created
        :return:
        """
        return Timestamp.from_snowflake(self.id)
