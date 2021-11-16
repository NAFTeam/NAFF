from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Optional, Union, List


class BaseTrigger(ABC):
    last_call_time: datetime

    def __new__(cls, *args, **kwargs):
        new_cls = super().__new__(cls)
        new_cls.last_call_time = datetime.now()
        return new_cls

    @abstractmethod
    def next_fire(self) -> Optional[datetime]:
        """
        Return the next datetime to fire on.

        If no datetime can be determined, return None
        Returns:
            Datetime if one can be determined
        """
        ...


class IntervalTrigger(BaseTrigger):
    """Trigger the task every set interval"""

    _t = Union[int, float]

    def __init__(self, seconds: _t = 0, minutes: _t = 0, hours: _t = 0, days: _t = 0, weeks: _t = 0):
        self.delta = timedelta(days=days, seconds=seconds, minutes=minutes, hours=hours, weeks=weeks)

        # lazy check for negatives
        if (datetime.now() + self.delta) < datetime.now():
            raise ValueError("Interval values must result in a time in the future!")

    def next_fire(self) -> Optional[datetime]:
        return self.last_call_time + self.delta


class DateTrigger(BaseTrigger):
    """Trigger the task once, when the specified datetime is reached"""

    def __init__(self, target_datetime: datetime):
        self.target = target_datetime

    def next_fire(self) -> Optional[datetime]:
        if datetime.now() < self.target:
            return self.target
        return None


class TimeTrigger(BaseTrigger):
    """Trigger the task every day, at a specified (24 hour clock) time"""

    def __init__(self, hour: int = 0, minute: int = 0, seconds: Union[int, float] = 0, utc: bool = True):
        self.target_time = (hour, minute, seconds)
        self.tz = timezone.utc if utc else None

    def next_fire(self) -> Optional[datetime]:
        now = datetime.now()
        target = datetime(
            now.year, now.month, now.day, self.target_time[0], self.target_time[1], self.target_time[2], tzinfo=self.tz
        )
        if target.tzinfo == timezone.utc:
            target = target.astimezone(now.tzinfo)
            target = target.replace(tzinfo=None)

        if target <= self.last_call_time:
            target += timedelta(days=1)

        return target


class OrTrigger(BaseTrigger):
    """Trigger a task when any sub-trigger is fulfilled"""

    def __init__(self, *trigger: BaseTrigger):
        self.triggers: List[BaseTrigger] = list(trigger)

    def _get_delta(self, d: BaseTrigger):
        if not d.next_fire():
            return float("inf")
        return abs(d.next_fire() - self.last_call_time)

    def next_fire(self) -> Optional[datetime]:
        if len(self.triggers) == 1:
            return self.triggers[0].next_fire()
        trigger = min(self.triggers, key=self._get_delta)
        return trigger.next_fire()
