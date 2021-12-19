import time
from collections import namedtuple
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union, Callable

import attr
from attr.converters import optional as optional_c

from dis_snek.const import MISSING, DISCORD_EPOCH
from dis_snek.mixins.send import SendMixin
from dis_snek.models.discord import DiscordObject
from dis_snek.models.discord_objects.invite import Invite, InviteTargetTypes
from dis_snek.models.discord_objects.stage_instance import StageInstance
from dis_snek.models.discord_objects.thread import ThreadMember, ThreadList
from dis_snek.models.discord_objects.webhooks import Webhook
from dis_snek.models.enums import (
    ChannelTypes,
    OverwriteTypes,
    Permissions,
    VideoQualityModes,
    AutoArchiveDuration,
    StagePrivacyLevel,
)
from dis_snek.models.iterator import AsyncIterator
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


class ChannelHistory(AsyncIterator):
    """
    An async iterator for searching through a channel's history

    Args:
        channel: The channel to search through
        limit: The maximum number of messages to return (set to 0 for no limit)
        before: get messages before this message ID
        after: get messages after this message ID
        around: get messages "around" this message ID
    """

    def __init__(self, channel: "BaseChannel", limit=50, before=None, after=None, around=None):
        self.channel: "BaseChannel" = channel
        self.before: "Snowflake_Type" = before
        self.after: "Snowflake_Type" = after
        self.around: "Snowflake_Type" = around
        super().__init__(limit)

    async def fetch(self):
        if self.after:
            if not self.last:
                self.last = namedtuple("temp", "id")
                self.last.id = self.after
            messages = await self.channel.get_messages(limit=self.get_limit, after=self.last.id)
            messages.sort(key=lambda x: x.id)

        elif self.around:
            messages = await self.channel.get_messages(limit=self.get_limit, around=self.around)
            # todo: decide how getting *more* messages from `around` would work
            self._limit = 1  # stops history from getting more messages

        else:
            if self.before and not self.last:
                self.last = namedtuple("temp", "id")
                self.last.id = self.before

            messages = await self.channel.get_messages(limit=self.get_limit, before=self.last.id)
            messages.sort(key=lambda x: x.id, reverse=True)
        return messages


@define()
class PermissionOverwrite(SnowflakeObject):
    """
    Channel Permissions Overwrite object

    Attributes:
        type: Permission overwrite type (role or member)
        allow: Permissions to allow
        deny: Permissions to deny
    """

    type: "OverwriteTypes" = field(repr=True, converter=OverwriteTypes)
    allow: "Permissions" = field(repr=True, converter=Permissions)
    deny: "Permissions" = field(repr=True, converter=Permissions)


