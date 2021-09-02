import time
from collections import OrderedDict
from collections.abc import ItemsView, ValuesView
from inspect import isawaitable, iscoroutinefunction
from operator import getitem
from typing import TYPE_CHECKING, Any, Callable, List, Union, Awaitable, Coroutine

import attr
from dis_snek.models.snowflake import to_snowflake
from dis_snek.utils.attr_utils import copy_converter

if TYPE_CHECKING:
    from dis_snek.models.snowflake import Snowflake_Type


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


@attr.define()
class CacheView:  # for global cache
    ids: Union[Awaitable, Callable[..., Coroutine[Any, Any, Any]], List["Snowflake_Type"]] = attr.field(
        converter=copy_converter
    )
    _method: Callable = attr.field(repr=False)

    async def get_dict(self):
        return {instance.id: instance async for instance in self}

    async def get_list(self):
        return [instance async for instance in self]

    def get(self, item):
        item = to_snowflake(item)
        return CacheProxy(id=item, method=self._method)

    def __await__(self):
        return self.get_list().__await__()

    def __getitem__(self, item):
        return self.get(item)

    async def __aiter__(self):
        ids = self.ids
        if isawaitable(ids):
            ids = await ids
        elif iscoroutinefunction(ids):
            ids = await ids()

        for instance_id in ids:
            yield await self._method(to_snowflake(instance_id))


class _BaseProxy:
    def __getattr__(self, item):
        return ValueProxy(self, item, getter=getattr)

    def __getitem__(self, item):
        return ValueProxy(self, item, getter=getitem)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return CallProxy(self, args, kwargs)

    async def _resolve_proxies(self):
        return await self


@attr.define()
class CacheProxy(_BaseProxy):
    id: "Snowflake_Type" = attr.field(converter=to_snowflake)
    _method: Callable = attr.field(repr=False)

    def __await__(self):
        return self._method(self.id).__await__()


@attr.define()
class ValueProxy(_BaseProxy):
    _proxy: "TYPE_ALL_PROXY" = attr.field()
    _item: Any = attr.field()
    _getter: Callable = attr.field()

    def __await__(self):
        return self._get_value(await_last=True).__await__()

    async def _resolve_proxies(self):
        return await self._get_value(await_last=False)

    async def _get_value(self, await_last=False):
        instance = await self._proxy._resolve_proxies()
        value = self._getter(instance, self._item)

        if await_last and isawaitable(value):  # for deeply nested async properties
            value = await value

        return value


@attr.define()
class CallProxy(_BaseProxy):
    _proxy: "TYPE_ALL_PROXY" = attr.field()
    _args: Any = attr.field(factory=tuple)
    _kwargs: Any = attr.field(factory=dict)

    def __await__(self):
        return self._call_proxy_method().__await__()

    async def _call_proxy_method(self):
        method = await self._proxy
        if iscoroutinefunction(method):
            return await method(*self._args, **self._kwargs)
        else:
            return method(*self._args, **self._kwargs)


@attr.define(init=False)
class PartialCallableProxy(_BaseProxy):
    _callable: Callable[..., Coroutine[Any, Any, Any]] = attr.field(repr=False)
    _args: Any = attr.field()
    _kwargs: Any = attr.field()

    def __init__(self, func, *args, **kwargs):
        self._callable = func
        self._args = args
        self._kwargs = kwargs

    def __await__(self):
        return self.__call__().__await__()

    async def __call__(self) -> Any:
        return await self._callable(*self._args, **self._kwargs)


TYPE_ALL_PROXY = Union[CacheProxy, ValueProxy, CallProxy, PartialCallableProxy]
