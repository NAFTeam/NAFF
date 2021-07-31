from datetime import datetime
from datetime import timezone
from enum import Enum
from typing import Optional, Union

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
    """A special class that represents Discord timestamps."""

    @classmethod
    def fromdatetime(cls, dt: datetime):
        timestamp = cls.fromtimestamp(dt.timestamp(), tz=dt.tzinfo)

        if timestamp.tzinfo is None:  # assume naive datetimes are based on local timezone
            return timestamp.astimezone()
        return timestamp

    @classmethod
    def utcfromtimestamp(cls, t: float):
        """Construct a timezone-aware UTC datetime from a POSIX timestamp."""
        return super().utcfromtimestamp(t).replace(tzinfo=timezone.utc)

    @classmethod
    def fromsnowflake(cls, snowflake: Union[str, int]):
        if isinstance(snowflake, str):
            snowflake = int(snowflake)

        timestamp = ((snowflake >> 22) + DISCORD_EPOCH) / 1000
        return cls.utcfromtimestamp(timestamp)

    @classmethod
    def fromisoformat(cls, date_string: str):
        timestamp = super().fromisoformat(date_string)

        if timestamp.tzinfo is None:  # assume naive datetimes are based on local timezone
            return timestamp.astimezone()
        return timestamp

    @classmethod
    def fromisocalendar(cls, year: int, week: int, day: int):
        return super().fromisocalendar(year, week, day).astimezone()

    @classmethod
    def fromtimestamp(cls, t: float, tz=None):  # TODO: typehint this
        timestamp = super().fromtimestamp(t, tz=tz)

        if timestamp.tzinfo is None:  # assume naive datetimes are based on local timezone
            return timestamp.astimezone()
        return timestamp

    @classmethod
    def fromordinal(cls, n: int):
        return super().fromordinal(n).astimezone()

    def tosnowflake(self, high: bool = False) -> Union[str, int]:
        """Returns a numeric snowflake pretending to be created at the given date.

        When using as the lower end of a range, use ``tosnowflake(high=False) - 1``
        to be inclusive, ``high=True`` to be exclusive.
        When using as the higher end of a range, use ``tosnowflake(high=True) + 1``
        to be inclusive, ``high=False`` to be exclusive"""

        discord_millis = int(self.timestamp() * 1000 - DISCORD_EPOCH)
        return (discord_millis << 22) + (2 ** 22 - 1 if high else 0)

    def format(self, style: Optional[TimestampStyles] = None):
        if not style:
            return f"<t:{self.timestamp():.0f}>"
        else:
            return f"<t:{self.timestamp():.0f}:{style}>"
