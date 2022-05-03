from typing import TYPE_CHECKING, Optional

from naff.client.const import MISSING, Absent
from naff.client.utils.attr_utils import define, field
from naff.models.discord.enums import StagePrivacyLevel
from naff.models.discord.snowflake import to_snowflake
from .base import DiscordObject

if TYPE_CHECKING:
    from naff.models import Guild, GuildStageVoice, Snowflake_Type

__all__ = ("StageInstance",)


@define
class StageInstance(DiscordObject):
    topic: str = field()
    privacy_level: StagePrivacyLevel = field()
    discoverable_disabled: bool = field()

    _guild_id: "Snowflake_Type" = field(converter=to_snowflake)
    _channel_id: "Snowflake_Type" = field(converter=to_snowflake)

    @property
    def guild(self) -> "Guild":
        return self._client.cache.get_guild(self._guild_id)

    @property
    def channel(self) -> "GuildStageVoice":
        return self._client.cache.get_channel(self._channel_id)

    async def delete(self, reason: Absent[Optional[str]] = MISSING) -> None:
        """
        Delete this stage instance. Effectively closes the stage.

        Args:
            reason: The reason for this deletion, for the audit log

        """
        await self._client.http.delete_stage_instance(self._channel_id, reason)
