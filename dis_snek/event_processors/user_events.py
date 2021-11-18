import logging
from typing import Union

from dis_snek.const import logger_name
from dis_snek.event_processors._template import EventMixinTemplate
from dis_snek.models import listen, events, User, Member, BaseChannel, Timestamp, to_snowflake, Activity
from dis_snek.models.enums import Status
from dis_snek.models.events import RawGatewayEvent

log = logging.getLogger(logger_name)


class UserEvents(EventMixinTemplate):
    @listen()
    async def _on_raw_typing_start(self, data: dict) -> None:
        """
        Process raw typing start and dispatch a processed typing event.

        Args:
            event: raw typing start event
        """
        author: Union[User, Member]
        channel: BaseChannel
        guild = None

        if member := data.get("member"):
            author = self.cache.place_member_data(data.get("guild_id"), member)
            guild = await self.cache.get_guild(data.get("guild_id"))
        else:
            author = await self.cache.get_user(data.get("user_id"))

        channel = await self.cache.get_channel(data.get("channel_id"))

        self.dispatch(
            events.TypingStart(
                author=author,
                channel=channel,
                guild=guild,
                timestamp=Timestamp.utcfromtimestamp(data.get("timestamp")),
            )
        )

    @listen()
    async def _on_raw_presence_update(self, data: dict) -> None:
        g_id = to_snowflake(data["guild_id"])
        user = await self.cache.get_user(data["user"]["id"])
        status = Status[data["status"].upper()]
        activities = [Activity.from_dict(a) for a in data.get("activities")]

        self.dispatch(events.PresenceUpdate(user, status, activities, data.get("client_status", None), g_id))
