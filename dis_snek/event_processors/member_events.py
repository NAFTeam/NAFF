import logging

from dis_snek.const import logger_name
from dis_snek.event_processors._template import EventMixinTemplate
from dis_snek.models import listen, events
from dis_snek.models.events import RawGatewayEvent

log = logging.getLogger(logger_name)


class MemberEvents(EventMixinTemplate):
    @listen()
    async def _on_raw_member_add(self, event: RawGatewayEvent) -> None:
        ...

    @listen()
    async def _on_raw_member_remove(self, event: RawGatewayEvent) -> None:
        ...

    @listen()
    async def _on_raw_member_update(self, event: RawGatewayEvent) -> None:
        ...
