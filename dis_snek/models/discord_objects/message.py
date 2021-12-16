import asyncio
from dataclasses import dataclass
from io import IOBase
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Union, AsyncGenerator

import attr
from aiohttp.formdata import FormData
from attr.converters import optional as optional_c

from dis_snek.const import MISSING
from dis_snek.errors import EphemeralEditException, ThreadOutsideOfGuild
from dis_snek.mixins.serialization import DictSerializationMixin
from dis_snek.models.discord import DiscordObject

from dis_snek.models.discord_objects.components import BaseComponent, process_components
from dis_snek.models.discord_objects.embed import Embed, process_embeds
from dis_snek.models.discord_objects.emoji import Emoji, process_emoji_req_format
from dis_snek.models.discord_objects.reaction import Reaction
from dis_snek.models.discord_objects.sticker import StickerItem
from dis_snek.models.enums import (
    ChannelTypes,
    InteractionTypes,
    MentionTypes,
    MessageActivityTypes,
    MessageFlags,
    MessageTypes,
    AutoArchiveDuration,
)
from dis_snek.models.file import File
from dis_snek.models.snowflake import to_snowflake, to_snowflake_list, to_optional_snowflake
from dis_snek.models.timestamp import Timestamp
from dis_snek.utils.attr_utils import define
from dis_snek.utils.converters import timestamp_converter
from dis_snek.utils.input_utils import OverriddenJson
from dis_snek.utils.serializer import dict_filter_none

if TYPE_CHECKING:
    from dis_snek.client import Snake
    from dis_snek.models.discord_objects.application import Application
    from dis_snek.models.discord_objects.channel import TYPE_THREAD_CHANNEL, TYPE_MESSAGEABLE_CHANNEL
    from dis_snek.models.discord_objects.components import ActionRow
    from dis_snek.models.discord_objects.guild import Guild
    from dis_snek.models.discord_objects.role import Role
    from dis_snek.models.discord_objects.sticker import Sticker
    from dis_snek.models.discord_objects.user import BaseUser, Member, User
    from dis_snek.models.snowflake import Snowflake_Type


@define()
class Attachment(DiscordObject):
    filename: str = attr.ib()
    content_type: Optional[str] = attr.ib(default=None)
    size: int = attr.ib()
    url: str = attr.ib()
    proxy_url: str = attr.ib()
    height: Optional[int] = attr.ib(default=None)
    width: Optional[int] = attr.ib(default=None)

    @property
    def size(self) -> tuple[Optional[int], Optional[int]]:
        return self.height, self.width


@define()
class ChannelMention(DiscordObject):
    guild_id: "Snowflake_Type" = attr.ib()
    type: ChannelTypes = attr.ib(converter=ChannelTypes)
    name: str = attr.ib()


@dataclass
class MessageActivity:
    type: MessageActivityTypes
    party_id: str = None


@attr.s(slots=True)
class MessageReference(DictSerializationMixin):
    """Reference to an originating message. Can be used for replies."""

    message_id: int = attr.ib(default=None, converter=optional_c(to_snowflake))
    """id of the originating message."""
    channel_id: Optional[int] = attr.ib(default=None, converter=optional_c(to_snowflake))
    """id of the originating message's channel."""
    guild_id: Optional[int] = attr.ib(default=None, converter=optional_c(to_snowflake))
    """id of the originating message's guild."""
    fail_if_not_exists: bool = attr.ib(default=True)
    """When sending a message, whether to error if the referenced message doesn't exist instead of sending as a normal (non-reply) message, default true."""

    @classmethod
    def for_message(cls, message: "Message", fail_if_not_exists: bool = True) -> "MessageReference":
        return cls(
            message_id=message.id,
            channel_id=message.channel.id,
            guild_id=message.guild.id,
            fail_if_not_exists=fail_if_not_exists,
        )


@define
class MessageInteraction(DiscordObject):
    type: InteractionTypes = attr.ib(converter=InteractionTypes)
    name: str = attr.ib()

    _user_id: "Snowflake_Type" = attr.ib()

    @classmethod
    def _process_dict(cls, data, client):
        user_data = data["user"]
        data["user_id"] = client.cache.place_user_data(user_data).id
        return data

    async def user(self) -> "User":
        """
        Get the user associated with this interaction.
        """
        return await self.get_user(self._user_id)


