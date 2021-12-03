import asyncio
import functools
import inspect
import logging
from typing import TYPE_CHECKING, Callable, Coroutine

from dis_snek.const import logger_name, MISSING
from dis_snek.models import events, SnakeBotUser

if TYPE_CHECKING:
    from dis_snek.smart_cache import GlobalCache

log = logging.getLogger(logger_name)


class Processor:
    def __init__(self, callback, name):
        self.callback = callback
        self.event_name = name

    @classmethod
    def define(cls, event_name: str = MISSING):
        def wrapper(coro):
            name = event_name
            if name is MISSING:
                name = coro.__name__
            name = name.lstrip("_")
            name = name.removeprefix("on_")

            return cls(coro, name)

        return wrapper


class EventMixinTemplate:
    """All event mixins inherit from this to keep them uniform"""

    cache: "GlobalCache"
    dispatch: Callable[[events.BaseEvent], None]
    _init_interactions: Callable[[], Coroutine]
    synchronise_interactions: Callable[[], Coroutine]
    _user: SnakeBotUser
    _guild_event: asyncio.Event

    def __init__(self):
        for call in inspect.getmembers(self):
            if isinstance(call[1], Processor):
                self.add_event_processor(call[1].event_name)(functools.partial(call[1].callback, self))
