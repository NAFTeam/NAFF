from ast import parse
import asyncio
from dataclasses import dataclass
from functools import partial
from dis_snek.models.discord_objects import embed
from dis_snek.utils.cache import CacheProxy, CacheView
from typing import TYPE_CHECKING, AsyncIterator, Awaitable, Dict, List, Optional, Union

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
        data["user_id"] = client.cache.place_user_data(user_data).id
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
    content: str = attr.ib()
    timestamp: Timestamp = attr.ib(converter=Timestamp.fromisoformat)
    edited_timestamp: Optional[Timestamp] = attr.ib(default=None, converter=optional_c(Timestamp.fromisoformat))
    tts: bool = attr.ib(default=False)
    mention_everyone: bool = attr.ib(default=False)
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
    interaction: Optional[CommandTypes] = attr.ib(default=None)  # TODO: This should be a message interaction object
    thread: Optional[Thread] = attr.ib(default=None)  # TODO: Validation
    components: Optional[List[ComponentTypes]] = attr.ib(default=None)  # TODO: This should be a component object
    sticker_items: Optional[List[PartialSticker]] = attr.ib(
        default=None
    )  # TODO: Perhaps automatically get the full sticker data.

    _author_id: Snowflake_Type = attr.ib()  # TODO: create override for detecting PartialMember
    _mention_ids: List[Snowflake_Type] = attr.ib(factory=list)
    _mention_roles: List[Snowflake_Type] = attr.ib(factory=list)
    _referenced_message_id: Optional[Snowflake_Type] = attr.ib(default=None)

    @classmethod
    def process_dict(cls, data: dict, client: "Snake") -> dict:
        # TODO: Is there a way to dynamically do this instead of hard coding?

        author_data = data.pop("author")
        if "guild_id" in data and "member" in data:
            author_data["member"] = data.pop("member")
            data["author_id"] = client.cache.place_member_data(data["guild_id"], author_data).id
        else:
            data["author_id"] = client.cache.place_user_data(author_data).id

        mention_ids = []
        for user_data in data.pop("mentions"):
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
        for attachment_data in data["attachments"]:
            attachments.append(Attachment.from_dict(attachment_data, client))
        data["attachments"] = attachments

        embeds = []
        for embed_data in data["embeds"]:
            embeds.append(Embed.from_dict(embed_data))
        data["embeds"] = embeds

        if "reactions" in data:
            reactions = []
            for reaction_data in data["reactions"]:
                reactions.append(Reaction.from_dict(reaction_data, client))
            data["reactions"] = reactions

        # TODO: Convert to application object

        ref_message_data = data.pop("referenced_message", None)
        if ref_message_data:
            data["referenced_message_id"] = client.cache.place_message_data(ref_message_data)

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

    @property
    def author(self) -> Union[CacheProxy, Awaitable[Union["Member", "User"]], Union["Member", "User"]]:
        if self.guild_id:
            return CacheProxy(id=self._author_id, method=partial(self._client.cache.get_member, self.guild_id))
        else:
            return CacheProxy(id=self._author_id, method=self._client.cache.get_user)

    @property
    def mentions(
        self,
    ) -> Union[
        CacheView, Awaitable[Dict[Snowflake_Type, Union["Member", "User"]]], AsyncIterator[Union["Member", "User"]]
    ]:
        if self.guild_id:
            return CacheView(ids=self._mention_ids, method=partial(self._client.cache.get_member, self.guild_id))
        else:
            return CacheView(ids=self._mention_ids, method=self._client.cache.get_user)

    @property
    def mention_roles(self) -> Union[CacheView, Awaitable[Dict[Snowflake_Type, "Role"]], AsyncIterator["Role"]]:
        return CacheView(ids=self._mention_roles, method=self._client.cache.get_role)

    @property
    def referenced_message(self) -> Optional[Union[CacheProxy, Awaitable["Message"], "Message"]]:
        if self._referenced_message_id:
            return CacheProxy(id=self._referenced_message_id, method=partial(self._client.cache.get_message, self.channel_id))
        # TODO should we return an awaitable None, or just None.

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
