from inspect import isawaitable, iscoroutinefunction
from functools import wraps
from operator import getitem
from typing import TYPE_CHECKING, Union, Awaitable, Callable, Coroutine, Any, List

import attr
import asyncio

from dis_snek.models.snowflake import to_snowflake
from dis_snek.utils.attr_utils import copy_converter

if TYPE_CHECKING:
    from dis_snek.models.snowflake import Snowflake_Type


def get_id(obj):
    try:
        return obj.id
    except AttributeError:
        return to_snowflake(obj)


def return_proxy(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        return AsyncPartial(func, self, *args, **kwargs)

    return wrapper


async def maybe_await(func, *args, **kwargs):
    value = func(*args, **kwargs)
    if isawaitable(value):
        value = await value
    return value


# @attr.define()
# class PartialHolder:
#     args: tuple = attr.field()
#     kwargs: dict = attr.field()
#
#
# def partial_holder(*args, **kwargs):
#     return PartialHolder(args, kwargs)


class _ProxyViewCalls:
    def map(self, func):
        pass

    def reduce(self, func):
        pass

    def filter(self, func):
        pass


@attr.define()
class CacheView(_ProxyViewCalls):
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


@attr.define()
class _BaseProxy:
    def __getattr__(self, item):
        return ValueProxy(self, item, getter=getattr)

    def __getitem__(self, item):
        return ValueProxy(self, item, getter=getitem)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return MethodCallProxy(self, args, kwargs)

    async def _resolve_proxies(self):
        return await self

    def chain(self, *func_chain):
        proxy = self
        for func in func_chain:
            proxy = SingleCallProxy(proxy, func)
        return proxy

    def parallel(self, *funcs, parallel=True):
        """parallel=False -> funcs run independently but in sequence"""
        return MultiCallProxy(self, funcs, parallel=parallel)

    # def map(self, func):
    #     pass


@attr.define()
class CacheProxy(_BaseProxy):
    id: "Snowflake_Type" = attr.field(converter=to_snowflake)
    _method: Callable = attr.field(repr=False)

    def __await__(self):
        return self._method(self.id).__await__()


@attr.define()
class ValueProxy(_BaseProxy):
    """Proxy that is used for name resolution"""
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
class MethodCallProxy(_BaseProxy):
    """Proxy for method calls"""
    _proxy: "TYPE_ALL_PROXY" = attr.field()
    _args: Any = attr.field(factory=tuple)
    _kwargs: Any = attr.field(factory=dict)

    def __await__(self):
        return self._call_proxy_method().__await__()

    async def _call_proxy_method(self):
        method = await self._proxy
        # for coroutines and sync methods returning awaitables (methods decorated with @return_proxy)
        return await maybe_await(method, *self._args, **self._kwargs)


@attr.define(init=False)
class AsyncPartial(_BaseProxy):
    _callable: Callable[..., Coroutine[Any, Any, Any]] = attr.field()
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


@attr.define()
class SingleCallProxy(_BaseProxy):
    _proxy: "TYPE_ALL_PROXY" = attr.field()
    _callable: Callable[..., Coroutine[Any, Any, Any]] = attr.field()

    def __await__(self):
        return self.__call__().__await__()

    async def __call__(self) -> Any:
        instance = await self._proxy
        return await maybe_await(self._callable, instance)


@attr.define()
class MultiCallProxy(_BaseProxy):
    _proxy: "TYPE_ALL_PROXY" = attr.field()
    _callables: List[Callable[..., Coroutine[Any, Any, Any]]] = attr.field()
    parallel: bool = attr.field()

    def __await__(self):
        return self.get_list().__await__()

    async def __call__(self) -> Any:
        return await self.get_list()

    async def get_list(self):
        return [instance async for instance in self]

    async def __aiter__(self):
        instance = await self._proxy
        if self.parallel:
            tasks = [maybe_await(func, instance) for func in self._callables]
            for result in asyncio.as_completed(tasks):
                yield await result
        else:
            for func in self._callables:
                yield await maybe_await(func, instance)


TYPE_ALL_PROXY = Union[CacheProxy, ValueProxy, MethodCallProxy, AsyncPartial, SingleCallProxy, MultiCallProxy]
