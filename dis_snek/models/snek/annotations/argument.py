from typing import TYPE_CHECKING

from dis_snek.client.errors import BadArgument
from dis_snek.models.snek.protocols import Converter
from dis_snek.models.snek.context import Context, PrefixedContext

__all__ = ["NoArgumentConverter", "CMD_ARGS", "CMD_AUTHOR", "CMD_BODY", "CMD_CHANNEL"]


if TYPE_CHECKING:
    from dis_snek.models import Member, User, TYPE_MESSAGEABLE_CHANNEL


class NoArgumentConverter(Converter):
    """
    A special type of converter that only uses the Context.

    This is mainly needed for prefixed commands, as arguments will be "eaten up" by converters otherwise.
    """


class CMD_BODY(NoArgumentConverter):
    """
    This argument is for the body of the message.

    IE:

    if `@bot hello how are you?` is sent this argument will be `hello how are you?`
    """

    async def convert(self, context: Context, _) -> str:
        """Returns the body of the message."""
        if not isinstance(context, PrefixedContext):
            raise BadArgument("CMD_BODY can only be used with prefixed commands.")
        return context.content_parameters


class CMD_AUTHOR(NoArgumentConverter):
    """This argument is the author of the context."""

    async def convert(self, context: Context, _) -> "Member | User":
        """Returns the author of the context."""
        return context.author


class CMD_CHANNEL(NoArgumentConverter):
    """This argument is the channel the command was sent in."""

    async def convert(self, context: Context, _) -> "TYPE_MESSAGEABLE_CHANNEL":
        """Returns the channel of the context."""
        return context.channel


class CMD_ARGS(NoArgumentConverter):
    """This argument is all of the arguments sent with this context."""

    @staticmethod
    async def convert(context: Context, _) -> list[str]:
        """Returns the arguments for this context."""
        return context.args
