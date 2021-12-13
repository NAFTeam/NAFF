import asyncio
import inspect
import logging
import re
from enum import IntEnum
from typing import TYPE_CHECKING, Callable, Coroutine, Dict, List, Union, Optional, Any

import attr

from dis_snek.const import (
    GLOBAL_SCOPE,
    CONTEXT_MENU_NAME_LENGTH,
    SLASH_OPTION_NAME_LENGTH,
    SLASH_CMD_NAME_LENGTH,
    SLASH_CMD_MAX_OPTIONS,
    SLASH_CMD_MAX_DESC_LENGTH,
    MISSING,
    logger_name,
)
from dis_snek.mixins.serialization import DictSerializationMixin
from dis_snek.models.auto_defer import AutoDefer
from dis_snek.models.command import BaseCommand
from dis_snek.models.discord_objects.channel import BaseChannel
from dis_snek.models.discord_objects.role import Role
from dis_snek.models.discord_objects.user import BaseUser
from dis_snek.models.enums import ChannelTypes, CommandTypes
from dis_snek.models.snowflake import to_snowflake, to_snowflake_list
from dis_snek.utils.attr_utils import docs
from dis_snek.utils.misc_utils import get_parameters
from dis_snek.utils.serializer import no_export_meta

if TYPE_CHECKING:
    from dis_snek.models.snowflake import Snowflake_Type
    from dis_snek.models.context import Context

log = logging.getLogger(logger_name)


class OptionTypes(IntEnum):
    """Option types supported by slash commands."""

    SUB_COMMAND = 1
    SUB_COMMAND_GROUP = 2
    STRING = 3
    INTEGER = 4
    BOOLEAN = 5
    USER = 6
    CHANNEL = 7
    ROLE = 8
    MENTIONABLE = 9
    NUMBER = 10

    @classmethod
    def from_type(cls, t: type) -> "OptionTypes":
        """
        Convert data types to their corresponding OptionType.

        parameters:
            t: The datatype to convert

        returns:
            OptionType or None
        """
        if issubclass(t, str):
            return cls.STRING
        if issubclass(t, int):
            return cls.INTEGER
        if issubclass(t, bool):
            return cls.BOOLEAN
        if issubclass(t, BaseUser):
            return cls.USER
        if issubclass(t, BaseChannel):
            return cls.CHANNEL
        if issubclass(t, Role):
            return cls.ROLE
        if issubclass(t, float):
            return cls.NUMBER


class PermissionTypes(IntEnum):
    """Types of target supported by the interaction permission."""

    ROLE = 1
    USER = 2

    @classmethod
    def from_type(cls, t: type) -> "PermissionTypes":
        if issubclass(t, Role):
            return cls.ROLE
        if issubclass(t, BaseUser):
            return cls.USER


class CallbackTypes(IntEnum):
    """Types of callback supported by interaction response."""

    PONG = 1
    CHANNEL_MESSAGE_WITH_SOURCE = 4
    DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE = 5
    DEFERRED_UPDATE_MESSAGE = 6
    UPDATE_MESSAGE = 7
    AUTOCOMPLETE_RESULT = 8


@attr.s(slots=True, hash=True)
class Permission:
    """
    Represents a interaction permission.

    parameters:
        id: The id of the role or user.
        guild_id: The guild this permission belongs to
        type: The type of id (user or role)
        permission: The state of permission. ``True`` to allow, ``False``, to disallow.
    """

    id: "Snowflake_Type" = attr.ib(converter=to_snowflake)
    guild_id: "Snowflake_Type" = attr.ib(converter=to_snowflake, metadata=no_export_meta)
    type: Union[PermissionTypes, int] = attr.ib(converter=PermissionTypes)
    permission: bool = attr.ib(default=True)

    def to_dict(self) -> dict:
        """
        Convert this object into a dict ready for discord.

        returns:
            Representation of this object
        """
        data = attr.asdict(self)
        data.pop("guild_id", None)
        data["id"] = str(data["id"])

        return data


