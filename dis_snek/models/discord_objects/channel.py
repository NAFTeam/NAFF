from typing import Any
from typing import List
from typing import Optional
from typing import TYPE_CHECKING
from typing import Union

import attr
from attr.converters import optional as optional_c

from dis_snek.models.enums import ChannelTypes
from dis_snek.models.snowflake import Snowflake
from dis_snek.models.snowflake import Snowflake_Type
from dis_snek.models.snowflake import to_snowflake
from dis_snek.models.timestamp import Timestamp
from dis_snek.utils.attr_utils import DictSerializationMixin

if TYPE_CHECKING:
    from dis_snek.client import Snake
    from dis_snek.models.discord_objects.message import Message


@attr.s(slots=True, kw_only=True)
class BaseChannel(Snowflake, DictSerializationMixin):
    _client: Any = attr.ib(repr=False)

    _type: ChannelTypes = attr.ib(converter=ChannelTypes)
    name: Optional[str] = attr.ib(default=None)

    @classmethod
    def from_dict(cls, data, client):
        """
        Creates a channel object of the appropriate type
        :param data:
        :param client:
        :return:
        """
        type_mapping = {
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
            ChannelTypes.GROUP_DM: DM,
        }
        channel_type = ChannelTypes(data["type"])

        return type_mapping[channel_type].from_dict_typed(data, client)

    @classmethod
    def from_dict_typed(cls, data, client):
        return cls(client=client, **cls._filter_kwargs(data, cls._get_init_keys()))


class _GuildMixin:
    guild_id: Optional[Snowflake_Type] = attr.ib(default=None)
    position: Optional[int] = attr.ib(default=0)
    nsfw: bool = attr.ib(default=False)
    parent_id: Optional[Snowflake_Type] = attr.ib(default=None)
    permission_overwrites: list[dict] = attr.ib(factory=list)  # todo  permissions obj
    permissions: Optional[str] = attr.ib(default=None)  # only in slash


@attr.s(slots=True, kw_only=True)
class TextChannel(BaseChannel):
    rate_limit_per_user: int = attr.ib(default=0)
    last_message_id: Optional[Snowflake_Type] = attr.ib(default=None)
    default_auto_archive_duration: int = attr.ib(default=60)
    last_pin_timestamp: Optional[Timestamp] = attr.ib(default=None, converter=optional_c(Timestamp.fromisoformat))

    async def fetch_message(self, message_id: Snowflake_Type) -> "Message":
        message_id = to_snowflake(message_id)
        message: "Message" = await self._client.cache.get_message(self.id, message_id)
        return message


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
class DM(TextChannel):
    owner_id: Snowflake_Type = attr.ib()
    application_id: Optional[Snowflake_Type] = attr.ib(default=None)
    recipients: List[dict] = attr.ib(factory=list)


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
    def from_dict_typed(cls, data, client):
        thread_metadata: dict = data.get("thread_metadata", {})
        data.update(thread_metadata)
        return cls(client=client, **cls._filter_kwargs(data, cls._get_init_keys()))

    @property
    def private(self):
        return self._type == ChannelTypes.GUILD_PRIVATE_THREAD


TYPE_ALL_CHANNEL = Union[
    BaseChannel,
    GuildCategory,
    GuildStore,
    TextChannel,
    VoiceChannel,
    DM,
    GuildText,
    Thread,
    GuildNews,
    GuildVoice,
    GuildStageVoice,
]

TYPE_GUILD_CHANNEL = Union[GuildCategory, GuildStore, GuildNews, GuildText, GuildVoice, GuildStageVoice]
