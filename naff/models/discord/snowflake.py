from typing import Union, List, SupportsInt, Optional


import naff.models as models
from naff.client.const import MISSING, Absent

__all__ = ("to_snowflake", "to_optional_snowflake", "to_snowflake_list", "SnowflakeObject", "Snowflake_Type")

from naff.client.mixins.nattrs import Field, Nattrs

# Snowflake_Type should be used in FUNCTION args of user-facing APIs (combined with to_snowflake to sanitize input)
# For MODEL id fields, just use int as type-hinting instead;
# For attr convertors: Use int() when API-facing conversion is expected,
# use to_snowflake when user should create this object
Snowflake_Type = Union[int, str, "SnowflakeObject", SupportsInt]


def to_snowflake(snowflake: Snowflake_Type) -> int:
    """
    Helper function to convert something into correct Discord snowflake int, gives more helpful errors Use internally to sanitize user input or in user- facing APIs (a must).

    For Discord-API - facing code, just int() is sufficient

    """
    try:
        snowflake = int(snowflake)
    except TypeError as e:
        raise TypeError(
            f"ID (snowflake) should be instance of int, str, SnowflakeObject, or support __int__. "
            f"Got '{snowflake}' ({type(snowflake)}) instead."
        ) from e
    except ValueError as e:
        raise ValueError(f"ID (snowflake) should represent int. Got '{snowflake}' ({type(snowflake)}) instead.") from e

    return snowflake


def to_optional_snowflake(snowflake: Absent[Optional[Snowflake_Type]] = MISSING) -> Optional[int]:
    if snowflake is MISSING or snowflake is None:
        return snowflake
    return to_snowflake(snowflake)


def to_snowflake_list(snowflakes: List[Snowflake_Type]) -> List[int]:
    return [to_snowflake(c) for c in snowflakes]


class SnowflakeObject(Nattrs):
    id: int = Field(converter=to_snowflake, repr=True)
    """Unique snowflake ID"""

    def __eq__(self, other: "SnowflakeObject") -> bool:
        if hasattr(other, "id"):
            other = other.id
        return self.id == other

    def __ne__(self, other: "SnowflakeObject") -> bool:
        return self.id != other.id

    def __hash__(self) -> int:
        return self.id << 32

    def __int__(self) -> int:
        return self.id

    @property
    def created_at(self) -> "models.Timestamp":
        """
        Returns a timestamp representing the date-time this discord object was created.

        :Returns:

        """
        return models.Timestamp.from_snowflake(self.id)
