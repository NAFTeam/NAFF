import copy
import logging
from typing import TYPE_CHECKING

import dis_snek.api.events as events
from dis_snek.models.discord.invite import Invite
from dis_snek.client.const import MISSING, logger_name
from ._template import EventMixinTemplate, Processor

if TYPE_CHECKING:
    from dis_snek.api.events import RawGatewayEvent

log = logging.getLogger(logger_name)


class ChannelEvents(EventMixinTemplate):
    @Processor.define()
    async def _on_raw_channel_create(self, event: "RawGatewayEvent") -> None:

        channel = self.cache.place_channel_data(event.data)
        if guild := channel.guild:
            guild._channel_ids.add(channel.id)
        self.dispatch(events.ChannelCreate(channel))

    @Processor.define()
    async def _on_raw_channel_delete(self, event: "RawGatewayEvent") -> None:
        # for some reason this event returns the deleted object?
        # so we cache it regardless
        channel = self.cache.place_channel_data(event.data)
        if guild := channel.guild:
            guild._channel_ids.discard(channel.id)
        self.dispatch(events.ChannelDelete(channel))

    @Processor.define()
    async def _on_raw_channel_update(self, event: "RawGatewayEvent") -> None:
        before = copy.copy(await self.cache.get_channel(channel_id=event.data.get("id"), request_fallback=False))
        self.dispatch(events.ChannelUpdate(before=before or MISSING, after=self.cache.place_channel_data(event.data)))

    @Processor.define()
    async def _on_raw_channel_pins_update(self, event: "RawGatewayEvent") -> None:
        channel = await self.cache.get_channel(event.data.get("channel_id"))
        channel.last_pin_timestamp = event.data.get("last_pin_timestamp")
        self.cache.channel_cache[channel.id] = channel
        self.dispatch(events.ChannelPinsUpdate(channel, channel.last_pin_timestamp))

    @Processor.define()
    async def _on_raw_invite_create(self, event: "RawGatewayEvent") -> None:
        self.dispatch(events.InviteCreate(Invite.from_dict(event.data, self)))  # type: ignore

    @Processor.define()
    async def _on_raw_invite_delete(self, event: "RawGatewayEvent") -> None:
        self.dispatch(events.InviteDelete(Invite.from_dict(event.data, self)))  # type: ignore