@attr.s(slots=True, kw_only=True, on_setattr=[attr.setters.convert, attr.setters.validate])
class InteractionCommand(BaseCommand):
    """
    Represents a discord abstract interaction command.

    parameters:
        scope: Denotes whether its global or for specific guild.
        default_permission: Is this command available to all users?
        permissions: Map of guild id and its respective list of permissions to apply.
        cmd_id: The id of this command given by discord.
        callback: The coroutine to callback when this interaction is received.
    """

    name: str = attr.ib(metadata=docs("1-32 character name") | no_export_meta)
    scopes: List["Snowflake_Type"] = attr.ib(
        default=[GLOBAL_SCOPE],
        converter=to_snowflake_list,
        metadata=docs("The scopes of this interaction. Global or guild ids") | no_export_meta,
    )

    default_permission: bool = attr.ib(
        default=True, metadata=docs("whether this command is enabled by default when the app is added to a guild")
    )
    permissions: Optional[List[Union[Permission, Dict]]] = attr.ib(
        factory=dict, metadata=docs("The permissions of this interaction")
    )

    cmd_id: Dict[str, "Snowflake_Type"] = attr.ib(
        factory=dict, metadata=docs("The unique IDs of this commands") | no_export_meta
    )  # scope: cmd_id
    callback: Callable[..., Coroutine] = attr.ib(
        default=None, metadata=docs("The coroutine to call when this interaction is received") | no_export_meta
    )
    auto_defer: "AutoDefer" = attr.ib(
        default=MISSING,
        metadata=docs("A system to automatically defer this command after a set duration") | no_export_meta,
    )

    def __attrs_post_init__(self):
        if self.callback is not None:
            if hasattr(self.callback, "auto_defer"):
                self.auto_defer = self.callback.auto_defer

        super().__attrs_post_init__()

    @property
    def resolved_name(self):
        """A representation of this interaction's name"""
        return self.name

    def get_cmd_id(self, scope: "Snowflake_Type"):
        return self.cmd_id.get(scope, self.cmd_id.get(GLOBAL_SCOPE, None))

    @property
    def is_subcommand(self) -> bool:
        return False

    async def _permission_enforcer(self, ctx: "Context") -> bool:
        """A check that enforces Discord permissions"""
        # I wish this wasn't needed, but unfortunately Discord permissions cant be trusted to actually prevent usage
        for perm in self.permissions or []:
            if perm.type == PermissionTypes.ROLE:
                if ctx.author.has_role(perm.id):
                    if perm.permission is True:
                        return True
                    elif self.default_permission is True:
                        return False

            elif perm.type == PermissionTypes.USER:
                if ctx.author.id == perm.id:
                    if perm.permission is True:
                        return True
                    elif self.default_permission is True:
                        return False
        return self.default_permission


@attr.s(slots=True, kw_only=True, on_setattr=[attr.setters.convert, attr.setters.validate])
class ContextMenu(InteractionCommand):
    """
    Represents a discord context menu.

    parameters:
        name: The name of this entry.
        type: The type of entry (user or message).
    """

    name: str = attr.ib(metadata=docs("1-32 character name"))
    type: CommandTypes = attr.ib(metadata=docs("The type of command, defaults to 1 if not specified"))

    @name.validator
    def _name_validator(self, attribute: str, value: str) -> None:
        if not 1 <= len(value) <= CONTEXT_MENU_NAME_LENGTH:
            raise ValueError("Context Menu name attribute must be between 1 and 32 characters")

    @type.validator
    def _type_validator(self, attribute: str, value: int):
        if not isinstance(value, CommandTypes):
            if value not in CommandTypes.__members__.values():
                raise ValueError("Context Menu type not recognised, please consult the docs.")
        elif value == CommandTypes.CHAT_INPUT:
            raise ValueError(
                "The CHAT_INPUT type is basically slash commands. Please use the @slash_command() " "decorator instead."
            )


@attr.s(slots=True)
class SlashCommandChoice(DictSerializationMixin):
    """
    Represents a discord slash command choice.

    parameters:
        name: The name the user will see
        value: The data sent to your code when this choice is used
    """

    name: str = attr.ib()
    value: Union[str, int, float] = attr.ib()


