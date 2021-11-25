"""These are events dispatched by the client. This is intended as a reference so you know what data to expect for each event

??? Hint "Example Usage:"
    The event classes outlined here are in `CamelCase` to comply with Class naming convention, however the event names
    are actually in `lower_case_with_underscores` so your listeners should be named as following:

    ```python
    @listen()
    def on_ready():
        # ready events pass no data, so dont have params
        print("Im ready!")

    @listen()
    def on_guild_join(event):
        # guild_create events pass a guild object, expect a single param
        print(f"{event.guild.name} created")
    ```
!!! warning
    While all of these events are documented, not all of them are used, currently.
"""
import re
from typing import TYPE_CHECKING

import attr

from dis_snek.const import MISSING
from dis_snek.models.snowflake import to_snowflake
from dis_snek.utils.attr_utils import docs

if TYPE_CHECKING:
    from dis_snek import Snake
    from dis_snek.models.context import ComponentContext
    from dis_snek.models.snowflake import Snowflake_Type

_event_reg = re.compile("(?<!^)(?=[A-Z])")


@attr.s()
class BaseEvent:
    """A base event that all other events inherit from"""

    override_name: str = attr.ib(kw_only=True, default=None)
    bot: "Snake" = attr.ib(kw_only=True, default=MISSING)

    @property
    def resolved_name(self):
        name = self.override_name or self.__class__.__name__
        return _event_reg.sub("_", name).lower()


@attr.s()
class GuildEvent:
    """A base event that adds guild_id"""

    guild_id: "Snowflake_Type" = attr.ib(metadata=docs("The ID of the guild"), converter=to_snowflake)


@attr.s(slots=True)
class Login(BaseEvent):
    """The bot has just logged in"""


@attr.s(slots=True)
class Connect(BaseEvent):
    """The bot is now connected to the discord Gateway."""


@attr.s(slots=True)
class Resume(BaseEvent):
    """The bot has resumed its connection to the discord Gateway"""


@attr.s(slots=True)
class Disconnect(BaseEvent):
    """The bot has just disconnected."""


@attr.s(slots=True)
class Startup(BaseEvent):
    """The client is now ready for the first time

    Use this for tasks you want to do upon login, instead of ready, as this will only be called once."""


@attr.s(slots=True)
class Ready(BaseEvent):
    """The client is now ready.

    Note:
        Don't use this event for things that must only happen once, on startup, as this event may be called multiple times.
        Instead, use the `Startup` event
    """


@attr.s(slots=True)
class WebsocketReady(BaseEvent):
    """The gateway has reported that it is ready"""

    data: dict = attr.ib(metadata=docs("The data from the ready event"))


@attr.s(slots=True)
class Component(BaseEvent):
    """Dispatched when a user uses a Component"""

    context: "ComponentContext" = attr.ib(metadata=docs("The context of the interaction"))


@attr.s(slots=True)
class Button(Component):
    """Dispatched when a user uses a Button"""


@attr.s(slots=True)
class Select(Component):
    """Dispatched when a user uses a Select"""
