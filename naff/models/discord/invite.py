from typing import TYPE_CHECKING, Optional, Union, Dict, Any

from naff.client.const import MISSING, Absent
from naff.client.utils.attr_utils import define, field
from naff.client.utils.attr_converters import optional as optional_c
from naff.client.utils.attr_converters import timestamp_converter
from naff.models.discord.application import Application
from naff.models.discord.enums import InviteTargetTypes
from naff.models.discord.guild import GuildPreview
from naff.models.discord.snowflake import to_snowflake
from naff.models.discord.stage_instance import StageInstance
from naff.models.discord.timestamp import Timestamp
from .base import ClientObject

if TYPE_CHECKING:
    from naff.client import Client
    from naff.models import TYPE_GUILD_CHANNEL
    from naff.models.discord.user import User
    from naff.models.discord.snowflake import Snowflake_Type

__all__ = ("Invite",)


@define()
class Invite(ClientObject):
    code: str = field(repr=True)
    """the invite code (unique ID)"""

    # metadata
    uses: int = field(default=0, repr=True)
    """the guild this invite is for"""
    max_uses: int = field(default=0)
    """max number of times this invite can be used"""
    max_age: int = field(default=0)
    """duration (in seconds) after which the invite expires"""
    created_at: Timestamp = field(default=MISSING, converter=optional_c(timestamp_converter), repr=True)
    """when this invite was created"""
    temporary: bool = field(default=False, repr=True)
    """whether this invite only grants temporary membership"""

    # target data
    target_type: Optional[Union[InviteTargetTypes, int]] = field(
        default=None, converter=optional_c(InviteTargetTypes), repr=True
    )
    """the type of target for this voice channel invite"""
    approximate_presence_count: Optional[int] = field(default=MISSING)
    """approximate count of online members, returned from the `GET /invites/<code>` endpoint when `with_counts` is `True`"""
    approximate_member_count: Optional[int] = field(default=MISSING)
    """approximate count of total members, returned from the `GET /invites/<code>` endpoint when `with_counts` is `True`"""
    scheduled_event: Optional["Snowflake_Type"] = field(default=None, converter=optional_c(to_snowflake), repr=True)
    """guild scheduled event data, only included if `guild_scheduled_event_id` contains a valid guild scheduled event id"""
    expires_at: Optional[Timestamp] = field(default=None, converter=optional_c(timestamp_converter), repr=True)
    """the expiration date of this invite, returned from the `GET /invites/<code>` endpoint when `with_expiration` is `True`"""
    stage_instance: Optional[StageInstance] = field(default=None)
    """stage instance data if there is a public Stage instance in the Stage channel this invite is for (deprecated)"""
    target_application: Optional[dict] = field(default=None)
    """the embedded application to open for this voice channel embedded application invite"""
    guild_preview: Optional[GuildPreview] = field(default=MISSING)
    """the guild this invite is for"""

    # internal for props
    _channel_id: "Snowflake_Type" = field(converter=to_snowflake, repr=True)
    _inviter_id: Optional["Snowflake_Type"] = field(default=None, converter=optional_c(to_snowflake), repr=True)
    _target_user_id: Optional["Snowflake_Type"] = field(default=None, converter=optional_c(to_snowflake))

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

    @classmethod
    def _process_dict(cls, data: Dict[str, Any], client: "Client") -> Dict[str, Any]:
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
        """The invite link."""
        if self.scheduled_event:
            return f"https://discord.gg/{self.code}?event={self.scheduled_event}"
        return f"https://discord.gg/{self.code}"

    async def delete(self, reason: Absent[str] = MISSING) -> None:
        """
        Delete this invite.

        !!! note
            You must have the `manage_channels` permission on the channel this invite belongs to.

        !!! note
            With `manage_guild` permission, you can delete any invite across the guild.

        Args:
            reason: The reason for the deletion of invite.

        """
        await self._client.http.delete_invite(self.code, reason=reason)