@attr.s(slots=True)
class AllowedMentions(DictSerializationMixin):
    """
    The allowed mention field allows for more granular control over mentions without various hacks to the message content.
    This will always validate against message content to avoid phantom pings, and check against user/bot permissions.
    """

    parse: Optional[List[str]] = attr.ib(factory=list)
    """An array of allowed mention types to parse from the content."""
    roles: Optional[List["Snowflake_Type"]] = attr.ib(factory=list, converter=to_snowflake_list)
    """Array of role_ids to mention. (Max size of 100)"""
    users: Optional[List["Snowflake_Type"]] = attr.ib(factory=list, converter=to_snowflake_list)
    """Array of user_ids to mention. (Max size of 100)"""
    replied_user = attr.ib(default=False)
    """For replies, whether to mention the author of the message being replied to. (default false)"""

    def add_parse(self, *mention_types: Union["MentionTypes", str]):
        for mention_type in mention_types:
            if not isinstance(mention_type, MentionTypes) and mention_type not in MentionTypes.__members__.values():
                raise ValueError(f"Invalid mention type: {mention_type}")
            self.parse.append(mention_type)

    def add_roles(self, *roles: Union["Role", "Snowflake_Type"]):
        for role in roles:
            self.roles.append(to_snowflake(role))

    def add_users(self, *users: Union["Member", "BaseUser", "Snowflake_Type"]):
        for user in users:
            self.users.append(to_snowflake(user))

    @classmethod
    def all(cls):
        return cls(parse=list(MentionTypes.__members__.values()), replied_user=True)

    @classmethod
    def none(cls):
        return cls()


@define()
class BaseMessage(DiscordObject):
    _channel_id: "Snowflake_Type" = attr.ib(default=MISSING, converter=to_optional_snowflake)
    _thread_channel_id: Optional["Snowflake_Type"] = attr.ib(default=None, converter=to_optional_snowflake)
    _guild_id: Optional["Snowflake_Type"] = attr.ib(default=None, converter=to_optional_snowflake)
    _author_id: "Snowflake_Type" = attr.ib(default=MISSING, converter=to_optional_snowflake)

    @property
    def guild(self) -> "Guild":
        return self._client.cache.guild_cache.get(self._guild_id)

    @property
    def channel(self) -> "TYPE_MESSAGEABLE_CHANNEL":
        return self._client.cache.channel_cache.get(self._channel_id)

    @property
    def thread(self) -> "TYPE_THREAD_CHANNEL":
        return self._client.cache.channel_cache.get(self._thread_channel_id)

    @property
    def author(self) -> Union["Member", "User"]:
        if self._author_id:
            member = None
            if self._guild_id:
                member = self._client.cache.member_cache.get((self._guild_id, self._author_id))
            return member or self._client.cache.user_cache.get(self._author_id)
        return MISSING


