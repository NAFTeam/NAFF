import asyncio
from typing import TYPE_CHECKING

import attr

if TYPE_CHECKING:
    from dis_snek.models.context import InteractionContext


@attr.s(kw_only=True, slots=True)
class AutoDefer:
    """Automatically defer application commands for you!"""

    enabled: bool = attr.ib(default=False)
    """Whether or not auto-defer is enabled"""

    ephemeral: bool = attr.ib(default=False)
    """Should the command be deferred as ephemeral or not"""

    time_until_defer: float = attr.ib(default=1.5)
    """How long to wait before automatically deferring"""

    async def __call__(self, ctx: "InteractionContext"):
        if self.enabled:
            await asyncio.sleep(self.time_until_defer)
            if not ctx.responded:
                await ctx.defer(self.ephemeral)
