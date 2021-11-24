import asyncio
from asyncio import QueueEmpty
from collections import namedtuple
from typing import TYPE_CHECKING

import attr

from dis_snek.const import MISSING
from dis_snek.models.discord import ClientObject
from dis_snek.models.discord_objects.emoji import Emoji
from dis_snek.models.iterator import AsyncIterator
from dis_snek.models.snowflake import to_snowflake
from dis_snek.utils.attr_utils import define

if TYPE_CHECKING:
    from dis_snek.models.snowflake import Snowflake_Type
    from dis_snek.models import Message, TYPE_ALL_CHANNEL
    from dis_snek.models.discord_objects.user import BaseUser


class ReactionUsers(AsyncIterator):
    """
    An async iterator for searching through a channel's history

    Args:
        channel_id: The ID of the channel to search through
        limit: The maximum number of users to return (set to 0 for no limit)
        after: get users after this message ID
    """

    def __init__(self, reaction: "Reaction", limit=50, after=None):
        self.reaction: "Reaction" = reaction
        self.after: "Snowflake_Type" = after
        self._more = True
        super().__init__(limit)

    async def fetch(self):
        if self._more:
            expected = self.get_limit

            if self.after and not self.last:
                self.last = namedtuple("temp", "id")
                self.last.id = self.after

            users = await self.reaction._client.http.get_reactions(
                self.reaction._channel_id,
                self.reaction._message_id,
                self.reaction.emoji.req_format,
                limit=expected,
                after=self.last.id or MISSING,
            )
            if not users:
                raise QueueEmpty()
            self._more = len(users) == expected
            return [self.reaction._client.cache.place_user_data(u) for u in users]
        else:
            raise QueueEmpty()


@define()
class Reaction(ClientObject):
    count: int = attr.ib()
    me: bool = attr.ib(default=False)
    emoji: "Emoji" = attr.ib(converter=Emoji.from_dict)

    _channel_id: "Snowflake_Type" = attr.ib(converter=to_snowflake)
    _message_id: "Snowflake_Type" = attr.ib(converter=to_snowflake)

    def users(self, limit: int = 0, after=None) -> ReactionUsers:
        return ReactionUsers(self, limit, after)

    @property
    def message(self) -> "Message":
        return self._client.cache.message_cache.get((self._channel_id, self._message_id))

    @property
    def channel(self) -> "TYPE_ALL_CHANNEL":
        return self._client.cache.channel_cache.get(self._channel_id)

    async def remove(self):
        """Remove all this emoji's reactions from the message"""
        await self._client.http.clear_reaction(self._channel_id, self._message_id, self.emoji.req_format)
