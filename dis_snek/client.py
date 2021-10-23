import asyncio
import importlib.util
import inspect
import logging
import sys
import traceback
from typing import TYPE_CHECKING, Callable, Coroutine, Dict, List, Optional, Union

import aiohttp

from dis_snek.const import logger_name, GLOBAL_SCOPE, MISSING
from dis_snek.errors import (
    GatewayNotFound,
    SnakeException,
    WebSocketClosed,
    WebSocketRestart,
    BotException,
    ScaleLoadException,
    ExtensionLoadException,
    ExtensionNotFound,
    Forbidden,
    InteractionMissingAccess,
)
from dis_snek.event_processors import *
from dis_snek.gateway import WebsocketClient
from dis_snek.http_client import HTTPClient
from dis_snek.models import (
    Activity,
    Application,
    Guild,
    Listener,
    listen,
    Message,
    Scale,
    SnakeBotUser,
    User,
    Member,
    StickerPack,
    Sticker,
    events,
    InteractionCommand,
    SlashCommand,
    OptionTypes,
    MessageCommand,
    BaseCommand,
    to_snowflake,
    ComponentContext,
    InteractionContext,
    MessageContext,
    AutocompleteContext,
    ComponentCommand,
)
from dis_snek.models.enums import ComponentTypes, Intents, InteractionTypes, Status, ActivityType
from dis_snek.models.events import RawGatewayEvent, MessageCreate
from dis_snek.smart_cache import GlobalCache
from dis_snek.utils.cache import TTLCache
from dis_snek.utils.input_utils import get_first_word
from dis_snek.utils.misc_utils import wrap_partial

if TYPE_CHECKING:
    from dis_snek.models import Snowflake_Type, TYPE_ALL_CHANNEL

log = logging.getLogger(logger_name)


