import io
import textwrap
import traceback
from contextlib import redirect_stdout
from typing import Any

from dis_snek.annotations import CMD_BODY
from dis_snek.debug_scale.utils import debug_embed
from dis_snek.models import (
    Embed,
    message_command,
    MessageContext,
    Message,
    File,
    checks,
)
from dis_snek.models.paginators import Paginator
from dis_snek.models.scale import Scale


class DebugExec(Scale):
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
                e = debug_embed("Exec", timestamp=result.created_at, url=result.jump_url)
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
            paginator = Paginator.create_from_string(self.bot, result, prefix="```py", suffix="```", page_size=4000)
            return await paginator.send(ctx)


def setup(bot):
    DebugExec(bot)
