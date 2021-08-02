from typing import List
from typing import Optional
from typing import TYPE_CHECKING

from dis_snek.models.discord_objects.channel import BaseChannel
from dis_snek.models.discord_objects.channel import Thread
from dis_snek.models.discord_objects.channel import TYPE_ALL_CHANNEL
from dis_snek.models.snowflake import Snowflake
from dis_snek.models.snowflake import Snowflake_Type

if TYPE_CHECKING:
    from dis_snek.client import Snake


class BaseGuild(Snowflake):
    __slots__ = "id", "unavailable", "_client"

    def __init__(self, data, client):
        self._client: Snake = client
        self.id: Snowflake_Type = data["id"]
        self.unavailable: bool = data.get("unavailable", False)


class Guild(BaseGuild):
    __slots__ = (
        "name",
        "icon",
        "icon_hash",
        "splash",
        "discovery_splash",
        "is_owner",
        "owner_id",
        "permissions",
        "afk_channel_id",
        "afk_timeout",
        "widget_enabled",
        "widget_channel_id",
        "verification_level",
        "default_message_notifications",
        "explicit_content_filter",
        "roles",
        "emojis",
        "features",
        "mfa_level",
        "system_channel_id",
        "system_channel_flags",
        "rules_channel_id",
        "joined_at",
        "large",
        "member_count",
        "voice_states",
        "members",
        "_channels",
        "_threads",
        "presences",
        "max_presences",
        "max_members",
        "vanity_url_code",
        "description",
        "banner",
        "premium_tier",
        "premium_sub_count",
        "preferred_locale",
        "public_updates_channel_id",
        "max_video_channel_users",
        "welcome_screen",
        "nsfw_level",
        "stage_instances",
        "stickers",
    )

    def __init__(self, data: dict, client):
        super().__init__(data, client)

        self.name: str = data.get("name")
        self.icon: Optional[str] = data.get("icon")
        self.icon_hash: Optional[str] = data.get("icon_hash")
        self.splash: Optional[str] = data.get("splash")
        self.discovery_splash: Optional[str] = data.get("discovery_splash")
        self.is_owner: bool = data.get("owner", False)
        self.owner_id: Snowflake_Type = data.get("owner_id")
        self.permissions: Optional[str] = data.get("permissions")
        self.afk_channel_id: Optional[Snowflake_Type] = data.get("afk_channel_id")
        self.afk_timeout: Optional[int] = data.get("afk_timeout", 0)
        self.widget_enabled: bool = data.get("widget_enabled", False)
        self.widget_channel_id: Optional[Snowflake_Type] = data.get("widget_channel_id")
        self.verification_level: int = data.get("verification_level", 0)
        self.default_message_notifications: int = data.get("default_message_notifications", 0)
        self.explicit_content_filter: int = data.get("explicit_content_filter", 0)
        self.roles: List[{}] = data.get("roles", [])
        self.emojis: List[{}] = data.get("emojis", [])
        self.features: List[str] = data.get("features", [])
        self.mfa_level: int = data.get("mfa_level", 0)
        self.system_channel_id: Optional[Snowflake_Type] = data.get("system_channel_id")
        self.system_channel_flags: int = data.get("system_channel_flags", 0)
        self.rules_channel_id: Optional[Snowflake_Type] = data.get("rules_channel_id")
        self.joined_at: str = data.get("joined_at")
        self.large: bool = data.get("large", False)
        self.member_count: int = data.get("member_count", 0)
        self.voice_states: List[{}] = data.get("voice_states", 0)
        self.members: List[{}] = data.get("members", [])
        self._channels: List[BaseChannel] = []
        self._threads: List[Thread] = []
        self.presences: List[{}] = data.get("presences", [])
        self.max_presences: Optional[int] = data.get("max_presences")
        self.max_members: Optional[int] = data.get("max_members")
        self.vanity_url_code: Optional[str] = data.get("vanity_url_code")
        self.description: Optional[str] = data.get("description")
        self.banner: Optional[str] = data.get("banner")
        self.premium_tier: Optional[str] = data.get("premium_tier")
        self.premium_sub_count: int = data.get("premium_subscription_count", 0)
        self.preferred_locale: str = data.get("preferred_locale")
        self.public_updates_channel_id: Optional[Snowflake_Type] = data.get("public_updates_channel_id")
        self.max_video_channel_users: int = data.get("max_video_channel_users", 0)
        self.welcome_screen: Optional[{}] = data.get("welcome_screen", [])
        self.nsfw_level: int = data.get("nsfw_level", 0)
        self.stage_instances: List[{}] = data.get("stage_instances", [])
        self.stickers: List[{}] = data.get("stickers", [])

        if not self.member_count and "approximate_member_count" in data:
            self.member_count = data.get("approximate_member_count", 0)

        channels: List[{}] = data.get("channels", [])
        threads: List[{}] = data.get("threads", [])

        for c_data in channels:
            self._channels.append(BaseChannel.from_dict(c_data, self._client))

        for t_data in threads:
            self._threads.append(BaseChannel.from_dict(t_data, self._client))

    @property
    async def channels(self) -> List[TYPE_ALL_CHANNEL]:
        if not self._channels:
            # need to acquire channels
            _channels = await self._client.http.get_channels(self.id)

            for c_data in _channels:
                self._channels.append(BaseChannel.from_dict(c_data, self._client))
        return self._channels
