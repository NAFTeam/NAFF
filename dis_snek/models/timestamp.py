from datetime import datetime
from enum import Enum


class TimestampStyles(str, Enum):
    ShortTime = "t"
    LongTime = "T"
    ShortDate = "d"
    LongDate = "D"
    ShortDateTime = "f"  # default
    LongDateTime = "F"
    RelativeTime = "R"


class Timestamp(datetime):
    @classmethod
    def from_datetime(cls, dt: datetime):
        return cls.utcfromtimestamp(dt.timestamp())

    def format(self, style=None):
        if not style:
            return f"<t:{self.timestamp():.0f}>"
        else:
            return f"<t:{self.timestamp():.0f}:{style}>"
