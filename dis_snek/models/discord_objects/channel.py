from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

import attr
from attr.converters import optional as optional_c

from dis_snek.const import MISSING
from dis_snek.mixins.send import SendMixin
from dis_snek.models.discord import DiscordObject
from dis_snek.models.discord_objects.invite import Invite, InviteTargetTypes
from dis_snek.models.discord_objects.thread import ThreadMember, ThreadList
from dis_snek.models.enums import ChannelTypes, OverwriteTypes, Permissions, VideoQualityModes, AutoArchiveDuration
from dis_snek.models.snowflake import SnowflakeObject, to_snowflake
from dis_snek.models.timestamp import Timestamp
from dis_snek.utils.attr_utils import define, field
from dis_snek.utils.converters import timestamp_converter
from dis_snek.utils.serializer import to_image_data

if TYPE_CHECKING:
    from io import IOBase
    from pathlib import Path

    from aiohttp import FormData

    from dis_snek.client import Snake
    from dis_snek.models.discord_objects.application import Application
    from dis_snek.models.discord_objects.guild import Guild
    from dis_snek.models.discord_objects.role import Role
    from dis_snek.models.discord_objects.message import Message
    from dis_snek.models.discord_objects.user import User, Member
    from dis_snek.models.snowflake import Snowflake_Type


@define()
class PermissionOverwrite(SnowflakeObject):
    type: "OverwriteTypes" = field(repr=True, converter=OverwriteTypes)
    allow: "Permissions" = field(repr=True, converter=Permissions)
    deny: "Permissions" = field(repr=True, converter=Permissions)


@define(slots=False)
class MessageableChannelMixin(SendMixin):
    last_message_id: Optional["Snowflake_Type"] = attr.ib(
        default=None
    )  # TODO May need to think of dynamically updating this.
    default_auto_archive_duration: int = attr.ib(default=AutoArchiveDuration.ONE_DAY)
    last_pin_timestamp: Optional[Timestamp] = attr.ib(default=None, converter=optional_c(timestamp_converter))

    async def _send_http_request(self, message_payload: Union[dict, "FormData"]) -> dict:
        return await self._client.http.create_message(message_payload, self.id)

    async def get_message(self, message_id: "Snowflake_Type") -> "Message":
        """
        Fetch a message from the channel.

        parameters:
            message_id: ID of message to retrieve.

        returns:
            The message object fetched.
        """
        message_id = to_snowflake(message_id)
        message: "Message" = await self._client.cache.get_message(self.id, message_id)
        return message

    async def get_messages(
        self,
        limit: int = 50,
        around: "Snowflake_Type" = MISSING,
        before: "Snowflake_Type" = MISSING,
        after: "Snowflake_Type" = MISSING,
    ) -> Optional[List["Message"]]:
        """
        Fetch multiple messages from the channel.

        parameters:
            limit: Max number of messages to return, default `50`, max `100`
            around: Message to get messages around
            before: Message to get messages before
            after: Message to get messages after

        returns:
            A list of messages fetched.
        """
        if limit > 100:
            raise ValueError("You cannot fetch more than 100 messages at once.")

        if around:
            around = to_snowflake(around)
        elif before:
            before = to_snowflake(before)
        elif after:
            after = to_snowflake(after)

        messages_data = await self._client.http.get_channel_messages(self.id, limit, around, before, after)
        messages = []
        for message_data in messages_data:
            messages.append(self._client.cache.place_message_data(message_data))
        return messages

    async def get_pinned_messages(self):
        """
        Fetch pinned messages from the channel.

        returns:
            A list of messages fetched.
        """
        messages_data = await self._client.http.get_pinned_messages(self.id)
        messages = []
        for message_data in messages_data:
            messages.append(self._client.cache.place_message_data(message_data))
        return messages

    async def delete_messages(self, messages: List[Union["Snowflake_Type", "Message"]], reason: Optional[str] = MISSING) -> None:
        """
        Bulk delete messages from channel.

        parameters:
            messages: List of messages or message IDs to delete.
            reason: The reason for this action. Used for audit logs.
        """
        message_ids = [to_snowflake(message) for message in messages]
        # TODO Add check for min/max and duplicates.
        await self._client.http.bulk_delete_messages(self.id, message_ids, reason)

    async def trigger_typing(self):
        raise NotImplementedError


