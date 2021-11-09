from typing import Union, List, Optional, Type

from dis_snek.models import (
    OptionTypes,
    SlashCommandChoice,
    ChannelTypes,
    SlashCommandOption,
    User,
    BaseChannel,
    Role,
    Member,
)


def slash_str_option(
    description: str,
    required: bool = False,
    autocomplete: bool = False,
    choices: List[Union[SlashCommandChoice, dict]] = None,
) -> Type[str]:
    """
    Annotates an argument as a string type slash command option.

    Args:
        description: The description of your option
        required: Is this option required?
        autocomplete: Use autocomplete for this option
        choices: The choices allowed by this command
    """
    option = SlashCommandOption(
        name="placeholder",
        description=description,
        required=required,
        autocomplete=autocomplete,
        choices=choices,
        type=OptionTypes.STRING,
    )
    return option  # type: ignore


def slash_float_option(
    description: str,
    required: bool = False,
    autocomplete: bool = False,
    choices: List[Union[SlashCommandChoice, dict]] = None,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
) -> Type[float]:
    """
    Annotates an argument as a float type slash command option.

    Args:
        description: The description of your option
        required: Is this option required?
        autocomplete: Use autocomplete for this option
        choices: The choices allowed by this command
        min_value:
        max_value:
    """
    option = SlashCommandOption(
        name="placeholder",
        description=description,
        required=required,
        autocomplete=autocomplete,
        choices=choices,
        max_value=max_value,
        min_value=min_value,
        type=OptionTypes.NUMBER,
    )
    return option  # type: ignore


def slash_int_option(
    description: str,
    required: bool = False,
    autocomplete: bool = False,
    choices: List[Union[SlashCommandChoice, dict]] = None,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
) -> Type[int]:
    """
    Annotates an argument as a integer type slash command option.

    Args:
        description: The description of your option
        required: Is this option required?
        autocomplete: Use autocomplete for this option
        choices: The choices allowed by this command
        min_value:
        max_value:
    """
    option = SlashCommandOption(
        name="placeholder",
        description=description,
        required=required,
        autocomplete=autocomplete,
        choices=choices,
        max_value=max_value,
        min_value=min_value,
        type=OptionTypes.INTEGER,
    )
    return option  # type: ignore


def slash_bool_option(
    description: str,
    required: bool = False,
) -> Type[bool]:
    """
    Annotates an argument as a boolean type slash command option.

    Args:
        description: The description of your option
        required: Is this option required?
    """
    option = SlashCommandOption(
        name="placeholder",
        description=description,
        required=required,
        type=OptionTypes.BOOLEAN,
    )
    return option  # type: ignore


def slash_user_option(
    description: str,
    required: bool = False,
    autocomplete: bool = False,
) -> Type[Union[User, Member]]:
    """
    Annotates an argument as a user type slash command option.

    Args:
        description: The description of your option
        required: Is this option required?
        autocomplete: Use autocomplete for this option
    """
    option = SlashCommandOption(
        name="placeholder",
        description=description,
        required=required,
        autocomplete=autocomplete,
        type=OptionTypes.USER,
    )
    return option  # type: ignore


def slash_channel_option(
    description: str,
    required: bool = False,
    autocomplete: bool = False,
    choices: List[Union[SlashCommandChoice, dict]] = None,
    channel_types: Optional[list[Union[ChannelTypes, int]]] = None,
) -> Type[BaseChannel]:
    """
    Annotates an argument as a channel type slash command option.

    Args:
        description: The description of your option
        required: Is this option required?
        autocomplete: Use autocomplete for this option
        choices: The choices allowed by this command
        channel_types: The types of channel allowed by this option
    """
    option = SlashCommandOption(
        name="placeholder",
        description=description,
        required=required,
        autocomplete=autocomplete,
        choices=choices,
        channel_types=channel_types,
        type=OptionTypes.CHANNEL,
    )
    return option  # type: ignore


def slash_role_option(
    description: str,
    required: bool = False,
    autocomplete: bool = False,
    choices: List[Union[SlashCommandChoice, dict]] = None,
) -> Type[Role]:
    """
    Annotates an argument as a role type slash command option.

    Args:
        description: The description of your option
        required: Is this option required?
        autocomplete: Use autocomplete for this option
        choices: The choices allowed by this command
    """
    option = SlashCommandOption(
        name="placeholder",
        description=description,
        required=required,
        autocomplete=autocomplete,
        choices=choices,
        type=OptionTypes.ROLE,
    )
    return option  # type: ignore


def slash_mentionable_option(
    description: str,
    required: bool = False,
    autocomplete: bool = False,
    choices: List[Union[SlashCommandChoice, dict]] = None,
) -> Type[Union[Role, BaseChannel, User, Member]]:
    """
    Annotates an argument as a mentionable type slash command option.

    Args:
        description: The description of your option
        required: Is this option required?
        autocomplete: Use autocomplete for this option
        choices: The choices allowed by this command
    """
    option = SlashCommandOption(
        name="placeholder",
        description=description,
        required=required,
        autocomplete=autocomplete,
        choices=choices,
        type=OptionTypes.MENTIONABLE,
    )
    return option  # type: ignore
