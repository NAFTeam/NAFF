from inspect import isawaitable, isasyncgen
from operator import getitem, methodcaller
from typing import TYPE_CHECKING, Union, Awaitable, Callable, Any, List

import attr
import asyncio

# from dis_snek.models.snowflake import to_snowflake
from dis_snek.utils.attr_utils import copy_converter

if TYPE_CHECKING:
    from dis_snek.models.snowflake import Snowflake_Type


def proxy_partial(func, *args, **kwargs):
    """Use this instead as partial where you need to return proxy of async function or method"""
    return Proxy().call(func, *args, **kwargs)


def proxy_none():
    """Just a shortcut"""
    return Proxy(attr.NOTHING)


def call(func, *args, **kwargs):
    return func(*args, **kwargs)


# async def maybe_await(func, *args, **kwargs):
#     value = func(*args, **kwargs)
#     if isawaitable(value):
#         value = await value
#     return value


async def _resolve_action(action, value, *args, **kwargs):
    # resolve dud (when it's Dud-created Proxy instead of proper function eg dud.add_reaction("🤖"))
    if getattr(action, "_is_dud", False):
        # noinspection PyProtectedMember
        return await action._resolve_from(value)

    if value is Ellipsis:  # Ellipsis won't be passed to functions as argument
        value = action(*args, **kwargs)
    else:
        value = action(value, *args, **kwargs)

    if isinstance(value, CacheView):
        pass
    elif isasyncgen(value):
        value = [item async for item in value]
    elif isawaitable(value):
        value = await value

    return value

# ---
# Functions for internal usage in proxies


async def iterate(tasks: List[Awaitable], sequential=False):
    if sequential:
        for task in tasks:
            yield await task
    else:
        for task in asyncio.as_completed(tasks):
            yield await task


async def parallel_iterator(value, *funcs, sequential=False):
    # one initial value, iterates several functions over it
    tasks = [_resolve_action(func, value) for func in funcs]
    async for result in iterate(tasks, sequential):
        yield result


async def map_iterator(items: list, func, sequential=False):
    # several initial values (list), iterates one function over it, returns results
    tasks = [_resolve_action(func, value) for value in items]
    async for result in iterate(tasks, sequential):
        yield result


async def _filter_caller(func, value):
    return await _resolve_action(func, value), value


async def filter_iterator(items: list, func, sequential=False):
    # several initial values (list), iterates one function over it, returns initial values if result
    tasks = [_filter_caller(func, value) for value in items]
    async for success, value in iterate(tasks, sequential):
        if success:
            yield value


@attr.define()
class Proxy:
    """Base proxy class with all the cool stuff"""
    _initial_value = attr.field(default=...)
    _sequence = attr.field(factory=list, kw_only=True)
    _is_dud = attr.field(default=False, kw_only=True)

    @classmethod
    def _prototype(cls, proxy: "Proxy") -> "Proxy":
        # noinspection PyArgumentList
        return cls(initial_value=proxy._initial_value, sequence=proxy._sequence, is_dud=proxy._is_dud)

    def call(self, func, *args, **kwargs) -> "Proxy":
        """
        Runs a function with specified args and kwargs on previous chain result value

        one value goes in -> one comes out

        Functions should have signature func(value, *args, **kwargs)
        sync/async functions, partials, duds can be used
        """
        return Proxy._prototype(self)._add_action(func, *args, **kwargs)

    def chain(self, *funcs) -> "Proxy":
        """
        Runs several functions in sequence on previous chain result value

        one value goes in -> one comes out

        Return value of each function is fed to the next one)
        Functions should accept only one argument
        sync/async functions, partials, duds can be used
        """
        proxy = Proxy._prototype(self)
        for func in funcs:
            proxy._add_action(func)
        return proxy

    def parallel(self, *funcs, sequential=False) -> "IterableProxy":
        """
        Runs independently several functions on previous chain result value
        Produces list (in middle of the chain) or can be used as async iterator (in the end of the chain)

        one value goes in -> iterable comes out

        Functions should accept only one argument
        sync/async functions, partials, duds can be used

        sequential=True -> funcs run independently but in sequence
        sequential=False -> funcs run independently and start at the same time. Order is not preserved
        """
        return IterableProxy._prototype(self)._add_action(parallel_iterator, *funcs, sequential=sequential)

    def __await__(self):
        result = self._resolve_from(self._initial_value).__await__()
        if result is attr.NOTHING:
            return None
        return result

    def __getattr__(self, item) -> "Proxy":
        return Proxy._prototype(self)._add_action(getattr, item)

    def __getitem__(self, item) -> "Proxy":
        return Proxy._prototype(self)._add_action(getitem, item)

    def __call__(self, *args, **kwargs) -> "Proxy":
        return Proxy._prototype(self)._add_action(call, *args, **kwargs)

    def _add_action(self, action, *args, **kwargs):
        self._sequence.append((action, args, kwargs))
        return self

    def _resolve_from(self, initial_value):
        return self._resolve(initial_value, self._sequence)

    @classmethod
    async def _resolve(cls, initial_value, sequence):
        value = initial_value

        if isawaitable(value):
            value = await value

        for action, args, kwargs in sequence:
            # NOTHING is used internally to indicate that the value is missing and no further actions will be performed on it
            # unlike None, which could be a legit return value of some functions
            if value is attr.NOTHING:
                return attr.NOTHING

            # print("value", str(value)[:100])
            # print(str(action)[:100], str(args)[:100], str(kwargs)[:100])
            value = await _resolve_action(action, value, *args, **kwargs)
            # print("new", value)

        if isawaitable(value):
            value = await value

        return value