@attr.s(slots=True, on_setattr=[attr.setters.convert, attr.setters.validate])
class SlashCommandOption(DictSerializationMixin):
    """
    Represents a discord slash command option.

    parameters:
        name: The name of this option
        type: The type of option
        description: The description of this option
        required: "This option must be filled to use the command"
        choices: A list of choices the user has to pick between
        channel_types: The channel types permitted. The option needs to be a channel
        min_value: The minimum value permitted. The option needs to be an integer or float
        max_value: The maximum value permitted. The option needs to be an integer or float
    """

    name: str = attr.ib()
    type: Union[OptionTypes, int] = attr.ib()
    description: str = attr.ib(default="No Description Set")
    required: bool = attr.ib(default=True)
    autocomplete: bool = attr.ib(default=False)
    choices: List[Union[SlashCommandChoice, Dict]] = attr.ib(factory=list)
    channel_types: Optional[list[Union[ChannelTypes, int]]] = attr.ib(default=None)
    min_value: Optional[float] = attr.ib(default=None)
    max_value: Optional[float] = attr.ib(default=None)

    @name.validator
    def _name_validator(self, attribute: str, value: str) -> None:
        if not re.match(rf"^[\w-]{{1,{SLASH_CMD_NAME_LENGTH}}}$", value) or value != value.lower():
            raise ValueError(
                f"Options names must be lower case and match this regex: ^[\w-]{1, {SLASH_CMD_NAME_LENGTH} }$"
            )  # noqa: W605

    @description.validator
    def _description_validator(self, attribute: str, value: str) -> None:
        if not 1 <= len(value) <= SLASH_OPTION_NAME_LENGTH:
            raise ValueError("Options must be between 1 and 100 characters long")

    @type.validator
    def _type_validator(self, attribute: str, value: int) -> None:
        if value == OptionTypes.SUB_COMMAND or value == OptionTypes.SUB_COMMAND_GROUP:
            raise ValueError(
                "Options cannot be SUB_COMMAND or SUB_COMMAND_GROUP. If you want to use subcommands, "
                "see the @sub_command() decorator."
            )

    @channel_types.validator
    def _channel_types_validator(self, attribute: str, value: Optional[list[OptionTypes]]) -> None:
        if value is not None:
            if self.type != OptionTypes.CHANNEL:
                raise ValueError("The option needs to be CHANNEL to use this")

            allowed_int = [channel_type.value for channel_type in ChannelTypes]
            for item in value:
                if (item not in allowed_int) and (item not in ChannelTypes):
                    raise ValueError(f"{value} is not allowed here")

    @min_value.validator
    def _min_value_validator(self, attribute: str, value: Optional[float]) -> None:
        if value is not None:
            if self.type != OptionTypes.INTEGER and self.type != OptionTypes.NUMBER:
                raise ValueError("`min_value` can only be supplied with int or float options")

            if self.type == OptionTypes.INTEGER:
                if isinstance(value, float):
                    raise ValueError("`min_value` needs to be an int in an int option")

            if self.max_value is not None and self.min_value is not None:
                if self.max_value < self.min_value:
                    raise ValueError("`min_value` needs to be <= than `max_value`")

    @max_value.validator
    def _max_value_validator(self, attribute: str, value: Optional[float]) -> None:
        if value is not None:
            if self.type != OptionTypes.INTEGER and self.type != OptionTypes.NUMBER:
                raise ValueError("`max_value` can only be supplied with int or float options")

            if self.type == OptionTypes.INTEGER:
                if isinstance(value, float):
                    raise ValueError("`max_value` needs to be an int in an int option")

            if self.max_value and self.min_value:
                if self.max_value < self.min_value:
                    raise ValueError("`min_value` needs to be <= than `max_value`")


