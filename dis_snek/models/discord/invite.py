from typing import TYPE_CHECKING, Optional, Union, Dict, Any, Type

from dis_snek.client.const import MISSING, Absent, T
from dis_snek.client.utils.attr_utils import define, field
from dis_snek.client.utils.converters import optional
from dis_snek.client.utils.converters import timestamp_converter
from dis_snek.models.discord.enums import InviteTargetTypes
from dis_snek.models.discord.guild import GuildPreview
from dis_snek.models.discord.snowflake import to_snowflake, to_optional_snowflake
from dis_snek.models.discord.stage_instance import StageInstance
from dis_snek.models.discord.timestamp import Timestamp
from .base import ClientObject

if TYPE_CHECKING:
    from dis_snek.client import Snake
    from dis_snek.models import TYPE_GUILD_CHANNEL
    from dis_snek.models.discord.user import User
    from dis_snek.models.discord.snowflake import Snowflake_Type

__all__ = ["Invite"]


def deserialize(cls: Type[T]) -> T:
    """
    Deserialize a class from a dict.

    Args:
        cls: The class to deserialize

    Returns:
        The deserialized class
    """

    def inner(value: dict, data: Dict[str, Any], client: "Snake") -> T:
        return cls.from_dict(value, client)

    return inner


def to_user_id(value: dict, data: Dict[str, Any], client: "Snake") -> "Snowflake_Type":
    user = client.cache.place_user_data(value)
    return user.id


def get_id(value: dict, data: Dict[str, Any], client: "Snake") -> "Snowflake_Type":
    return to_snowflake(value["id"])


@define()
class Invite(ClientObject):
    code: str = field(repr=True)

    # metadata
    uses: int = field(default=0, repr=True)
    max_uses: int = field(default=0)
    created_at: Timestamp = field(default=MISSING, converter=optional(timestamp_converter), repr=True)
    expires_at: Optional[Timestamp] = field(default=None, converter=optional(timestamp_converter), repr=True)
    temporary: bool = field(default=False, repr=True)

    # target data
    target_type: Optional[InviteTargetTypes] = field(default=None, converter=optional(InviteTargetTypes), repr=True)
    approximate_presence_count: Optional[int] = field(default=MISSING)
    approximate_member_count: Optional[int] = field(default=MISSING)
    scheduled_event: Optional["Snowflake_Type"] = field(
        default=None, data_key="target_event_id", converter=to_optional_snowflake, repr=True
    )
    stage_instance: Optional[StageInstance] = field(default=None, deserializer=deserialize(StageInstance))
    target_application: Optional[dict] = field(default=None)
    guild_preview: Optional[GuildPreview] = field(
        default=MISSING, data_key="guild", deserializer=deserialize(GuildPreview)
    )

    # internal for props
    _channel_id: Optional["Snowflake_Type"] = field(repr=True, data_key="channel", deserializer=get_id)
    _inviter_id: Optional["Snowflake_Type"] = field(
        default=None, data_key="inviter", deserializer=to_user_id, repr=True
    )
    _target_user_id: Optional["Snowflake_Type"] = field(default=None, converter=to_optional_snowflake)

    @property
    def channel(self) -> "TYPE_GUILD_CHANNEL":
        """The channel the invite is for."""
        return self._client.cache.get_channel(self._channel_id)

    @property
    def inviter(self) -> Optional["User"]:
        """The user that created the invite or None."""
        return self._client.cache.get_user(self._inviter_id) if self._inviter_id else None

    @property
    def target_user(self) -> Optional["User"]:
        """The user whose stream to display for this voice channel stream invite or None."""
        return self._client.cache.get_user(self._target_user_id) if self._target_user_id else None

    def __str__(self) -> str:
        return self.link

    @property
    def link(self) -> str:
        if self.scheduled_event:
            return f"https://discord.gg/{self.code}?event={self.scheduled_event}"
        return f"https://discord.gg/{self.code}"

    async def delete(self, reason: Absent[str] = MISSING) -> None:
        """
        Delete this invite.

        You must have the `manage_channels` permission on the channel this invite belongs to.

        Note:
            With `manage_guild` permission, you can delete any invite across the guild.

        Args:
            reason: The reason for the deletion
        """
        await self._client.http.delete_invite(self.code, reason=reason)
