import logging
from typing import Union

from dis_snek.const import logger_name
from dis_snek.event_processors._template import EventMixinTemplate
from dis_snek.models import listen, events, User, Member, BaseChannel, Timestamp
from dis_snek.models.events import RawGatewayEvent

log = logging.getLogger(logger_name)


class UserEvents(EventMixinTemplate):
    @listen()
    async def _on_raw_typing_start(self, event: RawGatewayEvent) -> None:
        """
        Process raw typing start and dispatch a processed typing event.

        Args:
            event: raw typing start event
        """
        author: Union[User, Member]
        channel: BaseChannel
        guild = None

        if member := event.data.get("member"):
            author = self.cache.place_member_data(event.data.get("guild_id"), member)
            guild = await self.cache.get_guild(event.data.get("guild_id"))
        else:
            author = await self.cache.get_user(event.data.get("user_id"))

        channel = await self.cache.get_channel(event.data.get("channel_id"))

        self.dispatch(
            events.TypingStart(
                author=author,
                channel=channel,
                guild=guild,
                timestamp=Timestamp.utcfromtimestamp(event.data.get("timestamp")),
            )
        )
