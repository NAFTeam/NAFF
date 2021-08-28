from ast import parse
import asyncio
from dataclasses import dataclass
from dis_snek.utils.cache import CacheProxy
from typing import TYPE_CHECKING, Awaitable, List, Optional, Union

import attr
from attr.converters import optional as optional_c

from dis_snek.mixins.edit import EditMixin
from dis_snek.models.discord_objects import components
from dis_snek.models.discord_objects.application import Application
from dis_snek.models.discord_objects.channel import Thread
from dis_snek.models.discord_objects.components import BaseComponent, ComponentTypes
from dis_snek.models.discord_objects.embed import Embed
from dis_snek.models.discord_objects.emoji import Emoji, PartialEmoji
from dis_snek.models.discord_objects.interactions import CommandTypes
from dis_snek.models.discord_objects.reaction import Reaction
from dis_snek.models.discord_objects.role import Role
from dis_snek.models.discord_objects.sticker import PartialSticker, Sticker
from dis_snek.models.discord_objects.user import BaseUser, Member, User
from dis_snek.models.enums import (
    ChannelTypes,
    InteractionTypes,
    MentionTypes,
    MessageActivityTypes,
    MessageFlags,
    MessageTypes,
)
from dis_snek.models.snowflake import Snowflake_Type
from dis_snek.models.timestamp import Timestamp
from dis_snek.models.base_object import DiscordObject
from dis_snek.utils.attr_utils import define, field

if TYPE_CHECKING:
    from dis_snek.client import Snake


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
    def size(self):
        return self.height, self.width


@define()
class ChannelMention(DiscordObject):
    guild_id: Snowflake_Type = attr.ib()
    type: ChannelTypes = attr.ib(converter=ChannelTypes)
    name: str = attr.ib()


@dataclass
class MessageActivity:
    type: MessageActivityTypes
    party_id: str = None


@attr.s(slots=True)
class MessageReference:
    # Add pointers to actual message, channel, guild objects
    message_id: Optional[int] = attr.ib(default=None)
    channel_id: Optional[int] = attr.ib(default=None)
    guild_id: Optional[int] = attr.ib(default=None)
    fail_if_not_exists: bool = attr.ib(default=True)


@define
class MesssageInteraction(DiscordObject):
    _user_id: Snowflake_Type = attr.ib()
    type: InteractionTypes = attr.ib(converter=InteractionTypes)
    name: str = attr.ib()

    @classmethod
    def process_dict(cls, data, client):
        user_data = data["user"]
        data["user_id"] = user_data["id"]
        client.cache.place_user_data(user_data["id"], user_data)
        return data

    @property
    def user(self) -> Union[CacheProxy, Awaitable["User"], "User"]:
        return CacheProxy(id=self._user_id, method=self._client.cache.get_user)


@attr.s(slots=True)
class AllowedMentions:
    """
    The allowed mention field allows for more granular control over mentions without various hacks to the message content.
    This will always validate against message content to avoid phantom pings, and check against user/bot permissions.

    :param parse: An array of allowed mention types to parse from the content.
    :param roles: Array of role_ids to mention. (Max size of 100)
    :param users: Array of user_ids to mention. (Max size of 100)
    :param replied_user: For replies, whether to mention the author of the message being replied to. (default false)
    """

    parse: Optional[List[str]] = attr.ib(factory=list)
    roles: Optional[List[Snowflake_Type]] = attr.ib(factory=list)
    users: Optional[List[Snowflake_Type]] = attr.ib(factory=list)
    replied_user = attr.ib(default=False)

    def add_roles(self, *roles: Union[Role, Snowflake_Type]):
        for role in roles:
            if isinstance(role, DiscordObject):
                role = role.id
            self.roles.append(role)

    def add_users(self, *users: Union[Member, BaseUser, Snowflake_Type]):
        for user in users:
            if isinstance(user, DiscordObject):
                user = user.id
            self.users.append(user)

    def to_dict(self) -> dict:
        return attr.asdict(self, filter=lambda key, value: isinstance(value, bool) or value)

    @classmethod
    def all(cls):
        return cls(parse=list(MentionTypes.__members__.values()), replied_user=True)

    @classmethod
    def none(cls):
        return cls()


