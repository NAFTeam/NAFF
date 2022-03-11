import time
from collections import namedtuple
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union, Callable

import attrs

import dis_snek.models as models
from dis_snek.client.const import MISSING, DISCORD_EPOCH, Absent
from dis_snek.client.errors import NotFound
from dis_snek.client.mixins.send import SendMixin
from dis_snek.client.mixins.serialization import DictSerializationMixin
from dis_snek.client.utils.attr_utils import define, field
from dis_snek.client.utils.converters import optional as optional_c
from dis_snek.client.utils.converters import timestamp_converter
from dis_snek.client.utils.misc_utils import get
from dis_snek.client.utils.serializer import to_dict, to_image_data
from dis_snek.models.discord.base import DiscordObject
from dis_snek.models.discord.file import UPLOADABLE_TYPE
from dis_snek.models.discord.snowflake import Snowflake_Type, to_snowflake, to_optional_snowflake, SnowflakeObject
from dis_snek.models.snek import AsyncIterator
from .enums import (
    ChannelTypes,
    OverwriteTypes,
    Permissions,
    VideoQualityModes,
    AutoArchiveDuration,
    StagePrivacyLevel,
    MessageFlags,
    InviteTargetTypes,
)

if TYPE_CHECKING:
    from aiohttp import FormData
    from dis_snek import Snake
    from dis_snek.models.snek.VoiceState import ActiveVoiceState

__all__ = [
    "ChannelHistory",
    "PermissionOverwrite",
    "MessageableMixin",
    "InvitableMixin",
    "ThreadableMixin",
    "WebhookMixin",
    "BaseChannel",
    "DMChannel",
    "DM",
    "DMGroup",
    "GuildChannel",
    "GuildCategory",
    "GuildStore",
    "GuildNews",
    "GuildText",
    "ThreadChannel",
    "GuildNewsThread",
    "GuildPublicThread",
    "GuildPrivateThread",
    "GuildVoice",
    "GuildStageVoice",
    "process_permission_overwrites",
    "TYPE_ALL_CHANNEL",
    "TYPE_DM_CHANNEL",
    "TYPE_GUILD_CHANNEL",
    "TYPE_THREAD_CHANNEL",
    "TYPE_VOICE_CHANNEL",
    "TYPE_CHANNEL_MAPPING",
    "TYPE_MESSAGEABLE_CHANNEL",
]


class ChannelHistory(AsyncIterator):
    """
    An async iterator for searching through a channel's history.

    Attributes:
        channel: The channel to search through
        limit: The maximum number of messages to return (set to 0 for no limit)
        before: get messages before this message ID
        after: get messages after this message ID
        around: get messages "around" this message ID

    """

    def __init__(self, channel: "BaseChannel", limit=50, before=None, after=None, around=None) -> None:
        self.channel: "BaseChannel" = channel
        self.before: Snowflake_Type = before
        self.after: Snowflake_Type = after
        self.around: Snowflake_Type = around
        super().__init__(limit)

    async def fetch(self) -> List["models.Message"]:
        """
        Fetch additional objects.

        Your implementation of this method *must* return a list of objects.
        If no more objects are available, raise QueueEmpty

        Returns:
            List of objects

        Raises:
              QueueEmpty when no more objects are available.

        """
        if self.after:
            if not self.last:
                self.last = namedtuple("temp", "id")
                self.last.id = self.after
            messages = await self.channel.fetch_messages(limit=self.get_limit, after=self.last.id)
            messages.sort(key=lambda x: x.id)

        elif self.around:
            messages = await self.channel.fetch_messages(limit=self.get_limit, around=self.around)
            # todo: decide how getting *more* messages from `around` would work
            self._limit = 1  # stops history from getting more messages

        else:
            if self.before and not self.last:
                self.last = namedtuple("temp", "id")
                self.last.id = self.before

            messages = await self.channel.fetch_messages(limit=self.get_limit, before=self.last.id)
            messages.sort(key=lambda x: x.id, reverse=True)
        return messages


@define()
class PermissionOverwrite(SnowflakeObject, DictSerializationMixin):
    """
    Channel Permissions Overwrite object.

    !!! Note
        `id` here is not an attribute of the overwrite, it is the ID of the overwritten instance

    """

    type: "OverwriteTypes" = field(repr=True, converter=OverwriteTypes)
    """Permission overwrite type (role or member)"""
    allow: Optional["Permissions"] = field(repr=True, converter=optional_c(Permissions), kw_only=True, default=None)
    """Permissions to allow"""
    deny: Optional["Permissions"] = field(repr=True, converter=optional_c(Permissions), kw_only=True, default=None)
    """Permissions to deny"""

    @classmethod
    def for_target(cls, target_type: Union["models.Role", "models.Member", "models.User"]) -> "PermissionOverwrite":
        """
        Create a PermissionOverwrite for a role or member.

        Args:
            target_type: The type of the target (role or member)

        Returns:
            PermissionOverwrite

        """
        if isinstance(target_type, models.Role):
            return cls(type=OverwriteTypes.ROLE, id=target_type.id)
        elif isinstance(target_type, (models.Member, models.User)):
            return cls(type=OverwriteTypes.MEMBER, id=target_type.id)
        else:
            raise TypeError("target_type must be a Role, Member or User")

    def add_allows(self, *perms: "Permissions") -> None:
        """
        Add permissions to allow.

        Args:
            *perms: Permissions to add

        """
        if not self.allow:
            self.allow = Permissions.NONE
        for perm in perms:
            self.allow |= perm

    def add_denies(self, *perms: "Permissions") -> None:
        """
        Add permissions to deny.

        Args:
            *perms: Permissions to add

        """
        if not self.deny:
            self.deny = Permissions.NONE
        for perm in perms:
            self.deny |= perm


