from typing import TYPE_CHECKING, Optional

import attr

from dis_snek.client.const import MISSING, Absent
from dis_snek.client.utils.attr_utils import define
from dis_snek.models.discord.enums import StagePrivacyLevel
from dis_snek.models.discord.snowflake import to_snowflake
from .base import DiscordObject

if TYPE_CHECKING:
    from dis_snek.models import Guild, GuildStageVoice, Snowflake_Type


@define
class StageInstance(DiscordObject):
    topic: str = attr.ib()
    privacy_level: StagePrivacyLevel = attr.ib()
    discoverable_disabled: bool = attr.ib()

    _guild_id: "Snowflake_Type" = attr.ib(converter=to_snowflake)
    _channel_id: "Snowflake_Type" = attr.ib(converter=to_snowflake)

    @property
    def guild(self) -> "Guild":
        return self._client.cache.guild_cache.get(self._guild_id)

    @property
    def channel(self) -> "GuildStageVoice":
        return self._client.cache.channel_cache.get(self._channel_id)

    async def delete(self, reason: Absent[Optional[str]] = MISSING) -> None:
        """
        Delete this stage instance. Effectively closes the stage.

        Args:
            reason: The reason for this deletion, for the audit log

        """
        await self._client.http.delete_stage_instance(self._channel_id, reason)
