from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

import attr
from attr.converters import optional
from dis_snek.const import MISSING
from dis_snek.mixins.serialization import DictSerializationMixin
from dis_snek.models.discord import DiscordObject

from dis_snek.models.snowflake import Snowflake_Type, to_snowflake
from dis_snek.models.timestamp import Timestamp
from dis_snek.utils.attr_utils import define
from dis_snek.utils.converters import timestamp_converter


from enum import IntEnum

if TYPE_CHECKING:
    from dis_snek.client import Snake
    from dis_snek.models.discord_objects.guild import Guild
    from dis_snek.models.discord_objects.channel import GuildStageVoice, GuildVoice
    from dis_snek.models.discord_objects.user import Member
    from dis_snek.models.discord_objects.user import User
    from dis_snek.models.snowflake import Snowflake_Type


class ScheduledEventPrivacyLevel(IntEnum):
    """The privacy level of the scheduled event."""

    # Discord only has one at the momment.
    GUILD_ONLY = 2


class ScheduledEventEntityType(IntEnum):
    """The type of entity that the scheduled event is attached to."""

    STAGE_INSTANCE = 1
    """ Stage Channel """
    VOICE = 2
    """ Voice Channel """
    EXTERNAL = 3
    """ External URL """


class ScheduledEventStatus(IntEnum):
    """The status of the scheduled event."""

    # Discord only has one at the momment.
    SCHEDULED = 1
    ACTIVE = 2
    COMPLETED = 3
    CANCELED = 4



@define()
class ScheduledEventUser(DiscordObject):
    user: "User" = attr.ib()
    member: "Member" = attr.ib(default=MISSING)

    @classmethod
    def _process_dict(cls, data: Dict[str, Any], client: "Snake") -> Dict[str, Any]:
        if data.get("member"):
            fixed_member = data
            fixed_member["user"]["member"] = fixed_member["member"]
            data["member"] = client.cache.place_member_data(data["guild_scheduled_event_id"], fixed_member["user"])
        data["user"] = client.cache.place_user_data(data["user"])
        data["id"] = data["user"].id
        return data



@define()
class ScheduledEvent(DiscordObject):
    name: str = attr.ib()
    description: str = attr.ib(default=MISSING)
    entity_type: Union[ScheduledEventEntityType, int] = attr.ib(converter=ScheduledEventEntityType)
    """	the type of the scheduled event"""
    scheduled_start_time: Timestamp = attr.ib(converter=timestamp_converter)
    """ a Timestamp object representing the scheduled start time of the event """
    scheduled_end_time: Optional[Timestamp] = attr.ib(default=MISSING, converter=optional(timestamp_converter))
    """	optinal Timstamp object representing the scheduled end time, required if entity_type is EXTERNAL"""
    privacy_level: Union[ScheduledEventPrivacyLevel, int] = attr.ib(converter=ScheduledEventPrivacyLevel)
    """the privacy level of the scheduled event"""
    status: Union[ScheduledEventStatus, int] = attr.ib(converter=ScheduledEventStatus)
    """	the status of the scheduled event"""
    entity_id: Optional["Snowflake_Type"] = attr.ib(default=MISSING, converter=optional(to_snowflake))
    """the id of an entity associated with a guild scheduled event"""
    entity_metadata: Optional[Dict[str, Any]] = attr.ib(default=MISSING) # TODO make this 
    """the metadata associated with the entity_type"""
    user_count: int = attr.ib(default=MISSING)
    """	the number of users subscribed to the scheduled event"""

    _guild_id: "Snowflake_Type" = attr.ib(converter=to_snowflake)
    _creator: Optional["User"] = attr.ib(default=MISSING)
    _creator_id: Optional["Snowflake_Type"] = attr.ib(default=MISSING, converter=optional(to_snowflake))
    _channel_id: Optional["Snowflake_Type"] = attr.ib(default=None, converter=optional(to_snowflake))

    __guild: "Guild" = attr.ib()

    @property
    async def creator(self) -> Optional["User"]:
        """Returns the user who created this event

        !!! note:
            Events made before October 25th, 2021 will not have a creator.
        """
        return await self._client.cache.get_user(self._creator_id) if self._creator_id else None

    @classmethod
    def _process_dict(cls, data: Dict[str, Any], client: "Snake") -> Dict[str, Any]:
        if data.get("creator"):
            data["creator"] = client.cache.place_user_data(data["creator"])
        if data.get("channel_id"):
            data["channel"] = client.cache.get_channel("channel_id")

        data = super()._process_dict(data, client)
        return data

    @property
    def location(self) -> Optional[str]:
        """Returns the external locatian of this event"""
        if self.entity_type == ScheduledEventEntityType.EXTERNAL:
            return self.entity_metadata["location"]
        return None

    @property
    def invite_url(self) -> str:
        """ The event invite url """



    async def get_channel(self) -> Optional[Union["GuildVoice", "GuildStageVoice"]]:
        """Returns the channel this event is scheduled in if it is scheduled in a channel"""
        return self._client.cache.channel_cache.get(self._channel_id) if self._channel_id else None

    async def get_event_users(
        self,
        limit: Optional[int] = 100,
        with_member_data: bool = False,
        before: Optional["Snowflake_Type"] = MISSING,
        after: Optional["Snowflake_Type"] = MISSING,
    ) -> Optional[List["ScheduledEventUser"]]:
        """Get event users

        Args:
            limit: Discord defualts to 100
        """
        event_users =  await self._client.http.get_scheduled_event_users(self._guild_id, self.id, limit, with_member_data)
        if event_users:
            return ScheduledEventUser.from_list(event_users, self._client)
        else:
            return None

    async def delete(self, reason: str = MISSING) -> None:
        """Deletes this event"""
        await self._client.http.delete_scheduled_event(self._guild_id, self.id, reason)

    async def edit(
        self,
        name: str = MISSING,
        description: str = MISSING,
        channel_id: Optional["Snowflake_Type"] = MISSING,
        entity_type: ScheduledEventEntityType = MISSING,
        scheduled_start_time: "Timestamp" = MISSING,
        scheduled_end_time: "Timestamp" = MISSING,
        status: ScheduledEventStatus = MISSING,
        entity_metadata: dict = MISSING,
        privacy_level: ScheduledEventPrivacyLevel = MISSING,
        reason: str = MISSING,
    ):
        """Edits this event

        Parameters:
            name: The name of the event
            description: The description of the event
            channel_id: The channel id of the event
            entity_type: The type of the event
            start_time: The scheduled start time of the event
            end_time: The scheduled end time of the event
            status: The status of the event
            entity_metadata: The metadata of the event
            privacy_level: The privacy level of the event
            reason: The reason for editing the event
        """
        payload = dict(
            name=name,
            description=description,
            channel_id=channel_id,
            entity_type=entity_type,
            scheduled_start_time=scheduled_start_time.isoformat(),
            scheduled_end_time=scheduled_end_time.isoformat(),
            status=status,
            entity_metadata=entity_metadata,
            privacy_level=privacy_level,
        )
        await self._client.http.modify_scheduled_event(self._guild_id, self.id, payload, reason)
