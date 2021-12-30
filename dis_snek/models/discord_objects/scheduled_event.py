from enum import IntEnum
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

import attr
from attr.converters import optional

from dis_snek.const import MISSING, Absent
from dis_snek.errors import EventLocationNotProvided
from dis_snek.models.discord import DiscordObject
from dis_snek.models.snowflake import Snowflake_Type, to_snowflake
from dis_snek.models.timestamp import Timestamp
from dis_snek.utils.attr_utils import define
from dis_snek.utils.converters import timestamp_converter

if TYPE_CHECKING:
    from dis_snek.client import Snake
    from dis_snek.models.discord_objects.channel import GuildStageVoice, GuildVoice
    from dis_snek.models.discord_objects.guild import Guild
    from dis_snek.models.discord_objects.user import Member
    from dis_snek.models.discord_objects.user import User


class ScheduledEventPrivacyLevel(IntEnum):
    """The privacy level of the scheduled event."""

    GUILD_ONLY = 2


class ScheduledEventType(IntEnum):
    """The type of entity that the scheduled event is attached to."""

    STAGE_INSTANCE = 1
    """ Stage Channel """
    VOICE = 2
    """ Voice Channel """
    EXTERNAL = 3
    """ External URL """


class ScheduledEventStatus(IntEnum):
    """The status of the scheduled event."""

    SCHEDULED = 1
    ACTIVE = 2
    COMPLETED = 3
    CANCELED = 4


