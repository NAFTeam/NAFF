import asyncio
import inspect
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
)
from dis_snek.mixins.serialization import DictSerializationMixin
from dis_snek.models.command import BaseCommand
from dis_snek.models.discord_objects.channel import BaseChannel
from dis_snek.models.discord_objects.role import Role
from dis_snek.models.discord_objects.user import BaseUser
from dis_snek.models.enums import CommandTypes
from dis_snek.models.snowflake import to_snowflake, to_snowflake_list
from dis_snek.utils.attr_utils import docs
from dis_snek.utils.serializer import no_export_meta

if TYPE_CHECKING:
    from dis_snek.models.snowflake import Snowflake_Type
    from dis_snek.models.context import InteractionContext


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


@attr.s(slots=True)
class Permission:
    """
    Represents a interaction permission.

    parameters:
        id: The id of the role or user.
        type: The type of id (user or role)
        permission: The state of permission. ``True`` to allow, ``False``, to disallow.
    """

    id: "Snowflake_Type" = attr.ib(converter=to_snowflake)
    type: Union[PermissionTypes, int] = attr.ib(converter=PermissionTypes)
    permission: bool = attr.ib(default=True)

    def to_dict(self) -> dict:
        """
        Convert this object into a dict ready for discord.

        returns:
            Representation of this object
        """
        return attr.asdict(self)


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
    permissions: Dict["Snowflake_Type", Union[Permission, Dict]] = attr.ib(
        factory=dict, metadata=docs("The permissions of this interaction")
    )

    cmd_id: "Snowflake_Type" = attr.ib(
        default=None, metadata=docs("The unique ID of this interaction") | no_export_meta
    )
    callback: Callable[..., Coroutine] = attr.ib(
        default=None, metadata=docs("The coroutine to call when this interaction is received") | no_export_meta
    )

    @property
    def resolved_name(self):
        """A representation of this interaction's name"""
        return self.name


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
    """

    name: str = attr.ib()
    type: Union[OptionTypes, int] = attr.ib()
    description: str = attr.ib(default="No Description Set")
    required: bool = attr.ib(default=True)
    autocomplete: bool = attr.ib(default=False)
    choices: List[Union[SlashCommandChoice, Dict]] = attr.ib(factory=list)

    @name.validator
    def _name_validator(self, attribute: str, value: str) -> None:
        if not re.match(rf"^[\w-]{{1,{SLASH_CMD_NAME_LENGTH}}}$", value) or value != value.lower():
            raise ValueError(
                f"Options names must be lower case and match this regex: ^[\w-]{1,{SLASH_CMD_NAME_LENGTH}}$"
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


@attr.s(slots=True, kw_only=True, on_setattr=[attr.setters.convert, attr.setters.validate])
class _SlashCommandMeta(InteractionCommand):
    name: str = attr.ib()
    description: str = attr.ib("No Description Set")

    options: List[Union[SlashCommandOption, Dict]] = attr.ib(factory=list)
    autocomplete_callbacks: dict = attr.ib(factory=dict, metadata=no_export_meta)

    def __attrs_post_init__(self):
        if self.callback is not None:
            if hasattr(self.callback, "options"):
                if not self.options:
                    self.options = []
                self.options += self.callback.options

            if hasattr(self.callback, "permissions"):
                self.permissions = self.callback.permissions
        super().__attrs_post_init__()

    @name.validator
    def name_validator(self, attribute: str, value: str) -> None:
        if value:
            if not re.match(rf"^[\w-]{{1,{SLASH_CMD_NAME_LENGTH}}}$", value) or value != value.lower():
                raise ValueError(
                    f"Slash Command names must be lower case and match this regex: ^[\w-]{1, {SLASH_CMD_NAME_LENGTH} }$"
                )  # noqa: W605

    @description.validator
    def description_validator(self, attribute: str, value: str) -> None:
        if not 1 <= len(value) <= SLASH_CMD_MAX_DESC_LENGTH:
            raise ValueError(f"Description must be between 1 and {SLASH_CMD_MAX_DESC_LENGTH} characters long")

    @options.validator
    def options_validator(self, attribute: str, value: List) -> None:
        if value:
            if isinstance(value, list):
                if len(value) > SLASH_CMD_MAX_OPTIONS:
                    raise ValueError(f"Slash commands can only hold {SLASH_CMD_MAX_OPTIONS} options")
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


@attr.s(slots=True, kw_only=True, on_setattr=[attr.setters.convert, attr.setters.validate])
class SlashCommand(_SlashCommandMeta):
    """
    Represents a discord slash command.

    parameters:
        name: The name of this command.
        description: The description of this command.
        options: A list of options for this command.
    """

    subcommands: Dict[str, "SubCommand"] = attr.ib(factory=dict, metadata=no_export_meta)

    def to_dict(self) -> Dict[str, Any]:

        if self.subcommands:
            # we're dealing with subcommands, behave differently
            self.options = []
            json = super().to_dict()
            groups = {}
            sub_cmds = []
            for sc in self.subcommands.values():
                if sc.group_name:
                    if sc.group_name not in groups.keys():
                        groups[sc.group_name] = {
                            "name": sc.group_name,
                            "description": sc.group_description,
                            "type": OptionTypes.SUB_COMMAND_GROUP,
                            "options": [sc.to_dict()],
                        }
                        continue
                    groups[sc.group_name]["options"].append(sc.to_dict())
                else:
                    sub_cmds.append(sc.to_dict())
            options = [g for g in groups.values()] + sub_cmds
            json["options"] = options
            return json
        else:
            return super().to_dict()

    async def _subcommand_call_no_wrap(self, context: "InteractionContext", *args, **kwargs):
        if call := self.subcommands.get(context.invoked_name):
            return await call(context, *args, **kwargs)
        breakpoint()
        raise ValueError(f"Error {context.invoked_name} is not a known subcommand")

    def subcommand(
        self,
        sub_cmd_name: str,
        group_name: str = None,
        group_description: str = "No Description Set",
        sub_cmd_description: str = "No Description Set",
        options: List[Union[SlashCommandOption, Dict]] = None,
    ) -> Callable[..., "SubCommand"]:
        def wrapper(call: Callable[..., Coroutine]) -> "SubCommand":
            if not asyncio.iscoroutinefunction(call):
                raise TypeError("Subcommand must be coroutine")

            self.callback = self._subcommand_call_no_wrap

            sub = SubCommand(
                name=self.name,
                description=self.description,
                group_name=group_name,
                group_description=group_description,
                subcommand_name=sub_cmd_name,
                subcommand_description=sub_cmd_description,
                options=options,
                scopes=self.scopes,
                callback=call,
            )
            self.subcommands[sub.resolved_name] = sub
            return sub

        return wrapper


@attr.s(slots=True, kw_only=True, on_setattr=[attr.setters.convert, attr.setters.validate])
class SubCommand(_SlashCommandMeta):
    group_name: str = attr.ib(default=None, metadata=no_export_meta)
    group_description: str = attr.ib(default=None, metadata=no_export_meta)

    subcommand_name: str = attr.ib(default=None, metadata=no_export_meta)
    subcommand_description: str = attr.ib(default=None, metadata=no_export_meta)

    @group_name.validator
    @subcommand_name.validator
    def _name_validator(self, attribute: str, value: str) -> None:
        return self.name_validator(attribute, value)

    @group_description.validator
    @subcommand_description.validator
    def _description_validator(self, attribute: str, value: str) -> None:
        return self.description_validator(attribute, value)

    @property
    def resolved_name(self):
        return f"{self.name} {f'{self.group_name} ' if self.group_name else ''}{self.subcommand_name}"

    def to_dict(self) -> dict:
        return super().to_dict() | {
            "name": self.subcommand_name,
            "description": self.subcommand_description,
            "type": OptionTypes.SUB_COMMAND,
        }


@attr.s(slots=True, kw_only=True, on_setattr=[attr.setters.convert, attr.setters.validate])
class ComponentCommand(InteractionCommand):
    # right now this adds no extra functionality, but for future dev ive implemented it
    listeners: list[str] = attr.ib(factory=list)


##############
# Decorators #
##############


def slash_command(
    name: str,
    description: str = "No description set",
    scopes: List["Snowflake_Type"] = MISSING,
    options: Optional[List[Union[SlashCommandOption, Dict]]] = None,
    default_permission: bool = True,
    permissions: Optional[Dict["Snowflake_Type", Union[Permission, Dict]]] = None,
    sub_cmd_name: str = None,
    group_name: str = None,
    sub_cmd_description: str = "No description set",
    group_description: str = "No description set",
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

        if not sub_cmd_name:

            cmd = SlashCommand(
                name=name,
                description=description,
                scopes=scopes if scopes else [GLOBAL_SCOPE],
                default_permission=default_permission,
                permissions=permissions,
                callback=func,
                options=options,
            )

        else:
            cmd = SlashCommand(
                name=name,
                description=description,
                scopes=scopes if scopes else [GLOBAL_SCOPE],
                default_permission=default_permission,
                permissions=permissions,
            )
            cmd.subcommand(
                group_name=group_name,
                sub_cmd_name=sub_cmd_name,
                group_description=group_description,
                sub_cmd_description=sub_cmd_description,
                options=options,
            )(func)

        return cmd

    return wrapper


def context_menu(
    name: str,
    context_type: "CommandTypes",
    scopes: List["Snowflake_Type"] = MISSING,
    default_permission: bool = True,
    permissions: Optional[Dict["Snowflake_Type", Union[Permission, Dict]]] = None,
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

        perm = permissions
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
) -> Any:
    """
    A decorator to add an option to a slash command.

    parameters:
        name: 1-32 lowercase character name matching ^[\w-]{1,32}$
        opt_type: The type of option
        description: 1-100 character description of option
        required: If the parameter is required or optional--default false
        choices: A list of choices the user has to pick between (max 25)
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
        )
        if not hasattr(func, "options"):
            func.options = []
        func.options.insert(0, option)
        return func

    return wrapper


def slash_permission(guild_id: "Snowflake_Type", permissions: List[Union[Permission, Dict]]) -> Any:
    """
    A decorator to add permissions for a guild to a slash command or context menu.

    parameters:
        guild_id: The target guild to apply the permissions.
        permissions: A list of interaction permission rights.
    """
    guild_id = to_snowflake(guild_id)

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