@define()
class Message(BaseMessage):
    content: str = attr.ib(default=MISSING)
    timestamp: Timestamp = attr.ib(converter=timestamp_converter)
    edited_timestamp: Optional[Timestamp] = attr.ib(default=None, converter=optional_c(timestamp_converter))
    tts: bool = attr.ib(default=False)
    mention_everyone: bool = attr.ib(default=False)
    mention_channels: Optional[List[ChannelMention]] = attr.ib(default=None)
    attachments: List[Attachment] = attr.ib(factory=list)
    embeds: List[Embed] = attr.ib(factory=list)
    reactions: List[Reaction] = attr.ib(factory=list)
    nonce: Optional[Union[int, str]] = attr.ib(default=None)
    pinned: bool = attr.ib(default=False)
    webhook_id: Optional["Snowflake_Type"] = attr.ib(default=None, converter=optional_c(to_snowflake))
    type: MessageTypes = attr.ib(converter=MessageTypes)
    activity: Optional[MessageActivity] = attr.ib(default=None, converter=optional_c(MessageActivity))
    application: Optional["Application"] = attr.ib(default=None)  # TODO: partial application
    application_id: Optional["Snowflake_Type"] = attr.ib(default=None)
    message_reference: Optional[MessageReference] = attr.ib(
        default=None, converter=optional_c(MessageReference.from_dict)
    )
    flags: Optional[MessageFlags] = attr.ib(default=None, converter=optional_c(MessageFlags))
    interaction: Optional["MessageInteraction"] = attr.ib(default=None)
    components: Optional[List["ActionRow"]] = attr.ib(default=None)
    sticker_items: Optional[List[StickerItem]] = attr.ib(
        default=None
    )  # TODO: Perhaps automatically get the full sticker data.

    _mention_ids: List["Snowflake_Type"] = attr.ib(factory=list)
    _mention_roles: List["Snowflake_Type"] = attr.ib(factory=list)
    _referenced_message_id: Optional["Snowflake_Type"] = attr.ib(default=None)

    @property
    async def mention_users(self) -> AsyncGenerator["Member", None]:
        for u_id in self._mention_ids:
            yield await self._client.cache.get_member(self._guild_id, u_id)

    @property
    async def mention_roles(self) -> AsyncGenerator["Role", None]:
        for r_id in self._mention_roles:
            yield await self._client.cache.get_role(self._guild_id, r_id)

    async def get_referenced_message(self) -> Optional["Message"]:
        """
        Get the message this message is referencing, if any
        Returns:
            The referenced message, if found
        """
        if self._referenced_message_id is None:
            return None
        return await self._client.cache.get_message(self._channel_id, self._referenced_message_id)

    @classmethod
    def _process_dict(cls, data: dict, client: "Snake") -> dict:

        try:
            author_data = data.pop("author")
        except KeyError:
            # todo: properly handle message updates that change flags (ie recipient add)
            return data
        if "guild_id" in data and "member" in data:
            author_data["member"] = data.pop("member")
            data["author_id"] = client.cache.place_member_data(data["guild_id"], author_data).id
        else:
            data["author_id"] = client.cache.place_user_data(author_data).id

        mention_ids = []
        for user_data in data.pop("mentions", {}):
            if "guild_id" in data and "member" in user_data:
                mention_ids.append(client.cache.place_member_data(data["guild_id"], user_data).id)
            else:
                mention_ids.append(client.cache.place_user_data(user_data).id)
        data["mention_ids"] = mention_ids

        if "mention_channels" in data:
            mention_channels = []
            for channel_data in data["mention_channels"]:
                mention_channels.append(ChannelMention.from_dict(channel_data, client))
            data["mention_channels"] = mention_channels

        attachments = []
        for attachment_data in data.get("attachments", []):
            attachments.append(Attachment.from_dict(attachment_data, client))
        data["attachments"] = attachments

        embeds = []
        for embed_data in data.get("embeds", []):
            embeds.append(Embed.from_dict(embed_data))
        data["embeds"] = embeds

        if "reactions" in data:
            reactions = []
            for reaction_data in data["reactions"]:
                reactions.append(
                    Reaction.from_dict(
                        reaction_data | {"message_id": data["id"], "channel_id": data["channel_id"]}, client
                    )
                )
            data["reactions"] = reactions

        # TODO: Convert to application object

        ref_message_data = data.pop("referenced_message", None)
        if ref_message_data:
            data["referenced_message_id"] = client.cache.place_message_data(ref_message_data)

        if "interaction" in data:
            data["interaction"] = MessageInteraction.from_dict(data["interaction"], client)

        thread_data = data.pop("thread", None)
        if thread_data:
            data["thread_channel_id"] = client.cache.place_channel_data(thread_data).id

        if "components" in data:
            components = []
            for component_data in data["components"]:
                components.append(BaseComponent.from_dict_factory(component_data))
            data["components"] = components

        if "sticker_items" in data:
            data["sticker_items"] = StickerItem.from_list(data["sticker_items"], client)
        return data

    @property
    def jump_url(self) -> str:
        """A url that allows the client to *jump* to this message"""
        return f"https://discord.com/channels/{self._guild_id or '@me'}/{self._channel_id}/{self.id}"

    @property
    def proto_url(self) -> str:
        """A URL like `jump_url` that uses protocols"""
        return f"discord://-/channels/{self._guild_id or '@me'}/{self._channel_id}/{self.id}"

    async def edit(
        self,
        content: Optional[str] = None,
        embeds: Optional[Union[List[Union[Embed, dict]], Union[Embed, dict]]] = None,
        embed: Optional[Union["Embed", dict]] = None,
        components: Optional[
            Union[List[List[Union["BaseComponent", dict]]], List[Union["BaseComponent", dict]], "BaseComponent", dict]
        ] = None,
        allowed_mentions: Optional[Union[AllowedMentions, dict]] = None,
        attachments: Optional[Optional[List[Union[Attachment, dict]]]] = None,
        file: Optional[Union["File", "IOBase", "Path", str]] = None,
        tts: bool = False,
        flags: Optional[Union[int, MessageFlags]] = None,
    ) -> "Message":
        """
        Edits the message.

        Args:
            content: Message text content.
            embeds: Embedded rich content (up to 6000 characters).
            embed: Embedded rich content (up to 6000 characters).
            components: The components to include with the message.
            allowed_mentions: Allowed mentions for the message.
            attachments: The attachments to keep, only used when editing message.
            file: Location of file to send, the bytes or the File() instance, defaults to None.
            tts: Should this message use Text To Speech.
            flags: Message flags to apply.

        Returns:
            New message object with edits applied
        """
        message_payload = process_message_payload(
            content=content,
            embeds=embeds or embed,
            components=components,
            allowed_mentions=allowed_mentions,
            attachments=attachments,
            file=file,
            tts=tts,
            flags=flags,
        )

        if self.flags == MessageFlags.EPHEMERAL:
            raise EphemeralEditException()

        message_data = await self._client.http.edit_message(message_payload, self._channel_id, self.id)
        if message_data:
            return self._client.cache.place_message_data(message_data)

    async def delete(self, delay: Optional[int] = MISSING):
        """
        Delete message.

        Args:
            delay: Seconds to wait before deleting message.
        """
        if delay and delay > 0:

            async def delayed_delete():
                await asyncio.sleep(delay)
                try:
                    await self._client.http.delete_message(self._channel_id, self.id)
                except Exception:
                    pass  # No real way to handle this

            asyncio.ensure_future(delayed_delete())

        else:
            await self._client.http.delete_message(self._channel_id, self.id)

    async def reply(
        self,
        content: Optional[str] = None,
        embeds: Optional[Union[List[Union[Embed, dict]], Union[Embed, dict]]] = None,
        embed: Optional[Union["Embed", dict]] = None,
        **kwargs,
    ) -> "Message":
        """Reply to this message, takes all the same attributes as `send`"""
        return await self.channel.send(content=content, reply_to=self, embeds=embeds or embed, **kwargs)

    async def create_thread(
        self,
        name: str,
        auto_archive_duration: Union[AutoArchiveDuration, int] = AutoArchiveDuration.ONE_DAY,
        reason: Optional[str] = None,
    ) -> "TYPE_THREAD_CHANNEL":
        """
        Create a thread from this message

        Args:
            name: The name of this thread
            auto_archive_duration: duration in minutes to automatically archive the thread after recent activity,
            can be set to: 60, 1440, 4320, 10080
            reason: The optional reason for creating this thread

        Returns:
            The created thread object

        Raises:
            ThreadOutsideOfGuild: if this is invoked on a message outside of a guild
        """
        if not self.channel.type == ChannelTypes.GUILD_TEXT:
            raise ThreadOutsideOfGuild()

        thread_data = await self._client.http.create_thread(
            channel_id=self._channel_id,
            name=name,
            auto_archive_duration=auto_archive_duration,
            message_id=self.id,
            reason=reason,
        )
        return self._client.cache.place_channel_data(thread_data)

    async def get_reaction(self, emoji: Union["Emoji", dict, str]) -> List["User"]:
        """
        Get reactions of a specific emoji from this message

        Args:
            emoji: The emoji to get

        Returns:
            list of users who have reacted with that emoji
        """
        reaction_data = await self._client.http.get_reactions(self._channel_id, self.id, emoji)
        return [self._client.cache.place_user_data(user_data) for user_data in reaction_data]

    async def add_reaction(self, emoji: Union["Emoji", dict, str]):
        """
        Add a reaction to this message.

        Args:
            emoji: the emoji to react with
        """
        emoji = process_emoji_req_format(emoji)
        await self._client.http.create_reaction(self._channel_id, self.id, emoji)

    async def remove_reaction(
        self, emoji: Union["Emoji", dict, str], member: Optional[Union["Member", "User", "Snowflake_Type"]] = MISSING
    ):
        """
        Remove a specific reaction that a user reacted with

        Args:
            emoji: Emoji to remove
            member: Member to remove reaction of. Default's to snake bot user.
        """
        emoji_str = process_emoji_req_format(emoji)
        if not member:
            member = self._client.user
        user_id = to_snowflake(member)
        await self._client.http.remove_user_reaction(self._channel_id, self.id, emoji_str, user_id)

    async def clear_reactions(self, emoji: Union["Emoji", dict, str]):
        # TODO Should we combine this with clear_all_reactions?
        """
        Clear a specific reaction from message

        Args:
            emoji: The emoji to clear
        """
        emoji = process_emoji_req_format(emoji)
        await self._client.http.clear_reaction(self._channel_id, self.id, emoji)

    async def clear_all_reactions(self):
        """Clear all emojis from a message."""
        await self._client.http.clear_reactions(self.channel.id, self.id)

    async def pin(self):
        """Pin message"""
        await self._client.http.pin_message(self._channel_id, self.id)
        self.pinned = True

    async def unpin(self):
        """Unpin message"""
        await self._client.http.unpin_message(self._channel_id, self.id)
        self.pinned = False

    async def publish(self):
        """Publish this message. (Discord api calls it "crosspost")"""
        await self._client.http.crosspost_message(self._channel_id, self.id)


