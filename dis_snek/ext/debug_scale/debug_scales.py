from dis_snek import Scale
from dis_snek.client.errors import ScaleLoadException, CommandCheckFailure, ExtensionLoadException
from dis_snek.models import (
    prefixed_command,
    PrefixedContext,
    Context,
)

__all__ = ["DebugScales"]


class DebugScales(Scale):
    @prefixed_command("debug_regrow")
    async def regrow(self, ctx: PrefixedContext, module: str) -> None:
        try:
            await self.shed_scale.callback(ctx, module)
        except (ExtensionLoadException, ScaleLoadException):
            pass
        await self.grow_scale.callback(ctx, module)

    @prefixed_command("debug_grow")
    async def grow_scale(self, ctx: PrefixedContext, module: str) -> None:
        self.bot.grow_scale(module)
        await ctx.message.add_reaction("🪴")

    @prefixed_command("debug_shed")
    async def shed_scale(self, ctx: PrefixedContext, module: str) -> None:
        self.bot.shed_scale(module)
        await ctx.message.add_reaction("💥")

    @regrow.error
    @grow_scale.error
    @shed_scale.error
    async def regrow_error(self, error: Exception, ctx: Context, *args) -> None:
        if isinstance(error, CommandCheckFailure):
            return await ctx.send("You do not have permission to execute this command")
        elif isinstance(error, ExtensionLoadException):
            return await ctx.send(str(error))
        raise


def setup(bot) -> None:
    DebugScales(bot)
