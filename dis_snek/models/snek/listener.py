import asyncio
from typing import Coroutine, Callable

from dis_snek.client.const import MISSING, Absent


class Listener:

    event: str
    callback: Coroutine

    def __init__(self, func: Coroutine, event: str):
        self.event = event
        self.callback = func

    async def __call__(self, *args, **kwargs):
        return await self.callback(*args, **kwargs)

    @classmethod
    def create(cls, event_name: Absent[str] = MISSING) -> Callable[[Coroutine], "Listener"]:
        def wrapper(coro: Coroutine) -> "Listener":
            if not asyncio.iscoroutinefunction(coro):
                raise TypeError("Listener must be a coroutine")

            name = event_name
            if name is MISSING:
                name = coro.__name__
            name = name.lstrip("_")
            name = name.removeprefix("on_")

            return cls(coro, name)

        return wrapper


def listen(event_name: Absent[str] = MISSING) -> Callable[[Coroutine], Listener]:
    return Listener.create(event_name)