def process_allowed_mentions(allowed_mentions: Optional[Union[AllowedMentions, dict]]) -> Optional[dict]:
    """
    Process allowed mentions into a dictionary

    Args:
        allowed_mentions: Allowed mentions object or dictionary

    Returns:
        Dictionary of allowed mentions

    Raises:
        ValueError: Invalid allowed mentions
    """
    if not allowed_mentions:
        return allowed_mentions

    if isinstance(allowed_mentions, dict):
        return allowed_mentions

    if isinstance(allowed_mentions, AllowedMentions):
        return allowed_mentions.to_dict()

    raise ValueError(f"Invalid allowed mentions: {allowed_mentions}")


def process_message_reference(
    message_reference: Optional[Union[MessageReference, Message, dict, "Snowflake_Type"]]
) -> Optional[dict]:
    """
    Process mention references into a dictionary

    Args:
        message_reference: Message reference object

    Returns:
        Message reference dictionary

    Raises:
        ValueError: Invalid message reference
    """
    if not message_reference:
        return message_reference

    if isinstance(message_reference, dict):
        return message_reference

    if isinstance(message_reference, (str, int)):
        message_reference = MessageReference(message_id=message_reference)

    if isinstance(message_reference, Message):
        message_reference = MessageReference.for_message(message_reference)

    if isinstance(message_reference, MessageReference):
        return message_reference.to_dict()

    raise ValueError(f"Invalid message reference: {message_reference}")


