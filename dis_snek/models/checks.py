from dis_snek.models.discord_objects.context import Context


def has_role(role_id):
    """
    Checks if the author has a role with a specific id.
    :param coro: the function to check
    :return:
    """

    async def check(ctx: Context) -> bool:
        if any(role.id == role_id for role in await ctx.author.roles):
            return True
        return False

    return check


def has_id(user_id):
    """
    Checks if the author has the desired ID.
    :param coro: the function to check
    :return:
    """

    async def check(ctx: Context) -> bool:
        author = await ctx.author
        if ctx.author.id == user_id:
            return True
        return False

    return check
