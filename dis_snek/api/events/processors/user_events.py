import logging
from typing import Union, TYPE_CHECKING
import dis_snek.api.events as events

from dis_snek.client.const import logger_name
from ._template import EventMixinTemplate, Processor
from dis_snek.models import User, Member, BaseChannel, Timestamp, to_snowflake, Activity
from dis_snek.models.discord.enums import Status

if TYPE_CHECKING:
    from dis_snek.api.events import RawGatewayEvent

__all__ = ["UserEvents"]

log = logging.getLogger(logger_name)


class UserEvents(EventMixinTemplate):
    @Processor.define()
    async def _on_raw_typing_start(self, event: "RawGatewayEvent") -> None:
        """
        Process raw typing start and dispatch a processed typing event.

        Args:
            event: raw typing start event

        """
        author: Union[User, Member]
        channel: BaseChannel
        guild = None

        if member := event.data.get("member"):
            author = self.cache.place_member_data(event.data.get("guild_id"), member)
            guild = await self.cache.fetch_guild(event.data.get("guild_id"))
        else:
            author = await self.cache.fetch_user(event.data.get("user_id"))

        channel = await self.cache.fetch_channel(event.data.get("channel_id"))

        self.dispatch(
            events.TypingStart(
                author=author,
                channel=channel,
                guild=guild,
                timestamp=Timestamp.utcfromtimestamp(event.data.get("timestamp")),
            )
        )

    @Processor.define()
    async def _on_raw_presence_update(self, event: "RawGatewayEvent") -> None:
        g_id = to_snowflake(event.data["guild_id"])
        user = await self.cache.fetch_user(event.data["user"]["id"], request_fallback=False)
        if user:
            status = Status[event.data["status"].upper()]
            activities = [Activity.from_dict(a) for a in event.data.get("activities")]

            self.dispatch(events.PresenceUpdate(user, status, activities, event.data.get("client_status", None), g_id))
