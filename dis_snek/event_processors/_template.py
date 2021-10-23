import asyncio
import logging
from typing import TYPE_CHECKING, Callable, Coroutine

from dis_snek.const import logger_name
from dis_snek.models import events, SnakeBotUser

if TYPE_CHECKING:
    from dis_snek.smart_cache import GlobalCache

log = logging.getLogger(logger_name)


class EventMixinTemplate:
    """All event mixins inherit from this to keep them uniform"""

    cache: "GlobalCache"
    dispatch: Callable[[events.BaseEvent], None]
    _init_interactions: Callable[[], Coroutine]
    synchronise_interactions: Callable[[], Coroutine]
    _user: SnakeBotUser
    _guild_event: asyncio.Event
