from typing import TYPE_CHECKING, Optional, Union, Dict, Any

from attr.converters import optional as optional_c

from dis_snek.const import MISSING
from dis_snek.models.discord import ClientObject
from dis_snek.models.discord_objects.application import Application
from dis_snek.models.discord_objects.guild import GuildPreview
from dis_snek.models.discord_objects.stage_instance import StageInstance
from dis_snek.models.enums import InviteTargetTypes
from dis_snek.models.snowflake import to_snowflake
from dis_snek.models.timestamp import Timestamp
from dis_snek.utils.attr_utils import define, field
from dis_snek.utils.converters import timestamp_converter

if TYPE_CHECKING:
    from dis_snek.client import Snake
    from dis_snek.models import TYPE_GUILD_CHANNEL
    from dis_snek.models.discord_objects.user import Member
    from dis_snek.models.snowflake import Snowflake_Type


@define()
class Invite(ClientObject):
    code: str = field()

    # metadata
    uses: int = field(default=0)
    max_uses: int = field(default=0)
    created_at: Timestamp = field(default=MISSING, converter=optional_c(timestamp_converter))
    expires_at: Optional[Timestamp] = field(default=None, converter=optional_c(timestamp_converter))
    temporary: bool = field(default=False)

    # target data
    target_type: Optional[Union[InviteTargetTypes, int]] = field(default=None, converter=optional_c(InviteTargetTypes))
    approximate_presence_count: Optional[int] = field(default=MISSING)
    approximate_member_count: Optional[int] = field(default=MISSING)
    scheduled_event: Optional[dict] = field(default=None)  # todo: Scheduled Events
    stage_instance: Optional[StageInstance] = field(default=None)
    target_application: Optional[dict] = field(default=None)
    guild_preview: Optional[GuildPreview] = field(default=MISSING)

    # internal for props
    _channel_id: "Snowflake_Type" = field(converter=to_snowflake)
    _inviter_id: Optional["Snowflake_Type"] = field(default=None, converter=optional_c(to_snowflake))
    _target_user_id: Optional["Snowflake_Type"] = field(default=None, converter=optional_c(to_snowflake))

    @property
    def channel(self) -> "TYPE_GUILD_CHANNEL":
        """the channel the invite is for"""
        return self._client.cache.channel_cache.get(self._channel_id)

    def inviter(self) -> "Member":
        """the user that created the invite"""
        return self._client.cache.guild_cache.get(self._inviter_id) if self._inviter_id else None

    def target_user(self) -> "Member":
        """the user whose stream to display for this voice channel stream invite"""
        return self._client.cache.guild_cache.get(self._target_user_id) if self._inviter_id else None

    @classmethod
    def _process_dict(cls, data: Dict[str, Any], client: "Snake") -> Dict[str, Any]:
        if "stage_instance" in data:
            data["stage_instance"] = StageInstance.from_dict(data, client)

        if "target_application" in data:
            data["target_application"] = Application.from_dict(data, client)

        if channel := data.pop("channel", None):
            # invite metadata does not contain enough info to create a channel object
            data["channel_id"] = channel["id"]

        if guild := data.pop("guild", None):
            data["guild_preview"] = GuildPreview.from_dict(guild, client)

        if inviter := data.pop("inviter", None):
            inviter = client.cache.place_user_data(inviter)
            data["inviter_id"] = inviter.id

        return data

    @property
    def link(self) -> str:
        return f"https://discord.gg/{self.code}"