@define(slots=False)
class MessageableMixin(SendMixin):
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

        Args:
            message_id: ID of message to retrieve.

        Returns:
            The message object fetched.
        """
        message_id = to_snowflake(message_id)
        message: "Message" = await self._client.cache.get_message(self.id, message_id)
        return message

    def history(
        self,
        limit=100,
        before: "Snowflake_Type" = None,
        after: "Snowflake_Type" = None,
        around: "Snowflake_Type" = None,
    ):
        """
        Get an async iterator for the history of this channel

        Paramters:
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

    async def get_messages(
        self,
        limit: int = 50,
        around: "Snowflake_Type" = MISSING,
        before: "Snowflake_Type" = MISSING,
        after: "Snowflake_Type" = MISSING,
    ) -> List["Message"]:
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
        return [self._client.cache.place_message_data(message_data) for message_data in messages_data]

    async def get_pinned_messages(self) -> List["Message"]:
        """
        Fetch pinned messages from the channel.

        Returns:
            A list of messages fetched.
        """
        messages_data = await self._client.http.get_pinned_messages(self.id)
        return [self._client.cache.place_message_data(message_data) for message_data in messages_data]

    async def delete_messages(
        self, messages: List[Union["Snowflake_Type", "Message"]], reason: Optional[str] = MISSING
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

    async def delete_message(self, message: Union["Snowflake_Type", "Message"], reason: str = None) -> None:
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
        predicate: Callable[["Message"], bool] = MISSING,
        before: Optional["Snowflake_Type"] = MISSING,
        after: Optional["Snowflake_Type"] = MISSING,
        around: Optional["Snowflake_Type"] = MISSING,
        reason: Optional[str] = MISSING,
    ) -> int:
        """
        Bulk delete messages within a channel. If a `predicate` is provided, it will be used to determine which messages to delete,
        otherwise all messages will be deleted within the `deletion_limit`

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
            before: Search messages before this ID
            after: Search messages after this ID
            around: Search messages around this ID
            reason: The reason for this deletion

        Returns:
            The total amount of messages deleted
        """
        if not predicate:

            def predicate(m):
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
        await self._client.http.trigger_typing_indicator(self.id)


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

        Args:
            max_age: Max age of invite in seconds, default 86400 (24 hours).
            max_uses: Max uses of invite, default 0.
            temporary: Grants temporary membership, default False.
            unique: Invite is unique, default false.
            target_type: Target type for streams and embedded applications.
            target_user_id: Target User ID for Stream target type.
            target_application_id: Target Application ID for Embedded App target type.
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
        return Invite.from_dict(invite_data, self._client)

    async def get_invites(self) -> List["Invite"]:
        """
        Gets all invites (with invite metadata) for the channel.
        """
        invites_data = await self._client.http.get_channel_invites(self.id)
        return Invite.from_list(invites_data, self._client)


@define(slots=False)
class ThreadableMixin:
    async def create_thread_with_message(
        self,
        name: str,
        message: Union["Snowflake_Type", "Message"],
        auto_archive_duration: Union[AutoArchiveDuration, int] = AutoArchiveDuration.ONE_DAY,
        reason: Optional[str] = None,
    ) -> Union["GuildNewsThread", "GuildPublicThread"]:
        """
        Create a thread connected to a message
        Args:
            name: 1-100 character thread name
            message: The message to connect this thread to
            auto_archive_duration: Time before the thread will be automatically archived
            reason: The reason for creating this thread

        Returns:
            The created thread, if successful
        """
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
        """
        Creates a thread without a message source.
        Args:
            name: 	1-100 character thread name
            thread_type: Is the thread private or public
            invitable: whether non-moderators can add other non-moderators to a thread; only available when creating a private thread
            auto_archive_duration: Time before the thread will be automatically archived
            reason: The reason to create this thread

        Returns:
            The created thread, if successful
        """
        thread_data = await self._client.http.create_thread(
            channel_id=self.id,
            name=name,
            thread_type=thread_type,
            auto_archive_duration=auto_archive_duration,
            invitable=invitable,
            reason=reason,
        )
        return self._client.cache.place_channel_data(thread_data)

    async def get_public_archived_threads(self, limit: int = None, before: Optional["Timestamp"] = None) -> ThreadList:
        """
        Get a `ThreadList` of archived **public** threads available in this channel.

        Args:
            limit: optional maximum number of threads to return
            before: Returns threads before this timestamp
        """
        threads_data = await self._client.http.list_public_archived_threads(
            channel_id=self.id, limit=limit, before=before
        )
        threads_data["id"] = self.id
        return ThreadList.from_dict(threads_data, self._client)

    async def get_private_archived_threads(self, limit: int = None, before: Optional["Timestamp"] = None) -> ThreadList:
        """
        Get a `ThreadList` of archived **private** threads available in this channel.

        Args:
            limit: optional maximum number of threads to return
            before: Returns threads before this timestamp
        """
        threads_data = await self._client.http.list_private_archived_threads(
            channel_id=self.id, limit=limit, before=before
        )
        threads_data["id"] = self.id
        return ThreadList.from_dict(threads_data, self._client)

    async def get_archived_threads(self, limit: int = None, before: Optional["Timestamp"] = None) -> ThreadList:
        """
        Get a `ThreadList` of archived threads available in this channel.

        Args:
            limit: optional maximum number of threads to return
            before: Returns threads before this timestamp
        """
        threads_data = await self._client.http.list_private_archived_threads(
            channel_id=self.id, limit=limit, before=before
        )
        threads_data.update(
            await self._client.http.list_public_archived_threads(channel_id=self.id, limit=limit, before=before)
        )
        threads_data["id"] = self.id
        return ThreadList.from_dict(threads_data, self._client)

    async def get_joined_private_archived_threads(
        self, limit: int = None, before: Optional["Timestamp"] = None
    ) -> ThreadList:
        """
        Get a `ThreadList` of threads the bot is a participant of in this channel
        Args:
            limit: optional maximum number of threads to return
            before: Returns threads before this timestamp
        """
        threads_data = await self._client.http.list_joined_private_archived_threads(
            channel_id=self.id, limit=limit, before=before
        )
        threads_data["id"] = self.id
        return ThreadList.from_dict(threads_data, self._client)

    async def get_active_threads(self) -> ThreadList:
        """Returns all active threads in the channel, including public and private threads"""

        threads_data = await self._client.http.list_active_threads(guild_id=self.guild.id)

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

        return ThreadList.from_dict(threads_data, self._client)

    async def get_all_threads(self) -> ThreadList:
        """Returns all threads in the channel. Active and archived, including public and private threads"""

        threads = await self.get_active_threads()

        # update that data with the archived threads
        archived_threads = await self.get_archived_threads()
        threads.threads.extend(archived_threads.threads)
        threads.members.extend(archived_threads.members)

        return threads


