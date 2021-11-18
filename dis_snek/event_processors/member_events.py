import copy
import logging

from dis_snek.const import logger_name, MISSING
from dis_snek.event_processors._template import EventMixinTemplate
from dis_snek.models import listen, events
from dis_snek.models.events import RawGatewayEvent

log = logging.getLogger(logger_name)


class MemberEvents(EventMixinTemplate):
    @listen()
    async def _on_raw_guild_member_add(self, data: dict) -> None:
        g_id = data.pop("guild_id")
        member = self.cache.place_member_data(g_id, data)
        self.dispatch(events.MemberAdd(g_id, member))

    @listen()
    async def _on_raw_guild_member_remove(self, data: dict) -> None:
        g_id = data.pop("guild_id")
        user = self.cache.place_user_data(data["user"])
        self.dispatch(events.MemberAdd(g_id, await self.cache.get_member(g_id, user.id, False) or user))

    @listen()
    async def _on_raw_guild_member_update(self, data: dict) -> None:
        g_id = data.pop("guild_id")
        before = copy.copy(await self.cache.get_member(g_id, data["user"]["id"], False)) or MISSING
        self.dispatch(events.MemberUpdate(g_id, before, self.cache.place_member_data(g_id, data)))
