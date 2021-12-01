import copy
import logging

from dis_snek.const import logger_name, MISSING
from dis_snek.event_processors._template import EventMixinTemplate, Processor
from dis_snek.models import events, GuildIntegration, to_snowflake
from dis_snek.models.events import RawGatewayEvent
from dis_snek.models.events.discord import IntegrationCreate, IntegrationUpdate, IntegrationDelete, BanCreate, BanRemove

log = logging.getLogger(logger_name)


class GuildEvents(EventMixinTemplate):
    @Processor.define()
    async def _on_raw_guild_create(self, event: RawGatewayEvent) -> None:
        """
        Automatically cache a guild upon GUILD_CREATE event from gateway.

        Args:
            event: raw guild create event
        """
        guild = self.cache.place_guild_data(event.data)

        self.user._guild_ids.add(to_snowflake(event.data.get("id")))

        self._guild_event.set()

        if self.fetch_members:  # noqa
            # delays events until chunking has completed
            await guild.chunk_guild(presences=True)

        self.dispatch(events.GuildJoin(guild))

    @Processor.define()
    async def _on_raw_guild_update(self, event: RawGatewayEvent) -> None:
        before = copy.copy(await self.cache.get_guild(event.data.get("id")))
        self.dispatch(events.GuildUpdate(before or MISSING, self.cache.place_guild_data(event.data)))

    @Processor.define()
    async def _on_raw_guild_delete(self, event: RawGatewayEvent) -> None:
        if event.data.get("unavailable", False):
            self.dispatch(
                events.GuildUnavailable(
                    event.data.get("id"),
                    await self.cache.get_guild(event.data.get("id"), False) or MISSING,
                )
            )
        else:
            if event.data.get("id") in self.user._guild_ids:
                self.user._guild_ids.remove(event.data.get("id"))
            self.dispatch(
                events.GuildLeft(
                    event.data.get("id"),
                    await self.cache.get_guild(event.data.get("id"), False) or MISSING,
                )
            )

    @Processor.define()
    async def _on_raw_guild_ban_add(self, event: RawGatewayEvent) -> None:
        self.dispatch(BanCreate(event.data.get("guild_id"), self.cache.place_user_data(event.data.get("user"))))

    @Processor.define()
    async def _on_raw_guild_ban_remove(self, event: RawGatewayEvent) -> None:
        self.dispatch(BanRemove(event.data.get("guild_id"), self.cache.place_user_data(event.data.get("user"))))

    @Processor.define()
    async def _on_raw_integration_create(self, event: RawGatewayEvent) -> None:
        self.dispatch(IntegrationCreate(GuildIntegration.from_dict(event.data, self)))  # type: ignore

    @Processor.define()
    async def _on_raw_integration_update(self, event: RawGatewayEvent) -> None:
        self.dispatch(IntegrationUpdate(GuildIntegration.from_dict(event.data, self)))  # type: ignore

    @Processor.define()
    async def _on_raw_integration_delete(self, event: RawGatewayEvent) -> None:
        self.dispatch(
            IntegrationDelete(event.data.get("guild_id"), event.data.get("id"), event.data.get("application_id"))
        )
