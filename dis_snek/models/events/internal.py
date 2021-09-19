from typing import TYPE_CHECKING

import attr

if TYPE_CHECKING:
    from dis_snek.models.discord_objects.context import ComponentContext
    from dis_snek.models.snowflake import Snowflake_Type


@attr.s()
class BaseEvent:
    """A base event that all other events inherit from"""

    override_name: str = attr.ib(kw_only=True, default=None)

    @property
    def resolved_name(self):
        return self.override_name or self.__class__.__name__


@attr.s()
class _GuildEvent:
    """A base event that adds guild_id"""

    guild_id: "Snowflake_Type" = attr.ib(metadata={"docs": "The ID of the guild"})


@attr.s()
class Login(BaseEvent):
    """The bot has just logged in"""


@attr.s()
class Connect(BaseEvent):
    """The bot is now connected to the discord Gateway."""


@attr.s()
class Resume(BaseEvent):
    """The bot has resumed its connection to the discord Gateway"""


@attr.s()
class Disconnect(BaseEvent):
    """The bot has just disconnected."""


@attr.s()
class Ready(BaseEvent):
    """The client is now ready.

    Note:
        Don't use this event for things that must only happen once, on startup, as this event may be called multiple times.
    """


class WebsocketReady(BaseEvent):
    """The gateway has reported that it is ready"""


@attr.s()
class Component(BaseEvent):
    """Dispatched when a user uses a Component"""

    context: "ComponentContext" = attr.ib(metadata={"docs": "The context of the interaction"})


@attr.s()
class Button(Component):
    """Dispatched when a user uses a Button"""


@attr.s()
class Select(Component):
    """Dispatched when a user uses a Select"""
