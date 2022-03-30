import asyncio
import inspect
from typing import Coroutine, Callable

from dis_snek.api.events.internal import BaseEvent
from dis_snek.client.const import MISSING, Absent
from dis_snek.client.utils import get_event_name

__all__ = ["Listener", "listen"]


class Listener:

    event: str
    callback: Callable[..., Coroutine]

    def __init__(self, func: Callable[..., Coroutine], event: str) -> None:
        self.event = event
        self.callback = func

    async def __call__(self, *args, **kwargs) -> None:
        return await self.callback(*args, **kwargs)

    @classmethod
    def create(cls, event_name: Absent[str | BaseEvent] = MISSING) -> Callable[[Callable[..., Coroutine]], "Listener"]:
        def wrapper(coro: Callable[..., Coroutine]) -> "Listener":
            if not asyncio.iscoroutinefunction(coro):
                raise TypeError("Listener must be a coroutine")

            name = event_name

            if name is MISSING:
                for typehint in coro.__annotations__.values():
                    if (
                        inspect.isclass(typehint)
                        and issubclass(typehint, BaseEvent)
                        and typehint.__name__ != "RawGatewayEvent"
                    ):
                        name = typehint.__name__
                        break

                if not name:
                    name = coro.__name__

            return cls(coro, get_event_name(name))

        return wrapper


def listen(event_name: Absent[str | BaseEvent] = MISSING) -> Callable[[Callable[..., Coroutine]], Listener]:
    return Listener.create(event_name)
