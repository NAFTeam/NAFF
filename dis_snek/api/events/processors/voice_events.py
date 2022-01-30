import copy
import logging
from typing import TYPE_CHECKING

import dis_snek.api.events as events

from dis_snek.client.const import logger_name
from ._template import EventMixinTemplate, Processor

if TYPE_CHECKING:
    from dis_snek.api.events import RawGatewayEvent

__all__ = ["VoiceEvents"]

log = logging.getLogger(logger_name)


class VoiceEvents(EventMixinTemplate):
    @Processor.define()
    async def _on_raw_voice_state_update(self, event: "RawGatewayEvent") -> None:
        before = copy.copy(self.cache.get_voice_state(event.data["user_id"])) or None
        after = self.cache.place_voice_state_data(event.data)
        self.dispatch(events.VoiceStateUpdate(before, after))
