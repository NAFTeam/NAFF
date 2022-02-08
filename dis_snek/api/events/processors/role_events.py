import copy
import logging
from typing import TYPE_CHECKING

import dis_snek.api.events as events

from dis_snek.client.const import logger_name, MISSING
from ._template import EventMixinTemplate, Processor

if TYPE_CHECKING:
    from dis_snek.api.events import RawGatewayEvent

__all__ = ["RoleEvents"]

log = logging.getLogger(logger_name)


class RoleEvents(EventMixinTemplate):
    @Processor.define()
    async def _on_raw_guild_role_create(self, event: "RawGatewayEvent") -> None:
        g_id = int(event.data.get("guild_id"))
        r_id = int(event.data["role"]["id"])

        guild = self.cache.guild_cache.get(g_id)
        guild._role_ids.add(r_id)

        role = self.cache.place_role_data(g_id, [event.data.get("role")])[r_id]
        self.dispatch(events.RoleCreate(g_id, role))

    @Processor.define()
    async def _on_raw_guild_role_update(self, event: "RawGatewayEvent") -> None:
        g_id = int(event.data.get("guild_id"))
        r_data = event.data.get("role")
        before = copy.copy(await self.cache.get_role(g_id, r_data["id"], False) or MISSING)

        after = self.cache.place_role_data(g_id, [r_data])
        after = after[int(event.data["role"]["id"])]

        self.dispatch(events.RoleUpdate(g_id, before, after))

    @Processor.define()
    async def _on_raw_guild_role_delete(self, event: "RawGatewayEvent") -> None:
        g_id = int(event.data.get("guild_id"))
        r_id = int(event.data.get("role_id"))

        guild = self.cache.guild_cache.get(g_id)
        role = self.cache.role_cache.pop(r_id, MISSING)

        guild._role_ids.discard(r_id)

        role_members = (member for member in guild.members if member.has_role(r_id))
        for member in role_members:
            member._role_ids.remove(r_id)

        self.dispatch(events.RoleDelete(g_id, r_id, role))
