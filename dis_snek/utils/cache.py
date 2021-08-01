from collections import OrderedDict
from typing import Any
import time
import attr


@attr.s(slots=True)
class TTLItem:
    value: Any = attr.ib()
    expire: float = attr.ib()

    def is_expired(self, timestamp):
        return timestamp >= self.expire


class TTLCache(OrderedDict):
    def __init__(self, ttl=600, soft_limit=50, hard_limit=250):
        super().__init__()

        self.ttl = ttl
        self.soft_limit = soft_limit
        self.hard_limit = hard_limit

    def __setitem__(self, key, value):
        expire = time.monotonic() + self.ttl
        item = TTLItem(value, expire)
        super().__setitem__(key, item)
        self.move_to_end(key)

        self.expire()

    def __getitem__(self, key):
        item = super().__getitem__(key)
        self._reset_expiration(key, item)
        return item.value

    def pop(self, key, default=attr.NOTHING):
        if key in self:
            item = self[key]
            del self[key]
            return item.value

        if default is attr.NOTHING:
            raise KeyError(key)

        return default

    def get(self, key, default=None):
        item = super().get(key, default)
        if item is not default:
            self._reset_expiration(key, item)
            return item.value

        return default

    def _reset_expiration(self, key: Any, item: TTLItem):
        self.move_to_end(key)
        item.expire = time.monotonic() + self.ttl

    def _first_item(self):
        return next(iter(self.items()))

    def expire(self):
        """Removes expired elements from the cache"""
        if self.soft_limit and len(self) <= self.soft_limit:
            return

        if self.hard_limit:
            while len(self) > self.hard_limit:
                self.popitem(last=False)

        timestamp = time.monotonic()
        while True:
            key, item = self._first_item()
            if item.is_expired(timestamp):
                self.popitem(last=False)
            else:
                break
