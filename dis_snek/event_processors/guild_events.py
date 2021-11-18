import copy
import logging

from dis_snek.const import logger_name, MISSING
from dis_snek.event_processors._template import EventMixinTemplate
from dis_snek.models import listen, events, GuildIntegration
from dis_snek.models.events import RawGatewayEvent
from dis_snek.models.events.discord import IntegrationCreate, IntegrationDelete, BanCreate, BanRemove

log = logging.getLogger(logger_name)


class GuildEvents(EventMixinTemplate):
    @listen()
    async def _on_raw_guild_create(self, data: dict) -> None:
        """
        Automatically cache a guild upon GUILD_CREATE event from gateway.

        Args:
            event: raw guild create event
        """
        guild = self.cache.place_guild_data(data)
        self._guild_event.set()

        self.dispatch(events.GuildJoin(guild))

    @listen()
    async def _on_raw_guild_update(self, data: dict) -> None:
        before = copy.copy(await self.cache.get_guild(data.get("id")))
        self.dispatch(events.GuildUpdate(before or MISSING, self.cache.place_guild_data(data)))

    @listen()
    async def _on_raw_guild_delete(self, data: dict) -> None:
        if data.get("unavailable", False):
            self.dispatch(
                events.GuildUnavailable(
                    data.get("id"),
                    await self.cache.get_guild(data.get("id"), False) or MISSING,
                )
            )
        else:
            self.dispatch(
                events.GuildLeft(
                    data.get("id"),
                    await self.cache.get_guild(data.get("id"), False) or MISSING,
                )
            )

    @listen()
    async def _on_raw_guild_ban_add(self, data: dict) -> None:
        self.dispatch(BanCreate(data.get("guild_id"), self.cache.place_user_data(data.get("user"))))

    @listen()
    async def _on_raw_guild_ban_remove(self, data: dict) -> None:
        self.dispatch(BanRemove(data.get("guild_id"), self.cache.place_user_data(data.get("user"))))

    @listen()
    async def _on_raw_integration_create(self, data: dict) -> None:
        self.dispatch(IntegrationCreate(GuildIntegration.from_dict(data, self)))  # type: ignore

    @listen()
    async def _on_raw_integration_update(self, data: dict) -> None:
        self.dispatch(IntegrationUpdate(GuildIntegration.from_dict(data, self)))  # type: ignore

    @listen()
    async def _on_raw_integration_delete(self, data: dict) -> None:
        self.dispatch(IntegrationDelete(data.get("guild_id"), data.get("id"), data.get("application_id")))