@attr.define()
class IterableProxy(Proxy):
    @classmethod
    def _prototype(cls, proxy: "Proxy") -> "IterableProxy":  # just so pycharm won't scream at me
        # noinspection PyTypeChecker
        return super()._prototype(proxy)  # just to retype

    async def get_list(self) -> list:
        """Returns list. What's more to this?"""
        return [item async for item in self]

    def map(self, func, sequential=False) -> "IterableProxy":
        """
        Runs independently several functions on previous chain result values (list of values)
        Produces list (in middle of the chain) or can be used as async iterator (in the end of the chain)

        list of values from previous steps goes in -> iterable comes out

        Functions should accept only one argument
        sync/async functions, partials, duds can be used

        sequential=True -> funcs run independently but in sequence
        sequential=False -> funcs run independently and start at the same time. Order is not preserved
        """
        return IterableProxy._prototype(self)._add_action(map_iterator, func, sequential=sequential)

    def filter(self, func, sequential=False) -> "IterableProxy":
        """
        Runs independently several functions on previous chain result values (list of values)
        Only values for which func returned True go into output
        Original values preserved
        Produces list (in middle of the chain) or can be used as async iterator (in the end of the chain)

        list of values from previous steps goes in -> iterable comes out. It may be empty

        Functions should accept only one argument
        sync/async functions, partials, duds can be used

        sequential=True -> funcs run independently but in sequence
        sequential=False -> funcs run independently and start at the same time. Order is not preserved
        """
        return IterableProxy._prototype(self)._add_action(filter_iterator, func, sequential=sequential)

    # def reduce(self):  # todo maybe
    #     pass

    async def __aiter__(self):
        """
        Rules of aiter: (async gens = parallel, map, filter, etc)
        1. async gen on sequence tail allows to use __aiter__. Or you get error, BAM
        2. async gens in the middle of sequence are resolved/converted to lists and passed on to the next steps
        3. want advanced crazy shit? use duds
        """
        value = await self._resolve(self._initial_value, self._sequence[:-1])
        if value is attr.NOTHING:
            return

        action, args, kwargs = self._sequence[-1]
        generator = action(value, *args, **kwargs)  # complex _resolve_action is not needed here
        async for item in generator:
            yield item


class AsyncInt(int):
    """Yes this is wrapper of int to allow awaiting it. Syntax consistency idk idk"""
    def __await__(self):
        return self._return_self().__await__()

    async def _return_self(self):
        return self


@attr.define()
class CacheProxy(Proxy):
    """
    Use this class internally in async properties of discord objects that should return single object by it's id

    """
    def __init__(self, id: "Snowflake_Type", method: Callable):
        super().__init__(id if id is not None else attr.NOTHING)
        self._add_action(method)

    @property
    def id(self) -> "Snowflake_Type":
        return AsyncInt(self._initial_value)


@attr.define(kw_only=True)
class CacheView(IterableProxy):
    """
    Use this class internally in async properties of discord objects that should return a number of objects by list of ids
    and can fetch a single object by it's id

    """
    _method: Callable = attr.field(repr=False)  # store to use in get()

    def __init__(self, ids: Union[Awaitable, List["Snowflake_Type"]], method: Callable):
        super().__init__(copy_converter(ids))  # if ids is not None else attr.NOTHING
        self._method = method
        self._add_action(map_iterator, method, sequential=True)

    @property
    def ids(self):
        return self._initial_value

    async def get_dict(self):
        return {instance.id: instance async for instance in self}

    def get(self, item):
        return CacheProxy(id=item, method=self._method)

    def __getitem__(self, item):
        return self.get(item)


class DudSingleton:
    dud_marker = object()

    """Do not instantiate directly. Don't touch. Don't look at"""
    @staticmethod
    def _init_proxy():
        return IterableProxy(is_dud=True)

    def __getattr__(self, item):
        return getattr(self._init_proxy(), item)

    def __getitem__(self, item):
        return methodcaller("__getitem__", item)(self._init_proxy())

    def __call__(self, *args, **kwargs):
        return methodcaller("__call__", *args, **kwargs)(self._init_proxy())


# noinspection PyTypeChecker
dud: "IterableProxy" = DudSingleton()

# what is dud?
# dud is a pseudo-function-placeholder that you can pass into some Proxy methods like .call, .chain, .parallel
# you can think about it like lambda:
# lambda msg: msg.add_reaction("👍🏻") ~ dud.add_reaction("👍🏻")
# but you can generate distinct duds in generator expressions unlike lambdas

# example:
# this:
# await user.send("Hello").add_reaction("👍🏻")
# can be replaced with this:
# user.send("Hello").call(dud.add_reaction("👍🏻"))
# Doesnt' seem useful yet? But duds can be used in Proxy.parallel to facilitate fairly complex expressions
# await member.user.dm.send("Hello").parallel(dud.add_reaction("👍🏻"), dud.add_reaction("🤖"))
# await member.user.dm.send("Hello").parallel(*(dud.add_reaction(e) for e in ("👍🏻", "🤖")), sequential=True)
# await member.user.dm.send("Hello").parallel(*(dud.add_reaction(e) for e in ("👍🏻", "🤖")), sequential=True).call(print)

TYPE_ALL_PROXY = Union[Proxy, CacheView]
