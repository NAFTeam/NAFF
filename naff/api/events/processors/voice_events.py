import copy
from typing import TYPE_CHECKING

import naff.api.events as events

from ._template import EventMixinTemplate, Processor

if TYPE_CHECKING:
    from naff.api.events import RawGatewayEvent

__all__ = ("VoiceEvents",)


class VoiceEvents(EventMixinTemplate):
    @Processor.define()
    async def _on_raw_voice_state_update(self, event: "RawGatewayEvent") -> None:
        before = copy.copy(self.cache.get_voice_state(event.data["user_id"])) or None
        after = await self.cache.place_voice_state_data(event.data)

        self.dispatch(events.VoiceStateUpdate(before, after))

        if before and before.user_id == self.user.id:
            if vc := self.cache.get_bot_voice_state(event.data["guild_id"]):
                # noinspection PyProtectedMember
                await vc._voice_state_update(before, after, event.data)

    @Processor.define()
    async def _on_raw_voice_server_update(self, event: "RawGatewayEvent") -> None:
        if vc := self.cache.get_bot_voice_state(event.data["guild_id"]):
            # noinspection PyProtectedMember
            await vc._voice_server_update(event.data)
