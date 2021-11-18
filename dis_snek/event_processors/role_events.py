import copy
import logging

from dis_snek.const import logger_name, MISSING
from dis_snek.event_processors._template import EventMixinTemplate
from dis_snek.models import listen, events
from dis_snek.models.events import RawGatewayEvent

log = logging.getLogger(logger_name)


class RoleEvents(EventMixinTemplate):
    @listen()
    async def _on_raw_guild_role_create(self, data: dict) -> None:
        g_id = data.get("guild_id")
        role = self.cache.place_role_data(g_id, [data.get("role")])
        self.dispatch(events.RoleCreate(g_id, role[int(data["role"]["id"])]))

    @listen()
    async def _on_raw_guild_role_update(self, data: dict) -> None:
        g_id = data.get("guild_id")
        r_data = data.get("role")
        before = copy.copy(await self.cache.get_role(g_id, r_data["id"], False) or MISSING)

        after = self.cache.place_role_data(g_id, [r_data])
        after = after[int(data["role"]["id"])]

        self.dispatch(events.RoleUpdate(g_id, before, after))

    @listen()
    async def _on_raw_guild_role_delete(self, data: dict) -> None:
        self.dispatch(events.RoleDelete(data.get("guild_id"), data.get("role_id")))
