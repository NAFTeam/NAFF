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
import re
from enum import IntEnum
from typing import TYPE_CHECKING, Callable, Coroutine, Dict, List, Union

import attr

from dis_snek.const import (
    GLOBAL_SCOPE,
    CONTEXT_MENU_NAME_LENGTH,
    SLASH_OPTION_NAME_LENGTH,
    SLASH_CMD_NAME_LENGTH,
    SLASH_CMD_MAX_OPTIONS,
    SLASH_CMD_MAX_DESC_LENGTH,
)
from dis_snek.models.discord_objects.channel import BaseChannel
from dis_snek.models.discord_objects.role import Role
from dis_snek.models.discord_objects.user import BaseUser
from dis_snek.models.enums import CommandTypes
from dis_snek.models.snowflake import to_snowflake

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
class BaseInteractionCommand:
    """
    Represents a discord abstract interaction command.

    :param scope: Denotes whether its global or for specific guild.
    :param default_permission: Is this command available to all users?
    :param permissions: Map of guild id and its respective list of permissions to apply.
    :param cmd_id: The id of this command given by discord.
    :param call: The coroutine to call when this interaction is received.
    """

    scope: "Snowflake_Type" = attr.ib(default=GLOBAL_SCOPE, converter=to_snowflake)
    default_permission: bool = attr.ib(default=True)
    permissions: Dict["Snowflake_Type", Union[Permission, Dict]] = attr.ib(factory=dict)

    cmd_id: "Snowflake_Type" = attr.ib(default=None)
    call: Callable[..., Coroutine] = attr.ib(default=None)

    def to_dict(self) -> dict:
        """
        Convert this object into a dict ready for discord.

        :return: dict
        """
        data = attr.asdict(self, filter=lambda key, value: isinstance(value, bool) or value)

        # remove internal data from dictionary
        data.pop("scope", None)
        data.pop("call", None)
        data.pop("cmd_id", None)

        return data


@attr.s(slots=True, kw_only=True, on_setattr=[attr.setters.convert, attr.setters.validate])
class ContextMenu(BaseInteractionCommand):
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
class SlashCommandChoice:
    """
    Represents a discord slash command choice.

    :param name: The name the user will see
    :param value: The data sent to your code when this choice is used
    """

    name: str = attr.ib()
    value: Union[str, int, float] = attr.ib()

    def to_dict(self) -> dict:
        """
        Convert this object into a dict ready for discord.

        :return: dict
        """
        return attr.asdict(self)


@attr.s(slots=True, on_setattr=[attr.setters.convert, attr.setters.validate])
class SlashCommandOption:
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

    def to_dict(self) -> dict:
        """
        Convert this object into a dict ready for discord.

        :return: dict
        """
        return attr.asdict(self, filter=lambda key, value: isinstance(value, bool) or value)


@attr.s(slots=True, kw_only=True, on_setattr=[attr.setters.convert, attr.setters.validate])
class SlashCommand(BaseInteractionCommand):
    """
    Represents a discord slash command.

    :param name: The name of this command.
    :param description: The description of this command.
    :param options: A list of options for this command.
    """

    name: str = attr.ib()
    description: str = attr.ib(default="No Description Set")
    options: List[Union[SlashCommandOption, Dict]] = attr.ib(factory=list)

    @name.validator
    def _name_validator(self, attribute: str, value: str) -> None:
        if not re.match(rf"^[\w-]{{1,{SLASH_CMD_NAME_LENGTH}}}$", value) or value != value.lower():
            raise ValueError(
                f"Slash Command names must be lower case and match this regex: ^[\w-]{1, {SLASH_CMD_NAME_LENGTH} }$"
            )  # noqa: W605

    @description.validator
    def _description_validator(self, attribute: str, value: str) -> None:
        if not 1 <= len(value) <= SLASH_CMD_MAX_DESC_LENGTH:
            raise ValueError("Description must be between 1 and 100 characters long")

    @options.validator
    def _options_validator(self, attribute: str, value: List) -> None:
        if value:
            if isinstance(value, list):
                if len(value) > SLASH_CMD_MAX_OPTIONS:
                    raise ValueError(f"Slash commands can only hold {SLASH_CMD_MAX_OPTIONS} options")
            else:
                raise TypeError("Options attribute must be either None or a list of options")
