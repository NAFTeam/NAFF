import asyncio
from typing import Coroutine, Callable

from dis_snek.const import MISSING


class Listener:
    def __init__(self, func: Callable[..., Coroutine], event: str):
        self.event = event
        self.callback = func

    async def __call__(self, *args, **kwargs):
        return await self.callback(*args, **kwargs)

    @classmethod
    def create(cls, event_name: str = MISSING):
        def wrapper(coro):
            if not asyncio.iscoroutinefunction(coro):
                raise TypeError("Listener must be a coroutine")

            name = event_name
            if name is MISSING:
                name = coro.__name__
            name = name.lstrip("_")
            name = name.removeprefix("on_")

            return cls(coro, name)

        return wrapper


def listen(event_name: str = MISSING):
    return Listener.create(event_name)
