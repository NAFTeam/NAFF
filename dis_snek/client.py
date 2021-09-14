import asyncio
import importlib.util
import inspect
import logging
import sys
import traceback
from functools import partial
from random import randint
from typing import TYPE_CHECKING, Any, Callable, Coroutine, Dict, List, Optional, Union

import aiohttp

from dis_snek.const import logger_name, GLOBAL_SCOPE
from dis_snek.errors import GatewayNotFound, SnakeException, WebSocketClosed, WebSocketRestart
from dis_snek.gateway import WebsocketClient
from dis_snek.http_client import HTTPClient
from dis_snek.models.command import MessageCommand, BaseCommand
from dis_snek.models.discord_objects.context import ComponentContext, InteractionContext, MessageContext
from dis_snek.models.discord_objects.guild import Guild
from dis_snek.models.discord_objects.interactions import (
    InteractionCommand,
    SlashCommand,
    OptionTypes,
    SubCommand,
)
from dis_snek.models.discord_objects.message import Message
from dis_snek.models.discord_objects.user import SnakeBotUser, User
from dis_snek.models.enums import ComponentTypes, Intents, InteractionTypes
from dis_snek.models.scale import Scale
from dis_snek.models.snowflake import to_snowflake
from dis_snek.smart_cache import GlobalCache
from dis_snek.utils.input_utils import get_first_word, get_args
from dis_snek.utils.proxy import CacheProxy

if TYPE_CHECKING:
    from dis_snek.models.snowflake import Snowflake_Type

log = logging.getLogger(logger_name)


