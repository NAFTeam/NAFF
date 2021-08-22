from typing import (
    TYPE_CHECKING,
    AsyncIterator,
    Awaitable,
    Dict,
    List,
    Optional,
    Union,
)

import attr
from attr.converters import optional as optional_c

from dis_snek.mixins.send import SendMixin
from dis_snek.models.enums import ChannelTypes
from dis_snek.models.snowflake import Snowflake, Snowflake_Type, to_snowflake
from dis_snek.models.timestamp import Timestamp
from dis_snek.utils.attr_utils import DictSerializationMixin
from dis_snek.utils.cache import CacheProxy, CacheView

if TYPE_CHECKING:
    from dis_snek.client import Snake
    from dis_snek.models.discord_objects.message import Message
    from dis_snek.models.discord_objects.user import User


@attr.s(slots=True, kw_only=True)
class BaseChannel(Snowflake, DictSerializationMixin):
    _client: "Snake" = attr.ib(repr=False)

    _type: ChannelTypes = attr.ib(converter=ChannelTypes)
    name: Optional[str] = attr.ib(default=None)

    @classmethod
    def from_dict(cls, data, client) -> "TYPE_ALL_CHANNEL":
        """
        Creates a channel object of the appropriate type

        :param data:
        :param client:

        :return:
        """
        channel_type = ChannelTypes(data["type"])
        return TYPE_MAPPING[channel_type].from_dict_typed(data, client)

    @classmethod
    def from_dict_typed(cls, data, client) -> "TYPE_ALL_CHANNEL":
        return super().from_dict(data, client)


class _GuildMixin:
    guild_id: Optional[Snowflake_Type] = attr.ib(default=None)
    position: Optional[int] = attr.ib(default=0)
    nsfw: bool = attr.ib(default=False)
    parent_id: Optional[Snowflake_Type] = attr.ib(default=None)
    permission_overwrites: list[dict] = attr.ib(factory=list)  # TODO  permissions obj
    permissions: Optional[str] = attr.ib(default=None)  # only in slash


@attr.s(slots=True, kw_only=True)
class TextChannel(BaseChannel, SendMixin):
    rate_limit_per_user: int = attr.ib(default=0)
    last_message_id: Optional[Snowflake_Type] = attr.ib(default=None)
    default_auto_archive_duration: int = attr.ib(default=60)
    last_pin_timestamp: Optional[Timestamp] = attr.ib(default=None, converter=optional_c(Timestamp.fromisoformat))

    async def fetch_message(self, message_id: Snowflake_Type) -> "Message":
        message_id = to_snowflake(message_id)
        message: "Message" = await self._client.cache.get_message(self.id, message_id)
        return message

    async def _send_http_request(self, message) -> "Message":
        return await self._client.http.create_message(message, self.id)


@attr.s(slots=True, kw_only=True)
class VoiceChannel(BaseChannel):
    bitrate: int = attr.ib()
    user_limit: int = attr.ib()
    rtc_region: str = attr.ib(default="auto")
    video_quality_mode: int = attr.ib(default=1)  # todo convert to enum


@attr.s(slots=True, kw_only=True)
class GuildVoice(VoiceChannel, _GuildMixin):
    pass


@attr.s(slots=True, kw_only=True)
class GuildStageVoice(GuildVoice):
    pass


@attr.s(slots=True, kw_only=True)
class DMGroup(TextChannel):
    owner_id: Snowflake_Type = attr.ib()
    application_id: Optional[Snowflake_Type] = attr.ib(default=None)
    _recipients_ids: List[Snowflake_Type] = attr.ib(factory=list)

    @classmethod
    def process_dict(cls, data: dict, client) -> "DMGroup":
        recipients_data = data.pop("recipients", [])
        recipients_ids = []
        for recipient_data in recipients_data:
            recipient_id = recipient_data["id"]
            recipients_ids.append(recipient_id)
        data["recipients_ids"] = recipients_ids

        return super().from_dict_typed(data, client)

    @property
    def recipients(self) -> Union[CacheView, Awaitable[Dict[Snowflake_Type, "User"]], AsyncIterator["User"]]:
        return CacheView(ids=self._recipients_ids, method=self._client.cache.get_user)


@attr.s(slots=True, kw_only=True)
class DM(DMGroup):
    @classmethod
    def process_dict(cls, data: dict, client: "Snake") -> "DM":
        data = super().process_dict(data, client)
        user_id = data["recipients_ids"][0]
        client.cache.place_dm_channel_id(user_id, data["id"])
        return super().from_dict_typed(data, client)

    @property
    def recipient(self) -> Union[CacheProxy, Awaitable["User"], "User"]:
        return CacheProxy(id=self._recipients_ids[0], method=self._client.cache.get_user)


@attr.s(slots=True, kw_only=True)
class GuildText(TextChannel, _GuildMixin):
    topic: Optional[str] = attr.ib(default=None)


@attr.s(slots=True, kw_only=True)
class GuildNews(GuildText):
    pass


@attr.s(slots=True, kw_only=True)
class GuildCategory(GuildText):
    pass  # todo forbid send() and getting messages


@attr.s(slots=True, kw_only=True)
class GuildStore(GuildText):
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
    archive_timestamp: Optional[Timestamp] = attr.ib(default=None, converter=optional_c(Timestamp.fromisoformat))

    @classmethod
    def process_dict(cls, data: dict, client: "Snake") -> "Thread":
        thread_metadata: dict = data.get("thread_metadata", {})
        data.update(thread_metadata)
        return super().from_dict_typed(data, client)

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


TYPE_MAPPING = {
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