@attr.s(slots=True, kw_only=True, on_setattr=[attr.setters.convert, attr.setters.validate])
class SlashCommand(InteractionCommand):
    name: str = attr.ib()
    description: str = attr.ib("No Description Set")

    group_name: str = attr.ib(default=None, metadata=no_export_meta)
    group_description: str = attr.ib(default="No Description Set", metadata=no_export_meta)

    sub_cmd_name: str = attr.ib(default=None, metadata=no_export_meta)
    sub_cmd_description: str = attr.ib(default="No Description Set", metadata=no_export_meta)

    options: List[Union[SlashCommandOption, Dict]] = attr.ib(factory=list)
    autocomplete_callbacks: dict = attr.ib(factory=dict, metadata=no_export_meta)

    @property
    def resolved_name(self):
        return f"{self.name}{f' {self.group_name}' if self.group_name else ''}{f' {self.sub_cmd_name}' if self.sub_cmd_name else ''}"

    @property
    def is_subcommand(self) -> bool:
        return self.sub_cmd_name is not None

    def __attrs_post_init__(self):
        params = get_parameters(self.callback)
        for name, val in params.items():
            if val.annotation and isinstance(val.annotation, SlashCommandOption):

                if not self.options:
                    self.options = []
                val.annotation.name = name
                self.options.append(val.annotation)

        if self.callback is not None:
            if hasattr(self.callback, "options"):
                if not self.options:
                    self.options = []
                self.options += self.callback.options

            if hasattr(self.callback, "permissions"):
                self.permissions = self.callback.permissions
        super().__attrs_post_init__()

    def to_dict(self) -> dict:
        data = super().to_dict()
        if self.is_subcommand:
            data["name"] = self.sub_cmd_name
            data["description"] = self.sub_cmd_description
            data.pop("default_permission", None)
            data.pop("permissions", None)
        return data

    @name.validator
    @group_name.validator
    @sub_cmd_name.validator
    def name_validator(self, attribute: str, value: str) -> None:
        if value:
            if not re.match(rf"^[\w-]{{1,{SLASH_CMD_NAME_LENGTH}}}$", value) or value != value.lower():
                raise ValueError(
                    f"Slash Command names must be lower case and match this regex: ^[\w-]{1, {SLASH_CMD_NAME_LENGTH} }$"
                )  # noqa: W605

    @description.validator
    @group_description.validator
    @sub_cmd_description.validator
    def description_validator(self, attribute: str, value: str) -> None:
        if not 1 <= len(value) <= SLASH_CMD_MAX_DESC_LENGTH:
            raise ValueError(f"Description must be between 1 and {SLASH_CMD_MAX_DESC_LENGTH} characters long")

    @options.validator
    def options_validator(self, attribute: str, value: List) -> None:
        if value:
            if isinstance(value, list):
                if len(value) > SLASH_CMD_MAX_OPTIONS:
                    raise ValueError(f"Slash commands can only hold {SLASH_CMD_MAX_OPTIONS} options")
                if value != sorted(
                    value,
                    key=lambda x: x.required if isinstance(x, SlashCommandOption) else x["required"],
                    reverse=True,
                ):
                    raise ValueError("Required options must go before optional options")

            else:
                raise TypeError("Options attribute must be either None or a list of options")

    def autocomplete(self, option_name: str):
        """A decorator to declare a coroutine as an option autocomplete"""

        def wrapper(call: Callable[..., Coroutine]):
            if not asyncio.iscoroutinefunction(call):
                raise TypeError("autocomplete must be coroutine")
            self.autocomplete_callbacks[option_name] = call

            # automatically set the option's autocomplete attribute to True
            for opt in self.options:
                if isinstance(opt, dict) and opt["name"] == option_name:
                    opt["autocomplete"] = True
                elif isinstance(opt, SlashCommandOption) and opt.name == option_name:
                    opt.autocomplete = True

            return call

        option_name = option_name.lower()
        return wrapper

    def subcommand(
        self,
        sub_cmd_name: str,
        group_name: str = None,
        group_description: str = "No Description Set",
        sub_cmd_description: str = "No Description Set",
        options: List[Union[SlashCommandOption, Dict]] = None,
    ) -> Callable[..., "SlashCommand"]:
        def wrapper(call: Callable[..., Coroutine]) -> "SlashCommand":
            if not asyncio.iscoroutinefunction(call):
                raise TypeError("Subcommand must be coroutine")
            return SlashCommand(
                name=self.name,
                description=self.description,
                group_name=group_name,
                group_description=group_description,
                sub_cmd_name=sub_cmd_name,
                sub_cmd_description=sub_cmd_description,
                options=options,
                callback=call,
            )

        return wrapper