@define(slots=False)
class MessageableMixin(SendMixin):
    last_message_id: Optional[Snowflake_Type] = field(
        default=None
    )  # TODO May need to think of dynamically updating this.
    """The id of the last message sent in this channel (may not point to an existing or valid message)"""
    default_auto_archive_duration: int = field(default=AutoArchiveDuration.ONE_DAY)
    """Default duration that the clients (not the API) will use for newly created threads, in minutes, to automatically archive the thread after recent activity"""
    last_pin_timestamp: Optional["models.Timestamp"] = field(default=None, converter=optional_c(timestamp_converter))
    """When the last pinned message was pinned. This may be None when a message is not pinned."""

    async def _send_http_request(self, message_payload: Union[dict, "FormData"]) -> dict:
        return await self._client.http.create_message(message_payload, self.id)

    async def fetch_message(self, message_id: Snowflake_Type) -> Optional["models.Message"]:
        """
        Fetch a message from the channel.

        Args:
            message_id: ID of message to retrieve.

        Returns:
            The message object fetched. If the message is not found, returns None.

        """
        try:
            return await self._client.cache.fetch_message(self.id, message_id)
        except NotFound:
            return None

    def get_message(self, message_id: Snowflake_Type) -> "models.Message":
        """
        Get a message from the channel.

        Args:
            message_id: ID of message to retrieve.

        Returns:
            The message object fetched.

        """
        message_id = to_snowflake(message_id)
        message: "models.Message" = self._client.cache.get_message(self.id, message_id)
        return message

    def history(
        self,
        limit=100,
        before: Snowflake_Type = None,
        after: Snowflake_Type = None,
        around: Snowflake_Type = None,
    ) -> ChannelHistory:
        """
        Get an async iterator for the history of this channel.

        Args:
            limit: The maximum number of messages to return (set to 0 for no limit)
            before: get messages before this message ID
            after: get messages after this message ID
            around: get messages "around" this message ID

        ??? Hint "Example Usage:"
            ```python
            async for message in channel.history(limit=0):
                if message.author.id == 174918559539920897:
                    print("Found author's message")
                    # ...
                    break
            ```
            or
            ```python
            history = channel.history(limit=250)
            # Flatten the async iterator into a list
            messages = await history.flatten()
            ```

        Returns:
            ChannelHistory (AsyncIterator)

        """
        return ChannelHistory(self, limit, before, after, around)

    async def fetch_messages(
        self,
        limit: int = 50,
        around: Snowflake_Type = MISSING,
        before: Snowflake_Type = MISSING,
        after: Snowflake_Type = MISSING,
    ) -> List["models.Message"]:
        """
        Fetch multiple messages from the channel.

        Args:
            limit: Max number of messages to return, default `50`, max `100`
            around: Message to get messages around
            before: Message to get messages before
            after: Message to get messages after

        Returns:
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
        for m in messages_data:
            m["guild_id"] = self._guild_id

        return [self._client.cache.place_message_data(m) for m in messages_data]

    async def fetch_pinned_messages(self) -> List["models.Message"]:
        """
        Fetch pinned messages from the channel.

        Returns:
            A list of messages fetched.

        """
        messages_data = await self._client.http.get_pinned_messages(self.id)
        return [self._client.cache.place_message_data(message_data) for message_data in messages_data]

    async def delete_messages(
        self, messages: List[Union[Snowflake_Type, "models.Message"]], reason: Absent[Optional[str]] = MISSING
    ) -> None:
        """
        Bulk delete messages from channel.

        Args:
            messages: List of messages or message IDs to delete.
            reason: The reason for this action. Used for audit logs.

        """
        message_ids = [to_snowflake(message) for message in messages]
        # TODO Add check for min/max and duplicates.

        if len(message_ids) == 1:
            # bulk delete messages will throw a http error if only 1 message is passed
            await self.delete_message(message_ids[0], reason)
        else:
            await self._client.http.bulk_delete_messages(self.id, message_ids, reason)

    async def delete_message(self, message: Union[Snowflake_Type, "models.Message"], reason: str = None) -> None:
        """
        Delete a single message from a channel.

        Args:
            message: The message to delete
            reason: The reason for this action

        """
        message = to_snowflake(message)
        await self._client.http.delete_message(self.id, message, reason=reason)

    async def purge(
        self,
        deletion_limit: int = 50,
        search_limit: int = 100,
        predicate: Callable[["models.Message"], bool] = MISSING,
        avoid_loading_msg: bool = True,
        before: Optional[Snowflake_Type] = MISSING,
        after: Optional[Snowflake_Type] = MISSING,
        around: Optional[Snowflake_Type] = MISSING,
        reason: Absent[Optional[str]] = MISSING,
    ) -> int:
        """
        Bulk delete messages within a channel. If a `predicate` is provided, it will be used to determine which messages to delete, otherwise all messages will be deleted within the `deletion_limit`.

        ??? Hint "Example Usage:"
            ```python
            # this will delete the last 20 messages sent by a user with the given ID
            deleted = await channel.purge(deletion_limit=20, predicate=lambda m: m.author.id == 174918559539920897)
            await channel.send(f"{deleted} messages deleted")
            ```

        Args:
            deletion_limit: The target amount of messages to delete
            search_limit: How many messages to search through
            predicate: A function that returns True or False, and takes a message as an argument
            avoid_loading_msg: Should the bot attempt to avoid deleting its own loading messages (recommended enabled)
            before: Search messages before this ID
            after: Search messages after this ID
            around: Search messages around this ID
            reason: The reason for this deletion

        Returns:
            The total amount of messages deleted

        """
        if not predicate:

            def predicate(m) -> bool:
                return True  # noqa

        to_delete = []

        # 1209600 14 days ago in seconds, 1420070400000 is used to convert to snowflake
        fourteen_days_ago = int((time.time() - 1209600) * 1000.0 - DISCORD_EPOCH) << 22
        async for message in self.history(limit=search_limit, before=before, after=after, around=around):
            if deletion_limit != 0 and len(to_delete) == deletion_limit:
                break

            if not predicate(message):
                # fails predicate
                continue

            if avoid_loading_msg:
                if message._author_id == self._client.user.id and MessageFlags.LOADING in message.flags:
                    continue

            if message.id < fourteen_days_ago:
                # message is too old to be purged
                continue

            to_delete.append(message.id)

        count = len(to_delete)
        while len(to_delete):
            iteration = [to_delete.pop() for i in range(min(100, len(to_delete)))]
            await self.delete_messages(iteration, reason=reason)
        return count

    async def trigger_typing(self) -> None:
        """Trigger a typing animation in this channel."""
        await self._client.http.trigger_typing_indicator(self.id)


@define(slots=False)
class InvitableMixin:
    async def create_invite(
        self,
        max_age: int = 86400,
        max_uses: int = 0,
        temporary: bool = False,
        unique: bool = False,
        target_type: Optional[InviteTargetTypes] = None,
        target_user: Optional[Union[Snowflake_Type, "models.User"]] = None,
        target_application: Optional[Union[Snowflake_Type, "models.Application"]] = None,
        reason: Optional[str] = None,
    ) -> "models.Invite":
        """
        Creates a new channel invite.

        Args:
            max_age: Max age of invite in seconds, default 86400 (24 hours).
            max_uses: Max uses of invite, default 0.
            temporary: Grants temporary membership, default False.
            unique: Invite is unique, default false.
            target_type: Target type for streams and embedded applications.
            target_user: Target User ID for Stream target type.
            target_application: Target Application ID for Embedded App target type.
            reason: The reason for creating this invite.

        Returns:
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
        return models.Invite.from_dict(invite_data, self._client)

    async def fetch_invites(self) -> List["models.Invite"]:
        """
        Fetches all invites (with invite metadata) for the channel.

        Returns:
            List of Invite objects.

        """
        invites_data = await self._client.http.get_channel_invites(self.id)
        return models.Invite.from_list(invites_data, self._client)


