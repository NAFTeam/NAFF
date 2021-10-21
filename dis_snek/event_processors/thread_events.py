import logging

from dis_snek.const import logger_name
from dis_snek.event_processors._template import EventMixinTemplate
from dis_snek.models import listen, events, ThreadChannel
from dis_snek.models.events import RawGatewayEvent

log = logging.getLogger(logger_name)


class ThreadEvents(EventMixinTemplate):
    @listen()
    async def _on_raw_thread_create(self, event: RawGatewayEvent) -> None:
        self.dispatch(events.ThreadCreate(self.cache.place_channel_data(event.data)))

    @listen()
    async def _on_raw_thread_update(self, event: RawGatewayEvent) -> None:
        # todo: Should this also have a before attribute? so you can compare the previous version against this one?
        self.dispatch(events.ThreadUpdate(self.cache.place_channel_data(event.data)))

    @listen()
    async def _on_raw_thread_delete(self, event: RawGatewayEvent) -> None:
        self.dispatch(
            events.ThreadDelete(
                await self.cache.get_channel(event.data.get("id"), request_fallback=False) or event.data.get("id")
            )
        )
