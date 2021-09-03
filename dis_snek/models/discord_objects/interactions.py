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
from typing import TYPE_CHECKING, Callable, Coroutine, Dict, List, Union, Optional

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
from dis_snek.utils.serializer import no_export_meta, to_dict

if TYPE_CHECKING:
    from dis_snek.models.snowflake import Snowflake_Type


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

    :param id: The id of the role or user.
    :param type: The type of id (user or role)
    :permission: The state of permission. ``True`` to allow, ``False``, to disallow.
    """

    id: "Snowflake_Type" = attr.ib()
    type: Union[PermissionTypes, int] = attr.ib()
    permission: bool = attr.ib()

    def to_dict(self) -> dict:
        """
        Convert this object into a dict ready for discord.

        :return: dict
        """
        return attr.asdict(self)


@attr.s(slots=True, kw_only=True, on_setattr=[attr.setters.convert, attr.setters.validate])
class InteractionCommand(BaseCommand):
    """
    Represents a discord abstract interaction command.

    :param scope: Denotes whether its global or for specific guild.
    :param default_permission: Is this command available to all users?
    :param permissions: Map of guild id and its respective list of permissions to apply.
    :param cmd_id: The id of this command given by discord.
    :param callback: The coroutine to callback when this interaction is received.
    """

    name: str = attr.ib()

    scope: "Snowflake_Type" = attr.ib(default=GLOBAL_SCOPE, converter=to_snowflake, metadata=no_export_meta)
    default_permission: bool = attr.ib(default=True)
    permissions: Dict["Snowflake_Type", Union[Permission, Dict]] = attr.ib(factory=dict)

    cmd_id: "Snowflake_Type" = attr.ib(default=None, metadata=no_export_meta)
    callback: Callable[..., Coroutine] = attr.ib(default=None, metadata=no_export_meta)


@attr.s(slots=True, kw_only=True, on_setattr=[attr.setters.convert, attr.setters.validate])
class ContextMenu(InteractionCommand):
    """
    Represents a discord context menu.

    :param name: The name of this entry.
    :param type: The type of entry (user or message).
    """

    name: str = attr.ib()
    type: CommandTypes = attr.ib()

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

    :param name: The name the user will see
    :param value: The data sent to your code when this choice is used
    """

    name: str = attr.ib()
    value: Union[str, int, float] = attr.ib()


@attr.s(slots=True, on_setattr=[attr.setters.convert, attr.setters.validate])
class SlashCommandOption(DictSerializationMixin):
    """
    Represents a discord slash command option.

    :param name: The name of this option
    :param type: The type of option
    :param description: The description of this option
    :param required: "This option must be filled to use the command"
    :param choices: A list of choices the user has to pick between
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

    :param name: The name of this command.
    :param description: The description of this command.
    :param options: A list of options for this command.
    """

    name: str = attr.ib()
    description: str = attr.ib(default="No Description Set")
    options: List[Union[SlashCommandOption, "SubCommand", Dict]] = attr.ib(factory=list)

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
                if any(opt.type != (OptionTypes.SUB_COMMAND, OptionTypes.SUB_COMMAND_GROUP) for opt in value):
                    raise ValueError("Options aren't supported when subcommands are defined")

    def add_subcommand(
        self,
        subcommand_name: str,
        subcommand_description: str = "No Description Set",
        group_name: str = None,
        group_description: str = "No Description Set",
        options: List = None,
    ):
        """Add a subcommand"""
        cmd = SubCommand(name=subcommand_name, description=subcommand_description, options=options)
        if group_name:
            for option in self.options:
                if option.type == OptionTypes.SUB_COMMAND_GROUP and option.name == group_name:
                    return option.options.append(cmd)
            group = SubCommand(
                name=group_name, description=group_description, type=OptionTypes.SUB_COMMAND_GROUP, options=[cmd]
            )
            self.options.append(group)
            return
        if not self.options:
            self.options = []
        self.options.append(cmd)


@attr.s(slots=True, kw_only=True, on_setattr=[attr.setters.convert, attr.setters.validate])
class SubCommand(SlashCommand):
    type: OptionTypes = attr.ib(default=OptionTypes.SUB_COMMAND)


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
    sub_cmd_description: str = None,
    group_name: str = None,
    group_description: str = None,
):
    def wrapper(func):
        if not asyncio.iscoroutinefunction(func):
            raise ValueError("Commands must be coroutines")

        cmd = SlashCommand(
            name=name,
            description=description,
            scope=scope,
            callback=func,
            options=options if not sub_cmd_name else None,
            default_permission=default_permission,
            permissions=permissions,
        )

        func.cmd_id = f"{scope}::{name}"
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


def slash_permission(guild_id: "Snowflake_Type", permissions: List[Union[Permission, Dict]]):
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
