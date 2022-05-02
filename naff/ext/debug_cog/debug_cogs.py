from naff import Cog
from naff.client.errors import CogLoadException, CommandCheckFailure, ExtensionLoadException
from naff.models import (
    prefixed_command,
    PrefixedContext,
    Context,
)

__all__ = ("DebugCogs",)


class DebugCogs(Cog):
    @prefixed_command("debug_reload")
    async def reload(self, ctx: PrefixedContext, module: str) -> None:
        try:
            await self.drop_cog.callback(ctx, module)
        except (ExtensionLoadException, CogLoadException):
            pass
        await self.mount_cog.callback(ctx, module)

    @prefixed_command("debug_mount")
    async def mount_cog(self, ctx: PrefixedContext, module: str) -> None:
        self.bot.mount_cog(module)
        await ctx.message.add_reaction("🪴")

    @prefixed_command("debug_drop")
    async def drop_cog(self, ctx: PrefixedContext, module: str) -> None:
        self.bot.drop_cog(module)
        await ctx.message.add_reaction("💥")

    @reload.error
    @mount_cog.error
    @drop_cog.error
    async def regrow_error(self, error: Exception, ctx: Context, *args) -> None:
        if isinstance(error, CommandCheckFailure):
            return await ctx.send("You do not have permission to execute this command")
        elif isinstance(error, ExtensionLoadException):
            return await ctx.send(str(error))
        raise


def setup(bot) -> None:
    DebugCogs(bot)
