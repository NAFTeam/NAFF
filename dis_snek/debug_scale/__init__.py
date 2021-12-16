import datetime
import logging
import platform
import tracemalloc

from dis_snek.const import logger_name, __version__, __py_version__
from dis_snek.debug_scale.debug_application_cmd import DebugAppCMD
from dis_snek.debug_scale.debug_exec import DebugExec
from dis_snek.debug_scale.debug_scales import DebugScales
from dis_snek.debug_scale.utils import get_cache_state, strf_delta, debug_embed
from dis_snek.models import Scale, checks, listen, slash_command, InteractionContext, Timestamp
from dis_snek.models.enums import Intents

log = logging.getLogger(logger_name)


class DebugScale(DebugExec, DebugAppCMD, DebugScales, Scale):
    def __init__(self, bot):
        self.add_scale_check(checks.is_owner())

        log.info("Debug Scale is growing! Activating memory allocation trace and asyncio debug...")

        if not tracemalloc.is_tracing():
            tracemalloc.start()
        if not self.bot.loop.get_debug():
            self.bot.loop.set_debug(True)

    @listen()
    async def on_startup(self):
        log.info(f"Started {self.bot.user.tag} [{self.bot.user.id}] in Debug Mode")

        log.info(f"Caching System State: \n{get_cache_state(self.bot)}")

    @slash_command(
        "debug",
        sub_cmd_name="info",
        sub_cmd_description="Get basic information about the bot",
    )
    async def debug_info(self, ctx: InteractionContext):
        await ctx.defer()

        uptime = datetime.datetime.now() - self.bot.start_time
        e = debug_embed("General")
        e.set_thumbnail(self.bot.user.avatar.url)
        e.add_field("Operating System", platform.platform())

        e.add_field("Version Info", f"Dis-Snek@{__version__} | Py@{__py_version__}")

        e.add_field(
            "Start Time",
            f"{Timestamp.fromdatetime(self.bot.start_time)}\n({strf_delta(uptime)} ago)",
        )

        privileged_intents = [i.name for i in self.bot.intents if i in Intents.PRIVILEGED]
        if privileged_intents:
            e.add_field("Privileged Intents", " | ".join(privileged_intents))

        e.add_field("Loaded Scales", ", ".join(self.bot.scales))

        e.add_field("Guilds", str(len(self.bot.guilds)))

        await ctx.send(embeds=[e])

    @debug_info.subcommand("cache", sub_cmd_description="Get information about the current cache state")
    async def cache_info(self, ctx: InteractionContext):
        await ctx.defer()
        e = debug_embed("Cache")

        e.description = get_cache_state(self.bot)
        await ctx.send(embeds=[e])

    @debug_info.subcommand("shutdown", sub_cmd_description="Shutdown the bot.")
    async def shutdown(self, ctx: InteractionContext):
        await ctx.send("Shutting down 😴")
        await self.bot.stop()


def setup(bot):
    DebugScale(bot)
