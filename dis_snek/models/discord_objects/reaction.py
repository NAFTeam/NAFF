import attr

from dis_snek.models.discord_objects.emoji import Emoji
from dis_snek.utils.attr_utils import DictSerializationMixin


@attr.s(slots=True, kw_only=True)
class Reaction(DictSerializationMixin):
    _client = attr.ib(repr=False)
    # TODO: custom_emoji, message
    count: int = attr.ib()
    me: bool = attr.ib(default=False)
    emoji: Emoji = attr.ib()  # TODO: partial emoji (name is null)

    # TODO: clear, remove, users
