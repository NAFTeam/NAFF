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
from dis_snek.models.discord_objects.role import Role
import re
from enum import IntEnum
from typing import Callable, Coroutine, Dict, List, Union

import attr

from dis_snek.models.discord_objects.channel import BaseChannel
from dis_snek.models.discord_objects.user import BaseUser
from dis_snek.models.enums import InteractionType
from dis_snek.models.snowflake import Snowflake_Type


class OptionType(IntEnum):
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
    def from_type(cls, t: type):
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


class PermissionType(IntEnum):

    ROLE = 1
    USER = 2

    @classmethod
    def from_type(cls, t: type):
        if issubclass(t, Role):
            return cls.ROLE
        if issubclass(t, BaseUser):
            return cls.USER


class CallbackType(IntEnum):
    """Types of callback supported by interaction response."""

    PONG = 1
    CHANNEL_MESSAGE_WITH_SOURCE = 4
    DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE = 5
    DEFERRED_UPDATE_MESSAGE = 6
    UPDATE_MESSAGE = 7


@attr.s(slots=True)
class Permission:

    id: Snowflake_Type = attr.ib()
    type: Union[PermissionType, int] = attr.ib()
    permission: bool = attr.ib()

    def to_dict(self) -> dict:
        """
        Convert this object into a dict ready for discord.

        :return: dict
        """
        return attr.asdict(self)


@attr.s(slots=True, on_setattr=[attr.setters.convert, attr.setters.validate])
class ContextMenu:
    """
    Represents a discord context menu.

    :param name: The name of this entry
    :param type: The type of entry (user or message)
    :param call: The coroutine to call when this interaction is received
    """

    name: str = attr.ib()
    type: InteractionType = attr.ib()
    scope: Snowflake_Type = attr.ib(default="global", converter=str)
    default_permission: bool = attr.ib(default=True)
    permissions: Dict[Snowflake_Type, Union[Permission, Dict]] = attr.ib(factory=dict)

    cmd_id: Snowflake_Type = attr.ib(default=None)
    call: Callable[..., Coroutine] = attr.ib(default=None)

    @name.validator
    def _name_validator(self, attribute: str, value: str) -> None:
        if not 1 <= len(value) <= 32:
            raise ValueError("Context Menu name attribute must be between 1 and 32 characters")

    @type.validator
    def _type_validator(self, attribute: str, value: int):
        if not isinstance(value, InteractionType):
            if value not in InteractionType.__members__.values():
                raise ValueError("Context Menu type not recognised, please consult the docs.")

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
    type: Union[OptionType, int] = attr.ib()
    description: str = attr.ib(default="No Description Set")
    required: bool = attr.ib(default=True)
    choices: List[Union[SlashCommandChoice, Dict]] = attr.ib(factory=list)

    @name.validator
    def _name_validator(self, attribute: str, value: str) -> None:
        if not re.match(r"^[\w-]{1,32}$", value) or value != value.lower():
            raise ValueError("Options names must be lower case and match this regex: ^[\w-]{1,32}$")  # noqa: W605

    @description.validator
    def _description_validator(self, attribute: str, value: str) -> None:
        if not 1 <= len(value) <= 100:
            raise ValueError("Options must be between 1 and 100 characters long")

    def to_dict(self) -> dict:
        """
        Convert this object into a dict ready for discord.

        :return: dict
        """
        return attr.asdict(self, filter=lambda key, value: isinstance(value, bool) or value)


@attr.s(slots=True, on_setattr=[attr.setters.convert, attr.setters.validate])
class SlashCommand:
    """
    Represents a discord slash command.

    :param name: The name of this command
    :param description: The description of this command
    :param options: A list of options for this command
    :param default_permission: Is this command available to all users?
    """

    name: str = attr.ib()
    description: str = attr.ib(default="No Description Set")
    scope: Snowflake_Type = attr.ib(default="global", converter=str)
    options: List[Union[SlashCommandOption, Dict]] = attr.ib(factory=list)
    default_permission: bool = attr.ib(default=True)
    permissions: Dict[Snowflake_Type, Union[Permission, Dict]] = attr.ib(factory=dict)
    cmd_id: Snowflake_Type = attr.ib(default=None)
    call: Callable[..., Coroutine] = attr.ib(default=None)

    @name.validator
    def _name_validator(self, attribute: str, value: str) -> None:
        if not re.match(r"^[\w-]{1,32}$", value) or value != value.lower():
            raise ValueError(
                "Slash Command option names must be lower case and match this regex: ^[\w-]{1,32}$"
            )  # noqa: W605

    @description.validator
    def _description_validator(self, attribute: str, value: str) -> None:
        if not 1 <= len(value) <= 100:
            raise ValueError("Description must be between 1 and 100 characters long")

    @options.validator
    def _options_validator(self, attribute: str, value: List) -> None:
        if value:
            if isinstance(value, list):
                if len(value) > 25:
                    raise ValueError("Slash commands can only hold 25 options")
            else:
                raise TypeError("Options attribute must be either None or a list of options")

    def to_dict(self) -> dict:
        """
        Convert this object into a dict ready for discord.

        :return: dict
        """
        self._name_validator("name", self.name)
        self._description_validator("description", self.description)
        self._options_validator("options", self.options)

        # Don't convert None or empty data structures
        data = attr.asdict(self, filter=lambda key, value: isinstance(value, bool) or value)

        # remove internal data from dictionary
        data.pop("scope", None)
        data.pop("call", None)
        data.pop("cmd_id", None)

        return data
