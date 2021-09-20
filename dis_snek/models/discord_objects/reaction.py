from typing import TYPE_CHECKING

import attr

from dis_snek.models.discord import DiscordObject
from dis_snek.utils.attr_utils import define

if TYPE_CHECKING:
    from dis_snek.models.discord_objects.emoji import Emoji


@define()
class Reaction(DiscordObject):
    count: int = attr.ib()
    me: bool = attr.ib(default=False)
    emoji: "Emoji" = attr.ib()

    # TODO: clear, remove, users
    # TODO: http endpoints for reactions require both a channel and message ID parameter, this object lacks both