@attr.s(slots=True, kw_only=True, on_setattr=[attr.setters.convert, attr.setters.validate])
class ComponentCommand(InteractionCommand):
    # right now this adds no extra functionality, but for future dev ive implemented it
    listeners: list[str] = attr.ib(factory=list)


##############
# Decorators #
##############


def slash_command(
    name: str,
    description: str = MISSING,
    scopes: List["Snowflake_Type"] = MISSING,
    options: Optional[List[Union[SlashCommandOption, Dict]]] = None,
    default_permission: bool = True,
    permissions: Optional[List[Union[Permission, Dict]]] = None,
    sub_cmd_name: str = None,
    group_name: str = None,
    sub_cmd_description: str = "No Description Set",
    group_description: str = "No Description Set",
):
    """
    A decorator to declare a coroutine as a slash command.

    note:
        While the base and group descriptions arent visible in the discord client, currently.
        We strongly advise defining them anyway, if you're using subcommands, as Discord has said they will be visible in
        one of the future ui updates.

    parameters:
        name: 1-32 character name of the command
        description: 1-100 character description of the command
        scope: The scope this command exists within
        options: The parameters for the command, max 25
        default_permission: Whether the command is enabled by default when the app is added to a guild
        permissions: The roles or users who can use this command
        sub_cmd_name: 1-32 character name of the subcommand
        sub_cmd_description: 1-100 character description of the subcommand
        group_name: 1-32 character name of the group
        group_description: 1-100 character description of the group

    returns:
        SlashCommand Object
    """

    def wrapper(func) -> SlashCommand:
        if not asyncio.iscoroutinefunction(func):
            raise ValueError("Commands must be coroutines")

        _description = description
        if _description is MISSING:
            _description = func.__doc__ if func.__doc__ else "No Description Set"

        cmd = SlashCommand(
            name=name,
            group_name=group_name,
            group_description=group_description,
            sub_cmd_name=sub_cmd_name,
            sub_cmd_description=sub_cmd_description,
            description=_description,
            scopes=scopes if scopes else [GLOBAL_SCOPE],
            default_permission=default_permission,
            permissions=permissions or {},
            callback=func,
            options=options,
        )

        return cmd

    return wrapper


def context_menu(
    name: str,
    context_type: "CommandTypes",
    scopes: List["Snowflake_Type"] = MISSING,
    default_permission: bool = True,
    permissions: Optional[List[Union[Permission, Dict]]] = None,
):
    """
    A decorator to declare a coroutine as a Context Menu

    parameters:
        name: 1-32 character name of the context menu
        context_type: The type of context menu
        scope: The scope this command exists within
        default_permission: Whether the menu is enabled by default when the app is added to a guild
        permissions: The roles or users who can use this menu

    returns:
        ContextMenu object
    """

    def wrapper(func) -> ContextMenu:
        if not asyncio.iscoroutinefunction(func):
            raise ValueError("Commands must be coroutines")

        perm = permissions or {}
        if hasattr(func, "permissions"):
            if perm:
                perm.update(func.permissions)
            else:
                perm = func.permissions

        cmd = ContextMenu(
            name=name,
            type=context_type,
            scopes=scopes if scopes else [GLOBAL_SCOPE],
            default_permission=default_permission,
            permissions=perm,
            callback=func,
        )
        return cmd

    return wrapper


def component_callback(*custom_id: str):
    """
    Register a coroutine as a component callback.

    Component callbacks work the same way as commands, just using components as a way of invoking, instead of messages.
    Your callback will be given a single argument, `ComponentContext`

    Args:
        custom_id: The custom ID of the component to wait for
    """

    def wrapper(func) -> ComponentCommand:
        if not asyncio.iscoroutinefunction(func):
            raise ValueError("Commands must be coroutines")

        return ComponentCommand(name=f"ComponentCallback::{custom_id}", callback=func, listeners=custom_id)

    # allows a mixture of generators and strings to be passed
    unpack = []
    for c in custom_id:
        if inspect.isgenerator(c):
            unpack += list(c)
        else:
            unpack.append(c)
    custom_id = unpack
    return wrapper


