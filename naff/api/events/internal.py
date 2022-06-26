"""
These are events dispatched by the client. This is intended as a reference so you know what data to expect for each event.

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

from naff.client.const import MISSING
from naff.models.discord.snowflake import to_snowflake
from naff.client.utils.attr_utils import define, field, docs

__all__ = (
    "BaseEvent",
    "Button",
    "Component",
    "Connect",
    "Disconnect",
    "ShardConnect",
    "ShardDisconnect",
    "GuildEvent",
    "Login",
    "Ready",
    "Resume",
    "Select",
    "Startup",
    "WebsocketReady",
)


if TYPE_CHECKING:
    from naff import Client
    from naff.models.naff.context import ComponentContext
    from naff.models.discord.snowflake import Snowflake_Type
    from naff.models.discord.guild import Guild

_event_reg = re.compile("(?<!^)(?=[A-Z])")


@define(slots=False)
class BaseEvent:
    """A base event that all other events inherit from."""

    override_name: str = field(kw_only=True, default=None)
    """Custom name of the event to be used when dispatching."""
    bot: "Client" = field(kw_only=True, default=MISSING)
    """The client instance that dispatched this event."""

    @property
    def resolved_name(self) -> str:
        """The name of the event, defaults to the class name if not overridden."""
        name = self.override_name or self.__class__.__name__
        return _event_reg.sub("_", name).lower()


@define(slots=False, kw_only=False)
class GuildEvent:
    """A base event that adds guild_id."""

    guild_id: "Snowflake_Type" = field(metadata=docs("The ID of the guild"), converter=to_snowflake)

    @property
    def guild(self) -> "Guild":
        """Guild related to event"""
        return self.bot.cache.get_guild(self.guild_id)


@define(kw_only=False)
class Login(BaseEvent):
    """The bot has just logged in."""


@define(kw_only=False)
class Connect(BaseEvent):
    """The bot is now connected to the discord Gateway."""


@define(kw_only=False)
class Resume(BaseEvent):
    """The bot has resumed its connection to the discord Gateway."""


@define(kw_only=False)
class Disconnect(BaseEvent):
    """The bot has just disconnected."""


class ShardConnect(Connect):
    """A shard just connected to the discord Gateway."""


@define(kw_only=False)
class ShardDisconnect(Disconnect):
    """A shard just disconnected."""


@define(kw_only=False)
class Startup(BaseEvent):
    """
    The client is now ready for the first time.

    Use this for tasks you want to do upon login, instead of ready, as
    this will only be called once.

    """


@define(kw_only=False)
class Ready(BaseEvent):
    """
    The client is now ready.

    Note:
        Don't use this event for things that must only happen once, on startup, as this event may be called multiple times.
        Instead, use the `Startup` event

    """


@define(kw_only=False)
class WebsocketReady(BaseEvent):
    """The gateway has reported that it is ready."""

    data: dict = field(metadata=docs("The data from the ready event"))


@define(kw_only=False)
class Component(BaseEvent):
    """Dispatched when a user uses a Component."""

    context: "ComponentContext" = field(metadata=docs("The context of the interaction"))


@define(kw_only=False)
class Button(Component):
    """Dispatched when a user uses a Button."""


@define(kw_only=False)
class Select(Component):
    """Dispatched when a user uses a Select."""
