from typing import Awaitable, Callable, Union

from naff.models.discord.role import Role
from naff.models.discord.snowflake import Snowflake_Type, to_snowflake
from naff.models.naff.context import Context

__all__ = ("has_role", "has_any_role", "has_id", "is_owner", "guild_only", "dm_only")

TYPE_CHECK_FUNCTION = Callable[[Context], Awaitable[bool]]


def has_role(role: Union[Snowflake_Type, Role]) -> TYPE_CHECK_FUNCTION:
    """
    Check if the user has the given role.

    Args:
        role: The Role or role id to check for

    """

    async def check(ctx: Context) -> bool:
        if ctx.guild is None:
            return False
        return ctx.author.has_role(role)

    return check


def has_any_role(*roles: Union[Snowflake_Type, Role]) -> TYPE_CHECK_FUNCTION:
    """
    Checks if the user has any of the given roles.

    Args:
        *roles: The Role(s) or role id(s) to check for
    """

    async def check(ctx: Context) -> bool:
        if ctx.guild is None:
            return False

        if any(ctx.author.has_role(to_snowflake(r)) for r in roles):
            return True
        return False

    return check


def has_id(user_id: int) -> TYPE_CHECK_FUNCTION:
    """
    Checks if the author has the desired ID.

    Args:
        coro: the function to check

    """

    async def check(ctx: Context) -> bool:
        return ctx.author.id == user_id

    return check


def is_owner() -> TYPE_CHECK_FUNCTION:
    """
    Is the author the owner of the bot.

    Args:
        coro: the function to check

    """

    async def check(ctx: Context) -> bool:
        if ctx.bot.app.team:
            return ctx.bot.app.team.is_in_team(ctx.author.id)
        return ctx.author.id == ctx.bot.owner.id

    return check


def guild_only() -> TYPE_CHECK_FUNCTION:
    """This command may only be ran in a guild."""

    async def check(ctx: Context) -> bool:
        return ctx.guild is not None

    return check


def dm_only() -> TYPE_CHECK_FUNCTION:
    """This command may only be ran in a dm."""

    async def check(ctx: Context) -> bool:
        return ctx.guild is None

    return check