@define()
class Message(DiscordObject, EditMixin):
    channel_id: Snowflake_Type = attr.ib()
    guild_id: Optional[Snowflake_Type] = attr.ib(default=None)
    author: Union[Member, User] = attr.ib()  # TODO: create override for detecting PartialMember
    content: str = attr.ib()
    timestamp: Timestamp = attr.ib(converter=Timestamp.fromisoformat)
    edited_timestamp: Optional[Timestamp] = attr.ib(default=None, converter=optional_c(Timestamp.fromisoformat))
    tts: bool = attr.ib(default=False)
    mention_everyone: bool = attr.ib(default=False)
    mentions: List[Union[Member, User]] = attr.ib(factory=list)
    mention_roles: List[Snowflake_Type] = attr.ib(factory=list)  # TODO: Perhaps automatically get the role data.
    mention_channels: Optional[List[ChannelMention]] = attr.ib(default=None)
    attachments: List[Attachment] = attr.ib(factory=list)
    embeds: List[Embed] = attr.ib(factory=list)
    reactions: List[Reaction] = attr.ib(factory=list)
    nonce: Optional[Union[int, str]] = attr.ib(default=None)
    pinned: bool = attr.ib(default=False)
    webhook_id: Optional[Snowflake_Type] = attr.ib(default=None)
    type: MessageTypes = attr.ib(converter=MessageTypes)
    activity: Optional[MessageActivity] = attr.ib(default=None, converter=optional_c(MessageActivity))
    application: Optional[Application] = attr.ib(default=None)  # TODO: partial application
    application_id: Optional[Snowflake_Type] = attr.ib(default=None)
    message_reference: Optional[MessageReference] = attr.ib(default=None, converter=optional_c(MessageReference))
    flags: Optional[MessageFlags] = attr.ib(default=None, converter=optional_c(MessageFlags))
    referenced_message: Optional["Message"] = attr.ib(default=None)
    interaction: Optional[CommandTypes] = attr.ib(default=None)  # TODO: This should be a message interaction object
    thread: Optional[Thread] = attr.ib(default=None)  # TODO: Validation
    components: Optional[List[ComponentTypes]] = attr.ib(default=None)  # TODO: This should be a component object
    sticker_items: Optional[List[PartialSticker]] = attr.ib(default=None)  # TODO: Perhaps automatically get the full sticker data.

    @classmethod
    def process_dict(cls, data: dict, client: "Snake") -> dict:
        # TODO: Is there a way to dynamically do this instead of hard coding?

        if "member" in data:
            author_data = data["author"]
            author_data["member"] = data["member"]
            author_data["member"]["guild_id"] = data["guild_id"]
            data["author"] = Member.from_dict(author_data, client)
        else:
            data["author"] = User.from_dict(data["author"], client)

        mentions = []
        for user_data in data["mentions"]:
            if "member" in user_data:
                user_data["member"]["guild_id"] = data["guild_id"]
                mentions.append(Member.from_dict(user_data, client))
            else:
                mentions.append(User.from_dict(user_data, client))
        data["mentions"] = mentions

        if "mention_channels" in data:
            mention_channels = []
            for channel_data in data["mention_channels"]:
                mention_channels.append(ChannelMention.from_dict(channel_data, client))

        attachments = []
        for attachment_data in data["attachments"]:
            attachments.append(Attachment.from_dict(attachment_data, client))
        data["attachments"] = attachments

        # TODO: Convert to embed objects

        if "reactions" in data:
            reactions = []
            for reaction_data in data["reactions"]:
                reactions.append(Reaction.from_dict(reaction_data, client))
            data["reactions"] = reactions

        # TODO: Convert to application object

        if data.get("referenced_message", None):
            data["referenced_message"] = Message.from_dict(data["referenced_message"], client)

        if "interaction" in data:
            data["interaction"] = MesssageInteraction.from_dict(data["interaction"], client)

        # TODO: Convert to thread object

        if "components" in data:
            components = []
            for component_data in data["components"]:
                components.append(BaseComponent.from_dict(component_data))
            data["components"] = components

        if "sticker_items" in data:
            stickers = []
            for sticker_data in data["sticker_items"]:
                stickers.append(PartialSticker.from_dict(sticker_data, client))
            data["sticker_items"] = stickers

        return data

    async def add_reaction(self, emoji: Union[PartialEmoji, str]):
        """
        Add a reaction to this message.

        :param emoji: the emoji to react with
        """
        if issubclass(type(emoji), PartialEmoji):
            emoji = emoji.req_format

        await self._client.http.create_reaction(self.channel_id, self.id, emoji)

    async def clear_reaction(self, emoji: Union[PartialEmoji, str]):
        """
        Clear a specific reaction from message

        :param emoji: The emoji to clear
        """
        if issubclass(type(emoji), PartialEmoji):
            emoji = emoji.req_format

        await self._client.http.clear_reaction(self.channel_id, self.id, emoji)

    async def remove_reaction(self, emoji: Union[PartialEmoji, str], member: Union[Member, Snowflake_Type]):
        """
        Remove a specific reaction that a user reacted with

        :param emoji: Emoji to remove
        :param member: Member to remove reaction of
        """
        if issubclass(type(emoji), PartialEmoji):
            emoji = emoji.req_format
        if isinstance(member, Member):
            member = member.id

        await self._client.http.remove_user_reaction(self.channel_id, self.id, emoji, member)

    async def clear_reactions(self):
        """Clear all emojis from a message."""
        await self._client.http.clear_reactions(self.channel.id, self.id)

    async def delete(self, delay: int = None):
        """
        Delete message.

        :param delay: Seconds to wait before deleting message
        """
        if delay is not None and delay > 0:

            async def delayed_delete():
                await asyncio.sleep(delay)
                try:
                    await self._client.http.delete_message(self.channel_id, self.id)
                except Exception:
                    pass  # No real way to handle this

            asyncio.ensure_future(delayed_delete())

        else:
            await self._client.http.delete_message(self.channel_id, self.id)

    async def pin(self):
        """Pin message"""
        await self._client.http.pin_message(self.channel_id, self.id)

    async def unpin(self):
        """Unpin message"""
        await self._client.http.unpin_message(self.channel_id, self.id)

    def _edit_http_request(self, message) -> dict:
        return self._client.http.edit_message(message, self.channel_id, self.id)
