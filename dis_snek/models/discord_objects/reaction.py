import attr

from dis_snek.models.discord_objects.emoji import Emoji
from dis_snek.models.base_object import DiscordObject
from dis_snek.utils.attr_utils import define, field


@define()
class Reaction(DiscordObject):
    # TODO: custom_emoji, message
    count: int = attr.ib()
    me: bool = attr.ib(default=False)
    emoji: Emoji = attr.ib()  # TODO: partial emoji (name is null)

    # TODO: clear, remove, users