@define(slots=False)
class ThreadableMixin:
    async def create_thread(
        self,
        name: str,
        message: Absent[Snowflake_Type] = MISSING,
        thread_type: Absent[ChannelTypes] = MISSING,
        invitable: Absent[bool] = MISSING,
        auto_archive_duration: AutoArchiveDuration = AutoArchiveDuration.ONE_DAY,
        reason: Absent[str] = None,
    ) -> "TYPE_THREAD_CHANNEL":
        """
        Creates a nee thread in this channel. If a message is provided, it will be used as the initial message.

        Args:
            name: 1-100 character thread name
            message: The message to connect this thread to. Required for news channel.
            thread_type: Is the thread private or public. Not applicable to news channel, it always be GUILD_NEWS_THREAD.
            invitable: whether non-moderators can add other non-moderators to a thread. Only applicable when creating a private thread.
            auto_archive_duration: Time before the thread will be automatically archived. Note 3 day and 7 day archive durations require the server to be boosted.
            reason: The reason for creating this thread.

        Returns:
            The created thread, if successful

        """
        if self.type == ChannelTypes.GUILD_NEWS and not message:
            raise ValueError("News channel must include message to create thread from.")

        elif message and (thread_type or invitable):
            raise ValueError("Message cannot be used with thread_type or invitable.")

        elif thread_type != ChannelTypes.GUILD_PRIVATE_THREAD and invitable:
            raise ValueError("Invitable only applies to private threads.")

        thread_data = await self._client.http.create_thread(
            channel_id=self.id,
            name=name,
            thread_type=thread_type,
            invitable=invitable,
            auto_archive_duration=auto_archive_duration,
            message_id=to_optional_snowflake(message),
            reason=reason,
        )
        return self._client.cache.place_channel_data(thread_data)

    async def fetch_public_archived_threads(
        self, limit: int = None, before: Optional["models.Timestamp"] = None
    ) -> "models.ThreadList":
        """
        Get a `ThreadList` of archived **public** threads available in this channel.

        Args:
            limit: optional maximum number of threads to return
            before: Returns threads before this timestamp

        Returns:
            A `ThreadList` of archived threads.

        """
        threads_data = await self._client.http.list_public_archived_threads(
            channel_id=self.id, limit=limit, before=before
        )
        threads_data["id"] = self.id
        return models.ThreadList.from_dict(threads_data, self._client)

    async def fetch_private_archived_threads(
        self, limit: int = None, before: Optional["models.Timestamp"] = None
    ) -> "models.ThreadList":
        """
        Get a `ThreadList` of archived **private** threads available in this channel.

        Args:
            limit: optional maximum number of threads to return
            before: Returns threads before this timestamp

        Returns:
            A `ThreadList` of archived threads.

        """
        threads_data = await self._client.http.list_private_archived_threads(
            channel_id=self.id, limit=limit, before=before
        )
        threads_data["id"] = self.id
        return models.ThreadList.from_dict(threads_data, self._client)

    async def fetch_archived_threads(
        self, limit: int = None, before: Optional["models.Timestamp"] = None
    ) -> "models.ThreadList":
        """
        Get a `ThreadList` of archived threads available in this channel.

        Args:
            limit: optional maximum number of threads to return
            before: Returns threads before this timestamp

        Returns:
            A `ThreadList` of archived threads.

        """
        threads_data = await self._client.http.list_private_archived_threads(
            channel_id=self.id, limit=limit, before=before
        )
        threads_data.update(
            await self._client.http.list_public_archived_threads(channel_id=self.id, limit=limit, before=before)
        )
        threads_data["id"] = self.id
        return models.ThreadList.from_dict(threads_data, self._client)

    async def fetch_joined_private_archived_threads(
        self, limit: int = None, before: Optional["models.Timestamp"] = None
    ) -> "models.ThreadList":
        """
        Get a `ThreadList` of threads the bot is a participant of in this channel.

        Args:
            limit: optional maximum number of threads to return
            before: Returns threads before this timestamp

        Returns:
            A `ThreadList` of threads the bot is a participant of.

        """
        threads_data = await self._client.http.list_joined_private_archived_threads(
            channel_id=self.id, limit=limit, before=before
        )
        threads_data["id"] = self.id
        return models.ThreadList.from_dict(threads_data, self._client)

    async def fetch_active_threads(self) -> "models.ThreadList":
        """
        Gets all active threads in the channel, including public and private threads.

        Returns:
            A `ThreadList` of active threads.

        """
        threads_data = await self._client.http.list_active_threads(guild_id=self._guild_id)

        # delete the items where the channel_id does not match
        removed_thread_ids = []
        cleaned_threads_data_threads = []
        for thread in threads_data["threads"]:
            if thread["parent_id"] == str(self.id):
                cleaned_threads_data_threads.append(thread)
            else:
                removed_thread_ids.append(thread["id"])
        threads_data["threads"] = cleaned_threads_data_threads

        # delete the member data which is not needed
        cleaned_member_data_threads = []
        for thread_member in threads_data["members"]:
            if thread_member["id"] not in removed_thread_ids:
                cleaned_member_data_threads.append(thread_member)
        threads_data["members"] = cleaned_member_data_threads

        return models.ThreadList.from_dict(threads_data, self._client)

    async def fetch_all_threads(self) -> "models.ThreadList":
        """
        Gets all threads in the channel. Active and archived, including public and private threads.

        Returns:
            A `ThreadList` of all threads.

        """
        threads = await self.fetch_active_threads()

        # update that data with the archived threads
        archived_threads = await self.fetch_archived_threads()
        threads.threads.extend(archived_threads.threads)
        threads.members.extend(archived_threads.members)

        return threads


@define(slots=False)
class WebhookMixin:
    async def create_webhook(self, name: str, avatar: Absent[UPLOADABLE_TYPE] = MISSING) -> "models.Webhook":
        """
        Create a webhook in this channel.

        Args:
            name: The name of the webhook
            avatar: An optional default avatar image to use

        Returns:
            The created webhook object

        Raises:
            ValueError: If you try to name the webhook "Clyde"

        """
        return await models.Webhook.create(self._client, self, name, avatar)  # type: ignore

    async def delete_webhook(self, webhook: "models.Webhook") -> None:
        """
        Delete a given webhook in this channel.

        Args:
            webhook: The webhook to delete

        """
        return await webhook.delete()

    async def fetch_webhooks(self) -> List["models.Webhook"]:
        """
        Fetches all the webhooks for this channel.

        Returns:
            List of webhook objects

        """
        resp = await self._client.http.get_channel_webhooks(self.id)
        return [models.Webhook.from_dict(d, self._client) for d in resp]


@define(slots=False)
class BaseChannel(DiscordObject):
    name: Optional[str] = field(repr=True, default=None)
    """The name of the channel (1-100 characters)"""
    type: Union[ChannelTypes, int] = field(repr=True, converter=ChannelTypes)
    """The channel topic (0-1024 characters)"""

    @classmethod
    def from_dict_factory(cls, data: dict, client: "Snake") -> "TYPE_ALL_CHANNEL":
        """
        Creates a channel object of the appropriate type.

        Args:
            data: The channel data.
            client: The bot.

        Returns:
            The new channel object.

        """
        channel_type = data.get("type", None)
        channel_class = TYPE_CHANNEL_MAPPING.get(channel_type, None)
        if not channel_class:
            raise TypeError(f"Unsupported channel type for {data} ({channel_type}), please consult the docs.")

        return channel_class.from_dict(data, client)

    @property
    def mention(self) -> str:
        """Returns a string that would mention the channel."""
        return f"<#{self.id}>"

    async def edit(
        self,
        name: Absent[str] = MISSING,
        icon: Absent[UPLOADABLE_TYPE] = MISSING,
        type: Absent[ChannelTypes] = MISSING,
        position: Absent[int] = MISSING,
        topic: Absent[str] = MISSING,
        nsfw: Absent[bool] = MISSING,
        rate_limit_per_user: Absent[int] = MISSING,
        bitrate: Absent[int] = MISSING,
        user_limit: Absent[int] = MISSING,
        permission_overwrites: Absent[
            Union[dict, PermissionOverwrite, List[Union[dict, PermissionOverwrite]]]
        ] = MISSING,
        parent_id: Absent[Snowflake_Type] = MISSING,
        rtc_region: Absent[Union["models.VoiceRegion", str]] = MISSING,
        video_quality_mode: Absent[VideoQualityModes] = MISSING,
        default_auto_archive_duration: Absent[AutoArchiveDuration] = MISSING,
        archived: Absent[bool] = MISSING,
        auto_archive_duration: Absent[AutoArchiveDuration] = MISSING,
        locked: Absent[bool] = MISSING,
        invitable: Absent[bool] = MISSING,
        reason: Absent[str] = MISSING,
        **kwargs,
    ) -> "TYPE_ALL_CHANNEL":
        """
        Edits the channel.

        Args:
            name: 1-100 character channel name
            icon: DM Group icon
            type: The type of channel; only conversion between text and news is supported and only in guilds with the "NEWS" feature
            position: The position of the channel in the left-hand listing
            topic: 0-1024 character channel topic
            nsfw: Whether the channel is nsfw
            rate_limit_per_user: Amount of seconds a user has to wait before sending another message (0-21600)
            bitrate: The bitrate (in bits) of the voice channel; 8000 to 96000 (128000 for VIP servers)
            user_limit: The user limit of the voice channel; 0 refers to no limit, 1 to 99 refers to a user limit
            permission_overwrites: Channel or category-specific permissions
            parent_id: The id of the new parent category for a channel
            rtc_region: Channel voice region id, automatic when set to None.
            video_quality_mode: The camera video quality mode of the voice channel
            default_auto_archive_duration: The default duration that the clients use (not the API) for newly created threads in the channel, in minutes, to automatically archive the thread after recent activity
            archived: Whether the thread is archived
            auto_archive_duration: Duration in minutes to automatically archive the thread after recent activity, can be set to: 60, 1440, 4320, 10080
            locked: Whether the thread is locked; when a thread is locked, only users with MANAGE_THREADS can unarchive it
            invitable: Whether non-moderators can add other non-moderators to a thread; only available on private threads
            reason: The reason for editing the channel

        Returns:
            The edited channel. May be a new object if the channel type changes.

        """
        payload = {
            "name": name,
            "icon": to_image_data(icon),
            "type": type,
            "position": position,
            "topic": topic,
            "nsfw": nsfw,
            "rate_limit_per_user": rate_limit_per_user,
            "bitrate": bitrate,
            "user_limit": user_limit,
            "permission_overwrites": process_permission_overwrites(permission_overwrites),
            "parent_id": to_optional_snowflake(parent_id),
            "rtc_region": rtc_region.id if isinstance(rtc_region, models.VoiceRegion) else rtc_region,
            "video_quality_mode": video_quality_mode,
            "default_auto_archive_duration": default_auto_archive_duration,
            "archived": archived,
            "auto_archive_duration": auto_archive_duration,
            "locked": locked,
            "invitable": invitable,
            **kwargs,
        }
        channel_data = await self._client.http.modify_channel(self.id, payload, reason)
        return self._client.cache.place_channel_data(channel_data)

    async def delete(self, reason: Absent[Optional[str]] = MISSING) -> None:
        """
        Delete this channel.

        Args:
            reason: The reason for deleting this channel

        """
        await self._client.http.delete_channel(self.id, reason)


