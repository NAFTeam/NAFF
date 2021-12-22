from typing import Callable, Union, TYPE_CHECKING, TypeVar

from dis_snek.utils.misc_utils import get_parameters

from dis_snek.models.context import Context, MessageContext
from dis_snek.models.scale import Scale

if TYPE_CHECKING:
    from dis_snek.models import Member, User, TYPE_MESSAGEABLE_CHANNEL

T = TypeVar("T")


def define_annotation() -> Callable[[Callable[[Context], T]], Callable[[Context], T]]:
    """
    Define a function as an annotation.

    The function **must** type hint its expected arguments. Make sure your annotation runs quickly,
    as command execution will be delayed until all annotations are completed

    **Supported Types:**
    `Context`
    `Scale`
    """

    def wrapper(func: Callable[[Context], T]) -> Callable[[Context], T]:
        params = get_parameters(func)
        args = []
        for param in params.values():
            if issubclass(param.annotation, Context):
                args.append("context")
            elif param.annotation is Scale:
                args.append("scale")
            # elif param.annotation is Snake:
            #     args.append("snake")
        func._annotation_dat = {"args": args}  # type: ignore
        return func

    return wrapper


@define_annotation()
def CMD_BODY(context: Context) -> str:
    """
    This argument is for the body of the message. IE:

    if `@bot hello how are you?` is sent this argument will be `hello how are you?`
    """
    if not isinstance(context, MessageContext):
        raise TypeError("CMD_BODY can only be used with Message Commands")
    return context.content_parameters


@define_annotation()
def CMD_AUTHOR(context: Context) -> Union["Member", "User"]:
    """This argument is the author of the command"""

    return context.author


@define_annotation()
def CMD_CHANNEL(context: Context) -> "TYPE_MESSAGEABLE_CHANNEL":
    """This argument is the channel the command was sent in"""
    return context.channel


@define_annotation()
def CMD_ARGS(context: Context) -> list:
    """This argument is all of the arguments sent with this command"""
    return context.args
