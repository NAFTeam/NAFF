import logging

from dis_snek.const import logger_name
from dis_snek.event_processors._template import EventMixinTemplate
from dis_snek.models import listen, events
from dis_snek.models.events import RawGatewayEvent

log = logging.getLogger(logger_name)


class RoleEvents(EventMixinTemplate):
    @listen()
    async def _on_raw_guild_role_create(self, event: RawGatewayEvent) -> None:
        ...

    @listen()
    async def _on_raw_guild_role_update(self, event: RawGatewayEvent) -> None:
        ...

    @listen()
    async def _on_raw_guild_role_delete(self, event: RawGatewayEvent) -> None:
        ...
