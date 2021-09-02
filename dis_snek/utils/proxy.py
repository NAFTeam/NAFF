from inspect import isawaitable, iscoroutinefunction
from operator import getitem
from typing import TYPE_CHECKING, Union, Awaitable, Callable, Coroutine, Any, List

import attr

from dis_snek.models.snowflake import to_snowflake
from dis_snek.utils.attr_utils import copy_converter

if TYPE_CHECKING:
    from dis_snek.models.snowflake import Snowflake_Type


@attr.define()
class CacheView:
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