################################################################
# DMs


@define(slots=False)
class DMChannel(BaseChannel, MessageableMixin):
    recipients: List["models.User"] = field(factory=list)
    """The users of the DM that will receive messages sent"""

    @classmethod
    def _process_dict(cls, data: Dict[str, Any], client: "Snake") -> Dict[str, Any]:
        data = super()._process_dict(data, client)
        if recipients := data.get("recipients", None):
            data["recipients"] = [client.cache.place_user_data(recipient) for recipient in recipients]
        return data

    @property
    def members(self) -> List["models.User"]:
        """Returns a list of users that are in this DM channel."""
        return self.recipients


@define()
class DM(DMChannel):
    @property
    def recipient(self) -> "models.User":
        """Returns the user that is in this DM channel."""
        return self.recipients[0]


@define()
class DMGroup(DMChannel):
    owner_id: Snowflake_Type = field(repr=True)
    """id of the creator of the group DM"""
    application_id: Optional[Snowflake_Type] = field(default=None)
    """Application id of the group DM creator if it is bot-created"""

    async def edit(
        self,
        name: Absent[str] = MISSING,
        icon: Absent[UPLOADABLE_TYPE] = MISSING,
        reason: Absent[str] = MISSING,
        **kwargs,
    ) -> "DMGroup":
        """
        Edit this DM Channel.

        Args:
            name: 1-100 character channel name
            icon: An icon to use
            reason: The reason for this change
        """
        return await super().edit(name=name, icon=icon, reason=reason, **kwargs)

    async def fetch_owner(self) -> "models.User":
        """Fetch the owner of this DM group"""
        return await self._client.cache.fetch_user(self.owner_id)

    def get_owner(self) -> "models.User":
        """Get the owner of this DM group"""
        return self._client.cache.get_user(self.owner_id)

    async def add_recipient(
        self, user: Union["models.User", Snowflake_Type], access_token: str, nickname: Absent[Optional[str]] = MISSING
    ) -> None:
        """
        Add a recipient to this DM Group.

        Args:
            user: The user to add
            access_token: access token of a user that has granted your app the gdm.join scope
            nickname: nickname to apply to the user being added

        """
        user = await self._client.cache.fetch_user(user)
        await self._client.http.group_dm_add_recipient(self.id, user.id, access_token, nickname)
        self.recipients.append(user)

    async def remove_recipient(self, user: Union["models.User", Snowflake_Type]) -> None:
        """
        Remove a recipient from this DM Group.

        Args:
            user: The user to remove

        """
        user = await self._client.cache.fetch_user(user)
        await self._client.http.group_dm_remove_recipient(self.id, user.id)
        self.recipients.remove(user)


################################################################
# Guild


@define(slots=False)
class GuildChannel(BaseChannel):
    position: Optional[int] = field(default=0)
    """Sorting position of the channel"""
    nsfw: bool = field(default=False)
    """Whether the channel is nsfw"""
    parent_id: Optional[Snowflake_Type] = field(default=None, converter=optional_c(to_snowflake))
    """id of the parent category for a channel (each parent category can contain up to 50 channels)"""
    permission_overwrites: list[PermissionOverwrite] = field(factory=list)
    """A list of the overwritten permissions for the members and roles"""

    _guild_id: Optional[Snowflake_Type] = field(default=None, converter=optional_c(to_snowflake))

    @property
    def guild(self) -> "models.Guild":
        """The guild this channel belongs to."""
        return self._client.cache.get_guild(self._guild_id)

    @property
    def category(self) -> Optional["GuildCategory"]:
        """The parent category of this channel."""
        return self._client.cache.get_channel(self.parent_id)

    @classmethod
    def _process_dict(cls, data: Dict[str, Any], client: "Snake") -> Dict[str, Any]:
        if overwrites := data.get("permission_overwrites"):
            data["permission_overwrites"] = PermissionOverwrite.from_list(overwrites)
        return data

    def permissions_for(self, instance: Snowflake_Type) -> Permissions:
        """
        Calculates permissions for an instance

        Args:
            instance: Member or Role instance (or its ID)

        Returns:
            Permissions data

        Raises:
            ValueError: If could not find any member or role by given ID
            RuntimeError: If given instance is from another guild

        """
        if (is_member := isinstance(instance, models.Member)) or isinstance(instance, models.Role):
            if instance._guild_id != self._guild_id:
                raise RuntimeError("Unable to calculate permissions for the instance from different guild")

            if is_member:
                return instance.channel_permissions(self)

            else:
                permissions = instance.permissions

                for overwrite in self.permission_overwrites:
                    if overwrite.id == instance.id:
                        permissions &= ~overwrite.deny
                        permissions |= overwrite.allow
                        break

                return permissions

        else:
            instance = to_snowflake(instance)
            guild = self.guild
            instance = guild.get_member(instance) or guild.get_role(instance)

            if not instance:
                raise ValueError("Unable to find any member or role by given instance ID")

            return self.permissions_for(instance)

    async def add_permission(
        self,
        target: Union["PermissionOverwrite", "models.Role", "models.User", "models.Member", "Snowflake_Type"],
        type: Optional["OverwriteTypes"] = None,
        allow: Optional[List["Permissions"] | int] = None,
        deny: Optional[List["Permissions"] | int] = None,
        reason: Optional[str] = None,
    ) -> None:
        """
        Add a permission to this channel.

        Args:
            target: The updated PermissionOverwrite object, or the Role or User object/id to update
            type: The type of permission overwrite. Only applicable if target is an id
            allow: List of permissions to allow. Only applicable if target is not an PermissionOverwrite object
            deny: List of permissions to deny. Only applicable if target is not an PermissionOverwrite object
            reason: The reason for this change

        Raises:
            ValueError: Invalid target for permission

        """
        allow = allow or []
        deny = deny or []
        if not isinstance(target, PermissionOverwrite):
            if isinstance(target, (models.User, models.Member)):
                target = target.id
                type = OverwriteTypes.MEMBER
            elif isinstance(target, models.Role):
                target = target.id
                type = OverwriteTypes.ROLE
            elif type and isinstance(target, Snowflake_Type):
                target = to_snowflake(target)
            else:
                raise ValueError("Invalid target and/or type for permission")
            overwrite = PermissionOverwrite(id=target, type=type, allow=Permissions.NONE, deny=Permissions.NONE)
            if isinstance(allow, int):
                overwrite.allow |= allow
            else:
                for perm in allow:
                    overwrite.allow |= perm
            if isinstance(deny, int):
                overwrite.deny |= deny
            else:
                for perm in deny:
                    overwrite.deny |= perm
        else:
            overwrite = target

        if exists := get(self.permission_overwrites, id=overwrite.id, type=overwrite.type):
            exists.deny = (exists.deny | overwrite.deny) & ~overwrite.allow
            exists.allow = (exists.allow | overwrite.allow) & ~overwrite.deny
            await self.edit_permission(exists, reason)
        else:
            permission_overwrites = self.permission_overwrites
            await self.edit(permission_overwrites=permission_overwrites)

    async def edit_permission(self, overwrite: PermissionOverwrite, reason: Optional[str] = None) -> None:
        """
        Edit the permissions for this channel.

        Args:
            overwrite: The permission overwrite to apply
            reason: The reason for this change
        """
        await self._client.http.edit_channel_permission(
            self.id, overwrite.id, overwrite.allow, overwrite.deny, overwrite.type, reason
        )

    async def delete_permission(
        self,
        target: Union["PermissionOverwrite", "models.Role", "models.User"],
        reason: Absent[Optional[str]] = MISSING,
    ) -> None:
        """
        Delete a permission overwrite for this channel.

        Args:
            target: The permission overwrite to delete
            reason: The reason for this change

        """
        target = to_snowflake(target)
        await self._client.http.delete_channel_permission(self.id, target, reason)

    @property
    def members(self) -> List["models.Member"]:
        """Returns a list of members that can see this channel."""
        return [m for m in self.guild.members if Permissions.VIEW_CHANNEL in m.channel_permissions(self)]  # type: ignore

    @property
    def bots(self) -> List["models.Member"]:
        """Returns a list of bots that can see this channel."""
        return [m for m in self.guild.members if m.bot and Permissions.VIEW_CHANNEL in m.channel_permissions(self)]  # type: ignore

    @property
    def humans(self) -> List["models.Member"]:
        """Returns a list of humans that can see this channel."""
        return [m for m in self.guild.members if not m.bot and Permissions.VIEW_CHANNEL in m.channel_permissions(self)]  # type: ignore

    async def clone(self, name: Optional[str] = None, reason: Absent[Optional[str]] = MISSING) -> "TYPE_GUILD_CHANNEL":
        """
        Clone this channel and create a new one.

        Args:
            name: The name of the new channel. Defaults to the current name
            reason: The reason for creating this channel

        Returns:
            The newly created channel.

        """
        await self.guild.create_channel(
            channel_type=self.type,
            name=name if name else self.name,
            topic=getattr(self, "topic", MISSING),
            position=self.position,
            permission_overwrites=self.permission_overwrites,
            category=self.category,
            nsfw=self.nsfw,
            bitrate=getattr(self, "bitrate", 64000),
            user_limit=getattr(self, "user_limit", 0),
            rate_limit_per_user=getattr(self, "rate_limit_per_user", 0),
            reason=reason,
        )


