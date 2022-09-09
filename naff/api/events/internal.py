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
from typing import TYPE_CHECKING, Any, Optional

from naff.api.events.base import BaseEvent, RawGatewayEvent
from naff.client.utils.attr_utils import define, field, docs

__all__ = (
    "Button",
    "Component",
    "Connect",
    "Disconnect",
    "Error",
    "ShardConnect",
    "ShardDisconnect",
    "Login",
    "Ready",
    "Resume",
    "Select",
    "Startup",
    "WebsocketReady",
)


if TYPE_CHECKING:
    from naff.models.naff.context import ComponentContext, Context

_event_reg = re.compile("(?<!^)(?=[A-Z])")


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


@define(kw_only=False)
class ShardConnect(Connect):
    """A shard just connected to the discord Gateway."""

    shard_id: int = field(metadata=docs("The ID of the shard"))


@define(kw_only=False)
class ShardDisconnect(Disconnect):
    """A shard just disconnected."""

    shard_id: int = field(metadata=docs("The ID of the shard"))


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

    !!! note
        Don't use this event for things that must only happen once, on startup, as this event may be called multiple times.
        Instead, use the `Startup` event

    """


@define(kw_only=False)
class WebsocketReady(RawGatewayEvent):
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


@define(kw_only=False)
class Error(BaseEvent):
    """Dispatched when the library encounters an error."""

    source: str = field(metadata=docs("The source of the error"))
    error: Exception = field(metadata=docs("The error that was encountered"))
    args: tuple[Any] = field(factory=tuple)
    kwargs: dict[str, Any] = field(factory=dict)
    ctx: Optional["Context"] = field(default=None, metadata=docs("The Context, if one was active"))
