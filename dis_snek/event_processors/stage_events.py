import logging

from dis_snek.const import logger_name
from dis_snek.event_processors._template import EventMixinTemplate, Processor
from dis_snek.models import events, StageInstance
from dis_snek.models.events import RawGatewayEvent

log = logging.getLogger(logger_name)


class StageEvents(EventMixinTemplate):
    @Processor.define()
    async def _on_raw_stage_instance_create(self, event: RawGatewayEvent) -> None:
        self.dispatch(events.StageInstanceCreate(StageInstance.from_dict(event.data, self)))  # type: ignore

    @Processor.define()
    async def _on_raw_stage_instance_update(self, event: RawGatewayEvent) -> None:
        self.dispatch(events.StageInstanceUpdate(StageInstance.from_dict(event.data, self)))  # type: ignore

    @Processor.define()
    async def _on_raw_stage_instance_delete(self, event: RawGatewayEvent) -> None:
        self.dispatch(events.StageInstanceDelete(StageInstance.from_dict(event.data, self)))  # type: ignore