@define()
class GuildCategory(GuildChannel):
    @property
    def channels(self) -> List["TYPE_GUILD_CHANNEL"]:
        """Get all channels within the category"""
        return [channel for channel in self.guild.channels if channel.parent_id == self.id]

    @property
    def voice_channels(self) -> List["GuildVoice"]:
        """Get all voice channels within the category"""
        return [
            channel
            for channel in self.channels
            if isinstance(channel, GuildVoice) and not isinstance(channel, GuildStageVoice)
        ]

    @property
    def stage_channels(self) -> List["GuildStageVoice"]:
        """Get all stage channels within the category"""
        return [channel for channel in self.channels if isinstance(channel, GuildStageVoice)]

    @property
    def text_channels(self) -> List["GuildText"]:
        """Get all text channels within the category"""
        return [channel for channel in self.channels if isinstance(channel, GuildText)]

    @property
    def news_channels(self) -> List["GuildNews"]:
        """Get all news channels within the category"""
        return [channel for channel in self.channels if isinstance(channel, GuildNews)]

    async def edit(
        self,
        name: Absent[str] = MISSING,
        position: Absent[int] = MISSING,
        permission_overwrites: Absent[
            Union[dict, PermissionOverwrite, List[Union[dict, PermissionOverwrite]]]
        ] = MISSING,
        reason: Absent[str] = MISSING,
        **kwargs,
    ) -> "GuildCategory":
        """
        Edit this channel.

        Args:
            name: 1-100 character channel name
            position: the position of the channel in the left-hand listing
            permission_overwrites: channel or category-specific permissions
            reason: the reason for this change

        Returns:
            The updated channel object.

        """
        return await super().edit(
            name=name,
            position=position,
            permission_overwrites=permission_overwrites,
            reason=reason,
            **kwargs,
        )

    async def create_channel(
        self,
        channel_type: Union[ChannelTypes, int],
        name: str,
        topic: Absent[Optional[str]] = MISSING,
        position: Absent[Optional[int]] = MISSING,
        permission_overwrites: Absent[
            Union[dict, PermissionOverwrite, List[Union[dict, PermissionOverwrite]]]
        ] = MISSING,
        nsfw: bool = False,
        bitrate: int = 64000,
        user_limit: int = 0,
        rate_limit_per_user: int = 0,
        reason: Absent[Optional[str]] = MISSING,
    ) -> "TYPE_GUILD_CHANNEL":
        """
        Create a guild channel within this category, allows for explicit channel type setting.

        Args:
            channel_type: The type of channel to create
            name: The name of the channel
            topic: The topic of the channel
            position: The position of the channel in the channel list
            permission_overwrites: Permission overwrites to apply to the channel
            nsfw: Should this channel be marked nsfw
            bitrate: The bitrate of this channel, only for voice
            user_limit: The max users that can be in this channel, only for voice
            rate_limit_per_user: The time users must wait between sending messages
            reason: The reason for creating this channel

        Returns:
            The newly created channel.

        """
        return await self.guild.create_channel(
            channel_type=channel_type,
            name=name,
            topic=topic,
            position=position,
            permission_overwrites=permission_overwrites,
            category=self.id,
            nsfw=nsfw,
            bitrate=bitrate,
            user_limit=user_limit,
            rate_limit_per_user=rate_limit_per_user,
            reason=reason,
        )

    async def create_text_channel(
        self,
        name: str,
        topic: Absent[Optional[str]] = MISSING,
        position: Absent[Optional[int]] = MISSING,
        permission_overwrites: Absent[
            Union[dict, PermissionOverwrite, List[Union[dict, PermissionOverwrite]]]
        ] = MISSING,
        nsfw: bool = False,
        rate_limit_per_user: int = 0,
        reason: Absent[Optional[str]] = MISSING,
    ) -> "GuildText":
        """
        Create a text channel in this guild within this category.

        Args:
            name: The name of the channel
            topic: The topic of the channel
            position: The position of the channel in the channel list
            permission_overwrites: Permission overwrites to apply to the channel
            nsfw: Should this channel be marked nsfw
            rate_limit_per_user: The time users must wait between sending messages
            reason: The reason for creating this channel

        Returns:
           The newly created text channel.

        """
        return await self.create_channel(
            channel_type=ChannelTypes.GUILD_TEXT,
            name=name,
            topic=topic,
            position=position,
            permission_overwrites=permission_overwrites,
            nsfw=nsfw,
            rate_limit_per_user=rate_limit_per_user,
            reason=reason,
        )

    async def create_news_channel(
        self,
        name: str,
        topic: Absent[Optional[str]] = MISSING,
        position: Absent[Optional[int]] = MISSING,
        permission_overwrites: Absent[
            Union[dict, PermissionOverwrite, List[Union[dict, PermissionOverwrite]]]
        ] = MISSING,
        nsfw: bool = False,
        reason: Absent[Optional[str]] = MISSING,
    ) -> "GuildNews":
        """
        Create a news channel in this guild within this category.

        Args:
            name: The name of the channel
            topic: The topic of the channel
            position: The position of the channel in the channel list
            permission_overwrites: Permission overwrites to apply to the channel
            nsfw: Should this channel be marked nsfw
            reason: The reason for creating this channel

        Returns:
           The newly created news channel.

        """
        return await self.create_channel(
            channel_type=ChannelTypes.GUILD_NEWS,
            name=name,
            topic=topic,
            position=position,
            permission_overwrites=permission_overwrites,
            nsfw=nsfw,
            reason=reason,
        )

    async def create_voice_channel(
        self,
        name: str,
        topic: Absent[Optional[str]] = MISSING,
        position: Absent[Optional[int]] = MISSING,
        permission_overwrites: Absent[
            Union[dict, PermissionOverwrite, List[Union[dict, PermissionOverwrite]]]
        ] = MISSING,
        nsfw: bool = False,
        bitrate: int = 64000,
        user_limit: int = 0,
        reason: Absent[Optional[str]] = MISSING,
    ) -> "GuildVoice":
        """
        Create a guild voice channel within this category.

        Args:
            name: The name of the channel
            topic: The topic of the channel
            position: The position of the channel in the channel list
            permission_overwrites: Permission overwrites to apply to the channel
            nsfw: Should this channel be marked nsfw
            bitrate: The bitrate of this channel, only for voice
            user_limit: The max users that can be in this channel, only for voice
            reason: The reason for creating this channel

        Returns:
           The newly created voice channel.

        """
        return await self.create_channel(
            channel_type=ChannelTypes.GUILD_VOICE,
            name=name,
            topic=topic,
            position=position,
            permission_overwrites=permission_overwrites,
            nsfw=nsfw,
            bitrate=bitrate,
            user_limit=user_limit,
            reason=reason,
        )

    async def create_stage_channel(
        self,
        name: str,
        topic: Absent[Optional[str]] = MISSING,
        position: Absent[Optional[int]] = MISSING,
        permission_overwrites: Absent[
            Union[dict, PermissionOverwrite, List[Union[dict, PermissionOverwrite]]]
        ] = MISSING,
        bitrate: int = 64000,
        user_limit: int = 0,
        reason: Absent[Optional[str]] = MISSING,
    ) -> "GuildStageVoice":
        """
        Create a guild stage channel within this category.

        Args:
            name: The name of the channel
            topic: The topic of the channel
            position: The position of the channel in the channel list
            permission_overwrites: Permission overwrites to apply to the channel
            bitrate: The bitrate of this channel, only for voice
            user_limit: The max users that can be in this channel, only for voice
            reason: The reason for creating this channel

        Returns:
            The newly created stage channel.

        """
        return await self.create_channel(
            channel_type=ChannelTypes.GUILD_STAGE_VOICE,
            name=name,
            topic=topic,
            position=position,
            permission_overwrites=permission_overwrites,
            bitrate=bitrate,
            user_limit=user_limit,
            reason=reason,
        )


