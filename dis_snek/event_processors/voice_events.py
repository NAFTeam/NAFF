import copy
import logging

from dis_snek.const import logger_name
from dis_snek.event_processors._template import EventMixinTemplate, Processor
from dis_snek.models import events
from dis_snek.models.events import RawGatewayEvent

log = logging.getLogger(logger_name)


class VoiceEvents(EventMixinTemplate):
    @Processor.define()
    async def _on_raw_voice_state_update(self, event: RawGatewayEvent) -> None:
        before = copy.copy(self.cache.get_voice_state(event.data["user_id"])) or None
        after = self.cache.place_voice_state_data(event.data)
        self.dispatch(events.VoiceStateUpdate(before, after))