@define(slots=False)
class InvitableMixin:
    async def create_invite(
        self,
        max_age: int = 86400,
        max_uses: int = 0,
        temporary: bool = False,
        unique: bool = False,
        target_type: Optional["InviteTargetTypes"] = None,
        target_user: Optional[Union["Snowflake_Type", "User"]] = None,
        target_application: Optional[Union["Snowflake_Type", "Application"]] = None,
        reason: Optional[str] = None,
    ) -> "Invite":
        """
        Create channel invite.

        parameters:
            max_age: Max age of invite in seconds, default 86400 (24 hours).
            max_uses: Max uses of invite, default 0.
            temporary: Grants temporary membership, default False.
            unique: Invite is unique, default false.
            target_type: Target type for streams and embedded applications.
            target_user_id: Target User ID for Stream target type.
            target_application_id: Target Application ID for Embedded App target type.
            reason: The reason for creating this invite.

        returns:
            Newly created Invite object.
        """
        if target_type:
            if target_type == InviteTargetTypes.STREAM and not target_user:
                raise ValueError("Stream target must include target user id.")
            elif target_type == InviteTargetTypes.EMBEDDED_APPLICATION and not target_application:
                raise ValueError("Embedded Application target must include target application id.")

        if target_user and target_application:
            raise ValueError("Invite target must be either User or Embedded Application, not both.")
        elif target_user:
            target_user = to_snowflake(target_user)
            target_type = InviteTargetTypes.STREAM
        elif target_application:
            target_application = to_snowflake(target_application)
            target_type = InviteTargetTypes.EMBEDDED_APPLICATION

        invite_data = await self._client.http.create_channel_invite(
            self.id, max_age, max_uses, temporary, unique, target_type, target_user, target_application, reason
        )
        return Invite.from_dict(invite_data, self._client)

    def get_invites(self):
        """
        Gets all invites (with invite metadata) for the channel.
        """
        raise NotImplementedError


@define(slots=False)
class BaseChannel(DiscordObject):
    _type: ChannelTypes = field(converter=ChannelTypes)
    name: Optional[str] = field(default=None)

    @classmethod
    def from_dict_factory(cls, data: dict, client: "Snake") -> "TYPE_ALL_CHANNEL":
        """
        Creates a channel object of the appropriate type

        parameters:
            data: The channel data.
            client: The bot.

        returns:
            The new channel object.
        """
        channel_type = data.get("type", None)
        channel_class = TYPE_CHANNEL_MAPPING.get(channel_type, None)
        if not channel_class:
            raise TypeError(f"Unsupported channel type for {data} ({channel_type}), please consult the docs.")

        return channel_class.from_dict(data, client)

    async def delete(self, reason: Optional[str] = MISSING):
        """
        Delete this channel.

        parameters:
            reason: The reason for deleting this channel
        """
        await self._client.http.delete_channel(self.id, reason)


################################################################
# DMs


@define()
class DMChannel(BaseChannel, MessageableChannelMixin):
    @classmethod
    def _process_dict(cls, data: Dict[str, Any], client: "Snake") -> Dict[str, Any]:
        data = super()._process_dict(data, client)
        data["recipients"] = [client.cache.place_user_data(recipient) for recipient in data["recipients"]]
        return data

    async def edit(
        self,
        name: Optional[str] = MISSING,
        icon: Optional[Union[str, "Path", "IOBase"]] = MISSING,
        reason: Optional[str] = MISSING,
    ):
        payload = dict(name=name, icon=to_image_data(icon))
        channel_data = self._client.http.modify_channel(self.id, payload, reason)
        self.update_from_dict(channel_data)


@define()
class DM(DMChannel):
    recipient: "User" = field()

    @classmethod
    def _process_dict(cls, data: Dict[str, Any], client: "Snake") -> Dict[str, Any]:
        data = super()._process_dict(data, client)
        data["recipient"] = data.pop("recipients")[0]
        client.cache.place_dm_channel_id(data["recipient"], data["id"])
        return data


@define()
class DMGroup(DMChannel):
    owner_id: "Snowflake_Type" = attr.ib()
    application_id: Optional["Snowflake_Type"] = attr.ib(default=None)
    recipients: List["User"] = field(factory=list)

    async def get_owner(self) -> "User":
        return await self._client.cache.get_user(self.owner_id)

    async def add_recipient(self, user: Union["User", "Snowflake_Type"], access_token: str, nickname: Optional[str] = MISSING):
        user = await self._client.cache.get_user(user)
        await self._client.http.group_dm_add_recipient(self.id, user.id, access_token, nickname)
        self.recipients.append(user)

    async def remove_recipient(self, user: Union["User", "Snowflake_Type"]):
        user = await self._client.cache.get_user(user)
        await self._client.http.group_dm_remove_recipient(self.id, user.id)
        self.recipients.remove(user)


################################################################
# Guild