@define()
class GuildStore(GuildChannel):
    async def edit(
        self,
        name: Absent[str] = MISSING,
        position: Absent[int] = MISSING,
        permission_overwrites: Absent[
            Union[dict, PermissionOverwrite, List[Union[dict, PermissionOverwrite]]]
        ] = MISSING,
        parent_id: Absent[Snowflake_Type] = MISSING,
        nsfw: Absent[bool] = MISSING,
        reason: Absent[str] = MISSING,
        **kwargs,
    ) -> "GuildStore":
        """
        Edit this channel.

        Args:
            name: 1-100 character channel name
            position: the position of the channel in the left-hand listing
            permission_overwrites: channel or category-specific permissions
            parent_id: id of the new parent category for a channel
            nsfw: whether the channel is nsfw
            reason: The reason for this change

        Returns:
            The edited channel.

        """
        return await super().edit(
            name=name,
            position=position,
            permission_overwrites=permission_overwrites,
            parent_id=parent_id,
            nsfw=nsfw,
            reason=reason,
            **kwargs,
        )


@define()
class GuildNews(GuildChannel, MessageableMixin, InvitableMixin, ThreadableMixin, WebhookMixin):
    topic: Optional[str] = field(default=None)
    """The channel topic (0-1024 characters)"""

    async def edit(
        self,
        name: Absent[str] = MISSING,
        position: Absent[int] = MISSING,
        permission_overwrites: Absent[
            Union[dict, PermissionOverwrite, List[Union[dict, PermissionOverwrite]]]
        ] = MISSING,
        parent_id: Absent[Snowflake_Type] = MISSING,
        nsfw: Absent[bool] = MISSING,
        topic: Absent[str] = MISSING,
        channel_type: Absent["ChannelTypes"] = MISSING,
        default_auto_archive_duration: Absent["AutoArchiveDuration"] = MISSING,
        reason: Absent[str] = MISSING,
        **kwargs,
    ) -> Union["GuildNews", "GuildText"]:
        """
        Edit the guild text channel.

        Args:
            name: 1-100 character channel name
            position: the position of the channel in the left-hand listing
            permission_overwrites: a list of PermissionOverwrite
            parent_id:  the parent category `Snowflake_Type` for the channel
            nsfw: whether the channel is nsfw
            topic: 0-1024 character channel topic
            channel_type: the type of channel; only conversion between text and news is supported and only in guilds with the "NEWS" feature
            default_auto_archive_duration: optional AutoArchiveDuration
            reason: An optional reason for the audit log

        Returns:
            The edited channel.

        """
        return await super().edit(
            name=name,
            position=position,
            permission_overwrites=permission_overwrites,
            parent_id=parent_id,
            nsfw=nsfw,
            topic=topic,
            type=channel_type,
            default_auto_archive_duration=default_auto_archive_duration,
            reason=reason,
            **kwargs,
        )

    async def follow(self, webhook_channel_id: Snowflake_Type) -> None:
        """
        Follow this channel.

        Args:
            webhook_channel_id: The ID of the channel to post messages from this channel to

        """
        await self._client.http.follow_news_channel(self.id, webhook_channel_id)

    async def create_thread_from_message(
        self,
        name: str,
        message: Snowflake_Type,
        auto_archive_duration: AutoArchiveDuration = AutoArchiveDuration.ONE_DAY,
        reason: Absent[str] = None,
    ) -> "GuildNewsThread":
        """
        Creates a new news thread in this channel.

        Args:
            name: 1-100 character thread name.
            message: The message to connect this thread to.
            auto_archive_duration: Time before the thread will be automatically archived. Note 3 day and 7 day archive durations require the server to be boosted.
            reason: The reason for creating this thread.

        Returns:
            The created public thread, if successful

        """
        return await self.create_thread(
            name=name,
            message=message,
            auto_archive_duration=auto_archive_duration,
            reason=reason,
        )


