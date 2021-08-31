from pathlib import Path
from dis_snek.models.discord_objects.message import AllowedMentions, MessageReference, Message, process_message_payload
from dis_snek.models.discord_objects.sticker import Sticker
from dis_snek.models.discord_objects.components import BaseComponent
from dis_snek.models.discord_objects.embed import Embed
from typing import (
    TYPE_CHECKING,
    AsyncIterator,
    Awaitable,
    Dict,
    List,
    Optional,
    Union,
    Any,
)

import attr
from attr.converters import optional as optional_c

from dis_snek.models.enums import ChannelTypes, MessageFlags, OverwriteTypes, Permissions
from dis_snek.models.snowflake import Snowflake_Type, to_snowflake
from dis_snek.models.timestamp import Timestamp
from dis_snek.models.base_object import DiscordObject, SnowflakeObject
from dis_snek.utils.cache import CacheProxy, CacheView
from dis_snek.utils.attr_utils import define, field

if TYPE_CHECKING:
    from dis_snek.client import Snake
    from dis_snek.models.discord_objects.user import User


@define()
class BaseChannel(DiscordObject):
    _type: ChannelTypes = field(converter=ChannelTypes)
    name: Optional[str] = field(default=None)

    @classmethod
    def from_dict_factory(cls, data, client) -> "TYPE_ALL_CHANNEL":
        """
        Creates a channel object of the appropriate type

        :param data:
        :param client:

        :return:
        """
        channel_type = ChannelTypes(data["type"])
        return TYPE_MAPPING[channel_type].from_dict(data, client)


@define()
class PermissionOverwrite(SnowflakeObject):
    type: "OverwriteTypes" = field(repr=True, converter=OverwriteTypes)
    allow: "Permissions" = field(repr=True, converter=Permissions)
    deny: "Permissions" = field(repr=True, converter=Permissions)


@define(slots=False)  # can we make some workaround?
class _GuildMixin:
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

    async def send(
        self,
        content: Optional[str] = None,
        embeds: Optional[Union[List[Union[Embed, dict]], Union[Embed, dict]]] = None,
        components: Optional[
            Union[List[List[Union[BaseComponent, dict]]], List[Union[BaseComponent, dict]], BaseComponent, dict]
        ] = None,
        stickers: Optional[Union[List[Union[Sticker, Snowflake_Type]], Sticker, Snowflake_Type]] = None,
        allowed_mentions: Optional[Union[AllowedMentions, dict]] = None,
        reply_to: Optional[Union[MessageReference, Message, dict, Snowflake_Type]] = None,
        filepath: Optional[Union[str, Path]] = None,
        tts: bool = False,
        flags: Optional[Union[int, MessageFlags]] = None,
    ):
        """
        Send a message.

        :param content: Message text content.
        :param embeds: Embedded rich content (up to 6000 characters).
        :param components: The components to include with the message.
        :param stickers: IDs of up to 3 stickers in the server to send in the message.
        :param allowed_mentions: Allowed mentions for the message.
        :param reply_to: Message to reference, must be from the same channel.
        :param filepath: Location of file to send, defaults to None.
        :param tts: Should this message use Text To Speech.

        :return: New message object that was sent.
        """
        message_payload = process_message_payload(
            content=content,
            embeds=embeds,
            components=components,
            stickers=stickers,
            allowed_mentions=allowed_mentions,
            reply_to=reply_to,
            filepath=filepath,
            tts=tts,
            flags=flags,
        )

        message_data = await self._client.http.create_message(message_payload, self.id)
        if message_data:
            return await self._client.cache.place_message_data(message_data)


@attr.s(slots=True, kw_only=True)
class VoiceChannel(BaseChannel):
    bitrate: int = attr.ib()
    user_limit: int = attr.ib()
    rtc_region: str = attr.ib(default="auto")
    video_quality_mode: int = attr.ib(default=1)  # todo convert to enum


@attr.s(slots=True, kw_only=True)
class GuildVoice(_GuildMixin, VoiceChannel):
    pass


@attr.s(slots=True, kw_only=True)
class GuildStageVoice(GuildVoice):
    pass


@attr.s(slots=True, kw_only=True)
class DMGroup(TextChannel):
    owner_id: Snowflake_Type = attr.ib(default=None)
    application_id: Optional[Snowflake_Type] = attr.ib(default=None)
    _recipients_ids: List[Snowflake_Type] = attr.ib(factory=list)

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
    def recipients(self) -> Union[CacheView, Awaitable[Dict[Snowflake_Type, "User"]], AsyncIterator["User"]]:
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
class GuildText(_GuildMixin, TextChannel):
    topic: Optional[str] = attr.ib(default=None)


@attr.s(slots=True, kw_only=True)
class GuildNews(GuildText):
    pass


@attr.s(slots=True, kw_only=True)
class GuildCategory(GuildText):
    pass  # todo forbid send() and getting messages. Anti-send-mixin?


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
