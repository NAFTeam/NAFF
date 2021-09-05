from functools import partial
from typing import TYPE_CHECKING, Any, AsyncIterator, Awaitable, Dict, List, Optional, Union

import attr
from attr.converters import optional as optional_c

from dis_snek.errors import SnakeException
from dis_snek.mixins.send import SendMixin
from dis_snek.models.discord import DiscordObject
from dis_snek.models.enums import (
    ChannelTypes,
    InviteTarget,
    OverwriteTypes,
    Permissions,
    VideoQualityModes,
)
from dis_snek.models.snowflake import SnowflakeObject, to_snowflake
from dis_snek.models.timestamp import Timestamp
from dis_snek.utils.attr_utils import define, field
from dis_snek.utils.proxy import CacheView, CacheProxy, AsyncPartial
from dis_snek.utils.converters import timestamp_converter

if TYPE_CHECKING:
    from aiohttp import FormData

    from dis_snek.client import Snake
    from dis_snek.models.discord_objects.guild import Guild
    from dis_snek.models.discord_objects.invite import Invite, InviteMetadata
    from dis_snek.models.discord_objects.member import Member
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

    async def delete(self, reason: str = None) -> None:
        """
        Delete channel.

        :param reason: Audit log reason
        """
        await self._client.http.delete_channel(self.id, reason=reason)


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

    @property
    def guild(self) -> Union[CacheProxy, Awaitable["Guild"], "Guild"]:
        """Channel guild."""
        return CacheProxy(id=self.guild_id, method=self._client.cache.get_guild)

    async def set_permissions(self, overwrite: PermissionOverwrite, reason: Optional[str] = None) -> None:
        return await self._client.edit_channel_permissions(self.id, overwrite, reason)

    async def get_channel_invites(self) -> List["Invite"]:
        pass

    async def create_invite(
        self,
        max_age: int = 86400,
        max_uses: int = 0,
        temporary: bool = False,
        unique: bool = False,
        target_type: Optional[InviteTarget] = None,
        target_user_id: Optional["Snowflake_Type"] = None,
        target_application_id: Optional["Snowflake_Type"] = None,
        reason: Optional[str] = None,
    ) -> "Invite":
        """
        Create channel invite.

        :param max_age: Max age of invite in seconds, default 86400 (24 hours)
        :param max_uses: Max uses of invite, default 0
        :param temporary: Grants temporary membership, default False
        :param unique: Invite is unique, default false
        :param target_type: Target type for streams and embedded applications
        :param target_user_id: Target User ID for Stream target type
        :param target_application_id: Target Application ID for Embedded App target type
        """
        if target_type:
            if target_type == InviteTarget.STREAM and not target_user_id:
                raise ValueError("Stream target must include target user ID")
            elif target_type == InviteTarget.EMBEDDED_APPLICATION and not target_application_id:
                raise ValueError("Embedded Application target must include target application ID")
        elif target_user_id and target_application_id:
            raise ValueError("Invite target must be either User or Embedded Application, not both")
        elif target_user_id:
            target_user_id = to_snowflake(target_user_id)
            target_type = InviteTarget.STREAM
        elif target_application_id:
            target_application_id = to_snowflake(target_application_id)
            target_type = InviteTarget.EMBEDDED_APPLICATION

        return await self._client.create_channel_invite(
            self.id, max_age, max_uses, temporary, unique, target_type, target_user_id, target_application_id, reason
        )


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
        """
        Fetch a message from the channel.

        :param message_id: ID of message to retrieve
        """
        message_id = to_snowflake(message_id)
        message: "Message" = await self._client.cache.get_message(self.id, message_id)
        return message

    async def fetch_messages(
        self,
        limit: int = 50,
        around: "Snowflake_Type" = None,
        before: "Snowflake_Type" = None,
        after: "Snowflake_Type" = None,
    ) -> Optional[List["Message"]]:
        """
        Fetch messages from a channel

        :param limit: Max number of messages to return, default `50`, max `100`
        :param around: Message to get messages around
        :param before: Message to get messages before
        :param after: Message to get messages after
        """
        if around:
            around = to_snowflake(around)
        elif before:
            before = to_snowflake(before)
        elif after:
            after = to_snowflake(after)
        return await self._client.get_channel_messages(self.id, limit, around, before, after)

    async def bulk_delete(self, messages: List[Union["Snowflake_Type", "Message"]], reason: str = None) -> None:
        """
        Bulk delete messages from channel.

        :param messages: List of messages or message IDs to delete
        """
        for message in messages:
            if isinstance(message, "Message"):
                message = message.id

        return await self._client.bulk_delete(self.id, messages, reason)

    @property
    def pins(self) -> Union[CacheView, Awaitable[List["Message"]], AsyncIterator["Message"]]:
        """Channel pins."""
        ids = AsyncPartial(self._client.http.get_pinned_messages, self.id)
        return CacheView(ids=ids, method=partial(self._client.cache.get_message, self.id))


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

    # TODO: List public/private archived threads

    async def create_thread(
        self,
        name: str,
        auto_archive_duration: int = 60,
        thread_type: ChannelTypes = ChannelTypes.GUILD_PUBLIC_THREAD,
        message: Union["Message", "Snowflake_Type"] = None,
        reason: str = None,
    ) -> "Thread":
        """
        Create a thread.

        :param name: Name of thread
        :param auto_archive_duration: Auto archive duration in seconds, one of: 60, 1440, 4320, 10080
        :param thread_type: Thread type (Public/Private)
        :param message_id
        """
        if not 1 <= len(name) <= 100:
            raise ValueError("Length of thread name must be 1-100 characters")
        if auto_archive_duration not in [60, 1440, 4320, 10080]:
            raise ValueError("Auto archive duration must be one of: 60, 1400, 4320, 10080")
        if thread_type not in [ChannelTypes.GUILD_PUBLIC_THREAD, ChannelTypes.GUILD_PRIVATE_THREAD]:
            raise ValueError("Invalid thread type. Must be one of: GUILD_PUBLIC_THREAD, GUILD_PRIVATE_THREAD")
        if message:
            if isinstance(message, "Message"):
                message = message.id
            message_id = to_snowflake(message)
        return await self._client.http.create_thread(
            self.id,
            name=name,
            auto_archive_duration=auto_archive_duration,
            thread_type=thread_type,
            message_id=message_id,
            reason=reason,
        )


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

    @property
    def members(self) -> Union[CacheView, Awaitable[List["Member"]], List["Member"]]:
        """Thread members."""
        ids = AsyncPartial(self._client.http.list_thread_members, self.id)
        return CacheView(ids=ids, method=partial(self._client.cache.get_member, self.guild_id))

    async def add_member(self, user: Union["User", "Snowflake_Type"]) -> None:
        """
        Add a member to a thread.

        :param member: Member to add
        """
        if isinstance(user, "User"):
            user = user.id
        user = to_snowflake(user)
        return await self._client.http.add_thread_member(self.id, user)

    async def remove_member(self, user: Union["User", "Snowflake_Type"]) -> None:
        """
        Remove a member from a thread.

        :param member: Member to remove
        """
        if isinstance(user, "User"):
            user = user.id
        user = to_snowflake(user)
        return await self._client.http.remove_thread_member(self.id, user)


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
