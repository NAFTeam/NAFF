import asyncio
import importlib.util
import inspect
import json
import logging
import re
import sys
import time
import traceback
from collections.abc import Iterable
from datetime import datetime
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Coroutine,
    Dict,
    List,
    NoReturn,
    Optional,
    Type,
    Union,
    overload,
    Literal,
)

from discord_typings.interactions.receiving import (
    ComponentChannelInteractionData,
    AutocompleteChannelInteractionData,
    InteractionData,
)

import dis_snek.api.events as events
from dis_snek.api.events import RawGatewayEvent, MessageCreate
from dis_snek.api.events import processors
from dis_snek.api.events.internal import Component, BaseEvent
from dis_snek.api.gateway.gateway import GatewayClient
from dis_snek.api.gateway.state import ConnectionState
from dis_snek.api.http.http_client import HTTPClient
from dis_snek.client.const import logger_name, GLOBAL_SCOPE, MISSING, MENTION_PREFIX, Absent
from dis_snek.client.errors import (
    BotException,
    ScaleLoadException,
    ExtensionLoadException,
    ExtensionNotFound,
    Forbidden,
    InteractionMissingAccess,
    HTTPException,
    NotFound,
)
from dis_snek.client.utils.input_utils import get_first_word, get_args
from dis_snek.client.utils.misc_utils import wrap_partial, get_event_name
from dis_snek.client.utils.serializer import to_image_data
from dis_snek.models import (
    Activity,
    Application,
    CustomEmoji,
    Guild,
    GuildTemplate,
    Message,
    Scale,
    SnakeBotUser,
    User,
    Member,
    StickerPack,
    Sticker,
    ScheduledEvent,
    InteractionCommand,
    SlashCommand,
    OptionTypes,
    MessageCommand,
    BaseCommand,
    to_snowflake,
    to_snowflake_list,
    ComponentContext,
    InteractionContext,
    ModalContext,
    MessageContext,
    AutocompleteContext,
    ComponentCommand,
    Context,
    application_commands_to_dict,
    sync_needed,
    VoiceRegion,
)
from dis_snek.models import Wait
from dis_snek.models.discord.components import get_components_ids, BaseComponent
from dis_snek.models.discord.enums import ComponentTypes, Intents, InteractionTypes, Status
from dis_snek.models.discord.file import UPLOADABLE_TYPE
from dis_snek.models.discord.modal import Modal
from dis_snek.models.snek.auto_defer import AutoDefer
from dis_snek.models.snek.listener import Listener
from dis_snek.models.snek.tasks import Task
from .smart_cache import GlobalCache
from ..models.snek.active_voice_state import ActiveVoiceState

if TYPE_CHECKING:
    from dis_snek.models import Snowflake_Type, TYPE_ALL_CHANNEL

log = logging.getLogger(logger_name)

__all__ = ["Snake"]


