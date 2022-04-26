from typing import TYPE_CHECKING

from dis_snek.client.errors import BadArgument
from dis_snek.models.snek.context import Context, PrefixedContext

__all__ = ["CMD_ARGS", "CMD_AUTHOR", "CMD_BODY", "CMD_CHANNEL"]


if TYPE_CHECKING:
    from dis_snek.models import Member, User, TYPE_MESSAGEABLE_CHANNEL


class CMD_BODY:
    """
    This argument is for the body of the message.

    IE:

    if `@bot hello how are you?` is sent this argument will be `hello how are you?`
    """

    @staticmethod
    async def convert(context: Context, _) -> str:
        if not isinstance(context, PrefixedContext):
            raise BadArgument("CMD_BODY can only be used with prefixed commands.")
        return context.content_parameters


class CMD_AUTHOR:
    """This argument is the author of the command."""

    @staticmethod
    async def convert(context: Context, _) -> "Member | User":
        return context.author


class CMD_CHANNEL:
    """This argument is the channel the command was sent in."""

    @staticmethod
    async def convert(context: Context, _) -> "TYPE_MESSAGEABLE_CHANNEL":
        return context.channel


class CMD_ARGS:
    """This argument is all of the arguments sent with this command."""

    @staticmethod
    async def convert(context: Context, _) -> list[str]:
        return context.args
