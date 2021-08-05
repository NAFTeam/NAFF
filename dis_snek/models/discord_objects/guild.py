from typing import Dict
from typing import List
from typing import Optional
from typing import Any

import attr
from attr.converters import optional as optional_c

from dis_snek.models.discord_objects.channel import BaseChannel
from dis_snek.models.discord_objects.channel import Thread
from dis_snek.models.discord_objects.channel import TYPE_ALL_CHANNEL
from dis_snek.models.snowflake import Snowflake
from dis_snek.models.snowflake import Snowflake_Type
from dis_snek.utils.attr_utils import default_kwargs
from dis_snek.utils.attr_utils import DictSerializationMixin


@attr.s(**default_kwargs)
class BaseGuild(Snowflake, DictSerializationMixin):
    _client: Any = attr.ib()
    unavailable: bool = attr.ib(default=False)


@attr.define(**default_kwargs)
class Guild(BaseGuild):
    name: str = attr.ib()
    _icon: Optional[str] = attr.ib(default=None)  # todo merge, convert to asset
    _icon_hash: Optional[str] = attr.ib(default=None)
    splash: Optional[str] = attr.ib(default=None)
    discovery_splash: Optional[str] = attr.ib(default=None)
    is_owner: bool = attr.ib(default=False)
    owner_id: Snowflake_Type = attr.ib()
    permissions: Optional[str] = attr.ib(default=None)  # todo convert to permissions obj
    afk_channel_id: Optional[Snowflake_Type] = attr.ib(default=None)
    afk_timeout: Optional[int] = attr.ib(default=None)
    widget_enabled: bool = attr.ib(default=False)
    widget_channel_id: Optional[Snowflake_Type] = attr.ib(default=None)
    verification_level: int = attr.ib(default=0)  # todo enum
    default_message_notifications: int = attr.ib(default=0)  # todo enum
    explicit_content_filter: int = attr.ib(default=0)  # todo enum
    _roles: List[dict] = attr.ib(factory=list)
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
    members: List[dict] = attr.ib(factory=list)
    # _channels: Dict[str, BaseChannel] = {}
    # _threads: Dict[str, Thread] = {}
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

    # if not self.member_count and "approximate_member_count" in data:
    #     self.member_count = data.get("approximate_member_count", 0)

    # channels: List[{}] = data.get("channels", [])
    # threads: List[{}] = data.get("threads", [])
    #
    # for c_data in channels:
    #     _channel = BaseChannel.from_dict(c_data, self._client)
    #     self._channels[_channel.id] = _channel
    #
    # for t_data in threads:
    #     _channel = BaseChannel.from_dict(t_data, self._client)
    #     self._threads[_channel.id] = _channel

    # @property
    # async def channels(self) -> List[TYPE_ALL_CHANNEL]:
    #     if not self._channels:
    #         # need to acquire channels
    #         _channels = await self._client.http.get_channels(self.id)
    #
    #         for c_data in _channels:
    #             self._channels.append(BaseChannel.from_dict(c_data, self._client))
    #     return self._channels
