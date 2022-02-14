import copy
import logging
from typing import TYPE_CHECKING

import dis_snek.api.events as events

from dis_snek.client.const import logger_name, MISSING
from ._template import EventMixinTemplate, Processor
from dis_snek.models import GuildIntegration, to_snowflake
from dis_snek.api.events.discord import (
    GuildEmojisUpdate,
    IntegrationCreate,
    IntegrationUpdate,
    IntegrationDelete,
    BanCreate,
    BanRemove,
)

if TYPE_CHECKING:
    from dis_snek.api.events import RawGatewayEvent

__all__ = ["GuildEvents"]

log = logging.getLogger(logger_name)


class GuildEvents(EventMixinTemplate):
    @Processor.define()
    async def _on_raw_guild_create(self, event: "RawGatewayEvent") -> None:
        """
        Automatically cache a guild upon GUILD_CREATE event from gateway.

        Args:
            event: raw guild create event

        """
        guild = self.cache.place_guild_data(event.data)

        self._user._guild_ids.add(to_snowflake(event.data.get("id")))  # noqa : w0212

        self._guild_event.set()

        if self.fetch_members:  # noqa
            # delays events until chunking has completed
            await guild.chunk_guild(presences=True)

        self.dispatch(events.GuildJoin(guild))

    @Processor.define()
    async def _on_raw_guild_update(self, event: "RawGatewayEvent") -> None:
        before = copy.copy(await self.cache.fetch_guild(event.data.get("id")))
        self.dispatch(events.GuildUpdate(before or MISSING, self.cache.place_guild_data(event.data)))

    @Processor.define()
    async def _on_raw_guild_delete(self, event: "RawGatewayEvent") -> None:
        if event.data.get("unavailable", False):
            self.dispatch(
                events.GuildUnavailable(
                    event.data.get("id"),
                    await self.cache.fetch_guild(event.data.get("id"), False) or MISSING,
                )
            )
        else:
            # noinspection PyProtectedMember
            if event.data.get("id") in self._user._guild_ids:
                # noinspection PyProtectedMember
                self._user._guild_ids.remove(event.data.get("id"))

            self.cache.delete_guild(event.data.get("id"))

            self.dispatch(
                events.GuildLeft(
                    event.data.get("id"),
                    await self.cache.fetch_guild(event.data.get("id"), False) or MISSING,
                )
            )

    @Processor.define()
    async def _on_raw_guild_ban_add(self, event: "RawGatewayEvent") -> None:
        self.dispatch(BanCreate(event.data.get("guild_id"), self.cache.place_user_data(event.data.get("user"))))

    @Processor.define()
    async def _on_raw_guild_ban_remove(self, event: "RawGatewayEvent") -> None:
        self.dispatch(BanRemove(event.data.get("guild_id"), self.cache.place_user_data(event.data.get("user"))))

    @Processor.define()
    async def _on_raw_integration_create(self, event: "RawGatewayEvent") -> None:
        self.dispatch(IntegrationCreate(GuildIntegration.from_dict(event.data, self)))  # type: ignore

    @Processor.define()
    async def _on_raw_integration_update(self, event: "RawGatewayEvent") -> None:
        self.dispatch(IntegrationUpdate(GuildIntegration.from_dict(event.data, self)))  # type: ignore

    @Processor.define()
    async def _on_raw_integration_delete(self, event: "RawGatewayEvent") -> None:
        self.dispatch(
            IntegrationDelete(event.data.get("guild_id"), event.data.get("id"), event.data.get("application_id"))
        )

    @Processor.define()
    async def _on_raw_guild_emojis_update(self, event: "RawGatewayEvent") -> None:
        guild_id = event.data.get("guild_id")
        emojis = event.data.get("emojis")

        self.dispatch(
            GuildEmojisUpdate(
                guild_id=guild_id,
                before=[
                    copy.copy(await self.cache.fetch_emoji(guild_id, emoji["id"], request_fallback=False))
                    for emoji in emojis
                ]
                if self.cache.enable_emoji_cache
                else [],
                after=[self.cache.place_emoji_data(guild_id, emoji) for emoji in emojis],
            )
        )