class Snake:
    def __init__(
        self,
        intents: Union[int, Intents] = Intents.DEFAULT,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        prefix: str = ".",
        sync_interactions: bool = False,
        asyncio_debug: bool = False,
    ):
        self.loop: asyncio.AbstractEventLoop = asyncio.get_event_loop() if loop is None else loop
        if asyncio_debug:
            log.warning("Asyncio Debug is enabled, Your log will contain additional errors and warnings")
            import tracemalloc

            tracemalloc.start()
            self.loop.set_debug(True)

        self.intents = intents
        self.sync_interactions = sync_interactions
        self.prefix = prefix
        self.scales = {}

        # "Factories"
        self.http: HTTPClient = HTTPClient(loop=self.loop)
        self.ws: WebsocketClient = WebsocketClient

        self._connection = None
        self._closed = False

        self._guild_event = asyncio.Event()
        self.guild_event_timeout = 3

        # caches
        self.cache: GlobalCache = GlobalCache(self)
        self._user: SnakeBotUser = None
        self._app: dict = None
        self.interactions: Dict["Snowflake_Type", Dict[str, InteractionCommand]] = {}
        self.commands: Dict[str, MessageCommand] = {}
        self.__extensions = {}

        self._interaction_scopes: Dict["Snowflake_Type", "Snowflake_Type"] = {}

        self._listeners: Dict[str, List] = {}

        self.add_listener(self._on_raw_socket_receive, "raw_socket_receive")
        self.add_listener(self._on_websocket_ready, "websocket_ready")
        self.add_listener(self._on_raw_message_create, "raw_message_create")
        self.add_listener(self._on_raw_guild_create, "raw_guild_create")
        self.add_listener(self._dispatch_interaction, "raw_interaction_create")
        self.add_listener(self._dispatch_msg_commands, "message_create")

    @property
    def is_closed(self) -> bool:
        return self._closed

    @property
    def latency(self) -> float:
        return self.ws.latency

    @property
    def user(self) -> SnakeBotUser:
        return self._user

    @property
    def app(self) -> dict:
        # todo: create app object
        return self._app

    @property
    def owner(self) -> Coroutine[Any, Any, User]:
        return self.cache.get_user(self.app["owner"]["id"])

    def get_prefix(self):
        """A method to get the bot's prefix, can be overridden to add dynamic prefixes."""
        return self.prefix

    async def login(self, token):
        """
        Login to discord
        :param token: Your bots token
        """
        # i needed somewhere to put this call,
        # login will always run after initialisation
        # so im gathering commands here
        self._gather_commands()

        log.debug(f"Logging in with token: {token}")
        me = await self.http.login(token.strip())
        self._user = SnakeBotUser.from_dict(me, self)
        self._app = await self.http.get_current_bot_information()
        self.dispatch("login")
        await self._ws_connect()

    async def _ws_connect(self):
        params = {
            "http": self.http,
            "dispatch": self.dispatch,
            "intents": self.intents,
            "resume": False,
            "session_id": None,
            "sequence": None,
        }
        while not self.is_closed:
            log.info(f"Attempting to {'re' if params['resume'] else ''}connect to gateway...")

            try:
                self.ws = await self.ws.connect(**params)

                await self.ws.run()
            except WebSocketRestart as ex:
                # internally requested restart
                self.dispatch("disconnect")
                if ex.resume:
                    params.update(resume=True, session_id=self.ws.session_id, sequence=self.ws.sequence)
                    continue
                params.update(resume=False, session_id=None, sequence=None)

            except (OSError, GatewayNotFound, aiohttp.ClientError, asyncio.TimeoutError, WebSocketClosed) as ex:
                self.dispatch("disconnect")

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
                self.dispatch("disconnect")
                log.error("".join(traceback.format_exception(type(e), e, e.__traceback__)))
                params.update(resume=False, session_id=None, sequence=None)

            await asyncio.sleep(randint(1, 5))

    def start(self, token):
        self.loop.run_until_complete(self.login(token))

    def _queue_task(self, coro, event_name, *args, **kwargs):
        async def _async_wrap(_coro, _event_name, *_args, **_kwargs):
            try:
                await coro(*_args, **_kwargs)
            except asyncio.CancelledError:
                pass
            except Exception as e:
                log.error("".join(traceback.format_exception(type(e), e, e.__traceback__)))

        wrapped = _async_wrap(coro, event_name, *args, **kwargs)

        return asyncio.create_task(wrapped, name=f"snake:: {event_name}")

    def dispatch(self, event: str, *args, **kwargs):
        log.debug(f"Dispatching event: {event}")

        listeners = self._listeners.get(event, [])
        for _listen in listeners:
            try:
                self._queue_task(_listen, event, *args, **kwargs)
            except Exception as e:
                log.error(f"Error running listener: {e}")

    def add_listener(self, coro: Callable[..., Coroutine[Any, Any, Any]], event: Optional[str] = None):
        """
        Add a listener for an event, if no event is passed, one is determined
        :param coro: the coroutine to run
        :param event: the event to listen for
        :return:
        """
        if not asyncio.iscoroutinefunction(coro):
            raise ValueError("Listeners must be coroutines")

        if not event:
            event = coro.__name__

        event = event.removeprefix("on_")

        if event not in self._listeners:
            self._listeners[event] = []
        self._listeners[event].append(coro)

    def event(self, coro: Callable[..., Coroutine[Any, Any, Any]]) -> Callable[..., Coroutine[Any, Any, Any]]:
        """
        A decorator to add a coroutine as a listener for an event.

        The coroutines name is used to determine which event it should be listening for. Ie:

        `def on_ready` will listen for `ready` events.

        :param coro: The coroutine that will be a listener
        :return:
        """
        self.add_listener(coro)
        return coro

    async def _init_interactions(self) -> None:
        """
        Initialise slash commands.

        If `sync_interactions` this will submit all registered slash commands to discord.
        Otherwise, it will get the list of interactions and cache their scopes.
        """
        # allow for cogs and main to share the same decorator

        if self.sync_interactions:
            await self.synchronise_interactions()
        else:
            await self._cache_interactions()

    async def _cache_interactions(self):
        """Get all interactions used by this bot and cache them."""
        scopes = [g.id for g in self.cache.guild_cache.values()] + [None]
        for scope in scopes:
            resp_data = await self.http.get_interaction_element(self.user.id, scope)

            for cmd_data in resp_data:
                self._interaction_scopes[str(cmd_data["id"])] = scope if scope else GLOBAL_SCOPE
                try:
                    self.interactions[scope][cmd_data["name"]].cmd_id = str(cmd_data["id"])
                except KeyError:
                    pass

    def _gather_commands(self):
        """Gathers commands from __main__"""
        cmds = [obj for _, obj in inspect.getmembers(sys.modules["__main__"]) if isinstance(obj, BaseCommand)]
        for cmd in cmds:
            if isinstance(cmd, InteractionCommand):
                self.add_interaction(cmd)
            if isinstance(cmd, MessageCommand):
                self.add_message_command(cmd)

        log.debug(f"{len(cmds)} commands have been loaded from `__main__`")

    def add_interaction(self, command: InteractionCommand):
        """
        Add a slash command to the client.

        :param command: The command to add
        """
        if command.scope not in self.interactions:
            self.interactions[command.scope] = {}
        elif command.resolved_name in self.interactions[command.scope]:
            old_cmd = self.interactions[command.scope][command.name]
            raise ValueError(f"Duplicate Command! {old_cmd.scope}::{old_cmd.resolved_name}")

        if isinstance(command, SubCommand):
            if existing_sub := self.interactions[command.scope].get(command.name):
                if command.group_name:
                    existing_index = next(
                        (
                            index
                            for (index, val) in enumerate(existing_sub.options)
                            if val["name"] == command.group_name and val["type"] == 2
                        ),
                        None,
                    )
                    if existing_index is not None:
                        data = command.child_to_dict()
                        existing_sub.options[existing_index]["options"] += data["options"]
                        existing_sub.subcommand_callbacks[command.resolved_name] = command.callback
                        self.interactions[command.scope][command.name] = existing_sub
                        return

                existing_sub.options += [command.child_to_dict()]
                existing_sub.subcommand_callbacks[command.resolved_name] = command.callback
                command = existing_sub

            else:
                command.options = [command.child_to_dict()]
                command.subcommand_callbacks[command.resolved_name] = command.callback
                command.callback = command.subcommand_call

        self.interactions[command.scope][command.name] = command

    def add_message_command(self, command: MessageCommand):
        """
        Add a message command to the client.

        :param command: The command to add
        """
        if command.name not in self.commands:
            self.commands[command.name] = command
            return
        raise ValueError(f"Duplicate Command! Multiple commands share the name `{command.name}`")

    async def synchronise_interactions(self) -> None:
        """Synchronise registered interactions with discord

        One flaw of this is it cant determine if context menus need updating,
        as discord isn't returning that data on get req, so they are unnecessarily updated"""

        # first we need to make sure our local copy of cmd_ids is up-to-date
        await self._cache_interactions()
        cmd_scopes = [k for k in self.interactions.keys()]
        guild_perms = {}

        for cmd_scope in cmd_scopes:
            cmds_resp_data = await self.http.get_interaction_element(
                self.user.id, cmd_scope if cmd_scope != GLOBAL_SCOPE else None
            )
            need_to_sync = False
            cmds_to_sync = []

            for local_cmd in self.interactions[cmd_scope].values():
                # try and find remote equiv of this command
                remote_cmd = next((v for v in cmds_resp_data if v["id"] == local_cmd.cmd_id), None)
                local_cmd = local_cmd.to_dict()
                cmds_to_sync.append(local_cmd)

                if (
                    not remote_cmd
                    or local_cmd["name"] != remote_cmd["name"]
                    or local_cmd.get("description", "") != remote_cmd.get("description", "")
                    or local_cmd.get("default_permission", True) != remote_cmd.get("default_permission", True)
                    or local_cmd.get("options") != remote_cmd.get("options")
                ):  # if command local data doesnt match remote, a change has been made, sync it
                    need_to_sync = True

            if need_to_sync:
                log.debug(f"Updating {len(cmds_to_sync)} commands in {cmd_scope}")
                cmd_sync_resp = await self.http.post_interaction_element(
                    self.user.id, cmds_to_sync, guild_id=cmd_scope if cmd_scope != GLOBAL_SCOPE else None
                )
                # cache cmd_ids and their scopes
                for cmd_data in cmd_sync_resp:
                    self.interactions[cmd_scope][cmd_data["name"]].cmd_id = str(cmd_data["id"])
            else:
                log.debug(f"{cmd_scope} is already up-to-date")

            for local_cmd in self.interactions[cmd_scope].values():
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
                perm_sync_resp = await self.http.batch_edit_application_command_permissions(
                    application_id=self.user.id, scope=perm_scope, data=guild_perms[perm_scope]
                )

    async def get_context(
        self, data: Union[dict, Message], interaction: bool = False
    ) -> Union[MessageContext, InteractionContext, ComponentContext]:
        """
        Return a context object based on data passed

        :param data: The data of the event
        :param interaction: Is this an interaction or not?
        :return: A context object
        """
        # this line shuts up IDE warnings
        cls: Union[MessageContext, ComponentContext, InteractionContext]

        if interaction:
            if data["type"] == InteractionTypes.MESSAGE_COMPONENT:
                cls = ComponentContext.from_dict(data, self)
            else:
                cls = InteractionContext.from_dict(data, self)

            cls.guild = CacheProxy(id=str(data.get("guild_id")), method=self.cache.get_guild)

            if guild_id := data.get("guild_id"):
                self.cache.place_member_data(data.get("guild_id"), data["member"].copy())
                cls.channel = CacheProxy(id=data["channel_id"], method=self.cache.get_channel)
                cls.author = CacheProxy(
                    id=data["member"]["user"]["id"], method=partial(self.cache.get_member, guild_id)
                )
            else:
                self.cache.place_user_data(data["user"])
                cls.author = CacheProxy(id=data["user"]["id"], method=self.cache.get_user)

            if res_data := data["data"].get("resolved"):
                await cls.process_resolved(res_data)

            cls.data = data
            cls.target_id = data["data"].get("target_id")

        else:
            cls = MessageContext(
                self,
                data,
                author=data.author,
                channel=data.channel,
                guild=data.guild,
            )
            cls.arguments = get_args(data.content)[1:]
        return cls

    async def _dispatch_interaction(self, interaction_data: dict) -> None:
        """
        Identify and dispatch interaction of slash commands or components.

        :param interaction_data: raw interaction data
        """
        # Yes this is temporary, im just blocking out the basic logic

        if interaction_data["type"] in (InteractionTypes.PING, InteractionTypes.APPLICATION_COMMAND):
            # Slash Commands
            interaction_id = interaction_data["data"]["id"]
            name = interaction_data["data"]["name"]
            invoked_name = name
            scope = self._interaction_scopes.get(str(interaction_id))

            kwargs = {}
            # todo: redo this logic properly. This is a mess and you know it, Polls
            if options := interaction_data["data"].get("options"):
                if options[0]["type"] in (OptionTypes.SUB_COMMAND, OptionTypes.SUB_COMMAND_GROUP):
                    # subcommand, process accordingly
                    if options[0]["type"] == OptionTypes.SUB_COMMAND:
                        invoked_name = f"{name} {options[0]['name']}"
                    else:
                        invoked_name = (
                            f"{name} {options[0]['name']} "
                            f"{next(x for x in options[0]['options'] if x['type'] == OptionTypes.SUB_COMMAND)['name']}"
                        )
                        options = options[0]["options"][0].get("options")

                for option in options:
                    if option["type"] not in (OptionTypes.SUB_COMMAND, OptionTypes.SUB_COMMAND_GROUP):
                        kwargs[option["name"]] = option.get("value")

            if scope in self.interactions:
                command: SlashCommand = self.interactions[scope][name]
                print(f"{command.scope} :: {command.name} should be called")

                ctx = await self.get_context(interaction_data, True)
                ctx.invoked_name = invoked_name
                ctx.kwargs = kwargs
                ctx.args = kwargs.values()

                await command(ctx, **kwargs)
            else:
                log.error(f"Unknown cmd_id received:: {interaction_id} ({name})")

        elif interaction_data["type"] == InteractionTypes.MESSAGE_COMPONENT:
            # Buttons, Selects, ContextMenu::Message
            ctx = await self.get_context(interaction_data, True)
            component_type = interaction_data["data"]["component_type"]

            self.dispatch("component", ctx)
            if component_type == ComponentTypes.BUTTON:
                self.dispatch("button", ctx)
            if component_type == ComponentTypes.SELECT:
                self.dispatch("select", ctx)

        else:
            raise NotImplementedError(f"Unknown Interaction Received: {interaction_data['type']}")

    async def _dispatch_msg_commands(self, message: Message):
        """Determine if a command is being triggered, and dispatch it."""
        if not await message.author.bot:
            prefix = self.get_prefix()

            if message.content.startswith(prefix):
                invoked_name = get_first_word(message.content.removeprefix(prefix))
                command = self.commands.get(invoked_name)
                if command and command.enabled:
                    context = await self.get_context(message)
                    context.invoked_name = invoked_name
                    await command(context)

    async def _on_raw_message_create(self, data: dict) -> None:
        """
        Automatically convert MESSAGE_CREATE event data to the object.

        :param data: raw message data
        """
        msg = self.cache.place_message_data(data)
        self.dispatch("message_create", msg)

    async def _on_raw_guild_create(self, data: dict) -> None:
        """
        Automatically cache a guild upon GUILD_CREATE event from gateway.

        :param data: raw guild data
        """
        guild = self.cache.place_guild_data(data)
        self._guild_event.set()

        self.dispatch("guild_create", guild)

    async def _on_websocket_ready(self, data: dict) -> None:
        """
        Catches websocket ready and determines when to dispatch the client `READY` signal.

        :param data: the websocket ready packet
        """
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

        self.dispatch("ready")

    async def _on_raw_socket_receive(self, raw: dict):
        """
        Processes socket events and dispatches non-raw events

        :param raw: raw socket data
        """
        # TODO: I think don't really need this anymore? Unless just for debugging.
        event = raw.get("t")
        data = raw.get("d")
        log.debug(f"EVENT: {event}: {data}")

    # todo remove/move this
    async def get_guild(self, guild_id: "Snowflake_Type", with_counts: bool = False) -> Guild:
        g_data = await self.http.get_guild(guild_id, with_counts)
        return Guild.from_dict(g_data, self)

    # todo remove/move this
    async def get_guilds(
        self, limit: int = 200, before: Optional["Snowflake_Type"] = None, after: Optional["Snowflake_Type"] = None
    ):
        g_data = await self.http.get_guilds(limit, before, after)
        to_return = []
        for g in g_data:
            to_return.append(Guild(g, self))

        return to_return

    # todo remove/move this
    async def send_message(self, channel: "Snowflake_Type", content: str):
        await self.http.create_message(channel, content)

    def grow(self, file_name: str, package: str = None):
        """
        Helper method to load a scale.

        :param file_name: The name of the file to load the scale from.
        :param package: The package this scale is in.
        """
        self.load_extension(file_name, package)

    def shed(self, scale_name: str) -> None:
        """
        Helper method to unload a scale

        :param scale_name: The name of the scale"""
        try:
            self.scales[scale_name].shed(self.scales[scale_name])
        except KeyError:
            log.error(f"Unable to shed scale: No scale exists with name: `{scale_name}`")

    def load_extension(self, name, package=None):
        """
        Load an extension.

        :param name: The name of the extension
        :param package: The package this extension is in
        """
        name = importlib.util.resolve_name(name, package)
        if name in self.__extensions:
            raise Exception(f"{name} already loaded")

        module = importlib.import_module(name, package)
        try:
            setup = getattr(module, "setup")
            setup(self)
        except Exception as e:
            log.error(f"Error loading {name}: {e}")
        else:
            log.debug(f"Loaded Extension: {name}")
            self.__extensions[name] = module
            return

        del sys.modules[name]

    def unload_extension(self, name, package=None):
        """
        unload an extension.

        :param name: The name of the extension
        :param package: The package this extension is in
        """
        name = importlib.util.resolve_name(name, package)
        module = self.__extensions.get(name)

        if module is None:
            raise Exception(f"No extension called {name} is loaded")

        try:
            teardown = getattr(module, "teardown")
            teardown()
        except AttributeError:
            pass

        # todo: remove any events / commands / utils from this extension

        del sys.modules[name]
        del self.__extensions[name]

    def reload_extension(self, name, package=None):
        """
        Helper method to reload an extension.
        Simply unloads, then loads the extension.

        :param name: The name of the extension
        :param package: The package this extension is in
        """
        name = importlib.util.resolve_name(name, package)
        module = self.__extensions.get(name)

        if module is None:
            log.warning("Attempted to reload extension thats not loaded. Loading extension instead")
            return self.load_extension(name, package)

        self.unload_extension(name, package)
        self.load_extension(name, package)

        # todo: maybe add an ability to revert to the previous version if unable to load the new one