def slash_option(
    name: str,
    description: str,
    opt_type: Union[OptionTypes, int],
    required: bool = False,
    autocomplete: bool = False,
    choices: List[Union[SlashCommandChoice, dict]] = None,
    channel_types: Optional[list[Union[ChannelTypes, int]]] = None,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
) -> Any:
    """
    A decorator to add an option to a slash command.

    parameters:
        name: 1-32 lowercase character name matching ^[\w-]{1,32}$
        opt_type: The type of option
        description: 1-100 character description of option
        required: If the parameter is required or optional--default false
        choices: A list of choices the user has to pick between (max 25)
        channel_types: The channel types permitted. The option needs to be a channel
        min_value: The minimum value permitted. The option needs to be an integer or float
        max_value: The maximum value permitted. The option needs to be an integer or float
    """

    def wrapper(func):
        if hasattr(func, "cmd_id"):
            raise Exception("slash_option decorators must be positioned under a slash_command decorator")

        option = SlashCommandOption(
            name=name,
            type=opt_type,
            description=description,
            required=required,
            autocomplete=autocomplete,
            choices=choices if choices else [],
            channel_types=channel_types,
            min_value=min_value,
            max_value=max_value,
        )
        if not hasattr(func, "options"):
            func.options = []
        func.options.insert(0, option)
        return func

    return wrapper


def slash_permission(*permission: Union[Permission, Dict]) -> Any:
    """
    A decorator to add permissions for a guild to a slash command or context menu.

    parameters:
        *permission: The permissions to apply to this command
    """

    def wrapper(func):
        if hasattr(func, "cmd_id"):
            raise Exception("slash_permission decorators must be positioned under a slash_command decorator")

        if not hasattr(func, "permissions"):
            func.permissions = []
        func.permissions += list(permission)
        return func

    return wrapper


def auto_defer(ephemeral: bool = False, time_until_defer: float = 0.0):
    """
    A decorator to add an auto defer to a application command
    Args:
        ephemeral: Should the command be deferred as ephemeral
        time_until_defer: How long to wait before deferring automatically

    """

    def wrapper(func):
        if hasattr(func, "cmd_id"):
            raise Exception("auto_defer decorators must be positioned under a slash_command decorator")
        func.auto_defer = AutoDefer(enabled=True, ephemeral=ephemeral, time_until_defer=time_until_defer)
        return func

    return wrapper


def application_commands_to_dict(commands: Dict["Snowflake_Type", Dict[str, InteractionCommand]]) -> dict:
    """Convert the command list into a format that would be accepted by discord

    `Snake.interactions` should be the variable passed to this"""
    cmd_bases = {}  # {cmd_base: [commands]}
    """A store of commands organised by their base command"""
    output = {}
    """The output dictionary"""

    def squash_subcommand(subcommands: List) -> Dict:
        output_data = {}
        groups = {}
        sub_cmds = []
        for subcommand in subcommands:
            if not output_data:
                output_data = {
                    "name": subcommand.name,
                    "description": subcommand.description,
                    "options": [],
                    "permissions": [s.to_dict() if not isinstance(s, dict) else s for s in subcommand.permissions],
                    "default_permission": subcommand.default_permission,
                }
            if subcommand.group_name:
                if subcommand.group_name not in groups:
                    groups[subcommand.group_name] = {
                        "name": subcommand.group_name,
                        "description": subcommand.group_description,
                        "type": int(OptionTypes.SUB_COMMAND_GROUP),
                        "options": [],
                    }
                groups[subcommand.group_name]["options"].append(
                    subcommand.to_dict() | {"type": int(OptionTypes.SUB_COMMAND)}
                )
            else:
                sub_cmds.append(subcommand.to_dict() | {"type": int(OptionTypes.SUB_COMMAND)})
        options = [g for g in groups.values()] + sub_cmds
        output_data["options"] = options
        return output_data

    for scope, cmds in commands.items():
        for cmd in cmds.values():
            if cmd.name not in cmd_bases:
                cmd_bases[cmd.name] = [cmd]
                continue
            if cmd not in cmd_bases[cmd.name]:
                cmd_bases[cmd.name].append(cmd)

    for cmd_list in cmd_bases.values():
        if any(c.is_subcommand for c in cmd_list):
            # validate all commands share required attributes
            scopes: list[Snowflake_Type] = list(set(s for c in cmd_list for s in c.scopes))
            permissions: list = list(set(d for c in cmd_list for d in c.permissions))
            base_description = next(
                (c.description for c in cmd_list if c.description is not None), "No Description Set"
            )

            if not all(c.description in (base_description, "No Description Set") for c in cmd_list):
                log.warning(
                    f"Conflicting descriptions found in `{cmd_list[0].name}` subcommands; `{base_description}` will be used"
                )
            if not all(c.default_permission == cmd_list[0].default_permission for c in cmd_list):
                raise ValueError(f"Conflicting `default_permission` values found in `{cmd_list[0].name}`")

            for cmd in cmd_list:
                cmd.scopes = list(scopes)
                cmd.permissions = permissions
                cmd.description = base_description
            # end validation of attributes
            cmd_data = squash_subcommand(cmd_list)
        else:
            scopes = cmd_list[0].scopes
            cmd_data = cmd_list[0].to_dict()
        for s in scopes:
            if s not in output:
                output[s] = [cmd_data]
                continue
            output[s].append(cmd_data)

    return output


