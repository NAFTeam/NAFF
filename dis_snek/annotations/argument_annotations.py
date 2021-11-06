from typing import Union, TYPE_CHECKING, Any, List, Type, Dict

from dis_snek.const import MISSING
from dis_snek.utils.misc_utils import get_parameters

from dis_snek.models.context import Context
from dis_snek.models.scale import Scale
from dis_snek.client import Snake

if TYPE_CHECKING:
    from dis_snek.models import Member, User, TYPE_MESSAGEABLE_CHANNEL


def define_annotation():
    """
    Define a function as an annotation.

    The function **must** type hint its expected arguments. Make sure your annotation runs quickly,
    as command execution will be delayed until all annotations are completed

    **Supported Types:**
    `Context`
    `Scale`
    """

    def wrapper(func):
        params = get_parameters(func)
        args = []
        for param in params.values():
            if issubclass(param.annotation, Context):
                args.append("context")
            elif param.annotation is Scale:
                args.append("scale")
            # elif param.annotation is Snake:
            #     args.append("snake")
        func._annotation_dat = {"args": args}
        return func

    return wrapper


@define_annotation()
def CMD_BODY(context: Context) -> str:
    """
    This argument is for the body of the message. IE:

    if `@bot hello how are you?` is sent this argument will be `hello how are you?`
    """
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