def process_message_payload(
    content: Optional[str] = None,
    embeds: Optional[Union[List[Union[Embed, dict]], Union[Embed, dict]]] = None,
    components: Optional[
        Union[List[List[Union[BaseComponent, dict]]], List[Union[BaseComponent, dict]], BaseComponent, dict]
    ] = None,
    stickers: Optional[Union[List[Union["Sticker", "Snowflake_Type"]], "Sticker", "Snowflake_Type"]] = None,
    allowed_mentions: Optional[Union[AllowedMentions, dict]] = None,
    reply_to: Optional[Union[MessageReference, Message, dict, "Snowflake_Type"]] = None,
    attachments: Optional[List[Union[Attachment, dict]]] = None,
    file: Optional[Union["File", "IOBase", "Path", str]] = None,
    tts: bool = False,
    flags: Optional[Union[int, MessageFlags]] = None,
) -> Union[Dict, FormData]:
    """
    Format message content for it to be ready to send discord.

    Args:
        content: Message text content.
        embeds: Embedded rich content (up to 6000 characters).
        components: The components to include with the message.
        stickers: IDs of up to 3 stickers in the server to send in the message.
        allowed_mentions: Allowed mentions for the message.
        reply_to: Message to reference, must be from the same channel.
        attachments: The attachments to keep, only used when editing message.
        file: Location of file to send, defaults to None.
        tts: Should this message use Text To Speech.
        flags: Message flags to apply.

    Returns:
        Dictionary or multipart data form.
    """
    content = content
    embeds = process_embeds(embeds)
    if isinstance(embeds, list):
        embeds = embeds if all(e is not None for e in embeds) else None

    components = process_components(components)
    if stickers:
        stickers = [to_snowflake(sticker) for sticker in stickers]
    allowed_mentions = process_allowed_mentions(allowed_mentions)
    message_reference = process_message_reference(reply_to)
    if attachments:
        attachments = [attachment.to_dict() for attachment in attachments]

    message_data = dict_filter_none(
        dict(
            content=content,
            embeds=embeds,
            components=components,
            sticker_ids=stickers,
            allowed_mentions=allowed_mentions,
            message_reference=message_reference,
            attachments=attachments,
            tts=tts,
            flags=flags,
        )
    )

    if file:
        # We need to use multipart/form-data for file sending here.
        form = FormData()
        form.add_field("payload_json", OverriddenJson.dumps(message_data))
        if isinstance(file, File):
            if isinstance(file.file, IOBase):
                form.add_field("file", file.file, filename=file.file_name)
            else:
                form.add_field("file", open(str(file.file), "rb"), filename=file.file_name)
        elif isinstance(file, IOBase):
            form.add_field("file", file)
        else:
            form.add_field("file", open(str(file), "rb"))
        return form
    else:
        return message_data
