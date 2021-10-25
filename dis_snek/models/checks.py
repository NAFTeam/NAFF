from typing import Union, TYPE_CHECKING

from dis_snek.models.discord_objects.role import Role
from dis_snek.models.snowflake import Snowflake_Type, to_snowflake
from dis_snek.models.context import Context


def has_role(role: Union[Snowflake_Type, Role]):
    """
    Check if the user has the given role

    Args:
        role: The Role or role id to check for
    """

    async def check(ctx: Context) -> bool:
        if ctx.guild is None:
            return False
        return await ctx.author.has_role(role)

    return check


def has_any_role(*roles: Union[Snowflake_Type, Role]):
    """
    Checks if the user has any of the given roles
    Args:
        *roles: The Role(s) or role id(s) to check for
    """

    async def check(ctx: Context) -> bool:
        if ctx.guild is None:
            return False

        if any(ctx.author.has_role(to_snowflake(r)) for r in roles):
            return True
        return False


def has_id(user_id):
    """
    Checks if the author has the desired ID.

    parameters:
        coro: the function to check
    """

    async def check(ctx: Context) -> bool:
        return ctx.author.id == user_id

    return check


def is_owner():
    """
    Is the author the owner of the bot.

    !!! note
        this does not account for teams
    parameters:
        coro: the function to check
    """

    async def check(ctx: Context) -> bool:
        return ctx.author.id == ctx.bot.owner

    return check


def guild_only():
    """
    This command may only be ran in a guild
    """

    async def check(ctx: Context) -> bool:
        return ctx.guild is not None

    return check


def dm_only():
    """
    This command may only be ran in a dm
    """

    async def check(ctx: Context) -> bool:
        return ctx.guild is None

    return check
