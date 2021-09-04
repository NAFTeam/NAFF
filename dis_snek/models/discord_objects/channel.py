from typing import TYPE_CHECKING, Any, AsyncIterator, Awaitable, Dict, List, Optional, Union

import attr
from attr.converters import optional as optional_c

from dis_snek.errors import SnakeException
from dis_snek.mixins.send import SendMixin
from dis_snek.models.discord import DiscordObject
from dis_snek.models.enums import ChannelTypes, OverwriteTypes, Permissions, VideoQualityModes
from dis_snek.models.snowflake import SnowflakeObject, to_snowflake
from dis_snek.models.timestamp import Timestamp
from dis_snek.utils.attr_utils import define, field
from dis_snek.utils.proxy import CacheView, CacheProxy
from dis_snek.utils.converters import timestamp_converter

if TYPE_CHECKING:
    from aiohttp import FormData

    from dis_snek.client import Snake
    from dis_snek.models.discord_objects.message import Message
    from dis_snek.models.discord_objects.user import User
    from dis_snek.models.snowflake import Snowflake_Type


@define()
class BaseChannel(DiscordObject):
    _type: ChannelTypes = field(converter=ChannelTypes)
    name: Optional[str] = field(default=None)

    @classmethod
    def from_dict_factory(cls, data: dict, client: "Snake") -> "TYPE_ALL_CHANNEL":
        """
        Creates a channel object of the appropriate type

        :param data:
        :param client:

        :return:
        """
        channel_type = data.get("type", None)
        channel_class = TYPE_CHANNEL_MAPPING.get(channel_type, None)
        if not channel_class:
            raise TypeError(f"Unsupported channel type for {data} ({channel_type}), please consult the docs.")

        return channel_class.from_dict(data, client)


@define()
class PermissionOverwrite(SnowflakeObject):
    type: "OverwriteTypes" = field(repr=True, converter=OverwriteTypes)
    allow: "Permissions" = field(repr=True, converter=Permissions)
    deny: "Permissions" = field(repr=True, converter=Permissions)


@define(slots=False)  # can we make some workaround?
class _GuildChannelMixin:
    guild_id: Optional["Snowflake_Type"] = attr.ib(default=None)
    position: Optional[int] = attr.ib(default=0)
    nsfw: bool = attr.ib(default=False)
    parent_id: Optional["Snowflake_Type"] = attr.ib(default=None)
    _permission_overwrites: Dict["Snowflake_Type", "PermissionOverwrite"] = attr.ib(factory=list)

    @classmethod
    def process_dict(cls, data: Dict[str, Any], client: "Snake") -> Dict[str, Any]:
        permission_overwrites = data.get("permission_overwrites", [])
        data["permission_overwrites"] = {
            obj.id: obj for obj in (PermissionOverwrite(**permission) for permission in permission_overwrites)
        }
        return data


class _ReadOnlyChannelMixin:
    def send(self, *_, **__):
        raise SnakeException("This channel is readonly. You cannot send messages to it.")


@attr.s(slots=True, kw_only=True)
class TextChannel(BaseChannel, SendMixin):
    rate_limit_per_user: int = attr.ib(default=0)
    last_message_id: Optional["Snowflake_Type"] = attr.ib(default=None)
    default_auto_archive_duration: int = attr.ib(default=60)
    last_pin_timestamp: Optional[Timestamp] = attr.ib(default=None, converter=optional_c(timestamp_converter))

    async def _send_http_request(self, message_payload: Union[dict, "FormData"]) -> dict:
        return await self._client.http.create_message(message_payload, self.id)

    async def fetch_message(self, message_id: "Snowflake_Type") -> "Message":
        message_id = to_snowflake(message_id)
        message: "Message" = await self._client.cache.get_message(self.id, message_id)
        return message


@attr.s(slots=True, kw_only=True)
class VoiceChannel(BaseChannel):
    bitrate: int = attr.ib()
    user_limit: int = attr.ib()
    rtc_region: str = attr.ib(default="auto")
    video_quality_mode: Union[VideoQualityModes, int] = attr.ib(default=VideoQualityModes.AUTO)


@attr.s(slots=True, kw_only=True)
class GuildVoice(VoiceChannel, _GuildChannelMixin):
    pass


@attr.s(slots=True, kw_only=True)
class GuildStageVoice(GuildVoice):
    pass


