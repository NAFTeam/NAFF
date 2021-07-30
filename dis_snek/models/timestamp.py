from datetime import datetime
from enum import Enum
from typing import Optional


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

    def format(self, style: Optional[TimestampStyles] = None):
        if not style:
            return f"<t:{self.timestamp():.0f}>"
        else:
            return f"<t:{self.timestamp():.0f}:{style}>"
