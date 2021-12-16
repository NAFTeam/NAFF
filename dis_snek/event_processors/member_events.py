import copy
import logging

from dis_snek.const import logger_name, MISSING
from dis_snek.event_processors._template import EventMixinTemplate, Processor
from dis_snek.models import events
from dis_snek.models.events import RawGatewayEvent

log = logging.getLogger(logger_name)


class MemberEvents(EventMixinTemplate):
    @Processor.define()
    async def _on_raw_guild_member_add(self, event: RawGatewayEvent) -> None:
        g_id = event.data.pop("guild_id")
        member = self.cache.place_member_data(g_id, event.data)
        self.dispatch(events.MemberAdd(g_id, member))

    @Processor.define()
    async def _on_raw_guild_member_remove(self, event: RawGatewayEvent) -> None:
        g_id = event.data.pop("guild_id")
        user = self.cache.place_user_data(event.data["user"])
        self.dispatch(events.MemberRemove(g_id, await self.cache.get_member(g_id, user.id, False) or user))

    @Processor.define()
    async def _on_raw_guild_member_update(self, event: RawGatewayEvent) -> None:
        g_id = event.data.pop("guild_id")
        before = copy.copy(await self.cache.get_member(g_id, event.data["user"]["id"], False)) or MISSING
        self.dispatch(events.MemberUpdate(g_id, before, self.cache.place_member_data(g_id, event.data)))
