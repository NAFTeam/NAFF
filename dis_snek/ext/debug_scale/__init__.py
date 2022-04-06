import logging
import platform

from dis_snek import Snake, Scale, listen, slash_command, InteractionContext, Timestamp, TimestampStyles, Intents
from dis_snek.client.const import logger_name, __version__, __py_version__
from dis_snek.models.snek import checks
from .debug_application_cmd import DebugAppCMD
from .debug_exec import DebugExec
from .debug_scales import DebugScales
from .utils import get_cache_state, debug_embed, strf_delta

__all__ = ["DebugScale"]

log = logging.getLogger(logger_name)


class DebugScale(DebugExec, DebugAppCMD, DebugScales, Scale):
    def __init__(self, bot: Snake) -> None:
        super().__init__(bot)
        self.add_scale_check(checks.is_owner())

        log.info("Debug Scale is growing!")

    @listen()
    async def on_startup(self) -> None:
        log.info(f"Started {self.bot.user.tag} [{self.bot.user.id}] in Debug Mode")

        log.info(f"Caching System State: \n{get_cache_state(self.bot)}")

    @slash_command(
        "debug",
        sub_cmd_name="info",
        sub_cmd_description="Get basic information about the bot",
    )
    async def debug_info(self, ctx: InteractionContext) -> None:
        await ctx.defer()

        uptime = Timestamp.fromdatetime(self.bot.start_time)
        e = debug_embed("General")
        e.set_thumbnail(self.bot.user.avatar.url)
        e.add_field("Operating System", platform.platform())

        e.add_field("Version Info", f"Dis-Snek@{__version__} | Py@{__py_version__}")

        e.add_field("Start Time", f"{uptime.format(TimestampStyles.RelativeTime)}")

        privileged_intents = [i.name for i in self.bot.intents if i in Intents.PRIVILEGED]
        if privileged_intents:
            e.add_field("Privileged Intents", " | ".join(privileged_intents))

        e.add_field("Loaded Scales", ", ".join(self.bot.scales))

        e.add_field("Guilds", str(len(self.bot.guilds)))

        await ctx.send(embeds=[e])

    @debug_info.subcommand("cache", sub_cmd_description="Get information about the current cache state")
    async def cache_info(self, ctx: InteractionContext) -> None:
        await ctx.defer()
        e = debug_embed("Cache")

        e.description = f"```prolog\n{get_cache_state(self.bot)}\n```"
        await ctx.send(embeds=[e])

    @debug_info.subcommand("shutdown", sub_cmd_description="Shutdown the bot.")
    async def shutdown(self, ctx: InteractionContext) -> None:
        await ctx.send("Shutting down 😴")
        await self.bot.stop()


def setup(bot: Snake) -> None:
    DebugScale(bot)
