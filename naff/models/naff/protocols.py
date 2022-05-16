import typing
from typing import Protocol, Any, TYPE_CHECKING

from naff.client.const import T_co

if TYPE_CHECKING:
    from naff.models.naff.context import Context

__all__ = ("Converter",)


@typing.runtime_checkable
class Converter(Protocol[T_co]):
    """A protocol representing a class used to convert an argument."""

    async def convert(self, ctx: "Context", argument: Any) -> T_co:
        """
        The function that converts an argument to the appropriate type.

        This should be overridden by subclasses for their conversion logic.

        Args:
            ctx: The context to use for the conversion.
            argument: The argument to be converted.

        Returns:
            Any: The converted argument.
        """
        raise NotImplementedError("Derived classes need to implement this.")