@define()
class GuildChannel(BaseChannel):
    position: Optional[int] = attr.ib(default=0)
    nsfw: bool = attr.ib(default=False)
    parent_id: Optional["Snowflake_Type"] = attr.ib(default=None, converter=optional_c(to_snowflake))
    guild: "Guild" = attr.ib(default=None)

    _guild_id: Optional["Snowflake_Type"] = attr.ib(default=None, converter=optional_c(to_snowflake))
    _permission_overwrites: Dict["Snowflake_Type", "PermissionOverwrite"] = attr.ib(factory=list)

    @classmethod
    def _process_dict(cls, data: Dict[str, Any], client: "Snake") -> Dict[str, Any]:
        permission_overwrites = data.get("permission_overwrites", [])
        data["permission_overwrites"] = {
            obj.id: obj for obj in (PermissionOverwrite(**permission) for permission in permission_overwrites)
        }
        return data

    async def edit_permission(self, overwrite: PermissionOverwrite, reason: Optional[str] = None) -> None:
        await self._client.http.edit_channel_permission(
            self.id, overwrite.id, overwrite.allow, overwrite.deny, overwrite.type, reason  # TODO Convert to str...?
        )

    async def delete_permission(self, target: Union["PermissionOverwrite", "Role", "User"]):
        raise NotImplementedError


@define()
class GuildCategory(GuildChannel):
    async def edit(self, name, position, permission_overwrites):
        raise NotImplementedError


@define()
class GuildStore(GuildChannel):
    async def edit(self, name, position, permission_overwrites, parent_id, nsfw):
        raise NotImplementedError


@define()
class GuildText(GuildChannel, MessageableChannelMixin, InvitableMixin):
    topic: Optional[str] = attr.ib(default=None)
    rate_limit_per_user: int = attr.ib(default=0)

    async def edit(
        self,
        name,
        position,
        permission_overwrites,
        parent_id,
        nsfw,
        topic,
        channel_type,
        default_auto_archive_duration,
        rate_limit_per_user,
    ):
        raise NotImplementedError

    async def create_thread_with_message(
        self,
        name: str,
        message: Union["Snowflake_Type", "Message"],
        auto_archive_duration: Union[AutoArchiveDuration, int] = AutoArchiveDuration.ONE_DAY,
        reason: Optional[str] = None,
    ) -> Union["GuildNewsThread", "GuildPublicThread"]:
        thread_data = await self._client.http.create_thread(
            channel_id=self.id,
            name=name,
            auto_archive_duration=auto_archive_duration,
            message_id=to_snowflake(message),
            reason=reason,
        )
        return self._client.cache.place_channel_data(thread_data)

    async def create_thread_without_message(
        self,
        name: str,
        thread_type: Union[ChannelTypes, int],
        invitable: Optional[bool] = None,
        auto_archive_duration: Union[AutoArchiveDuration, int] = AutoArchiveDuration.ONE_DAY,
        reason: Optional[str] = None,
    ) -> Union["GuildPrivateThread", "GuildPublicThread"]:
        thread_data = await self._client.http.create_thread(
            channel_id=self.id,
            name=name,
            thread_type=thread_type,
            auto_archive_duration=auto_archive_duration,
            invitable=invitable,
            reason=reason,
        )
        return self._client.cache.place_channel_data(thread_data)

    async def get_public_archived_threads(self, limit: int = None, before: Union["Timestamp"] = None) -> ThreadList:
        threads_data = await self._client.http.list_public_archived_threads(
            channel_id=self.id, limit=limit, before=before
        )
        threads_data["id"] = self.id
        return ThreadList.from_dict(threads_data, self._client)

    async def get_private_archived_threads(self, limit: int = None, before: Union["Timestamp"] = None) -> ThreadList:
        threads_data = await self._client.http.list_private_archived_threads(
            channel_id=self.id, limit=limit, before=before
        )
        threads_data["id"] = self.id
        return ThreadList.from_dict(threads_data, self._client)

    async def get_joined_private_archived_threads(
        self, limit: int = None, before: Union["Timestamp"] = None
    ) -> ThreadList:
        threads_data = await self._client.http.list_joined_private_archived_threads(
            channel_id=self.id, limit=limit, before=before
        )
        threads_data["id"] = self.id
        return ThreadList.from_dict(threads_data, self._client)


@define()
class GuildNews(GuildText):
    rate_limit_per_user: int = attr.ib(
        default=0, init=False, on_setattr=attr.setters.frozen
    )  # TODO Not sure overriding like this is the best way to "disable" a property.

    async def edit(
        self,
        name,
        position,
        permission_overwrites,
        parent_id,
        nsfw,
        topic,
        channel_type,
        default_auto_archive_duration,
    ):
        raise NotImplementedError


################################################################
# Guild Threads


