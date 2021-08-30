import asyncio
import importlib.util
import logging
import sys
import time
import traceback
from random import randint
from typing import Any, Callable, Coroutine, Dict, List, Optional, Union

import aiohttp

from dis_snek.const import logger_name
from dis_snek.errors import (
    GatewayNotFound,
    SnakeException,
    WebSocketClosed,
    WebSocketRestart,
)
from dis_snek.gateway import WebsocketClient
from dis_snek.http_client import HTTPClient
from dis_snek.models.discord_objects.channel import BaseChannel
from dis_snek.models.discord_objects.context import (
    ComponentContext,
    Context,
    InteractionContext,
)
from dis_snek.models.discord_objects.guild import Guild
from dis_snek.models.discord_objects.interactions import (
    BaseInteractionCommand,
    ContextMenu,
    OptionTypes,
    SlashCommand,
    SlashCommandChoice,
    SlashCommandOption,
    Permission,
)
from dis_snek.models.discord_objects.message import Message
from dis_snek.models.discord_objects.user import Member, SnakeBotUser, User
from dis_snek.models.enums import ComponentTypes, Intents, CommandTypes, InteractionTypes
from dis_snek.models.snowflake import Snowflake_Type
from dis_snek.smart_cache import GlobalCache


log = logging.getLogger(logger_name)