@define()
class GuildText(GuildChannel, MessageableMixin, InvitableMixin, ThreadableMixin, WebhookMixin):
    topic: Optional[str] = field(default=None)
    """The channel topic (0-1024 characters)"""
    rate_limit_per_user: int = field(default=0)
    """Amount of seconds a user has to wait before sending another message (0-21600)"""

    async def edit(
        self,
        name: Absent[str] = MISSING,
        position: Absent[int] = MISSING,
        permission_overwrites: Absent[
            Union[dict, PermissionOverwrite, List[Union[dict, PermissionOverwrite]]]
        ] = MISSING,
        parent_id: Absent[Snowflake_Type] = MISSING,
        nsfw: Absent[bool] = MISSING,
        topic: Absent[str] = MISSING,
        channel_type: Absent["ChannelTypes"] = MISSING,
        default_auto_archive_duration: Absent["AutoArchiveDuration"] = MISSING,
        rate_limit_per_user: Absent[int] = MISSING,
        reason: Absent[str] = MISSING,
        **kwargs,
    ) -> Union["GuildText", "GuildNews"]:
        """
        Edit the guild text channel.

        Args:
            name: 1-100 character channel name
            position: the position of the channel in the left-hand listing
            permission_overwrites: a list of PermissionOverwrite
            parent_id:  the parent category `Snowflake_Type` for the channel
            nsfw: whether the channel is nsfw
            topic: 0-1024 character channel topic
            channel_type: the type of channel; only conversion between text and news is supported and only in guilds with the "NEWS" feature
            default_auto_archive_duration: optional AutoArchiveDuration
            rate_limit_per_user: amount of seconds a user has to wait before sending another message (0-21600)
            reason: An optional reason for the audit log

        Returns:
            The edited channel.

        """
        return await super().edit(
            name=name,
            position=position,
            permission_overwrites=permission_overwrites,
            parent_id=parent_id,
            nsfw=nsfw,
            topic=topic,
            type=channel_type,
            default_auto_archive_duration=default_auto_archive_duration,
            reason=reason,
            **kwargs,
        )

    async def create_public_thread(
        self,
        name: str,
        auto_archive_duration: AutoArchiveDuration = AutoArchiveDuration.ONE_DAY,
        reason: Absent[str] = None,
    ) -> "GuildPublicThread":
        """
        Creates a new public thread in this channel.

        Args:
            name: 1-100 character thread name.
            thread_type: Is the thread private or public.
            auto_archive_duration: Time before the thread will be automatically archived. Note 3 day and 7 day archive durations require the server to be boosted.
            reason: The reason for creating this thread.

        Returns:
            The created public thread, if successful

        """
        return await self.create_thread(
            name=name,
            thread_type=ChannelTypes.GUILD_PUBLIC_THREAD,
            auto_archive_duration=auto_archive_duration,
            reason=reason,
        )

    async def create_private_thread(
        self,
        name: str,
        invitable: Absent[bool] = MISSING,
        auto_archive_duration: AutoArchiveDuration = AutoArchiveDuration.ONE_DAY,
        reason: Absent[str] = None,
    ) -> "GuildPrivateThread":
        """
        Creates a new private thread in this channel.

        Args:
            name: 1-100 character thread name.
            message: The message to connect this thread to.
            invitable: whether non-moderators can add other non-moderators to a thread.
            auto_archive_duration: Time before the thread will be automatically archived. Note 3 day and 7 day archive durations require the server to be boosted.
            reason: The reason for creating this thread.

        Returns:
            The created thread, if successful

        """
        return await self.create_thread(
            name=name,
            thread_type=ChannelTypes.GUILD_PRIVATE_THREAD,
            invitable=invitable,
            auto_archive_duration=auto_archive_duration,
            reason=reason,
        )

    async def create_thread_from_message(
        self,
        name: str,
        message: Snowflake_Type,
        auto_archive_duration: AutoArchiveDuration = AutoArchiveDuration.ONE_DAY,
        reason: Absent[str] = None,
    ) -> "GuildPublicThread":
        """
        Creates a new public thread in this channel.

        Args:
            name: 1-100 character thread name.
            message: The message to connect this thread to.
            auto_archive_duration: Time before the thread will be automatically archived. Note 3 day and 7 day archive durations require the server to be boosted.
            reason: The reason for creating this thread.

        Returns:
            The created public thread, if successful

        """
        return await self.create_thread(
            name=name,
            message=message,
            auto_archive_duration=auto_archive_duration,
            reason=reason,
        )


################################################################
# Guild Threads


@define(slots=False)
class ThreadChannel(BaseChannel, MessageableMixin, WebhookMixin):
    parent_id: Snowflake_Type = field(default=None, converter=optional_c(to_snowflake))
    """id of the text channel this thread was created"""
    owner_id: Snowflake_Type = field(default=None, converter=optional_c(to_snowflake))
    """id of the creator of the thread"""
    topic: Optional[str] = field(default=None)
    """The thread topic (0-1024 characters)"""
    message_count: int = field(default=0)
    """An approximate count of messages in a thread, stops counting at 50"""
    member_count: int = field(default=0)
    """An approximate count of users in a thread, stops counting at 50"""
    archived: bool = field(default=False)
    """Whether the thread is archived"""
    auto_archive_duration: int = field(
        default=attrs.Factory(lambda self: self.default_auto_archive_duration, takes_self=True)
    )
    """Duration in minutes to automatically archive the thread after recent activity, can be set to: 60, 1440, 4320, 10080"""
    locked: bool = field(default=False)
    """Whether the thread is locked"""
    archive_timestamp: Optional["models.Timestamp"] = field(default=None, converter=optional_c(timestamp_converter))
    """Timestamp when the thread's archive status was last changed, used for calculating recent activity"""
    create_timestamp: Optional["models.Timestamp"] = field(default=None, converter=optional_c(timestamp_converter))
    """Timestamp when the thread was created"""

    _guild_id: Snowflake_Type = field(default=None, converter=optional_c(to_snowflake))

    @classmethod
    def _process_dict(cls, data: Dict[str, Any], client: "Snake") -> Dict[str, Any]:
        data = super()._process_dict(data, client)
        thread_metadata: dict = data.get("thread_metadata", {})
        data.update(thread_metadata)
        return data

    @property
    def is_private(self) -> bool:
        """Is this a private thread?"""
        return self.type == ChannelTypes.GUILD_PRIVATE_THREAD

    @property
    def guild(self) -> "models.Guild":
        """The guild this channel belongs to."""
        return self._client.cache.get_guild(self._guild_id)

    @property
    def parent_channel(self) -> GuildText:
        """The channel this thread is a child of."""
        return self._client.cache.get_channel(self.parent_id)

    @property
    def mention(self) -> str:
        """Returns a string that would mention this thread."""
        return f"<#{self.id}>"

    async def fetch_members(self) -> List["models.ThreadMember"]:
        """Get the members that have access to this thread."""
        members_data = await self._client.http.list_thread_members(self.id)
        return models.ThreadMember.from_list(members_data, self._client)

    async def add_member(self, member: Union["models.Member", Snowflake_Type]) -> None:
        """
        Add a member to this thread.

        Args:
            member: The member to add

        """
        await self._client.http.add_thread_member(self.id, to_snowflake(member))

    async def remove_member(self, member: Union["models.Member", Snowflake_Type]) -> None:
        """
        Remove a member from this thread.

        Args:
            member: The member to remove

        """
        await self._client.http.remove_thread_member(self.id, to_snowflake(member))

    async def join(self) -> None:
        """Join this thread."""
        await self._client.http.join_thread(self.id)

    async def leave(self) -> None:
        """Leave this thread."""
        await self._client.http.leave_thread(self.id)

    async def archive(self, locked: bool = False, reason: Absent[str] = MISSING) -> "TYPE_THREAD_CHANNEL":
        """
        Helper method to archive this thread.

        Args:
            locked: whether the thread is locked; when a thread is locked, only users with MANAGE_THREADS can unarchive it
            reason: The reason for this archive

        Returns:
            The archived thread channel object.

        """
        return await super().edit(locked=locked, archived=True, reason=reason)


@define()
class GuildNewsThread(ThreadChannel):
    async def edit(
        self,
        name: Absent[str] = MISSING,
        archived: Absent[bool] = MISSING,
        auto_archive_duration: Absent[AutoArchiveDuration] = MISSING,
        locked: Absent[bool] = MISSING,
        rate_limit_per_user: Absent[int] = MISSING,
        reason: Absent[str] = MISSING,
        **kwargs,
    ) -> "GuildNewsThread":
        """
        Edit this thread.

        Args:
            name: 1-100 character channel name
            archived: whether the thread is archived
            auto_archive_duration: duration in minutes to automatically archive the thread after recent activity, can be set to: 60, 1440, 4320, 10080
            locked: whether the thread is locked; when a thread is locked, only users with MANAGE_THREADS can unarchive it
            rate_limit_per_user: amount of seconds a user has to wait before sending another message (0-21600)
            reason: The reason for this change

        Returns:
            The edited thread channel object.

        """
        return await super().edit(
            name=name,
            archived=archived,
            auto_archive_duration=auto_archive_duration,
            locked=locked,
            rate_limit_per_user=rate_limit_per_user,
            reason=reason,
            **kwargs,
        )


@define()
class GuildPublicThread(ThreadChannel):
    async def edit(
        self,
        name: Absent[str] = MISSING,
        archived: Absent[bool] = MISSING,
        auto_archive_duration: Absent[AutoArchiveDuration] = MISSING,
        locked: Absent[bool] = MISSING,
        rate_limit_per_user: Absent[int] = MISSING,
        reason: Absent[str] = MISSING,
        **kwargs,
    ) -> "GuildPublicThread":
        """
        Edit this thread.

        Args:
            name: 1-100 character channel name
            archived: whether the thread is archived
            auto_archive_duration: duration in minutes to automatically archive the thread after recent activity, can be set to: 60, 1440, 4320, 10080
            locked: whether the thread is locked; when a thread is locked, only users with MANAGE_THREADS can unarchive it
            rate_limit_per_user: amount of seconds a user has to wait before sending another message (0-21600)
            reason: The reason for this change

        Returns:
            The edited thread channel object.

        """
        return await super().edit(
            name=name,
            archived=archived,
            auto_archive_duration=auto_archive_duration,
            locked=locked,
            rate_limit_per_user=rate_limit_per_user,
            reason=reason,
            **kwargs,
        )