@define()
class ThreadChannel(GuildChannel, MessageableChannelMixin):
    owner_id: "Snowflake_Type" = attr.ib(default=None)
    topic: Optional[str] = attr.ib(default=None)
    message_count: int = attr.ib(default=0)
    member_count: int = attr.ib(default=0)
    archived: bool = attr.ib(default=False)
    auto_archive_duration: int = attr.ib(
        default=attr.Factory(lambda self: self.default_auto_archive_duration, takes_self=True)
    )
    locked: bool = attr.ib(default=False)
    archive_timestamp: Optional[Timestamp] = attr.ib(default=None, converter=optional_c(timestamp_converter))

    @classmethod
    def _process_dict(cls, data: Dict[str, Any], client: "Snake") -> Dict[str, Any]:
        data = super()._process_dict(data, client)
        thread_metadata: dict = data.get("thread_metadata", {})
        data.update(thread_metadata)
        return data

    @property
    def is_private(self) -> bool:
        return self._type == ChannelTypes.GUILD_PRIVATE_THREAD

    async def edit(self, name, archived, auto_archive_duration, locked, rate_limit_per_user):
        raise NotImplementedError

    async def get_members(self) -> List["ThreadMember"]:
        members_data = await self._client.http.list_thread_members(self.id)
        members = []
        for member_data in members_data:
            members.append(ThreadMember.from_dict(member_data, self._client))
        return members

    async def add_member(self, member: Union["Member", "Snowflake_Type"]) -> None:
        await self._client.http.add_thread_member(self.id, to_snowflake(member))

    async def remove_member(self, member: Union["Member", "Snowflake_Type"]) -> None:
        await self._client.http.remove_thread_member(self.id, to_snowflake(member))

    async def join(self):
        raise NotImplementedError

    async def leave(self):
        raise NotImplementedError


@define()
class GuildNewsThread(ThreadChannel):
    pass


@define()
class GuildPublicThread(ThreadChannel):
    pass


@define()
class GuildPrivateThread(ThreadChannel):
    invitable: bool = field(default=False)

    async def edit(self, name, archived, auto_archive_duration, locked, rate_limit_per_user, invitable):
        raise NotImplementedError


################################################################
# Guild Voices


@define()
class VoiceChannel(GuildChannel):  # TODO May not be needed, can be directly just GuildVoice.
    bitrate: int = attr.ib()
    user_limit: int = attr.ib()
    rtc_region: str = attr.ib(default="auto")
    video_quality_mode: Union[VideoQualityModes, int] = attr.ib(default=VideoQualityModes.AUTO)

    async def edit(
        self,
        name,
        position,
        permission_overwrites,
        parent_id,
        bitrate,
        user_limit,
        rtc_region,
        video_quality_mode,
    ):
        raise NotImplementedError


@define()
class GuildVoice(VoiceChannel, InvitableMixin):
    pass


@define()
class GuildStageVoice(GuildVoice):
    pass


TYPE_ALL_CHANNEL = Union[
    GuildText,
    GuildNews,
    GuildVoice,
    GuildStageVoice,
    GuildCategory,
    GuildStore,
    GuildPublicThread,
    GuildPrivateThread,
    GuildNewsThread,
    DMChannel,
    DMGroup,
]


TYPE_DM_CHANNEL = Union[DM, DMGroup]


TYPE_GUILD_CHANNEL = Union[GuildCategory, GuildStore, GuildNews, GuildText, GuildVoice, GuildStageVoice]


TYPE_THREAD_CHANNEL = Union[GuildNewsThread, GuildPublicThread, GuildPrivateThread]


TYPE_VOICE_CHANNEL = Union[GuildVoice, GuildStageVoice]


TYPE_MESSAGEABLE_CHANNEL = Union[DM, DMGroup, GuildNews, GuildText, ThreadChannel]


TYPE_CHANNEL_MAPPING = {
    ChannelTypes.GUILD_TEXT: GuildText,
    ChannelTypes.GUILD_NEWS: GuildNews,
    ChannelTypes.GUILD_VOICE: GuildVoice,
    ChannelTypes.GUILD_STAGE_VOICE: GuildStageVoice,
    ChannelTypes.GUILD_CATEGORY: GuildCategory,
    ChannelTypes.GUILD_STORE: GuildStore,
    ChannelTypes.GUILD_PUBLIC_THREAD: GuildPublicThread,
    ChannelTypes.GUILD_PRIVATE_THREAD: GuildPrivateThread,
    ChannelTypes.GUILD_NEWS_THREAD: GuildNewsThread,
    ChannelTypes.DM: DM,
    ChannelTypes.GROUP_DM: DMGroup,
}
