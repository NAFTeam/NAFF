from collections import OrderedDict
from collections.abc import ValuesView
from collections.abc import ItemsView
from typing import Any
from typing import List
from typing import Callable

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
                self.popitem(last=False)

        timestamp = time.monotonic()
        while True:
            key, item = self._first_item()
            if item.is_expired(timestamp):
                self.popitem(last=False)
            else:
                break


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


@attr.define()
class CacheView:  # for global cache
    ids: List = attr.field()
    _method: Callable = attr.field()

    def __await__(self):
        return self.get_dict().__await__()

    async def get_dict(self):
        return {instance_id: instance async for instance_id, instance in self}

    async def get(self, item):
        return await self._method(item)

    def __getitem__(self, item):
        return self.get(item)

    async def __aiter__(self):
        for instance_id in self.ids:
            yield instance_id, await self._method(instance_id)
