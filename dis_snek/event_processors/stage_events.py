import logging

from dis_snek.const import logger_name
from dis_snek.event_processors._template import EventMixinTemplate
from dis_snek.models import listen, events, StageInstance
from dis_snek.models.events import RawGatewayEvent

log = logging.getLogger(logger_name)


class StageEvents(EventMixinTemplate):
    @listen()
    async def _on_raw_stage_instance_create(self, event: RawGatewayEvent) -> None:
        self.dispatch(events.StageInstanceCreate(StageInstance.from_dict(event.data, self)))  # type: ignore

    @listen()
    async def _on_raw_stage_instance_update(self, event: RawGatewayEvent) -> None:
        self.dispatch(events.StageInstanceUpdate(StageInstance.from_dict(event.data, self)))  # type: ignore

    @listen()
    async def _on_raw_stage_instance_delete(self, event: RawGatewayEvent) -> None:
        self.dispatch(events.StageInstanceDelete(StageInstance.from_dict(event.data, self)))  # type: ignore