class Snake:
    def __init__(
        self,
        intents: Union[int, Intents] = Intents.DEFAULT,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        sync_interactions: bool = False,
    ):
        self.loop: asyncio.AbstractEventLoop = asyncio.get_event_loop() if loop is None else loop
        self.intents = intents

        # "Factories"
        self.http: HTTPClient = HTTPClient(loop=self.loop)
        self.ws: WebsocketClient = WebsocketClient

        self._connection = None
        self._closed = False
        self.sync_interactions = sync_interactions

        # caches
        self.cache: GlobalCache = GlobalCache(self)
        self.guilds_cache = {}
        self._user: SnakeBotUser = None
        self.interactions: Dict[Snowflake_Type, Dict[str, BaseInteractionCommand]] = {}
        self.__extensions = {}

        self._interaction_scopes: Dict[Snowflake_Type, Snowflake_Type] = {}

        self._listeners: Dict[str, List] = {}

        self.add_listener(self._on_raw_socket_receive, "raw_socket_receive")
        self.add_listener(self._on_websocket_ready, "websocket_ready")
        self.add_listener(self._on_raw_message_create, "raw_message_create")
        self.add_listener(self._on_raw_guild_create, "raw_guild_create")
        self.add_listener(self._dispatch_interaction, "raw_interaction_create")

    @property
    def is_closed(self) -> bool:
        return self._closed

    @property
    def latency(self) -> float:
        return self.ws.latency

    @property
    def user(self) -> SnakeBotUser:
        return self._user

    async def login(self, token):
        """
        Login to discord
        :param token: Your bots token
        """
        log.debug(f"Logging in with token: {token}")
        me = await self.http.login(token.strip())
        self._user = SnakeBotUser.from_dict(me, self)
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
                self._interaction_scopes[str(cmd_data["id"])] = scope if scope else "global"
                try:
                    self.interactions[scope][cmd_data["name"]].cmd_id = str(cmd_data["id"])
                except KeyError:
                    pass

    def add_interaction(self, command: Union[SlashCommand, ContextMenu]):
        """
        Add a slash command to the client.

        :param command: The command to add
        :return:
        """
        if command.scope not in self.interactions:
            self.interactions[command.scope] = {}
        self.interactions[command.scope][command.name] = command

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
                self.user.id, cmd_scope if cmd_scope != "global" else None
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
                    self.user.id, cmds_to_sync, guild_id=cmd_scope if cmd_scope != "global" else None
                )
                # cache cmd_ids and their scopes
                for cmd_data in cmd_sync_resp:
                    self._interaction_scopes[str(cmd_data["id"])] = cmd_scope
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
        self, data: Dict, interaction: bool = False
    ) -> Union[Context, InteractionContext, ComponentContext]:
        """
        Return a context object based on data passed

        :param client: The bot itself
        :param data: The data of the event
        :param interaction: Is this an interaction or not?
        :return: A context object
        """
        cls = ComponentContext if data["type"] == InteractionTypes.MESSAGE_COMPONENT else InteractionContext

        if interaction:
            cls = cls(client=self, token=data.get("token"), interaction_id=data.get("id"))
            cls.guild = await self.cache.get_guild(data.get("guild_id"))
            if cls.guild:
                # this channel line is a placeholder
                cls.channel = await self.cache.get_channel(data["channel_id"])
                cls.author = data["member"]
            else:
                cls.author = data["user"]
            cls.data = data
            cls.target_id = data["data"].get("target_id")

            if res_data := data["data"].get("resolved"):
                # todo: maybe a resolved dataclass instead of this?
                if channels := res_data.get("channels"):
                    cls.resolved["channels"] = {}
                    for key, _channel in channels.items():
                        cls.resolved["channels"][key] = BaseChannel.from_dict_factory(_channel, self)

                if members := res_data.get("members"):
                    cls.resolved["members"] = {}
                    for key, _member in members.items():
                        user_obj = res_data["users"][key]
                        cls.resolved["members"][key] = Member.from_dict({**_member, **user_obj}, self)

                elif users := res_data.get("users"):
                    cls.resolved["users"] = {}
                    for key, _user in users.items():
                        cls.resolved["users"][key] = User.from_dict(_user, self)

                if roles := res_data.get("roles"):
                    cls.resolved["roles"] = {}
                    for key, _role in roles.items():
                        # todo: convert to role object
                        cls.resolved["roles"][key] = _role
        else:
            # todo: non-interaction context
            raise NotImplementedError

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
            scope = self._interaction_scopes.get(str(interaction_id))

            kwargs = {}
            if "options" in interaction_data["data"]:
                for option in interaction_data["data"]["options"]:
                    kwargs[option["name"]] = option["value"]

            if scope in self.interactions:
                command: SlashCommand = self.interactions[scope][name]
                print(f"{command.scope} :: {command.name} should be called")

                ctx = await self.get_context(interaction_data, True)
                ctx.kwargs = kwargs
                ctx.args = kwargs.values()

                await command.call(ctx, **kwargs)
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

    async def _on_raw_message_create(self, data: dict) -> None:
        """
        Automatically convert MESSAGE_CREATE event data to the object.

        :param data: raw message data
        """
        msg = Message.from_dict(data, self)
        self.dispatch("message_create", msg)

    async def _on_raw_guild_create(self, data: dict) -> None:
        """
        Automatically cache a guild upon GUILD_CREATE event from gateway.

        :param data: raw guild data
        """
        guild = self.cache.place_guild_data(data)
        self.dispatch("guild_create", guild)

    async def _on_websocket_ready(self, data: dict) -> None:
        """
        Catches websocket ready and determines when to dispatch the client `READY` signal.

        :param data: the websocket ready packet
        """
        expected_guild_count = len(data["guilds"])
        last_count = 0
        current_count = -1

        last_rcv = time.perf_counter()
        while True:
            # wait a while to let guilds cache
            await asyncio.sleep(0.5)

            current_count = len(self.cache.guild_cache)
            if current_count != expected_guild_count:
                if current_count == last_count:
                    # count hasnt changed, check how long we've been waiting
                    if time.perf_counter() - last_rcv >= 3:
                        # timeout
                        log.warning("Timeout waiting for guilds cache: Not all guilds will be in cache")
                        break
                else:
                    last_rcv = time.perf_counter()
                    last_count = current_count

                continue
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

    async def get_guild(self, guild_id: Snowflake_Type, with_counts: bool = False) -> Guild:
        g_data = await self.http.get_guild(guild_id, with_counts)
        return Guild(g_data, self)

    async def get_guilds(
        self, limit: int = 200, before: Optional[Snowflake_Type] = None, after: Optional[Snowflake_Type] = None
    ):
        g_data = await self.http.get_guilds(limit, before, after)
        to_return = []
        for g in g_data:
            to_return.append(Guild(g, self))

        return to_return

    async def send_message(self, channel: Snowflake_Type, content: str):
        await self.http.create_message(channel, content)

    def slash_command(
        self,
        name: str,
        description: str = "No description set",
        scope: Snowflake_Type = "global",
        options: Optional[List[Union[SlashCommandOption, Dict]]] = None,
        default_permission: bool = True,
        permissions: Optional[Dict[Snowflake_Type, Union[Permission, Dict]]] = None,
    ):
        def wrapper(func):
            if not asyncio.iscoroutinefunction(func):
                raise ValueError("Commands must be coroutines")

            opt = options
            if hasattr(func, "options"):
                if opt:
                    opt += func.options
                else:
                    opt = func.options

            perm = permissions
            if hasattr(func, "permissions"):
                if perm:
                    perm.update(func.permissions)
                else:
                    perm = func.permissions

            cmd = SlashCommand(
                name=name,
                description=description,
                scope=scope,
                call=func,
                options=opt,
                default_permission=default_permission,
                permissions=perm,
            )
            func.cmd_id = f"{scope}::{name}"
            self.add_interaction(cmd)
            return func

        return wrapper

    def context_menu(
        self,
        name: str,
        context_type: CommandTypes,
        scope: Snowflake_Type,
        default_permission: bool = True,
        permissions: Optional[Dict[Snowflake_Type, Union[Permission, Dict]]] = None,
    ):
        """
        Decorator to create a context menu command.

        :param name: The name of this context menu
        :param context_type: The type of context menu
        :param scope: The scope (ie guild_id or global)
        :return:
        """

        def wrapper(func):
            if not asyncio.iscoroutinefunction(func):
                raise ValueError("Commands must be coroutines")

            perm = permissions
            if hasattr(func, "permissions"):
                if perm:
                    perm.update(func.permissions)
                else:
                    perm = func.permissions

            cmd = ContextMenu(
                name=name,
                type=context_type,
                scope=scope,
                default_permission=default_permission,
                permissions=perm,
                call=func,
            )
            self.add_interaction(cmd)
            return func

        return wrapper

    def slash_option(
        self,
        name: str,
        description: str,
        opt_type: Union[OptionTypes, int],
        required: bool = False,
        choices: List[Union[SlashCommandChoice, dict]] = None,
    ):
        """
        Decorator to add an option to your slash command.

        :param name: The name of this option
        :param opt_type: The type of option
        :param description: The description of this option
        :param required: "This option must be filled to use the command"
        :param choices: A list of choices the user has to pick between
        """

        def wrapper(func):
            if hasattr(func, "cmd_id"):
                raise Exception("slash_option decorators must be positioned under a slash_command decorator")

            option = SlashCommandOption(
                name=name, type=opt_type, description=description, required=required, choices=choices if choices else []
            )

            if not hasattr(func, "options"):
                func.options = []
            func.options.append(option)
            return func

        return wrapper

    def slash_permission(self, guild_id: Snowflake_Type, permissions: List[Union[Permission, Dict]]):
        """
        Decorator to add permissions for a guild to your slash command or context menu.

        :param guild_id: The target guild to apply the permissions.
        :param permissions: A list of interaction permission rights.
        """

        def wrapper(func):
            if hasattr(func, "cmd_id"):
                raise Exception("slash_option decorators must be positioned under a slash_command decorator")

            if not hasattr(func, "permissions"):
                func.permissions = {}

            if guild_id not in func.permissions:
                func.permissions[guild_id] = []
            func.permissions[guild_id] += permissions
            return func

        return wrapper

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
        except AttributeError:
            log.error(f"No setup function in {name}")
        except Exception as e:
            log.error(e)
        else:
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
