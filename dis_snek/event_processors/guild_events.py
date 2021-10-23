import copy
import logging

from dis_snek.const import logger_name, MISSING
from dis_snek.event_processors._template import EventMixinTemplate
from dis_snek.models import listen, events
from dis_snek.models.events import RawGatewayEvent

log = logging.getLogger(logger_name)


class GuildEvents(EventMixinTemplate):
    @listen()
    async def _on_raw_guild_create(self, event: RawGatewayEvent) -> None:
        """
        Automatically cache a guild upon GUILD_CREATE event from gateway.

        Args:
            event: raw guild create event
        """
        guild = self.cache.place_guild_data(event.data)
        self._guild_event.set()

        self.dispatch(events.GuildJoin(guild))

    @listen()
    async def _on_raw_guild_update(self, event: RawGatewayEvent) -> None:
        before = copy.copy(await self.cache.get_guild(event.data.get("id")))
        self.dispatch(events.GuildUpdate(before or MISSING, self.cache.place_guild_data(event.data)))

    @listen()
    async def _on_raw_guild_delete(self, event: RawGatewayEvent) -> None:
        if event.data.get("unavailable", False):
            self.dispatch(
                events.GuildUnavailable(
                    event.data.get("id"),
                    await self.cache.get_guild(event.data.get("id"), False) or MISSING,
                )
            )
        else:
            self.dispatch(
                events.GuildLeft(
                    event.data.get("id"),
                    await self.cache.get_guild(event.data.get("id"), False) or MISSING,
                )
            )

    # ToDo: Waiting for guild ban objects to be made
    # @listen()
    # async def _on_raw_guild_ban_add(self, event: RawGatewayEvent) -> None:
    #     ...
    #
    # @listen()
    # async def _on_raw_guild_ban_remove(self, event: RawGatewayEvent) -> None:
    #     ...

    # ToDo: waiting for integration objects to be made
    # @listen()
    # async def _on_raw_integration_create(self, event: RawGatewayEvent) -> None:
    #     ...
    #
    # @listen()
    # async def _on_raw_integration_update(self, event: RawGatewayEvent) -> None:
    #     ...
    #
    # @listen()
    # async def _on_raw_integration_delete(self, event: RawGatewayEvent) -> None:
    #     ...