@define()
class GuildPrivateThread(ThreadChannel):
    invitable: bool = field(default=False)
    """Whether non-moderators can add other non-moderators to a thread"""

    async def edit(
        self,
        name: Absent[str] = MISSING,
        archived: Absent[bool] = MISSING,
        auto_archive_duration: Absent[AutoArchiveDuration] = MISSING,
        locked: Absent[bool] = MISSING,
        rate_limit_per_user: Absent[int] = MISSING,
        invitable: Absent[bool] = MISSING,
        reason: Absent[str] = MISSING,
        **kwargs,
    ) -> "GuildPrivateThread":
        """
        Edit this thread.

        Args:
            name: 1-100 character channel name
            archived: whether the thread is archived
            auto_archive_duration: duration in minutes to automatically archive the thread after recent activity, can be set to: 60, 1440, 4320, 10080
            locked: whether the thread is locked; when a thread is locked, only users with MANAGE_THREADS can unarchive it
            rate_limit_per_user: amount of seconds a user has to wait before sending another message (0-21600)
            invitable: whether non-moderators can add other non-moderators to a thread; only available on private threads
            reason: The reason for this change

        Returns:
            The edited thread channel object.

        """
        return await super().edit(
            name=name,
            archived=archived,
            auto_archive_duration=auto_archive_duration,
            locked=locked,
            rate_limit_per_user=rate_limit_per_user,
            invitable=invitable,
            reason=reason,
            **kwargs,
        )


################################################################
# Guild Voices


@define(slots=False)
class VoiceChannel(GuildChannel):  # May not be needed, can be directly just GuildVoice.
    bitrate: int = field()
    """The bitrate (in bits) of the voice channel"""
    user_limit: int = field()
    """The user limit of the voice channel"""
    rtc_region: str = field(default="auto")
    """Voice region id for the voice channel, automatic when set to None"""
    video_quality_mode: Union[VideoQualityModes, int] = field(default=VideoQualityModes.AUTO)
    """The camera video quality mode of the voice channel, 1 when not present"""
    _voice_member_ids: list[Snowflake_Type] = field(factory=list)

    async def edit(
        self,
        name: Absent[str] = MISSING,
        position: Absent[int] = MISSING,
        permission_overwrites: Absent[
            Union[dict, PermissionOverwrite, List[Union[dict, PermissionOverwrite]]]
        ] = MISSING,
        parent_id: Absent[Snowflake_Type] = MISSING,
        bitrate: Absent[int] = MISSING,
        user_limit: Absent[int] = MISSING,
        rtc_region: Absent[str] = MISSING,
        video_quality_mode: Absent[VideoQualityModes] = MISSING,
        reason: Absent[str] = MISSING,
        **kwargs,
    ) -> Union["GuildVoice", "GuildStageVoice"]:
        """
        Edit guild voice channel.

        Args:
            name: 1-100 character channel name
            position: the position of the channel in the left-hand listing
            permission_overwrites: a list of `PermissionOverwrite` to apply to the channel
            parent_id: the parent category `Snowflake_Type` for the channel
            bitrate: the bitrate (in bits) of the voice channel; 8000 to 96000 (128000 for VIP servers)
            user_limit: the user limit of the voice channel; 0 refers to no limit, 1 to 99 refers to a user limit
            rtc_region: channel voice region id, automatic when not set
            video_quality_mode: the camera video quality mode of the voice channel
            reason: optional reason for audit logs

        Returns:
            The edited voice channel object.

        """
        return await super().edit(
            name=name,
            position=position,
            permission_overwrites=permission_overwrites,
            parent_id=parent_id,
            bitrate=bitrate,
            user_limit=user_limit,
            rtc_region=rtc_region,
            video_quality_mode=video_quality_mode,
            reason=reason,
            **kwargs,
        )

    @property
    def members(self) -> List["models.Member"]:
        """Returns a list of members that have access to this voice channel"""
        return [m for m in self.guild.members if Permissions.CONNECT in m.channel_permissions(self)]  # type: ignore

    @property
    def voice_members(self) -> List["models.Member"]:
        """Returns a list of members that are currently in the channel. Note: This will not be accurate if the bot was offline while users joined the channel"""
        return [self._client.cache.get_member(self._guild_id, member_id) for member_id in self._voice_member_ids]

    @property
    def voice_state(self) -> "ActiveVoiceState":
        return self._client.get_bot_voice_state(self._guild_id)

    async def connect(self) -> "ActiveVoiceState":
        if not self.voice_state:
            return await self._client.connect_to_vc(self._guild_id, self.id)
        await self.voice_state.move(self.id)
        return self.voice_state


@define()
class GuildVoice(VoiceChannel, InvitableMixin):
    pass


@define()
class GuildStageVoice(GuildVoice):
    stage_instance: "models.StageInstance" = field(default=MISSING)
    """The stage instance that this voice channel belongs to"""

    # todo: Listeners and speakers properties (needs voice state caching)

    async def fetch_stage_instance(self) -> "models.StageInstance":
        """
        Fetches the stage instance associated with this channel.

        Returns:
            The stage instance associated with this channel. If no stage is live, will return None.

        """
        self.stage_instance = models.StageInstance.from_dict(
            await self._client.http.get_stage_instance(self.id), self._client
        )
        return self.stage_instance

    async def create_stage_instance(
        self,
        topic: str,
        privacy_level: StagePrivacyLevel = StagePrivacyLevel.GUILD_ONLY,
        reason: Absent[Optional[str]] = MISSING,
    ) -> "models.StageInstance":
        """
        Create a stage instance in this channel.

        Args:
            topic: The topic of the stage (1-120 characters)
            privacy_level: The privacy level of the stage
            reason: The reason for creating this instance

        Returns:
            The created stage instance object.

        """
        self.stage_instance = models.StageInstance.from_dict(
            await self._client.http.create_stage_instance(self.id, topic, privacy_level, reason), self._client
        )
        return self.stage_instance

    async def close_stage(self, reason: Absent[Optional[str]] = MISSING) -> None:
        """
        Closes the live stage instance.

        Args:
            reason: The reason for closing the stage

        """
        if not self.stage_instance:
            # we dont know of an active stage instance, so lets check for one
            if not await self.get_stage_instance():
                raise ValueError("No stage instance found")

        await self.stage_instance.delete(reason=reason)


def process_permission_overwrites(
    overwrites: Union[dict, PermissionOverwrite, List[Union[dict, PermissionOverwrite]]]
) -> List[dict]:
    """
    Processes a permission overwrite lists into format for sending to discord.

    Args:
        overwrites: The permission overwrites to process

    Returns:
        The processed permission overwrites

    """
    if not overwrites:
        return overwrites

    if isinstance(overwrites, dict):
        return [overwrites]

    if isinstance(overwrites, list):
        return list(map(to_dict, overwrites))

    if isinstance(overwrites, PermissionOverwrite):
        return [overwrites.to_dict()]

    raise ValueError(f"Invalid overwrites: {overwrites}")


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
    DM,
    DMGroup,
]


TYPE_DM_CHANNEL = Union[DM, DMGroup]


TYPE_GUILD_CHANNEL = Union[GuildCategory, GuildStore, GuildNews, GuildText, GuildVoice, GuildStageVoice]


TYPE_THREAD_CHANNEL = Union[GuildNewsThread, GuildPublicThread, GuildPrivateThread]


TYPE_VOICE_CHANNEL = Union[GuildVoice, GuildStageVoice]


TYPE_MESSAGEABLE_CHANNEL = Union[
    DM, DMGroup, GuildNews, GuildText, GuildPublicThread, GuildPrivateThread, GuildNewsThread
]


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
