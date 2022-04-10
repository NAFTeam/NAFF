import typing
from typing import Protocol, Any, TYPE_CHECKING

from dis_snek.client.const import T_co

if TYPE_CHECKING:
    from dis_snek.models.snek.context import Context

__all__ = ["Converter"]


@typing.runtime_checkable
class Converter(Protocol[T_co]):
    async def convert(self, ctx: "Context", argument: Any) -> T_co:
        raise NotImplementedError("Derived classes need to implement this.")