def _compare_options(local_opt_list: dict, remote_opt_list: dict):
    if local_opt_list != remote_opt_list:
        if len(local_opt_list) != len(remote_opt_list):
            return False
        for i in range(len(local_opt_list)):
            local_option = local_opt_list[i]
            remote_option = remote_opt_list[i]
            if local_option["type"] == remote_option["type"]:
                if local_option["type"] in (OptionTypes.SUB_COMMAND_GROUP, OptionTypes.SUB_COMMAND):
                    if not _compare_options(local_option.get("options", []), remote_option.get("options", [])):
                        return False
                else:
                    if (
                        local_option["name"] != remote_option["name"]
                        or local_option["description"] != remote_option["description"]
                        or local_option["required"] != remote_option.get("required", False)
                        or local_option["autocomplete"] != remote_option.get("autocomplete", False)
                    ):
                        return False
            else:
                return False
    return True


def sync_needed(local_cmd: dict, remote_cmd: Optional[dict] = None) -> bool:
    """
    Compares a local application command to its remote counterpart to determine if a sync is required.

    Args:
        local_cmd: The local json representation of the command
        remote_cmd: The json representation of the command from Discord

    Returns:
        Boolean indicating if a sync is needed
    """
    if not remote_cmd:
        # No remote version, command must be new
        return True

    if (
        local_cmd["name"] != remote_cmd["name"]
        or local_cmd.get("description", "") != remote_cmd.get("description", "")
        or local_cmd["default_permission"] != remote_cmd["default_permission"]
    ):
        # basic comparison of attributes
        return True

    if remote_cmd["type"] == CommandTypes.CHAT_INPUT:
        try:
            if not _compare_options(local_cmd["options"], remote_cmd["options"]):
                # options are not the same, sync needed
                return True
        except KeyError:
            if "options" in local_cmd or "options" in remote_cmd:
                return True

    return False


def maybe_int(x):
    try:
        return int(x)
    except:
        return x


def parse_application_command_error(errors: dict, cmd, keys=None):
    messages = []
    prefix = ""

    for key, cmd_attribute in errors.items():
        if isinstance(cmd_attribute, dict) and cmd_attribute.get("_errors", None):
            for attrib_num, error_message in errors[key].items():
                messages.append(f"{key}: {', '.join([i['message'] for i in error_message])}")

        else:
            if not keys:
                keys = []
            keys.append(maybe_int(key))

            if out := parse_application_command_error(cmd_attribute, cmd, keys.copy()):
                if cmd:
                    x = cmd
                    for k in keys:
                        try:
                            x = x[k]
                        except KeyError as e:
                            pass
                    if isinstance(x, dict):
                        key = x.get("name", key)
                        out = [f"`{key}` --> {o}" for o in out]

                messages += out

    return messages
