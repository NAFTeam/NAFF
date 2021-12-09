import copy
import logging

from dis_snek.const import logger_name
from dis_snek.event_processors._template import EventMixinTemplate, Processor
from dis_snek.models import events, to_snowflake, Message, BaseMessage
from dis_snek.models.events import RawGatewayEvent

log = logging.getLogger(logger_name)


class MessageEvents(EventMixinTemplate):
    @Processor.define()
    async def _on_raw_message_create(self, event: RawGatewayEvent) -> None:
        """
        Automatically convert MESSAGE_CREATE event data to the object.

        Args:
            event: raw message event
        """
        msg = self.cache.place_message_data(event.data)
        if not msg._guild_id and event.data.get("guild_id"):
            msg._guild_id = event.data["guild_id"]
            # todo: Determine why this isn't set *always*

        if not msg.author:
            # sometimes discord will only send an author ID, not the author. this catches that
            msg.channel = (
                await self.cache.get_channel(to_snowflake(msg._channel_id)) if not msg.channel else msg.channel
            )
            if msg._guild_id:
                msg.guild = await self.cache.get_guild(msg._guild_id) if not msg.guild else msg.guild
                msg.author = await self.cache.get_member(msg._guild_id, msg._author_id)
            else:
                msg.author = await self.cache.get_user(to_snowflake(msg._author_id))

        self.dispatch(events.MessageCreate(msg))

    @Processor.define()
    async def _on_raw_message_delete(self, event: RawGatewayEvent) -> None:
        """
        Process raw deletions and dispatch a processed deletion event.
        Args:
            event: raw message deletion event
        """
        message = await self.cache.get_message(
            event.data.get("channel_id"), event.data.get("id"), request_fallback=False
        )

        if not message:
            message = BaseMessage.from_dict(event.data, self)

        log.debug(f"Dispatching Event: {event.resolved_name}")
        self.dispatch(events.MessageDelete(message))

    @Processor.define()
    async def _on_raw_message_update(self, event: RawGatewayEvent) -> None:
        """
        Process raw message update event and dispatch a processed update event.

        Args:
            event: raw message update event
        """

        # a copy is made because the cache will update the original object in memory
        before = copy.copy(
            await self.cache.get_message(event.data.get("channel_id"), event.data.get("id"), request_fallback=False)
        )
        after = self.cache.place_message_data(event.data)
        self.dispatch(events.MessageUpdate(before=before, after=after))
