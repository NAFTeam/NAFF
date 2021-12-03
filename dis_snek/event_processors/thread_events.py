import logging

from dis_snek.const import logger_name
from dis_snek.event_processors._template import EventMixinTemplate, Processor
from dis_snek.models import events, to_snowflake
from dis_snek.models.events import RawGatewayEvent

log = logging.getLogger(logger_name)


class ThreadEvents(EventMixinTemplate):
    @Processor.define()
    async def _on_raw_thread_create(self, event: RawGatewayEvent) -> None:
        self.dispatch(events.ThreadCreate(self.cache.place_channel_data(event.data)))

    @Processor.define()
    async def _on_raw_thread_update(self, event: RawGatewayEvent) -> None:
        # todo: Should this also have a before attribute? so you can compare the previous version against this one?
        self.dispatch(events.ThreadUpdate(self.cache.place_channel_data(event.data)))

    @Processor.define()
    async def _on_raw_thread_delete(self, event: RawGatewayEvent) -> None:
        self.dispatch(
            events.ThreadDelete(
                await self.cache.get_channel(event.data.get("id"), request_fallback=False) or event.data.get("id")
            )
        )

    @Processor.define()
    async def _on_raw_thread_list_sync(self, event: RawGatewayEvent) -> None:
        # todo: when we decide how to store thread members, deal with that here
        threads = [self.cache.place_channel_data(t) for t in event.data.get("threads", [])]
        channel_ids = [to_snowflake(c) for c in event.data.get("channel_ids", [])]
        members = [self.cache.place_member_data(event.data.get("guild_id"), m) for m in event.data.get("members", [])]

        self.dispatch(events.ThreadListSync(channel_ids, threads, members))

    @Processor.define()
    async def _on_raw_thread_members_update(self, event: RawGatewayEvent) -> None:
        g_id = event.data.get("guild_id")
        self.dispatch(
            events.ThreadMembersUpdate(
                event.data.get("id"),
                event.data.get("member_count"),
                [await self.cache.get_member(g_id, m["user_id"]) for m in event.data.get("added_members", [])],
                event.data.get("removed_member_ids", []),
            )
        )
