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
        after = await self.cache.place_voice_state_data(event.data)

        self.dispatch(events.VoiceStateUpdate(before, after))

        if before:
            if after is None and before.user_id == self.user.id:
                if vc := self.cache.get_bot_voice_state(before._guild_id):
                    if vc.ws._closed:
                        self.cache.delete_bot_voice_state(before._guild_id)

    @Processor.define()
    async def on_raw_voice_server_update(self, event: "RawGatewayEvent") -> None:
        if vc := self.cache.get_bot_voice_state(event.data["guild_id"]):
            await vc.update_voice_server(event.data)
