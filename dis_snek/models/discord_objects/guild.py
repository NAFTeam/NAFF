from functools import partial
from typing import TYPE_CHECKING, AsyncIterator, Awaitable, Dict, List, Optional, Union

import attr

from dis_snek.models.discord_objects.channel import TYPE_GUILD_CHANNEL
from dis_snek.models.base_object import DiscordObject
from dis_snek.utils.attr_utils import define, field
from dis_snek.models.snowflake import Snowflake_Type
from dis_snek.utils.cache import CacheProxy, CacheView

if TYPE_CHECKING:
    from dis_snek.models.discord_objects.channel import Thread
    from dis_snek.models.discord_objects.user import Member
    from dis_snek.models.discord_objects.role import Role


@define()
class Guild(DiscordObject):
    unavailable: bool = attr.ib(default=False)
    name: str = attr.ib()
    _icon: Optional[str] = attr.ib(default=None)  # todo merge, convert to asset
    _icon_hash: Optional[str] = attr.ib(default=None)
    splash: Optional[str] = attr.ib(default=None)
    discovery_splash: Optional[str] = attr.ib(default=None)
    # owner: bool = attr.ib(default=False)  # we get this from api but it's kinda useless to store
    permissions: Optional[str] = attr.ib(default=None)  # todo convert to permissions obj
    afk_channel_id: Optional[Snowflake_Type] = attr.ib(default=None)
    afk_timeout: Optional[int] = attr.ib(default=None)
    widget_enabled: bool = attr.ib(default=False)
    widget_channel_id: Optional[Snowflake_Type] = attr.ib(default=None)
    verification_level: int = attr.ib(default=0)  # todo enum
    default_message_notifications: int = attr.ib(default=0)  # todo enum
    explicit_content_filter: int = attr.ib(default=0)  # todo enum
    _emojis: List[dict] = attr.ib(factory=list)
    _features: List[str] = attr.ib(factory=list)
    mfa_level: int = attr.ib(default=0)
    system_channel_id: Optional[Snowflake_Type] = attr.ib(default=None)
    system_channel_flags: int = attr.ib(default=0)  # todo enum
    rules_channel_id: Optional[Snowflake_Type] = attr.ib(default=None)
    joined_at: str = attr.ib()
    large: bool = attr.ib(default=False)
    member_count: int = attr.ib(default=0)
    voice_states: List[dict] = attr.ib(factory=list)
    presences: List[dict] = attr.ib(factory=list)
    max_presences: Optional[int] = attr.ib(default=None)
    max_members: Optional[int] = attr.ib(default=None)
    vanity_url_code: Optional[str] = attr.ib(default=None)
    description: Optional[str] = attr.ib(default=None)
    banner: Optional[str] = attr.ib(default=None)
    premium_tier: Optional[str] = attr.ib(default=None)
    premium_subscription_count: int = attr.ib(default=0)
    preferred_locale: str = attr.ib()
    public_updates_channel_id: Optional[Snowflake_Type] = attr.ib(default=None)
    max_video_channel_users: int = attr.ib(default=0)
    welcome_screen: Optional[dict] = attr.ib(factory=list)
    nsfw_level: int = attr.ib(default=0)  # todo enum
    stage_instances: List[dict] = attr.ib(factory=list)
    stickers: List[dict] = attr.ib(factory=list)

    _owner_id: "Snowflake_Type" = attr.ib()
    _channel_ids: List["Snowflake_Type"] = attr.ib(factory=list)
    _thread_ids: List["Snowflake_Type"] = attr.ib(factory=list)
    _member_ids: List["Snowflake_Type"] = attr.ib(factory=list)
    _role_ids: List["Snowflake_Type"] = attr.ib(factory=list)

    @classmethod
    def process_dict(cls, data, client):
        guild_id = data["id"]

        channels_data = data.pop("channels", [])
        data["channel_ids"] = [client.cache.place_channel_data(channel_data).id for channel_data in channels_data]

        threads_data = data.pop("threads", [])
        data["thread_ids"] = [client.cache.place_channel_data(thread_data).id for thread_data in threads_data]

        members_data = data.pop("members", [])
        data["member_ids"] = [client.cache.place_member_data(guild_id, member_data).id for member_data in members_data]

        roles_data = data.pop("roles", [])
        data["role_ids"] = list(client.cache.place_role_data(guild_id, roles_data).keys())

        return data

    @property
    def channels(
        self,
    ) -> Union[CacheView, Awaitable[Dict[Snowflake_Type, TYPE_GUILD_CHANNEL]], AsyncIterator[TYPE_GUILD_CHANNEL]]:
        return CacheView(ids=self._channel_ids, method=self._client.cache.get_channel)

    @property
    def threads(self) -> Union[CacheView, Awaitable[Dict[Snowflake_Type, "Thread"]], AsyncIterator["Thread"]]:
        return CacheView(ids=self._thread_ids, method=self._client.cache.get_channel)

    @property
    def members(self) -> Union[CacheView, Awaitable[Dict[Snowflake_Type, "Member"]], AsyncIterator["Member"]]:
        return CacheView(ids=self._member_ids, method=partial(self._client.cache.get_member, self.id))

    @property
    def roles(self) -> Union[CacheView, Awaitable[Dict[Snowflake_Type, "Role"]], AsyncIterator["Role"]]:
        return CacheView(ids=self._role_ids, method=partial(self._client.cache.get_role, self.id))

    @property
    def me(self) -> Union[CacheProxy, Awaitable["Member"], "Member"]:
        return CacheProxy(id=self._client.user.id, method=partial(self._client.cache.get_member, self.id))

    @property
    def owner(self) -> Union[CacheProxy, Awaitable["Member"], "Member"]:
        return CacheProxy(id=self._owner_id, method=partial(self._client.cache.get_member, self.id))

    def is_owner(self, member: "Member") -> bool:
        return self._owner_id == member.id

    # @property
    # def
    # if not self.member_count and "approximate_member_count" in data:
    #     self.member_count = data.get("approximate_member_count", 0)
