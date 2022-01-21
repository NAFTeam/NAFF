from typing import TYPE_CHECKING, Optional, Union, Dict, Any

from attr.converters import optional as optional_c

from dis_snek.client.const import MISSING, Absent
from dis_snek.client.utils.attr_utils import define, field
from dis_snek.client.utils.converters import optional_timestamp_converter, timestamp_converter
from dis_snek.models.discord.application import Application
from dis_snek.models.discord.enums import InviteTargetTypes
from dis_snek.models.discord.guild import GuildPreview
from dis_snek.models.discord.snowflake import to_snowflake
from dis_snek.models.discord.stage_instance import StageInstance
from dis_snek.models.discord.timestamp import Timestamp
from .base import ClientObject

if TYPE_CHECKING:
    from dis_snek.client import Snake
    from dis_snek.models import TYPE_GUILD_CHANNEL
    from dis_snek.models.discord.user import User
    from dis_snek.models.discord.snowflake import Snowflake_Type


@define()
class Invite(ClientObject):
    code: str = field(repr=True)

    # metadata
    uses: int = field(default=0, repr=True)
    max_uses: int = field(default=0)
    created_at: Timestamp = field(default=MISSING, converter=optional_c(optional_timestamp_converter))
    expires_at: Optional[Timestamp] = field(default=None, converter=optional_c(timestamp_converter), repr=True)
    temporary: bool = field(default=False, repr=True)

    # target data
    target_type: Optional[Union[InviteTargetTypes, int]] = field(default=None, converter=optional_c(InviteTargetTypes), repr=True)
    approximate_presence_count: Optional[int] = field(default=MISSING)
    approximate_member_count: Optional[int] = field(default=MISSING)
    scheduled_event: Optional["Snowflake_Type"] = field(default=None, converter=optional_c(to_snowflake), repr=True)
    stage_instance: Optional[StageInstance] = field(default=None)
    target_application: Optional[dict] = field(default=None)
    guild_preview: Optional[GuildPreview] = field(default=MISSING)

    # internal for props
    _channel_id: "Snowflake_Type" = field(converter=to_snowflake, repr=True)
    _inviter_id: Optional["Snowflake_Type"] = field(default=None, converter=optional_c(to_snowflake), repr=True)
    _target_user_id: Optional["Snowflake_Type"] = field(default=None, converter=optional_c(to_snowflake))

    @property
    def channel(self) -> "TYPE_GUILD_CHANNEL":
        """The channel the invite is for."""
        return self._client.cache.channel_cache.get(self._channel_id)

    @property
    def inviter(self) -> Optional["User"]:
        """The user that created the invite or None."""
        return self._client.cache.user_cache.get(self._inviter_id) if self._inviter_id else None

    @property
    def target_user(self) -> Optional["User"]:
        """The user whose stream to display for this voice channel stream invite or None."""
        return self._client.cache.user_cache.get(self._target_user_id) if self._target_user_id else None

    @classmethod
    def _process_dict(cls, data: Dict[str, Any], client: "Snake") -> Dict[str, Any]:
        if "stage_instance" in data:
            data["stage_instance"] = StageInstance.from_dict(data, client)

        if "target_application" in data:
            data["target_application"] = Application.from_dict(data, client)

        if "target_event_id" in data:
            data["scheduled_event"] = data["target_event_id"]

        if channel := data.pop("channel", None):
            # invite metadata does not contain enough info to create a channel object
            data["channel_id"] = channel["id"]

        if guild := data.pop("guild", None):
            data["guild_preview"] = GuildPreview.from_dict(guild, client)

        if inviter := data.pop("inviter", None):
            inviter = client.cache.place_user_data(inviter)
            data["inviter_id"] = inviter.id

        return data

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
