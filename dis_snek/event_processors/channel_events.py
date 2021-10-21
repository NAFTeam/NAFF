import logging

from dis_snek.const import logger_name
from dis_snek.event_processors._template import EventMixinTemplate
from dis_snek.models import listen, events
from dis_snek.models.events import RawGatewayEvent

log = logging.getLogger(logger_name)


class ChannelEvents(EventMixinTemplate):
    @listen()
    async def _on_raw_channel_create(self, event: RawGatewayEvent) -> None:
        """
        Automatically cache a guild upon CHANNEL_CREATE event from gateway.

        Args:
            data: raw channel data
        """
        channel = self.cache.place_channel_data(event.data)
        self.dispatch(events.ChannelCreate(channel))

    @listen()
    async def _on_raw_channel_delete(self, event: RawGatewayEvent) -> None:
        """
        Process raw channel deletions and dispatch a processed channel deletion event.

        Args:
            event: raw channel deletion event
        """
        # for some reason this event returns the deleted object?
        # so we cache it regardless
        channel = self.cache.place_channel_data(event.data)
        self.dispatch(events.ChannelDelete(channel))