class Snake(
    ChannelEvents,
    GuildEvents,
    MemberEvents,
    MessageEvents,
    ReactionEvents,
    RoleEvents,
    StageEvents,
    ThreadEvents,
    UserEvents,
):
    """
    The bot client.

    note:
        By default, all non-privileged intents will be enabled

    Attributes:
        intents Union[int, Intents]: The intents to use
        loop: An event loop to use, normally leave this blank
        default_prefix str: The default_prefix to use for message commands, defaults to `.`
        get_prefix Callable[..., Coroutine]: A coroutine that returns a string to determine prefixes
        sync_interactions bool: Should application commands be synced with discord?
        delete_unused_application_cmds bool: Delete any commands from discord that arent implemented in this client
        asyncio_debug bool: Enable asyncio debug features
        message_cache_ttl int: How long a message will remain in the cache, set to `None` to disable cache expiry
        message_cache_size int: The maximum number of messages that may be stored in the cache, set to `None` to not limit cache size
        status Status: The status the bot should login with (IE ONLINE, DND, IDLE)
        activity Activity: The activity the bot should login "playing"

    !!! note
        Setting message_cache_size to None is not recommended, as it could result in extremely high memory usage, we suggest a sane limit.

    """

    def __init__(
        self,
        intents: Union[int, Intents] = Intents.DEFAULT,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        default_prefix: str = ".",
        get_prefix: Callable[..., Coroutine] = MISSING,
        sync_interactions: bool = False,
        delete_unused_application_cmds: bool = False,
        asyncio_debug: bool = False,
        message_cache_ttl: Optional[int] = 600,
        message_cache_limit: Optional[int] = 250,
        status: Status = Status.ONLINE,
        activity: Union[Activity, str] = None,
    ):

        self.loop: asyncio.AbstractEventLoop = asyncio.get_event_loop() if loop is None else loop

        # Configuration

        if asyncio_debug:
            log.warning("Asyncio Debug is enabled, Your log will contain additional errors and warnings")
            import tracemalloc

            tracemalloc.start()
            self.loop.set_debug(True)

        self.intents = intents
        """The intents in use"""
        self.sync_interactions = sync_interactions
        """Should application commands be synced"""
        self.del_unused_app_cmd: bool = delete_unused_application_cmds
        """Should unused application commands be deleted?"""
        self.default_prefix = default_prefix
        """The default prefix to be used for message commands"""
        self.get_prefix = get_prefix if get_prefix is not MISSING else self.get_prefix
        """A coroutine that returns a prefix, for dynamic prefixes"""

        # resources

        self.http: HTTPClient = HTTPClient(loop=self.loop)
        """The HTTP client to use when interacting with discord endpoints"""
        self.ws: WebsocketClient = MISSING
        """The websocket collection for the Discord Gateway."""

        # flags
        self._ready = False
        self._closed = False
        self._guild_event = asyncio.Event()
        self.guild_event_timeout = 3
        """How long to wait for guilds to be cached"""

        # caches
        self.cache: GlobalCache = GlobalCache(self)
        # these store the last sent presence data for change_presence
        self._status: Status = status
        if isinstance(activity, str):
            self._activity = Activity.create(name=str(activity))
        else:
            self._activity: Activity = activity

        if message_cache_limit is None and message_cache_ttl is None:
            log.warning("NO MESSAGE CACHE LIMITS ARE ACTIVE! This is not recommended")
            self.cache.message_cache = dict()
        else:
            self.cache.message_cache = TTLCache(hard_limit=message_cache_limit, ttl=message_cache_ttl or float("inf"))

        self._user: SnakeBotUser = MISSING
        self._app: Application = MISSING

        # collections

        self.commands: Dict[str, MessageCommand] = {}
        """A dictionary of registered commands: `{name: command}`"""
        self.interactions: Dict["Snowflake_Type", Dict[str, InteractionCommand]] = {}
        """A dictionary of registered application commands: `{cmd_id: command}`"""
        self._component_callbacks: Dict[str, Callable[..., Coroutine]] = {}
        self._interaction_scopes: Dict["Snowflake_Type", "Snowflake_Type"] = {}
        self.__extensions = {}
        self.scales = {}
        """A dictionary of mounted Scales"""
        self.listeners: Dict[str, List] = {}

    @property
    def is_closed(self) -> bool:
        """Is the bot closed?"""
        return self._closed

    @property
    def is_ready(self):
        return self._ready

    @property
    def latency(self) -> float:
        """Returns the latency of the websocket connection"""
        return self.ws.latency

    @property
    def user(self) -> SnakeBotUser:
        """Returns the bot's user"""
        return self._user

    @property
    def app(self) -> Application:
        """Returns the bots application"""
        return self._app

    @property
    def owner(self) -> Optional["User"]:
        """Returns the bot's owner'"""
        try:
            return self.app.owner
        except TypeError:
            return MISSING

    @property
    def guilds(self) -> List["Guild"]:
        return self.user.guilds

    @property
    def status(self) -> Status:
        """Get the status of the bot. IE online, afk, dnd"""
        return self._status

    @property
    def activity(self) -> Activity:
        """Get the activity of the bot"""
        return self._activity

    async def get_prefix(self, message: Message) -> str:
        """A method to get the bot's default_prefix, can be overridden to add dynamic prefixes.

        !!! note
            To easily override this method, simply use the `get_prefix` parameter when instantiating the client

        Args:
            message: A message to determine the prefix from.

        Returns:
            A string to use as a prefix, by default will return `client.default_prefix`
        """
        return self.default_prefix

    async def login(self, token):
        """
        Login to discord

        Args:
            token str: Your bot's token
        """
        # i needed somewhere to put this call,
        # login will always run after initialisation
        # so im gathering commands here
        self._gather_commands()

        log.debug(f"Logging in with token: {token}")
        me = await self.http.login(token.strip())
        self._user = SnakeBotUser.from_dict(me, self)
        self.cache.place_user_data(me)
        self._app = Application.from_dict(await self.http.get_current_bot_information(), self)
        self.dispatch(events.Login())
        await self._ws_connect()

    async def _ws_connect(self):
        params = {
            "http": self.http,
            "dispatch": self.dispatch,
            "intents": self.intents,
            "resume": False,
            "session_id": None,
            "sequence": None,
            "presence": {"status": self._status, "activities": [self._activity.to_dict()] if self._activity else []},
        }
        while not self.is_closed:
            log.info(f"Attempting to {'re' if params['resume'] else ''}connect to gateway...")

            try:
                self.ws = await WebsocketClient.connect(**params)

                await self.ws.run()
            except WebSocketRestart as ex:
                # internally requested restart
                self.dispatch(events.Disconnect())
                if ex.resume:
                    params.update(resume=True, session_id=self.ws.session_id, sequence=self.ws.sequence)
                    continue
                params.update(resume=False, session_id=None, sequence=None)

            except (OSError, GatewayNotFound, aiohttp.ClientError, asyncio.TimeoutError, WebSocketClosed) as ex:
                self.dispatch(events.Disconnect())

                if isinstance(ex, WebSocketClosed):
                    if ex.code == 1000:
                        # clean close
                        return
                    elif ex.code == 4011:
                        raise SnakeException("Your bot is too large, you must use shards") from None
                    elif ex.code == 4013:
                        raise SnakeException("Invalid Intents have been passed") from None
                    elif ex.code == 4014:
                        raise SnakeException(
                            "You have requested privileged intents that have not been enabled or approved. Check the developer dashboard"
                        ) from None
                    raise

                if isinstance(ex, OSError) and ex.errno in (54, 10054):
                    print("should reconnect")
                    params.update(resume=True, session_id=self.ws.session_id, sequence=self.ws.sequence)
                    continue
                params.update(resume=False, session_id=None, sequence=None)

            except Exception as e:
                self.dispatch(events.Disconnect())
                log.error("".join(traceback.format_exception(type(e), e, e.__traceback__)))
                params.update(resume=False, session_id=None, sequence=None)

            await asyncio.sleep(5)

    def _queue_task(self, coro, event, *args, **kwargs):
        async def _async_wrap(_coro, _event, *_args, **_kwargs):
            try:
                if len(_event.__attrs_attrs__) == 1:
                    await _coro()
                else:
                    await _coro(_event, *_args, **_kwargs)
            except asyncio.CancelledError:
                pass
            except Exception as e:
                await self.on_error(event)

        wrapped = _async_wrap(coro, event, *args, **kwargs)

        return asyncio.create_task(wrapped, name=f"snake:: {event.resolved_name}")

    async def on_error(self, source: str, *args, **kwargs) -> None:
        """
        Catches all errors dispatched by the library.

        By default it will format and print them to console

        Override this to change error handling behaviour
        """
        print(f"Ignoring exception in {source}:\n{traceback.format_exc()}", file=sys.stderr)

    async def on_command_error(self, source: str, *args, **kwargs) -> None:
        """
        Catches all errors dispatched by commands

        By default it will call `Snake.on_error`

        Override this to change error handling behavior
        """
        return await self.on_error(source, *args, **kwargs)

    @listen()
    async def _on_websocket_ready(self, event: events.RawGatewayEvent) -> None:
        """
        Catches websocket ready and determines when to dispatch the client `READY` signal.

        Args:
            event: The websocket ready packet
        """
        data = event.data
        expected_guilds = set(to_snowflake(guild["id"]) for guild in data["guilds"])
        self._user._add_guilds(expected_guilds)

        while True:
            try:  # wait to let guilds cache
                await asyncio.wait_for(self._guild_event.wait(), self.guild_event_timeout)
            except asyncio.TimeoutError:
                log.warning("Timeout waiting for guilds cache: Not all guilds will be in cache")
                break
            self._guild_event.clear()

            if len(self.cache.guild_cache) == len(expected_guilds):
                # all guilds cached
                break

        # cache slash commands
        await self._init_interactions()

        self._ready = True
        self.dispatch(events.Ready())

    def start(self, token):
        """
        Start the bot.

        info:
            This is the recommended method to start the bot

        Args:
            token str: Your bot's token
        """
        try:
            self.loop.run_until_complete(self.login(token))
        except KeyboardInterrupt:
            self.loop.run_until_complete(self.stop())

    async def stop(self):
        log.debug("Stopping the bot.")
        await self.ws.close()

    def dispatch(self, event: events.BaseEvent, *args, **kwargs):
        """
        Dispatch an event.

        Args:
            event: The event to be dispatched.
        """
        log.debug(f"Dispatching Event: {event.resolved_name}")
        listeners = self.listeners.get(event.resolved_name, [])
        for _listen in listeners:
            try:
                self._queue_task(_listen, event, *args, **kwargs)
            except Exception as e:
                raise BotException(f"An error occurred attempting during {event.resolved_name} event processing")

    def add_listener(self, listener: Listener):
        """
        Add a listener for an event, if no event is passed, one is determined

        Args:
            coro Listener: The listener to add to the client
        """
        if listener.event not in self.listeners:
            self.listeners[listener.event] = []
        self.listeners[listener.event].append(listener)

    def add_interaction(self, command: InteractionCommand):
        """
        Add a slash command to the client.

        Args:
            command InteractionCommand: The command to add
        """
        for scope in command.scopes:
            if scope not in self.interactions:
                self.interactions[scope] = {}
            elif command.resolved_name in self.interactions[scope]:
                old_cmd = self.interactions[scope][command.name]
                raise ValueError(f"Duplicate Command! {old_cmd.scopes}::{old_cmd.resolved_name}")

            self.interactions[scope][command.name] = command

    def add_message_command(self, command: MessageCommand):
        """
        Add a message command to the client.

        Args:
            command InteractionCommand: The command to add
        """
        if command.name not in self.commands:
            self.commands[command.name] = command
            return
        raise ValueError(f"Duplicate Command! Multiple commands share the name `{command.name}`")

    def add_component_callback(self, command: ComponentCommand):
        """Add a component callback to the client

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

    def _gather_commands(self):
        """Gathers commands from __main__ and self"""

        def process(_cmds):

            for func in _cmds:
                if isinstance(func, ComponentCommand):
                    self.add_component_callback(func)
                elif isinstance(func, SlashCommand):
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

    async def _init_interactions(self) -> None:
        """
        Initialise slash commands.

        If `sync_interactions` this will submit all registered slash commands to discord.
        Otherwise, it will get the list of interactions and cache their scopes.
        """
        # allow for cogs and main to share the same decorator
        try:
            if self.sync_interactions:
                await self.synchronise_interactions()
            else:
                await self._cache_interactions(warn_missing=True)
        except:
            await self.on_error("Interaction Syncing")

    async def _cache_interactions(self, warn_missing: bool = False):
        """Get all interactions used by this bot and cache them."""
        bot_scopes = set(g.id for g in self.cache.guild_cache.values())
        bot_scopes.add(GLOBAL_SCOPE)

        # Match all interaction is registered with discord's data.
        for scope in self.interactions:
            bot_scopes.discard(scope)
            try:
                remote_cmds = await self.http.get_interaction_element(self.user.id, scope)
            except Forbidden as e:
                raise InteractionMissingAccess(scope) from None

            remote_cmds = {cmd_data["name"]: cmd_data for cmd_data in remote_cmds}
            for cmd in self.interactions[scope].values():
                cmd_data = remote_cmds.pop(cmd.name, MISSING)
                if cmd_data is MISSING:
                    if warn_missing:
                        log.error(
                            f'Detected yet to sync slash command "/{cmd.name}" for scope '
                            f"{'global' if scope == GLOBAL_SCOPE else scope}"
                        )
                    continue

                self._interaction_scopes[str(cmd_data["id"])] = scope
                cmd.cmd_id = str(cmd_data["id"])

            if warn_missing:
                for cmd_data in remote_cmds.values():
                    log.error(
                        f"Detected unimplemented slash command \"/{cmd_data['name']}\" for scope "
                        f"{'global' if scope == GLOBAL_SCOPE else scope}"
                    )

        # Remaining guilds that bot is in but, no interaction is registered
        for scope in bot_scopes:
            try:
                remote_cmds = await self.http.get_interaction_element(self.user.id, scope)
            except Forbidden:
                # We will just assume they don't want application commands in this guild.
                log.debug(f"Bot was not invited to guild {scope} with `application.commands` scope")
                continue

            for cmd_data in remote_cmds:
                self._interaction_scopes[str(cmd_data["id"])] = scope
                if warn_missing:
                    log.error(
                        f"Detected unimplemented slash command \"/{cmd_data['name']}\" for scope "
                        f"{'global' if scope == GLOBAL_SCOPE else scope}"
                    )

    async def synchronise_interactions(self) -> None:
        """Synchronise registered interactions with discord

        One flaw of this is it cant determine if context menus need updating,
        as discord isn't returning that data on get req, so they are unnecessarily updated"""

        # first we need to make sure our local copy of cmd_ids is up-to-date
        await self._cache_interactions()
        cmd_scopes = [g.id for g in self.guilds] + [GLOBAL_SCOPE]
        guild_perms = {}

        for cmd_scope in cmd_scopes:
            try:
                cmds_resp_data = await self.http.get_interaction_element(self.user.id, cmd_scope)
                need_to_sync = False
                cmds_to_sync = []

                for local_cmd in self.interactions.get(cmd_scope, {}).values():
                    # try and find remote equiv of this command
                    remote_cmd = next((v for v in cmds_resp_data if v["id"] == local_cmd.cmd_id), None)
                    if remote_cmd:
                        cmds_resp_data.remove(remote_cmd)

                    local_cmd = local_cmd.to_dict()
                    cmds_to_sync.append(local_cmd)

                    # todo: prevent un-needed syncs for subcommands
                    if (
                        not remote_cmd
                        or local_cmd["name"] != remote_cmd["name"]
                        or local_cmd.get("description", "") != remote_cmd.get("description", "")
                        or local_cmd.get("default_permission", True) != remote_cmd.get("default_permission", True)
                        or local_cmd.get("options") != remote_cmd.get("options")
                    ):  # if command local data doesnt match remote, a change has been made, sync it
                        need_to_sync = True

                if need_to_sync:
                    log.info(f"Updating {len(cmds_to_sync)} commands in {cmd_scope}")
                    cmd_sync_resp = await self.http.post_interaction_element(
                        self.user.id, cmds_to_sync, guild_id=cmd_scope
                    )
                    # cache cmd_ids and their scopes
                    for cmd_data in cmd_sync_resp:
                        self.interactions[cmd_scope][cmd_data["name"]].cmd_id = str(cmd_data["id"])
                        self._interaction_scopes[cmd_data["id"]] = cmd_scope
                else:
                    log.debug(f"{cmd_scope} is already up-to-date")

                for local_cmd in self.interactions.get(cmd_scope, {}).values():
                    if not local_cmd.permissions:
                        continue

                    for perm_scope, perms in local_cmd.permissions.items():
                        if perm_scope not in guild_perms:
                            guild_perms[perm_scope] = []
                        guild_perms[perm_scope].append(
                            {"id": local_cmd.cmd_id, "permissions": [perm.to_dict() for perm in perms]}
                        )

                for perm_scope in guild_perms:
                    log.debug(f"Updating {len(guild_perms[perm_scope])} command permissions in {perm_scope}")
                    await self.http.batch_edit_application_command_permissions(
                        application_id=self.user.id, scope=perm_scope, data=guild_perms[perm_scope]
                    )

                if self.del_unused_app_cmd:
                    for cmd in cmds_resp_data:
                        scope = cmd.get("guild_id", GLOBAL_SCOPE)
                        log.warning(
                            f"Deleting unimplemented slash command \"/{cmd['name']}\" from scope "
                            f"{'global' if scope == GLOBAL_SCOPE else scope}"
                        )
                        await self.http.delete_interaction_element(
                            self.user.id, cmd.get("guild_id", GLOBAL_SCOPE), cmd["id"]
                        )
            except Forbidden as e:
                raise InteractionMissingAccess(cmd_scope) from None

    async def get_context(
        self, data: Union[dict, Message], interaction: bool = False
    ) -> Union[MessageContext, InteractionContext, ComponentContext, AutocompleteContext]:
        """
        Return a context object based on data passed

        note:
            If you want to use custom context objects, this is the method to override. Your replacement must take the same arguments as this, and return a Context-like object.

        Args:
            data: The data of the event
            interaction: Is this an interaction or not?

        returns:
            Context object
        """
        # this line shuts up IDE warnings
        cls: Union[MessageContext, ComponentContext, InteractionContext, AutocompleteContext]

        if interaction:
            # todo: change to match
            if data["type"] == InteractionTypes.MESSAGE_COMPONENT:
                return ComponentContext.from_dict(data, self)
            elif data["type"] == InteractionTypes.AUTOCOMPLETE:
                cls = AutocompleteContext.from_dict(data, self)
            else:
                cls = InteractionContext.from_dict(data, self)

            invoked_name: str = data["data"]["name"]
            kwargs = {}

            if options := data["data"].get("options"):
                o_type = options[0]["type"]
                if o_type in (OptionTypes.SUB_COMMAND, OptionTypes.SUB_COMMAND_GROUP):
                    # this is a subcommand, process accordingly
                    if o_type == OptionTypes.SUB_COMMAND:
                        invoked_name = f"{invoked_name} {options[0]['name']}"
                        options = options[0].get("options", [])
                    else:
                        invoked_name = (
                            f"{invoked_name} {options[0]['name']} "
                            f"{next(x for x in options[0]['options'] if x['type'] == OptionTypes.SUB_COMMAND)['name']}"
                        )
                        options = options[0]["options"][0].get("options", [])

                for option in options:
                    value = option.get("value")

                    # todo change to match statement
                    # this block here resolves the options using the cache
                    if option["type"] == OptionTypes.USER:
                        value = (
                            self.cache.member_cache.get((to_snowflake(data.get("guild_id", 0)), to_snowflake(value)))
                            or self.cache.user_cache.get(to_snowflake(value))
                        ) or value
                    elif option["type"] == OptionTypes.CHANNEL:
                        value = self.cache.channel_cache.get(to_snowflake(value)) or value
                    elif option["type"] == OptionTypes.ROLE:
                        value = self.cache.role_cache.get(to_snowflake(value)) or value
                    elif option["type"] == OptionTypes.MENTIONABLE:
                        snow = to_snowflake(value)
                        if user := self.cache.member_cache.get(snow) or self.cache.user_cache.get(snow):
                            value = user
                        elif role := self.cache.role_cache.get(snow):
                            value = role
                    kwargs[option["name"].lower()] = value

            cls.invoked_name = invoked_name
            cls.kwargs = kwargs
            cls.args = [v for v in kwargs.values()]

            return cls
        else:
            return MessageContext.from_message(self, data)

    @listen("raw_interaction_create")
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
                command: SlashCommand = self.interactions[scope][name]  # type: ignore
                log.debug(f"{scope} :: {command.name} should be called")
                ctx = await self.get_context(interaction_data, True)

                if auto_opt := getattr(ctx, "focussed_option", None):
                    await command.autocomplete_callbacks[auto_opt](ctx, **ctx.kwargs)
                else:
                    try:
                        await command(ctx, **ctx.kwargs)
                    except Exception:
                        await self.on_command_error(f"cmd /`{name}`")
            else:
                log.error(f"Unknown cmd_id received:: {interaction_id} ({name})")

        elif interaction_data["type"] == InteractionTypes.MESSAGE_COMPONENT:
            # Buttons, Selects, ContextMenu::Message
            ctx = await self.get_context(interaction_data, True)
            component_type = interaction_data["data"]["component_type"]

            self.dispatch(events.Component(ctx))
            if callback := self._component_callbacks.get(ctx.custom_id):
                try:
                    await callback(ctx)
                except Exception:
                    await self.on_command_error(f"Component Callback for {ctx.custom_id}")
            if component_type == ComponentTypes.BUTTON:
                self.dispatch(events.Button(ctx))
            if component_type == ComponentTypes.SELECT:
                self.dispatch(events.Select(ctx))

        else:
            raise NotImplementedError(f"Unknown Interaction Received: {interaction_data['type']}")

    @listen("message_create")
    async def _dispatch_msg_commands(self, event: MessageCreate):
        """Determine if a command is being triggered, and dispatch it."""
        message = event.message

        if not message.author.bot:
            prefix = await self.get_prefix(message)

            if message.content.startswith(prefix):
                invoked_name = get_first_word(message.content.removeprefix(prefix))
                command = self.commands.get(invoked_name)
                if command and command.enabled:
                    context = await self.get_context(message)
                    context.invoked_name = invoked_name
                    try:
                        await command(context)
                    except:
                        await self.on_command_error(f"cmd `{invoked_name}`")

    def get_scale(self, name) -> Optional[Scale]:
        """
        Get a scale
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
        A helper method to load a scale

        Args:
            file_name: The name of the file to load the scale from.
            package: The package this scale is in.
        """
        self.load_extension(file_name, package)

    def shed_scale(self, scale_name: str) -> None:
        """
        Helper method to unload a scale

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

    def load_extension(self, name: str, package: str = None):
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
            setup = getattr(module, "setup")
            setup(self)
        except Exception as e:
            del sys.modules[name]
            raise ExtensionLoadException(f"Error loading {name}") from e

        else:
            log.debug(f"Loaded Extension: {name}")
            self.__extensions[name] = module
            return

    def unload_extension(self, name, package=None):
        """
        unload an extension.

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

    def reload_extension(self, name, package=None):
        """
        Helper method to reload an extension.
        Simply unloads, then loads the extension.

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

    async def get_guild(self, guild_id: "Snowflake_Type") -> Guild:
        """
        Get a guild

        Note:
            This method is an alias for the cache which will either return a cached object, or query discord for the object
            if its not already cached.

        Args:
            guild_id: The ID of the guild to get

        Returns:
            Guild Object
        """
        return await self.cache.get_guild(guild_id)

    async def get_channel(self, channel_id: "Snowflake_Type") -> "TYPE_ALL_CHANNEL":
        """
        Get a channel

        Note:
            This method is an alias for the cache which will either return a cached object, or query discord for the object
            if its not already cached.

        Args:
            channel_id: The ID of the channel to get

        Returns:
            Channel Object
        """
        return await self.cache.get_channel(channel_id)

    async def get_user(self, user_id: "Snowflake_Type") -> User:
        """
        Get a user

        Note:
            This method is an alias for the cache which will either return a cached object, or query discord for the object
            if its not already cached.

        Args:
            user_id: The ID of the user to get

        Returns:
            User Object
        """
        return await self.cache.get_user(user_id)

    async def get_member(self, user_id: "Snowflake_Type", guild_id: "Snowflake_Type") -> Member:
        """
        Get a member from a guild

        Note:
            This method is an alias for the cache which will either return a cached object, or query discord for the object
            if its not already cached.

        Args:
            user_id: The ID of the member
            guild_id: The ID of the guild to get the member from

        Returns:
            Member object
        """
        return await self.cache.get_member(guild_id, user_id)

    async def get_sticker(self, sticker_id: "Snowflake_Type"):
        sticker_data = await self.http.get_sticker(sticker_id)
        return Sticker.from_dict(sticker_data, self)

    async def get_nitro_packs(self) -> List["StickerPack"]:
        packs_data = await self.http.list_nitro_sticker_packs()
        packs = []
        for pack_data in packs_data:
            packs.append(StickerPack.from_dict(pack_data, self))
        return packs

    async def change_presence(
        self, status: Optional[Union[str, Status]] = Status.ONLINE, activity: Optional[Union[Activity, str]] = None
    ):
        """
        Change the bots presence.

        Args:
            status: The status for the bot to be. i.e. online, afk, etc.
            activity: The activity for the bot to be displayed as doing.

        note::
            Bots may only be `playing` `streaming` or `listening`, other activity types are likely to fail.
        """
        if activity:
            if not isinstance(activity, Activity):
                # squash whatever the user passed into an activity
                activity = Activity.create(name=str(activity))

            if activity.type == ActivityType.STREAMING:
                if not activity.url:
                    log.warning("Streaming activity cannot be set without a valid URL attribute")
            elif activity.type not in [ActivityType.GAME, ActivityType.STREAMING, ActivityType.LISTENING]:
                log.warning(f"Activity type `{ActivityType(activity.type).name}` may not be enabled for bots")
        else:
            activity = self._activity if self._activity else []

        if status:
            if not isinstance(status, Status):
                try:
                    status = Status[status.upper()]
                except KeyError:
                    raise ValueError(f"`{status}` is not a valid status type. Please use the Status enum") from None
        else:
            # in case the user set status to None
            if self._status:
                status = self._status
            else:
                log.warning("Status must be set to a valid status type, defaulting to online")
                status = Status.ONLINE

        self._status = status
        self._activity = activity
        await self.ws.change_presence(activity.to_dict() if activity else None, status)
