import typing
from typing import Protocol, Any, TypeVar, TYPE_CHECKING

if TYPE_CHECKING:
    from dis_snek.models.snek.context import Context

T_co = TypeVar("T_co", covariant=True)

__all__ = ["Converter"]


@typing.runtime_checkable
class Converter(Protocol[T_co]):
    async def convert(self, ctx: "Context", argument: Any) -> T_co:
        raise NotImplementedError("Derived classes need to implement this.")
