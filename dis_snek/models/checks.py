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