@define(slots=False)
class WebhookMixin:
    async def create_webhook(self, name: str, avatar: Optional[bytes] = MISSING) -> Webhook:
        """
        Create a webhook in this channel
        Args:
            name: The name of the webhook
            avatar: An optional default avatar to use

        Returns:
            The created webhook

        Raises:
            ValueError: If you try to name the webhook "Clyde"
        """
        return await Webhook.create(self._client, self, name, avatar)  # type: ignore

    async def delete_webhook(self, webhook: Webhook) -> None:
        """
        Delete a given webhook in this channel
        Args:
            webhook: The webhook to delete
        """
        return await webhook.delete()

    async def get_webhooks(self) -> List[Webhook]:
        """
        Get all the webhooks for this channel
        Returns:
            List of webhooks
        """
        resp = await self._client.http.get_channel_webhooks(self.id)
        return [Webhook.from_dict(d, self._client) for d in resp]


@define(slots=False)
class BaseChannel(DiscordObject):
    name: Optional[str] = field(default=None)
    type: Union[ChannelTypes, int] = field(converter=ChannelTypes)

    @classmethod
    def from_dict_factory(cls, data: dict, client: "Snake") -> "TYPE_ALL_CHANNEL":
        """
        Creates a channel object of the appropriate type

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
        """Returns a string that would mention the channel"""
        return f"<#{self.id}>"

    async def _edit(self, payload: dict, reason: Optional[str] = MISSING) -> None:
        """
        # TODO

        Args:
            payload:
            reason:

        Returns:

        """
        channel_data = await self._client.http.modify_channel(self.id, payload, reason)

        self.update_from_dict(channel_data)

    async def delete(self, reason: Optional[str] = MISSING) -> None:
        """
        Delete this channel.

        Args:
            reason: The reason for deleting this channel
        """
        await self._client.http.delete_channel(self.id, reason)
        if guild := getattr(self, "guild"):
            guild._channel_ids.discard(self.id)


################################################################
# DMs


@define()
class DMChannel(BaseChannel, MessageableMixin):
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
        await self._edit(payload=payload, reason=reason)

    @property
    def members(self) -> List["User"]:
        return self.recipients


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

    async def add_recipient(
        self, user: Union["User", "Snowflake_Type"], access_token: str, nickname: Optional[str] = MISSING
    ):
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

    _guild_id: Optional["Snowflake_Type"] = attr.ib(default=None, converter=optional_c(to_snowflake))
    _permission_overwrites: Dict["Snowflake_Type", "PermissionOverwrite"] = attr.ib(factory=list)

    @property
    def guild(self) -> "Guild":
        return self._client.cache.guild_cache.get(self._guild_id)

    @property
    def category(self) -> "GuildCategory":
        return self._client.cache.channel_cache.get(self.parent_id)

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

    async def delete_permission(
        self, target: Union["PermissionOverwrite", "Role", "User"], reason: Optional[str] = MISSING
    ):
        target = to_snowflake(target)
        await self._client.http.delete_channel_permission(self.id, target, reason)

    async def create_invite(
        self,
        max_age: int = 86400,
        max_uses: int = 0,
        temporary: bool = False,
        unique: bool = False,
        target_type: InviteTargetTypes = None,
        target_user_id: "Snowflake_Type" = None,
        target_application_id: "Snowflake_Type" = None,
        reason: str = MISSING,
    ) -> Invite:
        """
        Create an invite for this channel.
        Args:
            max_age: duration of invite in seconds before expiry, or 0 for never. between 0 and 604800 (7 days) (default 24 hours)
            max_uses: max number of uses or 0 for unlimited. between 0 and 100
            temporary: whether this invite only grants temporary membership
            unique: if true, don't try to reuse a similar invite (useful for creating many unique one time use invites)
            target_type: the type of target for this voice channel invite
            target_user_id: the id of the user whose stream to display for this invite, required if target_type is 1, the user must be streaming in the channel
            target_application_id: the id of the embedded application to open for this invite, required if target_type is 2, the application must have the EMBEDDED flag
            reason: An optional reason for the audit log

        Returns:
            The created invite
        """
        resp = await self._client.http.create_channel_invite(
            self.id,
            max_age,
            max_uses,
            temporary,
            unique,
            target_type,
            target_user_id,
            target_application_id,
            reason=reason,
        )
        return Invite.from_dict(resp, self._client)

    @property
    def members(self) -> List["Member"]:
        return [m for m in self.guild.members if Permissions.VIEW_CHANNEL in m.channel_permissions(self)]  # type: ignore


@define()
class GuildCategory(GuildChannel):
    @property
    def channels(self) -> List["TYPE_GUILD_CHANNEL"]:
        """
        Get all channels within the category.

        Returns:
            The list of channels
        """
        return [channel for channel in self.guild.channels if channel.parent_id == self.id]

    async def edit(
        self,
        name: Optional[str] = MISSING,
        position: Optional[int] = MISSING,
        permission_overwrites: Optional[List["PermissionOverwrite"]] = MISSING,
        reason: Optional[str] = MISSING,
    ):
        payload = dict(  # TODO Proper processing
            name=name,
            position=position,
            permission_overwrites=permission_overwrites,
        )
        await self._edit(payload=payload, reason=reason)


@define()
class GuildStore(GuildChannel):
    async def edit(
        self,
        name: Optional[str] = MISSING,
        position: Optional[int] = MISSING,
        permission_overwrites: Optional[List["PermissionOverwrite"]] = MISSING,
        parent_id: Optional["Snowflake_Type"] = MISSING,
        nsfw: Optional[bool] = MISSING,
        reason: Optional[str] = MISSING,
    ):
        payload = dict(  # TODO Proper processing
            name=name,
            position=position,
            permission_overwrites=permission_overwrites,
            parent_id=parent_id,
            nsfw=nsfw,
        )
        await self._edit(payload=payload, reason=reason)


@define()
class GuildNews(GuildChannel, MessageableMixin, InvitableMixin, ThreadableMixin, WebhookMixin):
    topic: Optional[str] = attr.ib(default=None)

    async def edit(
        self,
        name: Optional[str] = MISSING,
        position: Optional[int] = MISSING,
        permission_overwrites: Optional[List["PermissionOverwrite"]] = MISSING,
        parent_id: Optional["Snowflake_Type"] = MISSING,
        nsfw: Optional[bool] = MISSING,
        topic: Optional[str] = MISSING,
        channel_type: Optional["ChannelTypes"] = MISSING,
        default_auto_archive_duration: Optional["AutoArchiveDuration"] = MISSING,
        reason: Optional[str] = MISSING,
    ):
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
        """
        payload = dict(  # TODO Proper processing
            name=name,
            position=position,
            permission_overwrites=permission_overwrites,
            parent_id=parent_id,
            nsfw=nsfw,
            topic=topic,
            channel_type=channel_type,
            default_auto_archive_duration=default_auto_archive_duration,
        )
        await self._edit(payload=payload, reason=reason)

    async def follow(self, webhook_channel_id: "Snowflake_Type"):
        await self._client.http.follow_news_channel(self.id, webhook_channel_id)


