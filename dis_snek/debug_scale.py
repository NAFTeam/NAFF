"""
A debugging scale. To load this scale run `bot.grow_scale("dis_snek.debug_scale")`
"""
# todo: create paginators for responses

import datetime
import io
import logging
import platform
import pprint
import textwrap
import traceback
import tracemalloc
from collections import Counter
from contextlib import redirect_stdout
from typing import Any

from dis_snek.annotations import CMD_BODY
from dis_snek.const import __version__, __py_version__, logger_name
from dis_snek.models import (
    slash_command,
    InteractionContext,
    Embed,
    message_command,
    MessageContext,
    listen,
    checks,
    Message,
    File,
    slash_option,
    OptionTypes,
    MaterialColors,
    Timestamp,
    application_commands_to_dict,
)
from dis_snek.models.enums import Intents
from dis_snek.models.scale import Scale
from dis_snek.utils.cache import TTLCache

log = logging.getLogger(logger_name)

app_cmds_def = {
    "group_name": "app_cmds",
    "group_description": "Debug for application commands",
}


def strf_delta(time_delta: datetime.timedelta, show_seconds=True) -> str:
    """Formats timedelta into a human readable string"""
    years, days = divmod(time_delta.days, 365)
    hours, rem = divmod(time_delta.seconds, 3600)
    minutes, seconds = divmod(rem, 60)

    years_fmt = f"{years} year{'s' if years > 1 or years == 0 else ''}"
    days_fmt = f"{days} day{'s' if days > 1 or days == 0 else ''}"
    hours_fmt = f"{hours} hour{'s' if hours > 1 or hours == 0 else ''}"
    minutes_fmt = f"{minutes} minute{'s' if minutes > 1 or minutes == 0 else ''}"
    seconds_fmt = f"{seconds} second{'s' if seconds > 1 or seconds == 0 else ''}"

    if years >= 1:
        return f"{years_fmt} and {days_fmt}"
    if days >= 1:
        return f"{days_fmt} and {hours_fmt}"
    if hours >= 1:
        return f"{hours_fmt} and {minutes_fmt}"
    if show_seconds:
        return f"{minutes_fmt} and {seconds_fmt}"
    return f"{minutes_fmt}"