class Snake(
    processors.ChannelEvents,
    processors.GuildEvents,
    processors.MemberEvents,
    processors.MessageEvents,
    processors.ReactionEvents,
    processors.RoleEvents,
    processors.StageEvents,
    processors.ThreadEvents,
    processors.UserEvents,
    processors.VoiceEvents,
):
    """
    The bot client.

    note:
        By default, all non-privileged intents will be enabled

    Attributes:
        intents: Union[int, Intents]: The intents to use

        default_prefix: Union[str, Iterable[str]]: The default prefix (or prefixes) to use for message commands. Defaults to your bot being mentioned.
        generate_prefixes: Callable[..., Coroutine]: A coroutine that returns a string or an iterable of strings to determine prefixes.
        status: Status: The status the bot should log in with (IE ONLINE, DND, IDLE)
        activity: Union[Activity, str]: The activity the bot should log in "playing"

        sync_interactions: bool: Should application commands be synced with discord?
        delete_unused_application_cmds: bool: Delete any commands from discord that aren't implemented in this client
        enforce_interaction_perms: bool: Enforce discord application command permissions, locally
        fetch_members: bool: Should the client fetch members from guilds upon startup (this will delay the client being ready)

        auto_defer: AutoDefer: A system to automatically defer commands after a set duration
        interaction_context: Type[InteractionContext]: InteractionContext: The object to instantiate for Interaction Context
        message_context: Type[MessageContext]: The object to instantiate for Message Context
        component_context: Type[ComponentContext]: The object to instantiate for Component Context
        autocomplete_context: Type[AutocompleteContext]: The object to instantiate for Autocomplete Context

        global_pre_run_callback: Callable[..., Coroutine]: A coroutine to run before every command is executed
        global_post_run_callback: Callable[..., Coroutine]: A coroutine to run after every command is executed

        total_shards: int: The total number of shards in use
        shard_id: int: The zero based int ID of this shard

        debug_scope: Snowflake_Type: Force all application commands to be registered within this scope
        asyncio_debug: bool: Enable asyncio debug features

    Optionally, you can configure the caches here, by specifying the name of the cache, followed by a dict-style object to use.
    It is recommended to use `smart_cache.create_cache` to configure the cache here.
    as an example, this is a recommended attribute `message_cache=create_cache(250, 50)`,

    !!! note
        Setting a message cache hard limit to None is not recommended, as it could result in extremely high memory usage, we suggest a sane limit.

    """

    def __init__(
        self,
        intents: Union[int, Intents] = Intents.DEFAULT,
        default_prefix: str | Iterable[str] = MENTION_PREFIX,
        generate_prefixes: Absent[Callable[..., Coroutine]] = MISSING,
        sync_interactions: bool = True,
        delete_unused_application_cmds: bool = False,
        enforce_interaction_perms: bool = True,
        fetch_members: bool = False,
        debug_scope: Absent["Snowflake_Type"] = MISSING,
        status: Status = Status.ONLINE,
        activity: Union[Activity, str] = None,
        auto_defer: Absent[Union[AutoDefer, bool]] = MISSING,
        interaction_context: Type[InteractionContext] = InteractionContext,
        message_context: Type[MessageContext] = MessageContext,
        component_context: Type[ComponentContext] = ComponentContext,
        autocomplete_context: Type[AutocompleteContext] = AutocompleteContext,
        global_pre_run_callback: Absent[Callable[..., Coroutine]] = MISSING,
        global_post_run_callback: Absent[Callable[..., Coroutine]] = MISSING,
        total_shards: int = 1,
        shard_id: int = 0,
        **kwargs,
    ) -> None:

        # Configuration

        self.sync_interactions = sync_interactions
        """Should application commands be synced"""
        self.del_unused_app_cmd: bool = delete_unused_application_cmds
        """Should unused application commands be deleted?"""
        self.debug_scope = to_snowflake(debug_scope) if debug_scope is not MISSING else MISSING
        """Sync global commands as guild for quicker command updates during debug"""
        self.default_prefix = default_prefix
        """The default prefix to be used for message commands"""
        self.generate_prefixes = generate_prefixes if generate_prefixes is not MISSING else self.generate_prefixes
        """A coroutine that returns a prefix or an iterable of prefixes, for dynamic prefixes"""
        if auto_defer is True:
            auto_defer = AutoDefer(enabled=True)
        else:
            auto_defer = auto_defer or AutoDefer()
        self.auto_defer = auto_defer
        """A system to automatically defer commands after a set duration"""

        # resources

        self.http: HTTPClient = HTTPClient()
        """The HTTP client to use when interacting with discord endpoints"""

        # context objects
        self.interaction_context: Type[InteractionContext] = interaction_context
        """The object to instantiate for Interaction Context"""
        self.message_context: Type[MessageContext] = message_context
        """The object to instantiate for Message Context"""
        self.component_context: Type[ComponentContext] = component_context
        """The object to instantiate for Component Context"""
        self.autocomplete_context: Type[AutocompleteContext] = autocomplete_context
        """The object to instantiate for Autocomplete Context"""

        # flags
        self._ready = asyncio.Event()
        self._closed = False
        self._startup = False

        self._guild_event = asyncio.Event()
        self.guild_event_timeout = 3
        """How long to wait for guilds to be cached"""

        # Sharding
        self.total_shards = total_shards
        self._connection_state: ConnectionState = ConnectionState(self, intents, shard_id)

        self.enforce_interaction_perms = enforce_interaction_perms

        self.fetch_members = fetch_members
        """Fetch the full members list of all guilds on startup"""

        self._mention_reg = MISSING

        # caches
        self.cache: GlobalCache = GlobalCache(self, **{k: v for k, v in kwargs.items() if hasattr(GlobalCache, k)})
        # these store the last sent presence data for change_presence
        self._status: Status = status
        if isinstance(activity, str):
            self._activity = Activity.create(name=str(activity))
        else:
            self._activity: Activity = activity

        self._user: Absent[SnakeBotUser] = MISSING
        self._app: Absent[Application] = MISSING

        # collections
        self.commands: Dict[str, MessageCommand] = {}
        """A dictionary of registered commands: `{name: command}`"""
        self.interactions: Dict["Snowflake_Type", Dict[str, InteractionCommand]] = {}
        """A dictionary of registered application commands: `{cmd_id: command}`"""
        self._component_callbacks: Dict[str, Callable[..., Coroutine]] = {}
        self._interaction_scopes: Dict["Snowflake_Type", "Snowflake_Type"] = {}
        self.processors: Dict[str, Callable[..., Coroutine]] = {}
        self.__extensions = {}
        self.scales = {}
        """A dictionary of mounted Scales"""
        self.listeners: Dict[str, List] = {}
        self.waits: Dict[str, List] = {}

        # callbacks
        if global_pre_run_callback:
            if asyncio.iscoroutinefunction(global_pre_run_callback):
                self.pre_run_callback: Callable[..., Coroutine] = global_pre_run_callback
            else:
                raise TypeError("Callback must be a coroutine")
        else:
            self.pre_run_callback = MISSING

        if global_post_run_callback:
            if asyncio.iscoroutinefunction(global_post_run_callback):
                self.post_run_callback: Callable[..., Coroutine] = global_post_run_callback
            else:
                raise TypeError("Callback must be a coroutine")
        else:
            self.post_run_callback = MISSING

        super().__init__()
        self._sanity_check()

    @property
    def is_closed(self) -> bool:
        """Returns True if the bot has closed."""
        return self._closed

    @property
    def is_ready(self) -> bool:
        """Returns True if the bot is ready."""
        return self._ready.is_set()

    @property
    def latency(self) -> float:
        """Returns the latency of the websocket connection."""
        return self._connection_state.latency

    @property
    def average_latency(self) -> float:
        """Returns the average latency of the websocket connection."""
        return self._connection_state.average_latency

    @property
    def start_time(self) -> datetime:
        """The start time of the bot."""
        return self._connection_state.start_time

    @property
    def gateway_started(self) -> bool:
        """Returns if the gateway has been started."""
        return self._connection_state.gateway_started.is_set()

    @property
    def intents(self) -> Intents:
        """The intents being used by this bot."""
        return self._connection_state.intents

    @property
    def user(self) -> SnakeBotUser:
        """Returns the bot's user."""
        return self._user

    @property
    def app(self) -> Application:
        """Returns the bots application."""
        return self._app

    @property
    def owner(self) -> Optional["User"]:
        """Returns the bot's owner'."""
        try:
            return self.app.owner
        except TypeError:
            return MISSING

    @property
    def guilds(self) -> List["Guild"]:
        """Returns a list of all guilds the bot is in."""
        return self.user.guilds

    @property
    def status(self) -> Status:
        """
        Get the status of the bot.

        IE online, afk, dnd

        """
        return self._status

    @property
    def activity(self) -> Activity:
        """Get the activity of the bot."""
        return self._activity

    @property
    def application_commands(self) -> List[InteractionCommand]:
        """A list of all application commands registered within the bot."""
        commands = []
        for scope in self.interactions.keys():
            for cmd in self.interactions[scope].values():
                if cmd not in commands:
                    commands.append(cmd)

        return commands

    @property
    def ws(self) -> GatewayClient:
        """Returns the websocket client."""
        return self._connection_state.gateway

    def _sanity_check(self) -> None:
        """Checks for possible and common errors in the bot's configuration."""
        log.debug("Running client sanity checks...")
        contexts = {
            self.interaction_context: InteractionContext,
            self.message_context: MessageContext,
            self.component_context: ComponentContext,
            self.autocomplete_context: AutocompleteContext,
        }
        for obj, expected in contexts.items():
            if not issubclass(obj, expected):
                raise TypeError(f"{obj.__name__} must inherit from {expected.__name__}")

        if self.del_unused_app_cmd:
            log.warning(
                "As `delete_unused_application_cmds` is enabled, the client must cache all guilds app-commands, this could take a while."
            )

        if Intents.GUILDS not in self._connection_state.intents:
            log.warning("GUILD intent has not been enabled; this is very likely to cause errors")

        if self.fetch_members and Intents.GUILD_MEMBERS not in self._connection_state.intents:
            raise BotException("Members Intent must be enabled in order to use fetch members")
        elif self.fetch_members:
            log.warning("fetch_members enabled; startup will be delayed")

        if len(self.processors) == 0:
            log.warning("No Processors are loaded! This means no events will be processed!")

    async def generate_prefixes(self, bot: "Snake", message: Message) -> str | Iterable[str]:
        """
        A method to get the bot's default_prefix, can be overridden to add dynamic prefixes.

        !!! note
            To easily override this method, simply use the `generate_prefixes` parameter when instantiating the client

        Args:
            bot: A reference to the client
            message: A message to determine the prefix from.

        Returns:
            A string or an iterable of strings to use as a prefix. By default, this will return `client.default_prefix`

        """
        return self.default_prefix

    def _queue_task(self, coro: Listener, event: BaseEvent, *args, **kwargs) -> asyncio.Task:
        async def _async_wrap(_coro: Listener, _event: BaseEvent, *_args, **_kwargs) -> None:
            try:
                if len(_event.__attrs_attrs__) == 2:
                    # override_name & bot
                    await _coro()
                else:
                    await _coro(_event, *_args, **_kwargs)
            except asyncio.CancelledError:
                pass
            except Exception as e:
                await self.on_error(event, e)

        wrapped = _async_wrap(coro, event, *args, **kwargs)

        return asyncio.create_task(wrapped, name=f"snake:: {event.resolved_name}")

    @staticmethod
    def default_error_handler(source: str, error: BaseException) -> None:
        """
        The default error logging behaviour.

        Args:
            source: The source of this error
            error: The exception itself

        """
        out = traceback.format_exception(error)

        if isinstance(error, HTTPException):
            # HTTPException's are of 3 known formats, we can parse them for human readable errors
            try:
                errors = error.search_for_message(error.errors)
                out = f"HTTPException: {error.status}|{error.response.reason}: " + "\n".join(errors)
            except Exception:  # noqa : S110
                pass

        log.error(
            "Ignoring exception in {}:{}{}".format(source, "\n" if len(out) > 1 else " ", "".join(out)),
        )

    async def on_error(self, source: str, error: Exception, *args, **kwargs) -> None:
        """
        Catches all errors dispatched by the library.

        By default it will format and print them to console

        Override this to change error handling behaviour

        """
        self.default_error_handler(source, error)

    async def on_command_error(self, ctx: Context, error: Exception, *args, **kwargs) -> None:
        """
        Catches all errors dispatched by commands.

        By default it will call `Snake.on_error`

        Override this to change error handling behavior

        """
        return await self.on_error(f"cmd /`{ctx.invoked_name}`", error, *args, **kwargs)

    async def on_command(self, ctx: Context) -> None:
        """
        Called *after* any command is ran.

        By default, it will simply log the command, override this to change that behaviour

        Args:
            ctx: The context of the command that was called

        """
        if isinstance(ctx, MessageContext):
            symbol = "@"
        elif isinstance(ctx, InteractionContext):
            symbol = "/"
        else:
            symbol = "?"  # likely custom context
        log.info(f"Command Called: {symbol}{ctx.invoked_name} with {ctx.args = } | {ctx.kwargs = }")

    async def on_component_error(self, ctx: ComponentContext, error: Exception, *args, **kwargs) -> None:
        """
        Catches all errors dispatched by components.

        By default it will call `Snake.on_error`

        Override this to change error handling behavior

        """
        return await self.on_error(f"Component Callback for {ctx.custom_id}", error, *args, **kwargs)

    async def on_component(self, ctx: ComponentContext) -> None:
        """
        Called *after* any component callback is ran.

        By default, it will simply log the component use, override this to change that behaviour

        Args:
            ctx: The context of the component that was called

        """
        symbol = "¢"
        log.info(f"Component Called: {symbol}{ctx.invoked_name} with {ctx.args = } | {ctx.kwargs = }")

    async def on_autocomplete_error(self, ctx: AutocompleteContext, error: Exception, *args, **kwargs) -> None:
        """
        Catches all errors dispatched by autocompletion options.

        By default it will call `Snake.on_error`

        Override this to change error handling behavior

        """
        return await self.on_error(
            f"Autocomplete Callback for /{ctx.invoked_name} - Option: {ctx.focussed_option}",
            error,
            *args,
            **kwargs,
        )

    async def on_autocomplete(self, ctx: AutocompleteContext) -> None:
        """
        Called *after* any autocomplete callback is ran.

        By default, it will simply log the autocomplete callback, override this to change that behaviour

        Args:
            ctx: The context of the command that was called

        """
        symbol = "$"
        log.info(f"Autocomplete Called: {symbol}{ctx.invoked_name} with {ctx.args = } | {ctx.kwargs = }")

    @Listener.create()
    async def on_resume(self) -> None:
        self._ready.set()

    @Listener.create()
    async def _on_websocket_ready(self, event: events.RawGatewayEvent) -> None:
        """
        Catches websocket ready and determines when to dispatch the client `READY` signal.

        Args:
            event: The websocket ready packet

        """
        data = event.data
        expected_guilds = {to_snowflake(guild["id"]) for guild in data["guilds"]}
        self._user._add_guilds(expected_guilds)

        while True:
            try:  # wait to let guilds cache
                await asyncio.wait_for(self._guild_event.wait(), self.guild_event_timeout)
                if self.fetch_members:
                    # ensure all guilds have completed chunking
                    for guild in self.guilds:
                        if guild and not guild.chunked.is_set():
                            log.debug(f"Waiting for {guild.id} to chunk")
                            await guild.chunked.wait()

            except asyncio.TimeoutError:
                log.warning("Timeout waiting for guilds cache: Not all guilds will be in cache")
                break
            self._guild_event.clear()

            if len(self.cache.guild_cache) == len(expected_guilds):
                # all guilds cached
                break

        # cache slash commands
        if not self._startup:
            await self._init_interactions()

        self._ready.set()
        if not self._startup:
            self._startup = True
            self.dispatch(events.Startup())
        self.dispatch(events.Ready())

    async def login(self, token) -> None:
        """
        Login to discord via http.

        !!! note
            You will need to run Snake.start_gateway() before you start receiving gateway events.

        Args:
            token str: Your bot's token

        """
        # i needed somewhere to put this call,
        # login will always run after initialisation
        # so im gathering commands here
        self._gather_commands()

        log.debug("Attempting to login")
        me = await self.http.login(token.strip())
        self._user = SnakeBotUser.from_dict(me, self)
        self.cache.place_user_data(me)
        self._app = Application.from_dict(await self.http.get_current_bot_information(), self)
        self._mention_reg = re.compile(rf"^(<@!?{self.user.id}*>\s)")
        self.dispatch(events.Login())

    async def astart(self, token) -> None:
        """
        Asynchronous method to start the bot.

        Args:
            token: Your bot's token

        Returns:

        """
        await self.login(token)
        try:
            await self._connection_state.start()
        finally:
            await self.stop()

    def start(self, token) -> None:
        """
        Start the bot.

        info:
            This is the recommended method to start the bot

        Args:
            token: Your bot's token

        """
        try:
            asyncio.run(self.astart(token))
        except KeyboardInterrupt:
            # ignore, cus this is useless and can be misleading to the
            # user
            pass

    async def start_gateway(self) -> None:
        """Starts the gateway connection."""
        try:
            await self._connection_state.start()
        finally:
            await self.stop()

    async def stop(self) -> None:
        """Shutdown the bot."""
        log.debug("Stopping the bot.")
        self._ready.clear()
        await self.http.close()
        await self._connection_state.stop()

    def dispatch(self, event: events.BaseEvent, *args, **kwargs) -> None:
        """
        Dispatch an event.

        Args:
            event: The event to be dispatched.

        """
        listeners = self.listeners.get(event.resolved_name, [])
        if listeners:
            log.debug(f"Dispatching Event: {event.resolved_name}")
            event.bot = self
            for _listen in listeners:
                try:
                    self._queue_task(_listen, event, *args, **kwargs)
                except Exception as e:
                    raise BotException(
                        f"An error occurred attempting during {event.resolved_name} event processing"
                    ) from e

        _waits = self.waits.get(event.resolved_name, [])
        if _waits:
            index_to_remove = []
            for i, _wait in enumerate(_waits):
                result = _wait(event)
                if result:
                    index_to_remove.append(i)

            for idx in sorted(index_to_remove, reverse=True):
                _waits.pop(idx)

    async def wait_until_ready(self) -> None:
        """Waits for the client to become ready."""
        await self._ready.wait()

    def wait_for(
        self,
        event: Union[str, "BaseEvent"],
        checks: Absent[Optional[Callable[..., bool]]] = MISSING,
        timeout: Optional[float] = None,
    ) -> Any:
        """
        Waits for a WebSocket event to be dispatched.

        Args:
            event: The name of event to wait.
            checks: A predicate to check what to wait for.
            timeout: The number of seconds to wait before timing out.

        Returns:
            The event object.

        """
        event = get_event_name(event)

        if event not in self.waits:
            self.waits[event] = []

        future = asyncio.Future()
        self.waits[event].append(Wait(event, checks, future))

        return asyncio.wait_for(future, timeout)

    async def wait_for_modal(
        self,
        modal: "Modal",
        author: Optional["Snowflake_Type"] = None,
        timeout: Optional[float] = None,
    ) -> ModalContext:
        """
        Wait for a modal response.

        Args:
            modal: The modal we're waiting for.
            author: The user we're waiting for to reply
            timeout: A timeout in seconds to stop waiting

        Returns:
            The context of the modal response

        Raises:
            `asyncio.TimeoutError` if no response is received that satisfies the predicate before timeout seconds have passed

        """
        author = to_snowflake(author) if author else None

        def predicate(event) -> bool:
            if modal.custom_id != event.context.custom_id:
                return False
            if author and author != to_snowflake(event.context.author):
                return False
            return True

        resp = await self.wait_for("modal_response", predicate, timeout)
        return resp.context

    async def wait_for_component(
        self,
        messages: Union[Message, int, list] = None,
        components: Optional[
            Union[List[List[Union["BaseComponent", dict]]], List[Union["BaseComponent", dict]], "BaseComponent", dict]
        ] = None,
        check: Optional[Callable] = None,
        timeout: Optional[float] = None,
    ) -> "Component":
        """
        Waits for a component to be sent to the bot.

        Args:
            messages: The message object to check for.
            components: The components to wait for.
            check: A predicate to check what to wait for.
            timeout: The number of seconds to wait before timing out.

        Returns:
            `Component` that was invoked. Use `.context` to get the `ComponentContext`.

        Raises:
            `asyncio.TimeoutError` if timed out

        """
        if not (messages or components):
            raise ValueError("You must specify messages or components (or both)")

        message_ids = (
            to_snowflake_list(messages) if isinstance(messages, list) else to_snowflake(messages) if messages else None
        )
        custom_ids = list(get_components_ids(components)) if components else None

        # automatically convert improper custom_ids
        if custom_ids and not all(isinstance(x, str) for x in custom_ids):
            custom_ids = [str(i) for i in custom_ids]

        def _check(event: Component) -> bool:
            ctx: ComponentContext = event.context
            # if custom_ids is empty or there is a match
            wanted_message = not message_ids or ctx.message.id in (
                [message_ids] if isinstance(message_ids, int) else message_ids
            )
            wanted_component = not custom_ids or ctx.custom_id in custom_ids
            if wanted_message and wanted_component:
                if check is None or check(event):
                    return True
                return False
            return False

        return await self.wait_for("component", checks=_check, timeout=timeout)

    def listen(self, event_name: Absent[str] = MISSING) -> Listener:
        """
        A decorator to be used in situations that snek can't automatically hook your listeners. Ideally, the standard listen decorator should be used, not this.

        Args:
            event_name: The event name to use, if not the coroutine name

        Returns:
            A listener that can be used to hook into the event.

        """

        def wrapper(coro: Callable[..., Coroutine]) -> Listener:
            listener = Listener.create(event_name)(coro)
            self.add_listener(listener)
            return listener

        return wrapper

    def add_event_processor(self, event_name: Absent[str] = MISSING) -> Callable[..., Coroutine]:
        """
        A decorator to be used to add event processors.

        Args:
            event_name: The event name to use, if not the coroutine name

        Returns:
            A function that can be used to hook into the event.

        """

        def wrapper(coro: Callable[..., Coroutine]) -> Callable[..., Coroutine]:
            name = event_name
            if name is MISSING:
                name = coro.__name__
            name = name.lstrip("_")
            name = name.removeprefix("on_")
            self.processors[name] = coro
            return coro

        return wrapper

    def add_listener(self, listener: Listener) -> None:
        """
        Add a listener for an event, if no event is passed, one is determined.

        Args:
            listener Listener: The listener to add to the client

        """
        if listener.event not in self.listeners:
            self.listeners[listener.event] = []
        self.listeners[listener.event].append(listener)

    def add_interaction(self, command: InteractionCommand) -> bool:
        """
        Add a slash command to the client.

        Args:
            command InteractionCommand: The command to add

        """
        if self.debug_scope:
            command.scopes = [self.debug_scope]

        # for SlashCommand objs without callback (like objects made to hold group info etc)
        if command.callback is None:
            return False

        for scope in command.scopes:
            if scope not in self.interactions:
                self.interactions[scope] = {}
            elif command.resolved_name in self.interactions[scope]:
                old_cmd = self.interactions[scope][command.resolved_name]
                raise ValueError(f"Duplicate Command! {scope}::{old_cmd.resolved_name}")

            if self.enforce_interaction_perms:
                command.checks.append(command._permission_enforcer)  # noqa : w0212

            self.interactions[scope][command.resolved_name] = command

        return True

    def add_message_command(self, command: MessageCommand) -> None:
        """
        Add a message command to the client.

        Args:
            command InteractionCommand: The command to add

        """
        if command.name not in self.commands:
            self.commands[command.name] = command
            return
        raise ValueError(f"Duplicate Command! Multiple commands share the name `{command.name}`")

    def add_component_callback(self, command: ComponentCommand) -> None:
        """
        Add a component callback to the client.

        Args:
            command: The command to add

        """
        for listener in command.listeners:
            # I know this isn't an ideal solution, but it means we can lookup callbacks with O(1)
            if listener not in self._component_callbacks.keys():
                self._component_callbacks[listener] = command
                continue
            else:
                raise ValueError(f"Duplicate Component! Multiple component callbacks for `{listener}`")

    def _gather_commands(self) -> None:
        """Gathers commands from __main__ and self."""

        def process(_cmds) -> None:

            for func in _cmds:
                if isinstance(func, ComponentCommand):
                    self.add_component_callback(func)
                elif isinstance(func, InteractionCommand):
                    self.add_interaction(func)
                elif isinstance(func, MessageCommand):
                    self.add_message_command(func)
                elif isinstance(func, Listener):
                    self.add_listener(func)

            log.debug(f"{len(_cmds)} commands have been loaded from `__main__` and `client`")

        process(
            [obj for _, obj in inspect.getmembers(sys.modules["__main__"]) if isinstance(obj, (BaseCommand, Listener))]
        )
        process(
            [wrap_partial(obj, self) for _, obj in inspect.getmembers(self) if isinstance(obj, (BaseCommand, Listener))]
        )

        [wrap_partial(obj, self) for _, obj in inspect.getmembers(self) if isinstance(obj, Task)]

    async def _init_interactions(self) -> None:
        """
        Initialise slash commands.

        If `sync_interactions` this will submit all registered slash
        commands to discord. Otherwise, it will get the list of
        interactions and cache their scopes.

        """
        # allow for cogs and main to share the same decorator
        try:
            if self.sync_interactions:
                await self.synchronise_interactions()
            else:
                await self._cache_interactions(warn_missing=False)
        except Exception as e:
            await self.on_error("Interaction Syncing", e)

    async def _cache_interactions(self, warn_missing: bool = False) -> None:
        """Get all interactions used by this bot and cache them."""
        if warn_missing or self.del_unused_app_cmd:
            bot_scopes = {g.id for g in self.cache.guild_cache.values()}
            bot_scopes.add(GLOBAL_SCOPE)
        else:
            bot_scopes = set(self.interactions)

        req_lock = asyncio.Lock()

        async def wrap(*args, **kwargs) -> Absent[List[Dict]]:
            async with req_lock:
                # throttle this
                await asyncio.sleep(0.1)
            try:
                return await self.http.get_application_commands(*args, **kwargs)
            except Forbidden:
                return MISSING

        results = await asyncio.gather(*[wrap(self.app.id, scope) for scope in bot_scopes])
        results = dict(zip(bot_scopes, results))

        for scope, remote_cmds in results.items():
            if remote_cmds == MISSING:
                log.debug(f"Bot was not invited to guild {scope} with `application.commands` scope")
                continue

            remote_cmds = {cmd_data["name"]: cmd_data for cmd_data in remote_cmds}
            found = set()  # this is a temporary hack to fix subcommand detection
            if scope in self.interactions:
                for cmd in self.interactions[scope].values():
                    cmd_data = remote_cmds.get(cmd.name, MISSING)
                    if cmd_data is MISSING:
                        if cmd.name not in found:
                            if warn_missing:
                                log.error(
                                    f'Detected yet to sync slash command "/{cmd.name}" for scope '
                                    f"{'global' if scope == GLOBAL_SCOPE else scope}"
                                )
                        continue
                    else:
                        found.add(cmd.name)
                    self._interaction_scopes[str(cmd_data["id"])] = scope
                    cmd.cmd_id[scope] = int(cmd_data["id"])

            if warn_missing:
                for cmd_data in remote_cmds.values():
                    log.error(
                        f"Detected unimplemented slash command \"/{cmd_data['name']}\" for scope "
                        f"{'global' if scope == GLOBAL_SCOPE else scope}"
                    )

    async def synchronise_interactions(self) -> None:
        """Synchronise registered interactions with discord."""
        s = time.perf_counter()
        await self._cache_interactions()

        if self.del_unused_app_cmd:
            # if we're deleting unused commands, we check all scopes
            cmd_scopes = [to_snowflake(g_id) for g_id in self._user._guild_ids] + [GLOBAL_SCOPE]
        else:
            # if we're not deleting, just check the scopes we have cmds registered in
            cmd_scopes = list(set(self.interactions) | {GLOBAL_SCOPE})

        guild_perms = {}
        local_cmds_json = application_commands_to_dict(self.interactions)

        async def sync_scope(cmd_scope) -> None:

            sync_needed_flag = False  # a flag to force this scope to synchronise
            sync_payload = []  # the payload to be pushed to discord

            try:
                try:
                    remote_commands = await self.http.get_application_commands(self.app.id, cmd_scope)
                except Forbidden:
                    log.warning(f"Bot is lacking `application.commands` scope in {cmd_scope}!")
                    return

                for local_cmd in self.interactions.get(cmd_scope, {}).values():
                    # get remote equivalent of this command
                    remote_cmd_json = next(
                        (v for v in remote_commands if int(v["id"]) == local_cmd.cmd_id.get(cmd_scope)), None
                    )
                    # get json representation of this command
                    local_cmd_json = next((c for c in local_cmds_json[cmd_scope] if c["name"] == local_cmd.name))

                    # this works by adding any command we *want* on Discord, to a payload, and synchronising that
                    # this allows us to delete unused commands, add new commands, or do nothing in 1 or less API calls

                    if sync_needed(local_cmd_json, remote_cmd_json):
                        # determine if the local and remote commands are out-of-sync
                        sync_needed_flag = True
                        sync_payload.append(local_cmd_json)
                    elif not self.del_unused_app_cmd and remote_cmd_json:
                        _remote_payload = {
                            k: v for k, v in remote_cmd_json.items() if k not in ("id", "application_id", "version")
                        }
                        sync_payload.append(_remote_payload)
                    elif self.del_unused_app_cmd:
                        sync_payload.append(local_cmd_json)

                sync_payload = [json.loads(_dump) for _dump in {json.dumps(_cmd) for _cmd in sync_payload}]

                if sync_needed_flag or (self.del_unused_app_cmd and len(sync_payload) < len(remote_commands)):
                    # synchronise commands if flag is set, or commands are to be deleted
                    log.info(f"Overwriting {cmd_scope} with {len(sync_payload)} application commands")
                    sync_response: list[dict] = await self.http.overwrite_application_commands(
                        self.app.id, sync_payload, cmd_scope
                    )
                    self._cache_sync_response(sync_response, cmd_scope)
                else:
                    log.debug(f"{cmd_scope} is already up-to-date with {len(remote_commands)} commands.")

                for local_cmd in self.interactions.get(cmd_scope, {}).values():

                    if not local_cmd.permissions:
                        continue
                    for perm in local_cmd.permissions:
                        if perm.guild_id == cmd_scope:
                            if perm.guild_id not in guild_perms:
                                guild_perms[perm.guild_id] = []
                            payload = [perm.to_dict() for perm in local_cmd.permissions]
                            perm_json = {
                                "id": local_cmd.get_cmd_id(perm.guild_id),
                                "permissions": [dict(tup) for tup in {tuple(d.items()) for d in payload}],
                            }
                            if perm_json not in guild_perms[perm.guild_id]:
                                guild_perms[perm.guild_id].append(perm_json)

            except Forbidden as e:
                raise InteractionMissingAccess(cmd_scope) from e
            except HTTPException as e:
                self._raise_sync_exception(e, local_cmds_json, cmd_scope)

        await asyncio.gather(*[sync_scope(scope) for scope in cmd_scopes])

        for perm_scope in guild_perms:
            perms_to_sync = {}
            for cmd in guild_perms[perm_scope]:
                c = self.get_application_cmd_by_id(cmd["id"])

                if len(cmd["permissions"]) > 10:
                    log.error(
                        f"Error in command `{c.name}`: Command has {len(cmd['permissions'])} permissions. Maximum is 10 per guild."
                    )

                try:
                    remote_perms = await self.http.get_application_command_permissions(
                        self.app.id, perm_scope, c.get_cmd_id(perm_scope)
                    )
                except HTTPException:
                    remote_perms = {}
                cmd_perms = [perm for perm in guild_perms[perm_scope] if perm["id"] == c.get_cmd_id(perm_scope)][0]
                perms_to_sync[c.get_cmd_id(perm_scope)] = [
                    perm for perm in cmd_perms["permissions"] if perm not in remote_perms.get("permissions", [])
                ]
            perms_to_sync = [cmd for cmd in perms_to_sync.values() if cmd]
            if perms_to_sync:
                try:
                    log.debug(f"Updating {len(guild_perms[perm_scope])} command permissions in {perm_scope}")
                    await self.http.batch_edit_application_command_permissions(
                        application_id=self.app.id, scope=perm_scope, data=guild_perms[perm_scope]
                    )
                except Forbidden:
                    log.error(
                        f"Unable to sync permissions for guild `{perm_scope}` -- Ensure the bot was added to that guild with `application.commands` scope."
                    )
                except HTTPException as e:
                    self._raise_sync_exception(e, local_cmds_json, perm_scope)
            else:
                log.debug(f"Permissions in {perm_scope} are already up-to-date!")

        t = time.perf_counter() - s
        log.debug(f"Sync of {len(cmd_scopes)} scopes took {t} seconds")

    def get_application_cmd_by_id(self, cmd_id: "Snowflake_Type") -> Optional[InteractionCommand]:
        """
        Get a application command from the internal cache by its ID.

        Args:
            cmd_id: The ID of the command

        Returns:
            The command, if one with the given ID exists internally, otherwise None

        """
        scope = self._interaction_scopes.get(str(cmd_id), MISSING)
        cmd_id = int(cmd_id)  # ensure int ID
        if scope != MISSING:
            for cmd in self.interactions[scope].values():
                if int(cmd.cmd_id.get(scope)) == cmd_id:
                    return cmd
        return None

    @staticmethod
    def _raise_sync_exception(e: HTTPException, cmds_json: dict, cmd_scope: "Snowflake_Type") -> NoReturn:
        try:
            if isinstance(e.errors, dict):
                for cmd_num in e.errors.keys():
                    cmd = cmds_json[cmd_scope][int(cmd_num)]
                    output = e.search_for_message(e.errors[cmd_num], cmd)
                    if len(output) > 1:
                        output = "\n".join(output)
                        log.error(f"Multiple Errors found in command `{cmd['name']}`:\n{output}")
                    else:
                        log.error(f"Error in command `{cmd['name']}`: {output[0]}")
            else:
                raise e from None
        except Exception:
            # the above shouldn't fail, but if it does, just raise the exception normally
            raise e from None

    def _cache_sync_response(self, sync_response: list[dict], scope: "Snowflake_Type") -> None:
        for cmd_data in sync_response:
            self._interaction_scopes[cmd_data["id"]] = scope
            if cmd_data["name"] in self.interactions[scope]:
                self.interactions[scope][cmd_data["name"]].cmd_id[scope] = int(cmd_data["id"])
            else:
                # sub_cmd
                for sc in cmd_data["options"]:
                    if sc["type"] == OptionTypes.SUB_COMMAND:
                        if f"{cmd_data['name']} {sc['name']}" in self.interactions[scope]:
                            self.interactions[scope][f"{cmd_data['name']} {sc['name']}"].cmd_id[scope] = int(
                                cmd_data["id"]
                            )
                    elif sc["type"] == OptionTypes.SUB_COMMAND_GROUP:
                        for _sc in sc["options"]:
                            if f"{cmd_data['name']} {sc['name']} {_sc['name']}" in self.interactions[scope]:
                                self.interactions[scope][f"{cmd_data['name']} {sc['name']} {_sc['name']}"].cmd_id[
                                    scope
                                ] = int(cmd_data["id"])

    @overload
    async def get_context(self, data: ComponentChannelInteractionData, interaction: Literal[True]) -> ComponentContext:
        ...

    @overload
    async def get_context(
        self, data: AutocompleteChannelInteractionData, interaction: Literal[True]
    ) -> AutocompleteContext:
        ...

    # as of right now, discord_typings doesn't include anything like this
    # @overload
    # async def get_context(self, data: ModalSubmitInteractionData, interaction: Literal[True]) -> ModalContext:
    #     ...

    @overload
    async def get_context(self, data: InteractionData, interaction: Literal[True]) -> InteractionContext:
        ...

    @overload
    async def get_context(
        self, data: dict, interaction: Literal[True]
    ) -> ComponentContext | AutocompleteContext | ModalContext | InteractionContext:
        # fallback case since some data isn't typehinted properly
        ...

    @overload
    async def get_context(self, data: Message, interaction: Literal[False] = False) -> MessageContext:
        ...

    async def get_context(
        self, data: InteractionData | dict | Message, interaction: bool = False
    ) -> ComponentContext | AutocompleteContext | ModalContext | InteractionContext | MessageContext:
        """
        Return a context object based on data passed.

        note:
            If you want to use custom context objects, this is the method to override. Your replacement must take the same arguments as this, and return a Context-like object.

        Args:
            data: The data of the event
            interaction: Is this an interaction or not?

        Returns:
            Context object

        """
        # this line shuts up IDE warnings
        cls: ComponentContext | AutocompleteContext | ModalContext | InteractionContext | MessageContext

        if interaction:
            match data["type"]:
                case InteractionTypes.MESSAGE_COMPONENT:
                    cls = self.component_context.from_dict(data, self)

                case InteractionTypes.AUTOCOMPLETE:
                    cls = self.autocomplete_context.from_dict(data, self)

                case InteractionTypes.MODAL_RESPONSE:
                    cls = ModalContext.from_dict(data, self)

                case _:
                    cls = self.interaction_context.from_dict(data, self)

            if not cls.channel:
                cls.channel = await self.cache.fetch_channel(data["channel_id"])

        else:
            cls = self.message_context.from_message(self, data)
            if not cls.channel:
                cls.channel = await self.cache.fetch_channel(data._channel_id)

        return cls

    async def _run_slash_command(self, command: SlashCommand, ctx: InteractionContext) -> Any:
        """Overrideable method that executes slash commands, can be used to wrap callback execution"""
        return await command(ctx, **ctx.kwargs)

    async def _run_message_command(self, command: MessageCommand, ctx: MessageContext) -> Any:
        """Overrideable method that executes message commands, can be used to wrap callback execution"""
        return await command(ctx)

    @processors.Processor.define("raw_interaction_create")
    async def _dispatch_interaction(self, event: RawGatewayEvent) -> None:
        """
        Identify and dispatch interaction of slash commands or components.

        Args:
            raw interaction event

        """
        interaction_data = event.data

        if interaction_data["type"] in (
            InteractionTypes.PING,
            InteractionTypes.APPLICATION_COMMAND,
            InteractionTypes.AUTOCOMPLETE,
        ):
            interaction_id = interaction_data["data"]["id"]
            name = interaction_data["data"]["name"]
            scope = self._interaction_scopes.get(str(interaction_id))

            if scope in self.interactions:
                ctx = await self.get_context(interaction_data, True)

                command: SlashCommand = self.interactions[scope][ctx.invoked_name]  # type: ignore
                ctx.command = command
                log.debug(f"{scope} :: {command.name} should be called")

                if command.auto_defer:
                    auto_defer = command.auto_defer
                elif command.scale and command.scale.auto_defer:
                    auto_defer = command.scale.auto_defer
                else:
                    auto_defer = self.auto_defer

                if auto_opt := getattr(ctx, "focussed_option", None):
                    try:
                        await command.autocomplete_callbacks[auto_opt](ctx, **ctx.kwargs)
                    except Exception as e:
                        await self.on_autocomplete_error(ctx, e)
                    finally:
                        await self.on_autocomplete(ctx)
                else:
                    try:
                        await auto_defer(ctx)
                        if self.pre_run_callback:
                            await self.pre_run_callback(ctx, **ctx.kwargs)
                        await self._run_slash_command(command, ctx)
                        if self.post_run_callback:
                            await self.post_run_callback(ctx, **ctx.kwargs)
                    except Exception as e:
                        await self.on_command_error(ctx, e)
                    finally:
                        await self.on_command(ctx)
            else:
                log.error(f"Unknown cmd_id received:: {interaction_id} ({name})")

        elif interaction_data["type"] == InteractionTypes.MESSAGE_COMPONENT:
            # Buttons, Selects, ContextMenu::Message
            ctx = await self.get_context(interaction_data, True)
            component_type = interaction_data["data"]["component_type"]

            self.dispatch(events.Component(ctx))
            if callback := self._component_callbacks.get(ctx.custom_id):
                ctx.command = callback
                try:
                    if self.pre_run_callback:
                        await self.pre_run_callback(ctx)
                    await callback(ctx)
                    if self.post_run_callback:
                        await self.post_run_callback(ctx)
                except Exception as e:
                    await self.on_component_error(ctx, e)
                finally:
                    await self.on_component(ctx)
            if component_type == ComponentTypes.BUTTON:
                self.dispatch(events.Button(ctx))
            if component_type == ComponentTypes.SELECT:
                self.dispatch(events.Select(ctx))

        elif interaction_data["type"] == InteractionTypes.MODAL_RESPONSE:
            ctx = await self.get_context(interaction_data, True)
            self.dispatch(events.ModalResponse(ctx))
        else:
            raise NotImplementedError(f"Unknown Interaction Received: {interaction_data['type']}")

    @Listener.create("message_create")
    async def _dispatch_msg_commands(self, event: MessageCreate) -> None:
        """Determine if a command is being triggered, and dispatch it."""
        message = event.message

        if not message.content:
            return

        if not message.author.bot:
            prefixes = await self.generate_prefixes(self, message)

            if isinstance(prefixes, str) or prefixes == MENTION_PREFIX:
                # its easier to treat everything as if it may be an iterable
                # rather than building a special case for this
                prefixes = (prefixes,)

            prefix_used = None

            for prefix in prefixes:
                if prefix == MENTION_PREFIX:
                    mention = self._mention_reg.search(message.content)
                    if mention:
                        prefix = mention.group()
                    else:
                        continue

                if message.content.startswith(prefix):
                    prefix_used = prefix
                    break

            if prefix_used:
                invoked_name = get_first_word(message.content.removeprefix(prefix_used))
                command = self.commands.get(invoked_name)

                if command and command.enabled:
                    context = await self.get_context(message)
                    context.command = command
                    context.invoked_name = invoked_name
                    context.prefix = prefix_used
                    context.args = get_args(context.content_parameters)
                    try:
                        if self.pre_run_callback:
                            await self.pre_run_callback(context)
                        await self._run_message_command(command, context)
                        if self.post_run_callback:
                            await self.post_run_callback(context)
                    except Exception as e:
                        await self.on_command_error(context, e)
                    finally:
                        await self.on_command(context)

    @Listener.create("disconnect")
    async def _disconnect(self) -> None:
        self._ready.clear()

    def get_scale(self, name) -> Optional[Scale]:
        """
        Get a scale.

        Args:
            name: The name of the scale, or the name of it's extension

        Returns:
            Scale or None if no scale is found
        """
        if name not in self.scales.keys():
            for scale in self.scales.values():
                if scale.extension_name == name:
                    return scale

        return self.scales.get(name, None)

    def grow_scale(self, file_name: str, package: str = None) -> None:
        """
        A helper method to load a scale.

        Args:
            file_name: The name of the file to load the scale from.
            package: The package this scale is in.

        """
        self.load_extension(file_name, package)

    def shed_scale(self, scale_name: str) -> None:
        """
        Helper method to unload a scale.

        Args:
            scale_name: The name of the scale to unload.

        """
        if scale := self.get_scale(scale_name):
            return self.unload_extension(inspect.getmodule(scale).__name__)

        raise ScaleLoadException(f"Unable to shed scale: No scale exists with name: `{scale_name}`")

    def regrow_scale(self, scale_name: str) -> None:
        """
        Helper method to reload a scale.

        Args:
            scale_name: The name of the scale to reload

        """
        self.shed_scale(scale_name)
        self.grow_scale(scale_name)

    def load_extension(self, name: str, package: str = None) -> None:
        """
        Load an extension.

        Args:
            name: The name of the extension.
            package: The package the extension is in

        """
        name = importlib.util.resolve_name(name, package)
        if name in self.__extensions:
            raise Exception(f"{name} already loaded")

        module = importlib.import_module(name, package)
        try:
            setup = getattr(module, "setup", None)
            if not setup:
                raise ExtensionLoadException(
                    f"{name} lacks an entry point. Ensure you have a function called `setup` defined in that file"
                ) from None
            setup(self)
        except ExtensionLoadException:
            raise
        except Exception as e:
            del sys.modules[name]
            raise ExtensionLoadException(f"Unexpected Error loading {name}") from e

        else:
            log.debug(f"Loaded Extension: {name}")
            self.__extensions[name] = module
            return

    def unload_extension(self, name, package=None) -> None:
        """
        Unload an extension.

        Args:
            name: The name of the extension.
            package: The package the extension is in

        """
        name = importlib.util.resolve_name(name, package)
        module = self.__extensions.get(name)

        if module is None:
            raise ExtensionNotFound(f"No extension called {name} is loaded")

        try:
            teardown = getattr(module, "teardown")
            teardown()
        except AttributeError:
            pass

        if scale := self.get_scale(name):
            scale.shed()

        del sys.modules[name]
        del self.__extensions[name]

    def reload_extension(self, name, package=None) -> None:
        """
        Helper method to reload an extension. Simply unloads, then loads the extension.

        Args:
            name: The name of the extension.
            package: The package the extension is in

        """
        name = importlib.util.resolve_name(name, package)
        module = self.__extensions.get(name)

        if module is None:
            log.warning("Attempted to reload extension thats not loaded. Loading extension instead")
            return self.load_extension(name, package)

        self.unload_extension(name, package)
        self.load_extension(name, package)

        # todo: maybe add an ability to revert to the previous version if unable to load the new one

    async def fetch_guild(self, guild_id: "Snowflake_Type") -> Optional[Guild]:
        """
        Fetch a guild.

        Note:
            This method is an alias for the cache which will either return a cached object, or query discord for the object
            if its not already cached.

        Args:
            guild_id: The ID of the guild to get

        Returns:
            Guild Object if found, otherwise None

        """
        try:
            return await self.cache.fetch_guild(guild_id)
        except NotFound:
            return None

    def get_guild(self, guild_id: "Snowflake_Type") -> Optional[Guild]:
        """
        Get a guild.

        Note:
            This method is an alias for the cache which will return a cached object.

        Args:
            guild_id: The ID of the guild to get

        Returns:
            Guild Object if found, otherwise None

        """
        return self.cache.get_guild(guild_id)

    async def create_guild_from_template(
        self,
        template_code: Union["GuildTemplate", str],
        name: str,
        icon: Absent[UPLOADABLE_TYPE] = MISSING,
    ) -> Optional[Guild]:
        """
        Creates a new guild based on a template.

        note:
            This endpoint can only be used by bots in less than 10 guilds.

        Args:
            template_code: The code of the template to use.
            name: The name of the guild (2-100 characters)
            icon: Location or File of icon to set

        Returns:
            The newly created guild object

        """
        if isinstance(template_code, GuildTemplate):
            template_code = template_code.code

        if icon:
            icon = to_image_data(icon)
        guild_data = await self.http.create_guild_from_guild_template(template_code, name, icon)
        return Guild.from_dict(guild_data, self)

    async def fetch_channel(self, channel_id: "Snowflake_Type") -> Optional["TYPE_ALL_CHANNEL"]:
        """
        Fetch a channel.

        Note:
            This method is an alias for the cache which will either return a cached object, or query discord for the object
            if its not already cached.

        Args:
            channel_id: The ID of the channel to get

        Returns:
            Channel Object if found, otherwise None

        """
        try:
            return await self.cache.fetch_channel(channel_id)
        except NotFound:
            return None

    def get_channel(self, channel_id: "Snowflake_Type") -> Optional["TYPE_ALL_CHANNEL"]:
        """
        Get a channel.

        Note:
            This method is an alias for the cache which will return a cached object.

        Args:
            channel_id: The ID of the channel to get

        Returns:
            Channel Object if found, otherwise None

        """
        return self.cache.get_channel(channel_id)

    async def fetch_user(self, user_id: "Snowflake_Type") -> Optional[User]:
        """
        Fetch a user.

        Note:
            This method is an alias for the cache which will either return a cached object, or query discord for the object
            if its not already cached.

        Args:
            user_id: The ID of the user to get

        Returns:
            User Object if found, otherwise None

        """
        try:
            return await self.cache.fetch_user(user_id)
        except NotFound:
            return None

    def get_user(self, user_id: "Snowflake_Type") -> Optional[User]:
        """
        Get a user.

        Note:
            This method is an alias for the cache which will return a cached object.

        Args:
            user_id: The ID of the user to get

        Returns:
            User Object if found, otherwise None

        """
        return self.cache.get_user(user_id)

    async def fetch_member(self, user_id: "Snowflake_Type", guild_id: "Snowflake_Type") -> Optional[Member]:
        """
        Fetch a member from a guild.

        Note:
            This method is an alias for the cache which will either return a cached object, or query discord for the object
            if its not already cached.

        Args:
            user_id: The ID of the member
            guild_id: The ID of the guild to get the member from

        Returns:
            Member object if found, otherwise None

        """
        try:
            return await self.cache.fetch_member(guild_id, user_id)
        except NotFound:
            return None

    def get_member(self, user_id: "Snowflake_Type", guild_id: "Snowflake_Type") -> Optional[Member]:
        """
        Get a member from a guild.

        Note:
            This method is an alias for the cache which will return a cached object.

        Args:
            user_id: The ID of the member
            guild_id: The ID of the guild to get the member from

        Returns:
            Member object if found, otherwise None

        """
        return self.cache.get_member(guild_id, user_id)

    async def fetch_scheduled_event(
        self, guild_id: "Snowflake_Type", scheduled_event_id: "Snowflake_Type", with_user_count: bool = False
    ) -> Optional["ScheduledEvent"]:
        """
        Fetch a scheduled event by id.

        Args:
            event_id: The id of the scheduled event.

        Returns:
            The scheduled event if found, otherwise None

        """
        try:
            scheduled_event_data = await self.http.get_scheduled_event(guild_id, scheduled_event_id, with_user_count)
            return ScheduledEvent.from_dict(scheduled_event_data, self)
        except NotFound:
            return None

    async def fetch_custom_emoji(self, emoji_id: "Snowflake_Type", guild_id: "Snowflake_Type") -> Optional[CustomEmoji]:
        """
        Fetch a custom emoji by id.

        Args:
            emoji_id: The id of the custom emoji.
            guild_id: The id of the guild the emoji belongs to.

        Returns:
            The custom emoji if found, otherwise None.

        """
        try:
            return await self.cache.fetch_emoji(guild_id, emoji_id)
        except NotFound:
            return None

    def get_custom_emoji(
        self, emoji_id: "Snowflake_Type", guild_id: Optional["Snowflake_Type"] = None
    ) -> Optional[CustomEmoji]:
        """
        Get a custom emoji by id.

        Args:
            emoji_id: The id of the custom emoji.
            guild_id: The id of the guild the emoji belongs to.

        Returns:
            The custom emoji if found, otherwise None.

        """
        emoji = self.cache.get_emoji(emoji_id)
        if emoji and (not guild_id or emoji._guild_id == to_snowflake(guild_id)):
            return emoji
        return None

    async def fetch_sticker(self, sticker_id: "Snowflake_Type") -> Optional[Sticker]:
        """
        Fetch a sticker by ID.

        Args:
            sticker_id: The ID of the sticker.

        Returns:
            A sticker object if found, otherwise None

        """
        try:
            sticker_data = await self.http.get_sticker(sticker_id)
            return Sticker.from_dict(sticker_data, self)
        except NotFound:
            return None

    async def fetch_nitro_packs(self) -> Optional[List["StickerPack"]]:
        """
        List the sticker packs available to Nitro subscribers.

        Returns:
            A list of StickerPack objects if found, otherwise returns None

        """
        try:
            packs_data = await self.http.list_nitro_sticker_packs()
            packs = []
            for pack_data in packs_data:
                packs.append(StickerPack.from_dict(pack_data, self))
            return packs
        except NotFound:
            return None

    async def fetch_voice_regions(self) -> List["VoiceRegion"]:
        """
        List the voice regions available on Discord.

        Returns:
            A list of voice regions.

        """
        regions_data = await self.http.list_voice_regions()
        regions = VoiceRegion.from_list(regions_data)
        return regions

    async def connect_to_vc(
        self, guild_id: "Snowflake_Type", channel_id: "Snowflake_Type", muted: bool = False, deafened: bool = False
    ) -> ActiveVoiceState:
        """
        Connect the bot to a voice channel.

        Args:
            guild_id: id of the guild the voice channel is in.
            channel_id: id of the voice channel client wants to join.
            muted: Whether the bot should be muted when connected.
            deafened: Whether the bot should be deafened when connected.

        Returns:
            The new active voice state on successfully connection.

        """
        return await self._connection_state.voice_connect(guild_id, channel_id, muted, deafened)

    def get_bot_voice_state(self, guild_id: "Snowflake_Type") -> Optional[ActiveVoiceState]:
        """
        Get the bot's voice state for a guild.

        Args:
            guild_id: The target guild's id.

        Returns:
            The bot's voice state for the guild if connected, otherwise None.

        """
        return self._connection_state.get_voice_state(guild_id)

    async def change_presence(
        self, status: Optional[Union[str, Status]] = Status.ONLINE, activity: Optional[Union[Activity, str]] = None
    ) -> None:
        """
        Change the bots presence.

        Args:
            status: The status for the bot to be. i.e. online, afk, etc.
            activity: The activity for the bot to be displayed as doing.

        Note::
            Bots may only be `playing` `streaming` `listening` `watching` or `competing`, other activity types are likely to fail.

        """
        await self._connection_state.change_presence(status, activity)
