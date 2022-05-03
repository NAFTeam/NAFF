import copy
import logging
from typing import TYPE_CHECKING

import naff.api.events as events

from naff.client.const import logger_name, MISSING
from ._template import EventMixinTemplate, Processor

if TYPE_CHECKING:  # pragma: no cover
    from naff.api.events import RawGatewayEvent

__all__ = ("MemberEvents",)

log = logging.getLogger(logger_name)


class MemberEvents(EventMixinTemplate):
    @Processor.define()
    async def _on_raw_guild_member_add(self, event: "RawGatewayEvent") -> None:
        g_id = event.data.pop("guild_id")
        member = self.cache.place_member_data(g_id, event.data)
        guild = self.cache.get_guild(g_id)
        guild.member_count += 1
        self.dispatch(events.MemberAdd(g_id, member))

    @Processor.define()
    async def _on_raw_guild_member_remove(self, event: "RawGatewayEvent") -> None:
        g_id = event.data.pop("guild_id")
        user = self.cache.place_user_data(event.data["user"])
        guild = self.cache.get_guild(g_id)
        guild.member_count -= 1
        self.dispatch(events.MemberRemove(g_id, self.cache.get_member(g_id, user.id) or user))

    @Processor.define()
    async def _on_raw_guild_member_update(self, event: "RawGatewayEvent") -> None:
        g_id = event.data.pop("guild_id")
        before = copy.copy(self.cache.get_member(g_id, event.data["user"]["id"])) or MISSING
        self.dispatch(events.MemberUpdate(g_id, before, self.cache.place_member_data(g_id, event.data)))