@define()
class GuildText(GuildChannel, MessageableMixin, InvitableMixin, ThreadableMixin, WebhookMixin):
    topic: Optional[str] = attr.ib(default=None)
    rate_limit_per_user: int = attr.ib(default=0)

    async def edit(
        self,
        name: Optional[str] = MISSING,
        position: Optional[int] = MISSING,
        permission_overwrites: Optional[List["PermissionOverwrite"]] = MISSING,
        parent_id: Optional["Snowflake_Type"] = MISSING,
        nsfw: Optional[bool] = MISSING,
        topic: Optional[str] = MISSING,
        channel_type: Optional[Union["ChannelTypes", int]] = MISSING,
        default_auto_archive_duration: Optional["AutoArchiveDuration"] = MISSING,
        rate_limit_per_user: Optional[int] = MISSING,
        reason: Optional[str] = MISSING,
    ):
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
        """
        payload = dict(  # TODO Proper processing
            name=name,
            position=position,
            permission_overwrites=permission_overwrites,
            parent_id=parent_id,
            nsfw=nsfw,
            topic=topic,
            channel_type=channel_type,
            rate_limit_per_user=rate_limit_per_user,
            default_auto_archive_duration=default_auto_archive_duration,
        )
        await self._edit(payload=payload, reason=reason)

    async def follow(self, webhook_channel_id: "Snowflake_Type"):
        await self._client.http.follow_news_channel(self.id, webhook_channel_id)


################################################################
# Guild Threads


@define()
class ThreadChannel(GuildChannel, MessageableMixin, WebhookMixin):
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
        return self.type == ChannelTypes.GUILD_PRIVATE_THREAD

    @property
    def parent_channel(self) -> GuildText:
        """The channel this thread is a child of"""
        return self._client.cache.channel_cache.get(self.parent_id)

    @property
    def mention(self) -> str:
        return f"<#{self.id}>"

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
        await self._client.http.join_thread(self.id)

    async def leave(self):
        await self._client.http.leave_thread(self.id)


@define()
class GuildNewsThread(ThreadChannel):
    async def edit(self, name, archived, auto_archive_duration, locked, rate_limit_per_user, reason):
        payload = dict(  # TODO Proper processing
            name=name,
            archived=archived,
            auto_archive_duration=auto_archive_duration,
            locked=locked,
            rate_limit_per_user=rate_limit_per_user,
        )
        await self._edit(payload=payload, reason=reason)


@define()
class GuildPublicThread(ThreadChannel):
    async def edit(self, name, archived, auto_archive_duration, locked, rate_limit_per_user, reason):
        payload = dict(  # TODO Proper processing
            name=name,
            archived=archived,
            auto_archive_duration=auto_archive_duration,
            locked=locked,
            rate_limit_per_user=rate_limit_per_user,
        )
        await self._edit(payload=payload, reason=reason)


@define()
class GuildPrivateThread(ThreadChannel):
    invitable: bool = field(default=False)

    async def edit(self, name, archived, auto_archive_duration, locked, rate_limit_per_user, invitable, reason):
        payload = dict(  # TODO Proper processing
            name=name,
            archived=archived,
            auto_archive_duration=auto_archive_duration,
            locked=locked,
            rate_limit_per_user=rate_limit_per_user,
            invitable=invitable,
        )
        await self._edit(payload=payload, reason=reason)


################################################################
# Guild Voices


@define()
class VoiceChannel(GuildChannel):  # May not be needed, can be directly just GuildVoice.
    bitrate: int = attr.ib()
    user_limit: int = attr.ib()
    rtc_region: str = attr.ib(default="auto")
    video_quality_mode: Union[VideoQualityModes, int] = attr.ib(default=VideoQualityModes.AUTO)

    async def edit(
        self,
        name: Optional[str] = MISSING,
        position: Optional[int] = MISSING,
        permission_overwrites: Optional[List["PermissionOverwrite"]] = MISSING,
        parent_id: Optional["Snowflake_Type"] = MISSING,
        bitrate: Optional[int] = MISSING,
        user_limit: Optional[int] = MISSING,
        rtc_region: Optional[str] = MISSING,
        video_quality_mode: Optional[Union[VideoQualityModes, int]] = MISSING,
        reason: Optional[str] = MISSING,
    ):
        """
        Edit guild voice channel.

        Args:
            name: 1-100 character channel name
            position: the position of the channel in the left-hand listing
            permission_overwrites: a list of `PermissionOverwrite` to apply to the channel
            parent_id: the parent category `Snowflake_Type` for the channel
            bitrate: the bitrate (in bits) of the voice channel; 8000 to 96000 (128000 for VIP servers)
            user_limit: the user limit of the voice channel; 0 refers to no limit, 1 to 99 refers to a user limi
            rtc_region: channel voice region id, automatic when not set
            video_quality_mode: the camera video quality mode of the voice channel
            reason: optional reason for audit logs
        """
        payload = dict(  # TODO Proper processing
            name=name,
            position=position,
            permission_overwrites=permission_overwrites,
            parent_id=parent_id,
            bitrate=bitrate,
            user_limit=user_limit,
            rtc_region=rtc_region,
            video_quality_mode=video_quality_mode,
        )
        await self._edit(payload=payload, reason=reason)

    @property
    def members(self) -> List["Member"]:
        # todo: when we support voice states, check if user is within channel
        return [m for m in self.guild.members if Permissions.CONNECT in m.channel_permissions(self)]  # type: ignore


@define()
class GuildVoice(VoiceChannel, InvitableMixin):
    pass


@define()
class GuildStageVoice(GuildVoice):
    stage_instance: "StageInstance" = attr.ib(default=MISSING)

    # todo: Listeners and speakers properties (needs voice state caching)

    async def get_stage_instance(self) -> StageInstance:
        """Gets the stage instance associated with this channel. If no stage is live, will return None."""
        self.stage_instance = StageInstance.from_dict(await self._client.http.get_stage_instance(self.id), self._client)
        return self.stage_instance

    async def create_stage_instance(
        self,
        topic: str,
        privacy_level: StagePrivacyLevel = StagePrivacyLevel.GUILD_ONLY,
        reason: Optional[str] = MISSING,
    ) -> StageInstance:
        """
        Create a stage instance in this channel.

        Arguments:
            topic: The topic of the stage (1-120 characters)
            privacy_level: The privacy level of the stage
            reason: The reason for creating this instance
        """
        self.stage_instance = StageInstance.from_dict(
            await self._client.http.create_stage_instance(self.id, topic, privacy_level, reason), self._client
        )
        return self.stage_instance

    async def close_stage(self, reason: Optional[str] = MISSING):
        """
        Closes the live stage instance

        Arguments:
            reason: The reason for closing the stage
        """

        if not self.stage_instance:
            # we dont know of an active stage instance, so lets check for one
            if not await self.get_stage_instance():
                raise ValueError("No stage instance found")

        await self.stage_instance.delete(reason=reason)


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
