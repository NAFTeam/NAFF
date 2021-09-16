"""
The MIT License (MIT).

Copyright (c) 2021 - present LordOfPolls

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""
import asyncio
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
)
from dis_snek.mixins.serialization import DictSerializationMixin
from dis_snek.models.command import BaseCommand
from dis_snek.models.discord_objects.channel import BaseChannel
from dis_snek.models.discord_objects.role import Role
from dis_snek.models.discord_objects.user import BaseUser
from dis_snek.models.enums import CommandTypes
from dis_snek.models.snowflake import to_snowflake
from dis_snek.utils.serializer import no_export_meta

if TYPE_CHECKING:
    from dis_snek.models.snowflake import Snowflake_Type
    from dis_snek.models.discord_objects.context import InteractionContext


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

        :param t: The datatype to convert
        :return: OptionType or None
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
        # todo role
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


@attr.s(slots=True)
class Permission:
    """
    Represents a interaction permission.

    parameters:
        id: The id of the role or user.
        type: The type of id (user or role)
        permission: The state of permission. ``True`` to allow, ``False``, to disallow.
    """

    id: "Snowflake_Type" = attr.ib()
    type: Union[PermissionTypes, int] = attr.ib()
    permission: bool = attr.ib()

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

    name: str = attr.ib()
    """1-32 character name"""

    scope: "Snowflake_Type" = attr.ib(default=GLOBAL_SCOPE, converter=to_snowflake, metadata=no_export_meta)
    """The scope of this interaction. Global or guild ids"""
    default_permission: bool = attr.ib(default=True)
    """whether the command is enabled by default when the app is added to a guild"""
    permissions: Dict["Snowflake_Type", Union[Permission, Dict]] = attr.ib(factory=dict)
    """The permissions of this interaction"""

    cmd_id: "Snowflake_Type" = attr.ib(default=None, metadata=no_export_meta)
    """The unique ID of this interaction"""
    callback: Callable[..., Coroutine] = attr.ib(default=None, metadata=no_export_meta)
    """The coroutine to call when this interaction is received"""

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

    name: str = attr.ib()
    """1-32 character name"""
    type: CommandTypes = attr.ib()
    """the type of command, defaults 1 if not set"""

    @name.validator
    def _name_validator(self, attribute: str, value: str) -> None:
        if not 1 <= len(value) <= CONTEXT_MENU_NAME_LENGTH:
            raise ValueError("Context Menu name attribute must be between 1 and 32 characters")

    @type.validator
    def _type_validator(self, attribute: str, value: int):
        if not isinstance(value, CommandTypes):
            if value not in CommandTypes.__members__.values():
                raise ValueError("Context Menu type not recognised, please consult the docs.")


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


@attr.s(slots=True, kw_only=True, on_setattr=[attr.setters.convert, attr.setters.validate])
class SlashCommand(InteractionCommand):
    """
    Represents a discord slash command.

    parameters:
        name: The name of this command.
        description: The description of this command.
        options: A list of options for this command.
    """

    name: str = attr.ib()
    description: str = attr.ib(default="No Description Set")
    options: List[Union[SlashCommandOption, Dict]] = attr.ib(factory=list)
    subcommand_callbacks: dict = attr.ib(factory=dict, metadata=no_export_meta)

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
    def _name_validator(self, attribute: str, value: str) -> None:
        if not re.match(rf"^[\w-]{{1,{SLASH_CMD_NAME_LENGTH}}}$", value) or value != value.lower():
            raise ValueError(
                f"Slash Command names must be lower case and match this regex: ^[\w-]{1, {SLASH_CMD_NAME_LENGTH} }$"
            )  # noqa: W605

    @description.validator
    def _description_validator(self, attribute: str, value: str) -> None:
        if not 1 <= len(value) <= SLASH_CMD_MAX_DESC_LENGTH:
            raise ValueError(f"Description must be between 1 and {SLASH_CMD_MAX_DESC_LENGTH} characters long")

    @options.validator
    def _options_validator(self, attribute: str, value: List) -> None:
        if value:
            if isinstance(value, list):
                if len(value) > SLASH_CMD_MAX_OPTIONS:
                    raise ValueError(f"Slash commands can only hold {SLASH_CMD_MAX_OPTIONS} options")
            else:
                raise TypeError("Options attribute must be either None or a list of options")

            if any(opt.type in (OptionTypes.SUB_COMMAND, OptionTypes.SUB_COMMAND_GROUP) for opt in value):
                if any(opt.type not in (OptionTypes.SUB_COMMAND, OptionTypes.SUB_COMMAND_GROUP) for opt in value):
                    raise ValueError("Options aren't supported when subcommands are defined")


@attr.s(slots=True, kw_only=True, on_setattr=[attr.setters.convert, attr.setters.validate])
class SubCommand(SlashCommand):
    options: List[Union[SlashCommandOption, Dict]] = attr.ib(factory=list)

    group_name: str = attr.ib(default=None, metadata=no_export_meta)
    group_description: str = attr.ib(default=None, metadata=no_export_meta)

    subcommand_name: str = attr.ib(default=None, metadata=no_export_meta)
    subcommand_description: str = attr.ib(default=None, metadata=no_export_meta)

    @property
    def resolved_name(self):
        return f"{self.name} {f'{self.group_name} ' if self.group_name else ''}{self.subcommand_name}"

    async def subcommand_call(self, context: "InteractionContext", *args, **kwargs):
        if call := self.subcommand_callbacks.get(context.invoked_name):
            return await call(context, *args, **kwargs)
        raise ValueError(f"Error {context.invoked_name} is not a known subcommand")

    def child_to_dict(self):
        sub_cmd = {
            "name": self.subcommand_name,
            "description": self.subcommand_description,
            "type": OptionTypes.SUB_COMMAND,
            "options": [opt.to_dict() if hasattr(opt, "to_dict") else opt for opt in self.options],
        }
        if self.group_name:
            sub_cmd = {
                "name": self.group_name,
                "description": self.group_description,
                "type": OptionTypes.SUB_COMMAND_GROUP,
                "options": [sub_cmd],
            }
        return sub_cmd

    def to_dict(self):
        parent = super().to_dict()
        return parent


##############
# Decorators #
##############


def slash_command(
    name: str,
    description: str = "No description set",
    scope: "Snowflake_Type" = GLOBAL_SCOPE,
    options: Optional[List[Union[SlashCommandOption, Dict]]] = None,
    default_permission: bool = True,
    permissions: Optional[Dict["Snowflake_Type", Union[Permission, Dict]]] = None,
    sub_cmd_name: str = None,
    sub_cmd_description: str = "No description set",
    group_name: str = None,
    group_description: str = "No description set",
):
    """
    A decorator to declare a coroutine as a slash command.

    ..note: While the base and group descriptions arent visible in the discord client, currently.
    We strongly advise defining them anyway, if you're using subcommands, as Discord has said they will be visible in
    one of the future ui updates.

    :param name: 1-32 character name of the command
    :param description: 1-100 character description of the command
    :param scope: The scope this command exists within
    :param options: The parameters for the command, max 25
    :param default_permission: Whether the command is enabled by default when the app is added to a guild
    :param permissions: The roles or users who can use this command
    :param sub_cmd_name: 1-32 character name of the subcommand
    :param sub_cmd_description: 1-100 character description of the subcommand
    :param group_name: 1-32 character name of the group
    :param group_description: 1-100 character description of the group
    :return: SlashCommand Object
    """

    def wrapper(func) -> SlashCommand:
        if not asyncio.iscoroutinefunction(func):
            raise ValueError("Commands must be coroutines")

        if not sub_cmd_name:
            cmd = SlashCommand(
                name=name,
                description=description,
                scope=scope,
                callback=func,
                options=options,
                default_permission=default_permission,
                permissions=permissions,
            )
        else:
            cmd = SubCommand(
                name=name,
                description=description,
                subcommand_name=sub_cmd_name,
                subcommand_description=sub_cmd_description,
                group_name=group_name,
                group_description=group_description,
                options=options,
                callback=func,
                scope=scope,
                default_permission=default_permission,
                permissions=permissions,
            )

        func.cmd_id = f"{scope}::{name}"
        return cmd

    return wrapper


def sub_command(
    base_name: str,
    sub_name: str,
    group_name: str = None,
    base_description: str = "No Description set",
    sub_description: str = "No Description set",
    group_description: str = "No Description set",
    scope: "Snowflake_Type" = GLOBAL_SCOPE,
    options: Optional[List[Union[SlashCommandOption, Dict]]] = None,
    default_permission: bool = True,
    permissions: Optional[Dict["Snowflake_Type", Union[Permission, Dict]]] = None,
):
    """
    A decorator to declare a coroutine as a slash subcommand.

    ..note: While the base and group descriptions arent visible in the discord client, currently.
    We strongly advise defining them anyway, if you're using subcommands, as Discord has said they will be visible in
    one of the future ui updates.

    :param base_name: The name of the base command
    :param sub_name: The name of the subcommand
    :param group_name: The name of the command group (optional)
    :param base_description: The description of the base command
    :param sub_description: The description of the subcommand
    :param group_description: The description of the command group
    :param scope: The scope this command exists within
    :param options: The parameters for the command, max 25
    :param default_permission: Whether the command is enabled by default when the app is added to a guild
    :param permissions: The roles or users who can use this command
    :return:
    """

    def wrapper(func) -> SlashCommand:
        cmd = SubCommand(
            name=base_name,
            description=base_description,
            subcommand_name=sub_name,
            subcommand_description=sub_description,
            group_name=group_name,
            group_description=group_description,
            options=options,
            callback=func,
            scope=scope,
            default_permission=default_permission,
            permissions=permissions,
        )

        func.cmd_id = f"{scope}::{base_name}"
        return cmd

    return wrapper


def context_menu(
    name: str,
    context_type: "CommandTypes",
    scope: "Snowflake_Type",
    default_permission: bool = True,
    permissions: Optional[Dict["Snowflake_Type", Union[Permission, Dict]]] = None,
):
    """
    A decorator to declare a coroutine as a Context Menu

    :param name: 1-32 character name of the context menu
    :param context_type: The type of context menu
    :param scope: The scope this command exists within
    :param default_permission: Whether the menu is enabled by default when the app is added to a guild
    :param permissions: The roles or users who can use this menu
    :return: ContextMenu object
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
            scope=scope,
            default_permission=default_permission,
            permissions=perm,
            callback=func,
        )
        return cmd

    return wrapper


def slash_option(
    name: str,
    description: str,
    opt_type: Union[OptionTypes, int],
    required: bool = False,
    choices: List[Union[SlashCommandChoice, dict]] = None,
) -> Any:
    """
    A decorator to add an option to a slash command.

    :param name: 1-32 lowercase character name matching ^[\w-]{1,32}$
    :param opt_type: The type of option
    :param description: 1-100 character description of option
    :param required: If the parameter is required or optional--default false
    :param choices: A list of choices the user has to pick between (max 25)
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


def slash_permission(guild_id: "Snowflake_Type", permissions: List[Union[Permission, Dict]]) -> Any:
    """
    A decorator to add permissions for a guild to a slash command or context menu.

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
