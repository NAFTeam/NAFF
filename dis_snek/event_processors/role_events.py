import copy
import logging

from dis_snek.const import logger_name, MISSING
from dis_snek.event_processors._template import EventMixinTemplate, Processor
from dis_snek.models import events
from dis_snek.models.events import RawGatewayEvent

log = logging.getLogger(logger_name)


class RoleEvents(EventMixinTemplate):
    @Processor.define()
    async def _on_raw_guild_role_create(self, event: RawGatewayEvent) -> None:
        g_id = event.data.get("guild_id")
        role = self.cache.place_role_data(g_id, [event.data.get("role")])
        self.dispatch(events.RoleCreate(g_id, role[int(event.data["role"]["id"])]))

    @Processor.define()
    async def _on_raw_guild_role_update(self, event: RawGatewayEvent) -> None:
        g_id = event.data.get("guild_id")
        r_data = event.data.get("role")
        before = copy.copy(await self.cache.get_role(g_id, r_data["id"], False) or MISSING)

        after = self.cache.place_role_data(g_id, [r_data])
        after = after[int(event.data["role"]["id"])]

        self.dispatch(events.RoleUpdate(g_id, before, after))

    @Processor.define()
    async def _on_raw_guild_role_delete(self, event: RawGatewayEvent) -> None:
        self.dispatch(events.RoleDelete(event.data.get("guild_id"), event.data.get("role_id")))
