from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Optional, Union

if TYPE_CHECKING:
    from dis_snek.models.snowflake import Snowflake_Type


DISCORD_EPOCH = 1420070400000


class TimestampStyles(str, Enum):
    ShortTime = "t"
    LongTime = "T"
    ShortDate = "d"
    LongDate = "D"
    ShortDateTime = "f"  # default
    LongDateTime = "F"
    RelativeTime = "R"


class Timestamp(datetime):
    """A special class that represents Discord timestamps.

    Assumes that all naive datetimes are based on local timezone.
    """

    @classmethod
    def fromdatetime(cls, dt: datetime) -> "Timestamp":
        timestamp = cls.fromtimestamp(dt.timestamp(), tz=dt.tzinfo)

        if timestamp.tzinfo is None:  # assume naive datetimes are based on local timezone
            return timestamp.astimezone()
        return timestamp

    @classmethod
    def utcfromtimestamp(cls, t: float) -> "Timestamp":
        """Construct a timezone-aware UTC datetime from a POSIX timestamp."""
        return super().utcfromtimestamp(t).replace(tzinfo=timezone.utc)

    @classmethod
    def fromisoformat(cls, date_string: str) -> "Timestamp":
        timestamp = super().fromisoformat(date_string)

        if timestamp.tzinfo is None:  # assume naive datetimes are based on local timezone
            return timestamp.astimezone()
        return timestamp

    @classmethod
    def fromisocalendar(cls, year: int, week: int, day: int) -> "Timestamp":
        return super().fromisocalendar(year, week, day).astimezone()

    @classmethod
    def fromtimestamp(cls, t: float, tz=None) -> "Timestamp":
        timestamp = super().fromtimestamp(t, tz=tz)

        if timestamp.tzinfo is None:  # assume naive datetimes are based on local timezone
            return timestamp.astimezone()
        return timestamp

    @classmethod
    def fromordinal(cls, n: int) -> "Timestamp":
        return super().fromordinal(n).astimezone()

    def to_snowflake(self, high: bool = False) -> Union[str, int]:
        """Returns a numeric snowflake pretending to be created at the given date.

        When using as the lower end of a range, use ``tosnowflake(high=False) - 1``
        to be inclusive, ``high=True`` to be exclusive.
        When using as the higher end of a range, use ``tosnowflake(high=True) + 1``
        to be inclusive, ``high=False`` to be exclusive
        """

        discord_millis = int(self.timestamp() * 1000 - DISCORD_EPOCH)
        return (discord_millis << 22) + (2 ** 22 - 1 if high else 0)

    @classmethod
    def from_snowflake(cls, snowflake: "Snowflake_Type") -> "Timestamp":
        if isinstance(snowflake, str):
            snowflake = int(snowflake)

        timestamp = ((snowflake >> 22) + DISCORD_EPOCH) / 1000
        return cls.utcfromtimestamp(timestamp)

    def format(self, style: Optional[Union[TimestampStyles, str]] = None) -> str:
        if not style:
            return f"<t:{self.timestamp():.0f}>"
        else:
            return f"<t:{self.timestamp():.0f}:{style}>"

    def __str__(self):
        return self.format()