@attr.s(slots=True, kw_only=True)
class DMGroup(TextChannel):
    owner_id: "Snowflake_Type" = attr.ib(default=None)
    application_id: Optional["Snowflake_Type"] = attr.ib(default=None)
    _recipients_ids: List["Snowflake_Type"] = attr.ib(factory=list)

    @classmethod
    def process_dict(cls, data: Dict[str, Any], client: "Snake") -> Dict[str, Any]:
        recipients_data = data.pop("recipients", [])
        recipients_ids = []
        for recipient_data in recipients_data:
            recipient_id = recipient_data["id"]
            recipients_ids.append(recipient_id)
        data["recipients_ids"] = recipients_ids

        return data

    @property
    def recipients(self) -> Union[CacheView, Awaitable[Dict["Snowflake_Type", "User"]], AsyncIterator["User"]]:
        return CacheView(ids=self._recipients_ids, method=self._client.cache.get_user)


@attr.s(slots=True, kw_only=True)
class DM(DMGroup):
    @classmethod
    def process_dict(cls, data: Dict[str, Any], client: "Snake") -> Dict[str, Any]:
        data = super().process_dict(data, client)
        user_id = data["recipients_ids"][0]
        client.cache.place_dm_channel_id(user_id, data["id"])
        return data

    @property
    def recipient(self) -> Union[CacheProxy, Awaitable["User"], "User"]:
        return CacheProxy(id=self._recipients_ids[0], method=self._client.cache.get_user)


@attr.s(slots=True, kw_only=True)
class GuildText(TextChannel, _GuildChannelMixin):
    topic: Optional[str] = attr.ib(default=None)


@attr.s(slots=True, kw_only=True)
class GuildNews(GuildText):
    pass


@attr.s(slots=True, kw_only=True)
class GuildCategory(GuildText, _ReadOnlyChannelMixin):
    pass  # todo forbid send() and getting messages. Anti-send-mixin?


@attr.s(slots=True, kw_only=True)
class GuildStore(GuildText, _ReadOnlyChannelMixin):
    pass  # todo forbid send() and getting messages


@attr.s(slots=True, kw_only=True)
class Thread(GuildText):
    message_count: int = attr.ib(default=0)
    member_count: int = attr.ib(default=0)

    archived: bool = attr.ib(default=False)
    auto_archive_duration: int = attr.ib(
        default=attr.Factory(lambda self: self.default_auto_archive_duration, takes_self=True)
    )
    locked: bool = attr.ib(default=False)
    archive_timestamp: Optional[Timestamp] = attr.ib(default=None, converter=optional_c(timestamp_converter))

    @classmethod
    def process_dict(cls, data: Dict[str, Any], client: "Snake") -> Dict[str, Any]:
        data = super().process_dict(data, client)
        thread_metadata: dict = data.get("thread_metadata", {})
        data.update(thread_metadata)
        return data

    @property
    def private(self) -> bool:
        return self._type == ChannelTypes.GUILD_PRIVATE_THREAD


TYPE_ALL_CHANNEL = Union[
    BaseChannel,
    GuildCategory,
    GuildStore,
    TextChannel,
    VoiceChannel,
    DMGroup,
    DM,
    GuildText,
    Thread,
    GuildNews,
    GuildVoice,
    GuildStageVoice,
]


TYPE_GUILD_CHANNEL = Union[GuildCategory, GuildStore, GuildNews, GuildText, GuildVoice, GuildStageVoice]


TYPE_CHANNEL_MAPPING = {
    ChannelTypes.GUILD_TEXT: GuildText,
    ChannelTypes.GUILD_NEWS: GuildNews,
    ChannelTypes.GUILD_VOICE: GuildVoice,
    ChannelTypes.GUILD_STAGE_VOICE: GuildStageVoice,
    ChannelTypes.GUILD_CATEGORY: GuildCategory,
    ChannelTypes.GUILD_STORE: GuildStore,
    ChannelTypes.GUILD_PUBLIC_THREAD: Thread,
    ChannelTypes.GUILD_PRIVATE_THREAD: Thread,
    ChannelTypes.GUILD_NEWS_THREAD: Thread,
    ChannelTypes.DM: DM,
    ChannelTypes.GROUP_DM: DMGroup,
}
