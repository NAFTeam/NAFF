from typing import TYPE_CHECKING

import attr

from dis_snek.models.discord import ClientObject
from dis_snek.models.discord_objects.emoji import Emoji
from dis_snek.models.snowflake import to_snowflake
from dis_snek.utils.attr_utils import define

if TYPE_CHECKING:
    from dis_snek.models.snowflake import Snowflake_Type


@define()
class Reaction(ClientObject):
    count: int = attr.ib()
    me: bool = attr.ib(default=False)
    emoji: "Emoji" = attr.ib(converter=Emoji.from_dict)

    _channel_id: "Snowflake_Type" = attr.ib(converter=to_snowflake)
    _message_id: "Snowflake_Type" = attr.ib(converter=to_snowflake)

    @property
    def message(self):
        return self._client.cache.message_cache.get((self._channel_id, self._message_id))

    @property
    def channel(self):
        return self._client.cache.channel_cache.get(self._channel_id)

    async def remove(self):
        """Remove all this emoji's reactions from the message"""
        await self._client.http.clear_reaction(self._channel_id, self._message_id, self.emoji.req_format)

    # todo: make an async iterator to get all users who reacted
