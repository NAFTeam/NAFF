import time
from collections import OrderedDict
from collections.abc import ItemsView, ValuesView
from typing import Any

import attr


@attr.s(slots=True)
class TTLItem:
    value: Any = attr.ib()
    expire: float = attr.ib()

    def is_expired(self, timestamp):
        return timestamp >= self.expire


class TTLCache(OrderedDict):
    def __init__(self, ttl=600, soft_limit=50, hard_limit=250, on_expire=None):
        super().__init__()

        self.ttl = ttl
        self.hard_limit = hard_limit
        self.soft_limit = min(soft_limit, hard_limit)
        self.on_expire = on_expire

    def __setitem__(self, key, value):
        expire = time.monotonic() + self.ttl
        item = TTLItem(value, expire)
        super().__setitem__(key, item)
        self.move_to_end(key)

        self.expire()

    def __getitem__(self, key):
        # Will not (should not) reset expiration!
        item = super().__getitem__(key)
        # self._reset_expiration(key, item)
        return item.value

    def pop(self, key, default=attr.NOTHING):
        if key in self:
            item = self[key]
            del self[key]
            return item.value

        if default is attr.NOTHING:
            raise KeyError(key)

        return default

    def get(self, key, default=None, reset_expiration=True):
        item = super().get(key, default)
        if item is not default:
            if reset_expiration:
                self._reset_expiration(key, item)
            return item.value

        return default

    def values(self):
        return _CacheValuesView(self)

    def items(self):
        return _CacheItemsView(self)

    def _reset_expiration(self, key: Any, item: TTLItem):
        self.move_to_end(key)
        item.expire = time.monotonic() + self.ttl

    def _first_item(self):
        return next(super().items().__iter__())

    def expire(self):
        """Removes expired elements from the cache"""
        if self.soft_limit and len(self) <= self.soft_limit:
            return

        if self.hard_limit:
            while len(self) > self.hard_limit:
                self._expire_first()

        timestamp = time.monotonic()
        while True:
            key, item = self._first_item()
            if item.is_expired(timestamp):
                self._expire_first()
            else:
                break

    def _expire_first(self):
        key, value = self.popitem(last=False)
        if self.on_expire:
            self.on_expire(key, value)


class _CacheValuesView(ValuesView):
    def __contains__(self, value):
        for key in self._mapping:
            v = self._mapping.get(key, reset_expiration=False)
            if v is value or v == value:
                return True
        return False

    def __iter__(self):
        for key in self._mapping:
            yield self._mapping.get(key, reset_expiration=False)

    def __reversed__(self):
        for key in reversed(self._mapping):
            yield self._mapping.get(key, reset_expiration=False)


class _CacheItemsView(ItemsView):
    def __contains__(self, item):
        key, value = item
        v = self._mapping.get(key, default=attr.NOTHING, reset_expiration=False)
        if v is attr.NOTHING:
            return False
        else:
            return v is value or v == value

    def __iter__(self):
        for key in self._mapping:
            yield key, self._mapping.get(key, reset_expiration=False)

    def __reversed__(self):
        for key in reversed(self._mapping):
            yield key, self._mapping.get(key, reset_expiration=False)