class DebugScale(Scale):
    def __init__(self, bot):
        self.add_scale_check(checks.is_owner())

        log.info("Debug Scale is growing! Activating memory allocation trace and asyncio debug...")

        if not tracemalloc.is_tracing():
            tracemalloc.start()
        if not self.bot.loop.get_debug():
            self.bot.loop.set_debug(True)

    def D_Embed(self, title: str) -> Embed:
        e = Embed(
            f"Dis-Snek Debug: {title}",
            url="https://github.com/LordOfPolls/Rebecca/blob/master/scales/debug.py",
            color=MaterialColors.BLUE_GREY,
        )
        e.set_footer(
            "Dis-Snek Debug Scale",
            icon_url="https://avatars.githubusercontent.com/u/91958504?s=200&v=4",
        )
        return e

    def get_cache_state(self):
        caches = [
            "channel_cache",
            "dm_channels",
            "guild_cache",
            "guild_cache",
            "member_cache",
            "message_cache",
            "role_cache",
            "user_cache",
            "user_guilds",
        ]
        string = []
        length = len(max(caches, key=len))

        for cache in caches:
            val = getattr(self.bot.cache, cache)
            c_text = f"`{cache.ljust(length)}`"
            if isinstance(val, TTLCache):
                string.append(f"{c_text}: {len(val)} / {val.hard_limit}({val.soft_limit}) ttl:`{val.ttl}`s")
            else:
                string.append(f"{c_text}: {len(val)} / ∞ (no_expire)")

        return "\n".join(string)

    @listen()
    async def on_startup(self):
        log.info(f"Started {self.bot.user.tag} [{self.bot.user.id}] in Debug Mode")

        log.info(f"Caching System State: \n{self.get_cache_state()}")

    @slash_command(
        "debug",
        sub_cmd_name="info",
        sub_cmd_description="Get basic information about the bot",
    )
    async def debug_info(self, ctx: InteractionContext):
        await ctx.defer()

        uptime = datetime.datetime.now() - self.bot.start_time
        e = self.D_Embed("General")
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
        e = self.D_Embed("Cache")

        e.description = self.get_cache_state()
        e.set_footer(self.bot.user.username, icon_url=self.bot.user.avatar.url)
        await ctx.send(embeds=[e])

    @debug_info.subcommand(
        "internal_info", sub_cmd_description="Get Information about registered app commands", **app_cmds_def
    )
    async def app_cmd(self, ctx: InteractionContext):
        await ctx.defer()
        e = self.D_Embed("Application-Commands Cache")

        cmds = 0
        for v in self.bot.interactions.values():
            cmds += 1

        e.add_field("Local application cmds (incld. Subcommands)", str(cmds))
        e.add_field("Component callbacks", str(len(self.bot._component_callbacks)))
        e.add_field("Message commands", str(len(self.bot.commands)))
        e.add_field(
            "Tracked Scopes", str(len(Counter(scope for scope in self.bot._interaction_scopes.values()).keys()))
        )

        e.set_footer(self.bot.user.username, icon_url=self.bot.user.avatar.url)
        await ctx.send(embeds=[e])

    @debug_info.subcommand(
        "lookup", sub_cmd_description="Search for a specified command and get its json representation", **app_cmds_def
    )
    @slash_option("cmd_id", "The ID of the command you want to lookup", opt_type=OptionTypes.STRING, required=True)
    @slash_option(
        "scope",
        "The scope ID of the command, if you want to search for the cmd on remote",
        opt_type=OptionTypes.STRING,
        required=True,
    )
    @slash_option(
        "remote",
        "Should we search locally or remote for this command (default local)",
        opt_type=OptionTypes.BOOLEAN,
        required=False,
    )
    async def cmd_lookup(self, ctx: InteractionContext, cmd_id: str = None, scope: str = None, remote: bool = False):
        await ctx.defer()
        try:
            cmd_id = int(cmd_id.strip())
            scope = int(scope.strip())

            # search internal registers for command

            async def send(cmd_json: dict):
                await ctx.send(
                    file=File(io.BytesIO(pprint.pformat(cmd_json, 2).encode("utf-8")), f"{cmd_json.get('name')}.json")
                )

            if not remote:
                data = application_commands_to_dict(self.bot.interactions)[scope]
                cmd_obj = self.bot.get_application_cmd_by_id(cmd_id)
                for cmd in data:
                    if cmd["name"] == cmd_obj.name:
                        return await send(cmd)

            else:
                data = await self.bot.http.get_application_commands(self.bot.app.id, scope)

                for cmd in data:
                    if int(cmd["id"]) == cmd_id:
                        return await send(cmd)
        except Exception:
            pass
        return await ctx.send(f"Unable to locate any commands in {scope} with ID {cmd_id}!")

    @debug_info.subcommand(
        "list_scope", sub_cmd_description="List all synced commands in a specified scope", **app_cmds_def
    )
    @slash_option(
        "scope",
        "The scope ID of the command, if it is not registered in the bot (0 for global)",
        opt_type=OptionTypes.STRING,
        required=True,
    )
    async def list_scope(self, ctx: InteractionContext, scope: str):
        await ctx.defer()
        try:
            cmds = await self.bot.http.get_application_commands(self.bot.app.id, int(scope.strip()))
            if cmds:
                e = Embed("Dis-Snek Application Command Information", "")

                e.description = f"**Listing Commands Registered in {scope}**\n\n" + "\n".join(
                    [f"`{c['id']}` : `{c['name']}`" for c in cmds]
                )
                await ctx.send(embeds=e)
            else:
                return await ctx.send(f"No commands found in `{scope.strip()}`")
        except:
            return await ctx.send(f"No commands found in `{scope.strip()}`")

    @message_command("exec")
    async def debug_exec(self, ctx: MessageContext, body: CMD_BODY):
        await ctx.channel.trigger_typing()
        env = {
            "bot": self.bot,
            "ctx": ctx,
            "channel": ctx.channel,
            "author": ctx.author,
            "server": ctx.guild,
            "guild": ctx.guild,
            "message": ctx.message,
        } | globals()

        if body.startswith("```") and body.endswith("```"):
            body = "\n".join(body.split("\n")[1:-1])
        else:
            body = body.strip("` \n")

        stdout = io.StringIO()

        to_compile = "async def func():\n%s" % textwrap.indent(body, "  ")
        try:
            exec(to_compile, env)
        except SyntaxError as e:
            return await ctx.send(f"```py\n{traceback.format_exc()}\n```")

        func = env["func"]
        try:
            with redirect_stdout(stdout):
                ret = await func()  # noqa
        except Exception as e:
            await ctx.message.add_reaction("❌")
            return await ctx.message.reply(f"```py\n{stdout.getvalue()}{traceback.format_exc()}\n```")
        else:
            return await self.handle_exec_result(ctx, ret, stdout.getvalue())

    async def handle_exec_result(self, ctx: MessageContext, result: Any, value: Any):
        if not result:
            result = value or "No Output!"

        await ctx.message.add_reaction("✅")

        if isinstance(result, Message):
            try:
                e = Embed(timestamp=result.created_at, url=result.jump_url)
                e.description = result.content
                e.set_author(result.author.tag, icon_url=(result.author.guild_avatar or result.author.avatar).url)
                e.add_field("\u200b", f"[Jump To]({result.jump_url})\n{result.channel.mention}")

                return await ctx.message.reply(embeds=e)
            except Exception:
                return await ctx.message.reply(result.jump_url)

        if isinstance(result, Embed):
            return await ctx.message.reply(embeds=result)

        if isinstance(result, File):
            return await ctx.message.reply(file=result)

        if not isinstance(result, str):
            result = repr(result)

        if len(result) <= 2000:
            return await ctx.message.reply(f"```py\n{result.replace(self.bot.http.token, '[REDACTED TOKEN]')}```")

        else:
            # todo: paginator
            return await ctx.message.reply(f"Content too large to send! {len(result)} characters")


def setup(bot):
    DebugScale(bot)
