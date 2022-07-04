import asyncio
import inspect
from typing import Coroutine, Callable

from naff.models.naff.callback import CallbackObject
from naff.api.events.internal import BaseEvent
from naff.client.const import MISSING, Absent
from naff.client.utils import get_event_name

__all__ = ("Listener", "listen")


class Listener(CallbackObject):

    event: str
    """Name of the event to listen to."""
    callback: Coroutine
    """Coroutine to call when the event is triggered."""

    def __init__(self, func: Callable[..., Coroutine], event: str) -> None:
        super().__init__()

        self.event = event
        self.callback = func

    @classmethod
    def create(cls, event_name: Absent[str | BaseEvent] = MISSING) -> Callable[[Coroutine], "Listener"]:
        """
        Decorator for creating an event listener.

        Args:
            event_name: The name of the event to listen to. If left blank, event name will be inferred from the function name or parameter.

        Returns:
            A listener object.

        """

        def wrapper(coro: Coroutine) -> "Listener":
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
    """
    Decorator to make a function an event listener.

    Args:
        event_name: The name of the event to listen to. If left blank, event name will be inferred from the function name or parameter.

    Returns:
        A listener object.

    """
    return Listener.create(event_name)