@define()
class ScheduledEvent(DiscordObject):
    name: str = attr.ib()
    description: str = attr.ib(default=MISSING)
    entity_type: Union[ScheduledEventType, int] = attr.ib(converter=ScheduledEventType)
    """The type of the scheduled event"""
    start_time: Timestamp = attr.ib(converter=timestamp_converter)
    """A Timestamp object representing the scheduled start time of the event """
    end_time: Optional[Timestamp] = attr.ib(default=None, converter=optional(timestamp_converter))
    """Optional Timstamp object representing the scheduled end time, required if entity_type is EXTERNAL"""
    privacy_level: Union[ScheduledEventPrivacyLevel, int] = attr.ib(converter=ScheduledEventPrivacyLevel)
    """
    Privacy level of the scheduled event

    ??? note:
        Discord only has `GUILD_ONLY` at the momment.
    """
    status: Union[ScheduledEventStatus, int] = attr.ib(converter=ScheduledEventStatus)
    """Current status of the scheduled event"""
    entity_id: Optional["Snowflake_Type"] = attr.ib(default=MISSING, converter=optional(to_snowflake))
    """The id of an entity associated with a guild scheduled event"""
    entity_metadata: Optional[Dict[str, Any]] = attr.ib(default=MISSING)  # TODO make this
    """The metadata associated with the entity_type"""
    user_count: int = attr.ib(default=MISSING)
    """Amount of users subscribed to the scheduled event"""

    _guild_id: "Snowflake_Type" = attr.ib(converter=to_snowflake)
    _creator: Optional["User"] = attr.ib(default=MISSING)
    _creator_id: Optional["Snowflake_Type"] = attr.ib(default=MISSING, converter=optional(to_snowflake))
    _channel_id: Optional["Snowflake_Type"] = attr.ib(default=None, converter=optional(to_snowflake))

    @property
    async def creator(self) -> Optional["User"]:
        """
        Returns the user who created this event

        !!! note:
            Events made before October 25th, 2021 will not have a creator.
        """
        return await self._client.cache.get_user(self._creator_id) if self._creator_id else None

    @property
    def guild(self) -> "Guild":
        return self._client.cache.guild_cache.get(self._guild_id)

    @classmethod
    def _process_dict(cls, data: Dict[str, Any], client: "Snake") -> Dict[str, Any]:
        if data.get("creator"):
            data["creator"] = client.cache.place_user_data(data["creator"])

        if data.get("channel_id"):
            data["channel"] = client.cache.channel_cache.get(data["channel_id"])

        data["start_time"] = data.get("scheduled_start_time")

        if end_time := data.get("scheduled_end_time"):
            data["end_time"] = end_time
        else:
            data["end_time"] = None

        data = super()._process_dict(data, client)
        return data

    @property
    def location(self) -> Optional[str]:
        """Returns the external locatian of this event"""
        if self.entity_type == ScheduledEventType.EXTERNAL:
            return self.entity_metadata["location"]
        return None

    async def get_channel(self) -> Optional[Union["GuildVoice", "GuildStageVoice"]]:
        """Returns the channel this event is scheduled in if it is scheduled in a channel"""
        if self._channel_id:
            channel = await self._client.get_channel(self._channel_id)
            return channel
        return None

    async def get_event_users(
        self,
        limit: Optional[int] = 100,
        with_member_data: bool = False,
        before: Absent[Optional["Snowflake_Type"]] = MISSING,
        after: Absent[Optional["Snowflake_Type"]] = MISSING,
    ) -> List[Union["Member", "User"]]:
        """
        Get event users

        Args:
            limit: Discord defualts to 100
            with_member_data: Whether to include guild member data
            before: Snowflake of a user to get before
            after: Snowflake of a user to get after

        !!! note:
            This method is paginated
        """
        event_users = await self._client.http.get_scheduled_event_users(
            self._guild_id, self.id, limit, with_member_data, before, after
        )
        participants = []
        for u in event_users:
            if member := u.get("member"):
                u["member"]["user"] = u["user"]
                participants.append(self._client.cache.place_member_data(self._guild_id, member))
            else:
                participants.append(self._client.cache.place_user_data(u["user"]))

        return participants

    async def delete(self, reason: Absent[str] = MISSING) -> None:
        """
        Deletes this event

        Args:
            reason: The reason for deleting this event
        """
        await self._client.http.delete_scheduled_event(self._guild_id, self.id, reason)

    async def edit(
        self,
        name: Absent[str] = MISSING,
        start_time: Absent["Timestamp"] = MISSING,
        end_time: Absent["Timestamp"] = MISSING,
        status: Absent[ScheduledEventStatus] = MISSING,
        description: Absent[str] = MISSING,
        channel_id: Absent[Optional["Snowflake_Type"]] = MISSING,
        event_type: Absent[ScheduledEventType] = MISSING,
        external_location: Absent[Optional[str]] = MISSING,
        entity_metadata: Absent[dict] = MISSING,
        privacy_level: Absent[ScheduledEventPrivacyLevel] = MISSING,
        reason: Absent[str] = MISSING,
    ):
        """
        Edits this event

        Args:
            name: The name of the event
            description: The description of the event
            channel_id: The channel id of the event
            event_type: The type of the event
            start_time: The scheduled start time of the event
            end_time: The scheduled end time of the event
            status: The status of the event
            entity_metadata: The metadata of the event
            privacy_level: The privacy level of the event
            reason: The reason for editing the event

        !!! note:
            If updating event_type to EXTERNAL:
                `channel_id` is required and must be set to null

                `external_location` or `entity_metadata` with a location field must be provided

                `end_time` must be provided
        """

        if external_location is not MISSING:
            entity_metadata = dict(location=external_location)

        if event_type == ScheduledEventType.EXTERNAL:
            channel_id = None
            if external_location == MISSING:
                raise EventLocationNotProvided("Location is required for external events")

        payload = dict(
            name=name,
            description=description,
            channel_id=channel_id,
            entity_type=event_type,
            scheduled_start_time=start_time.isoformat() if start_time else MISSING,
            scheduled_end_time=end_time.isoformat() if end_time else MISSING,
            status=status,
            entity_metadata=entity_metadata,
            privacy_level=privacy_level,
        )
        await self._client.http.modify_scheduled_event(self._guild_id, self.id, payload, reason)
