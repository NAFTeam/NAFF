import datetime
import inspect
from typing import TYPE_CHECKING

from dis_snek.models import Embed, MaterialColors
from dis_snek.utils.cache import TTLCache

if TYPE_CHECKING:
    from dis_snek.client import Snake


def debug_embed(title: str, **kwargs) -> Embed:
    e = Embed(
        f"Dis-Snek Debug: {title}",
        url="https://github.com/Discord-Snake-Pit/Dis-Snek/blob/master/dis_snek/debug_scale",
        color=MaterialColors.BLUE_GREY,
        **kwargs,
    )
    e.set_footer(
        "Dis-Snek Debug Scale",
        icon_url="https://media.discordapp.net/attachments/907639005070377020/918600896433238097/sparkle-snekCUnetnoise_scaleLevel0x2.500000.png",
    )
    return e


def get_cache_state(bot: "Snake"):
    caches = [
        c[0]
        for c in inspect.getmembers(bot.cache, predicate=lambda x: isinstance(x, dict))
        if not c[0].startswith("__")
    ]
    string = []
    length = len(max(caches, key=len))

    for cache in caches:
        val = getattr(bot.cache, cache)
        c_text = f"`{cache.ljust(length)}`"
        if isinstance(val, TTLCache):
            string.append(f"{c_text}: {len(val)} / {val.hard_limit}({val.soft_limit}) ttl:`{val.ttl}`s")
        else:
            string.append(f"{c_text}: {len(val)} / ∞ (no_expire)")

    return "\n".join(string)


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
