import asyncio
from typing import TYPE_CHECKING

from dis_snek.client.errors import AlreadyDeferred, NotFound
from dis_snek.client.utils.attr_utils import define, field

if TYPE_CHECKING:
    from dis_snek.models.snek.context import InteractionContext

__all__ = ["AutoDefer"]


@define()
class AutoDefer:
    """Automatically defer application commands for you!"""

    enabled: bool = field(default=False)
    """Whether or not auto-defer is enabled"""

    ephemeral: bool = field(default=False)
    """Should the command be deferred as ephemeral or not"""

    time_until_defer: float = field(default=1.5)
    """How long to wait before automatically deferring"""

    async def __call__(self, ctx: "InteractionContext"):
        if self.enabled:
            if self.time_until_defer > 0:
                loop = asyncio.get_event_loop()
                loop.call_later(self.time_until_defer, loop.create_task, self.defer(ctx))
            else:
                await ctx.defer(self.ephemeral)

    async def defer(self, ctx: "InteractionContext") -> None:
        if not ctx.responded or not ctx.deferred:
            try:
                await ctx.defer(self.ephemeral)
            except (AlreadyDeferred, NotFound):
                pass
