from ast import parse
import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, List, Optional, Union

import attr
from attr.converters import optional as optional_c

from dis_snek.mixins.edit import EditMixin
from dis_snek.models.discord_objects.application import Application
from dis_snek.models.discord_objects.channel import Thread
from dis_snek.models.discord_objects.components import ComponentTypes
from dis_snek.models.discord_objects.embed import Embed
from dis_snek.models.discord_objects.emoji import Emoji
from dis_snek.models.discord_objects.interactions import CommandTypes
from dis_snek.models.discord_objects.reaction import Reaction
from dis_snek.models.discord_objects.role import Role
from dis_snek.models.discord_objects.sticker import Sticker
from dis_snek.models.discord_objects.user import BaseUser, Member, User
from dis_snek.models.enums import (
    ChannelTypes,
    MentionTypes,
    MessageActivityTypes,
    MessageFlags,
    MessageTypes,
)
from dis_snek.models.snowflake import Snowflake, Snowflake_Type
from dis_snek.models.timestamp import Timestamp
from dis_snek.utils.attr_utils import DictSerializationMixin

if TYPE_CHECKING:
    from dis_snek.client import Snake


@attr.s(slots=True, kw_only=True)
class Attachment(Snowflake, DictSerializationMixin):
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


@attr.s(slots=True, kw_only=True)
class ChannelMention(Snowflake, DictSerializationMixin):
    guild_id: Snowflake_Type = attr.ib()
    type: ChannelTypes = attr.ib(converter=ChannelTypes)
    name: str = attr.ib()


@dataclass
class MessageActivity:
    type: MessageActivityTypes
    party_id: str = None


class MessageReference:  # todo refactor into actual class, add pointers to actual message, channel, guild objects
    message_id: Optional[int] = None
    channel_id: Optional[int] = None
    guild_id: Optional[int] = None
    fail_if_not_exists: bool = True


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
            if isinstance(role, Snowflake):
                role = role.id
            self.roles.append(role)

    def add_users(self, *users: Union[Member, BaseUser, Snowflake_Type]):
        for user in users:
            if isinstance(user, Snowflake):
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


@attr.s(slots=True, kw_only=True)
class Message(Snowflake, DictSerializationMixin, EditMixin):
    _client: "Snake" = attr.ib(repr=False)
    channel_id: Snowflake_Type = attr.ib()
    guild_id: Optional[Snowflake_Type] = attr.ib(default=None)
    author: Union[Member, User] = attr.ib()  # TODO: create override for detecting PartialMember
    content: str = attr.ib()
    timestamp: Timestamp = attr.ib(converter=Timestamp.fromisoformat)
    edited_timestamp: Optional[Timestamp] = attr.ib(default=None, converter=optional_c(Timestamp.fromisoformat))
    tts: bool = attr.ib(default=False)
    mention_everyone: bool = attr.ib(default=False)
    mentions: List[Member] = attr.ib(factory=list)
    mention_roles: List[Role] = attr.ib(factory=list)
    mention_channels: Optional[List[ChannelMention]] = attr.ib(default=None)
    attachments: List["Attachment"] = attr.ib(factory=list)
    embeds: List[Embed] = attr.ib(factory=list)
    reactions: Optional[List[Reaction]] = attr.ib(default=None)
    nonce: Optional[Union[int, str]] = attr.ib(default=None)
    pinned: bool = attr.ib(default=False)
    webhook_id: Optional[Snowflake_Type] = attr.ib(default=None)
    type: MessageTypes = attr.ib(converter=MessageTypes)
    activity: Optional[MessageActivity] = attr.ib(default=None, converter=optional_c(MessageActivity))
    application: Optional[Application] = attr.ib(default=None)  # TODO: partial application
    application_id: Optional[Snowflake_Type] = attr.ib(default=None)
    message_reference: Optional[MessageReference] = attr.ib(default=None)
    flags: Optional[MessageFlags] = attr.ib(default=None, converter=optional_c(MessageFlags))
    referenced_message: Optional["Message"] = attr.ib(default=None)
    interaction: Optional[CommandTypes] = attr.ib(default=None)
    thread: Optional[Thread] = attr.ib(default=None)  # TODO: Validation
    components: Optional[List[ComponentTypes]] = attr.ib(default=None)
    sticker_items: Optional[List[Sticker]] = attr.ib(default=None)  # TODO: StickerItem -> Sticker

    # @classmethod
    # def process_dict(cls, data, client):
    #     roles_data = data.pop("mention_roles")
    #     roles = []
    #     for role_data in roles_data:
    #         role_id = role_data["id"]
    #         role = client.cache.get_role(data["guild_id"], role_id)
    #         roles.append(role)
    #     data["mention_roles"] = roles
    #
    #     mentions_data = data.pop("mentions")
    #     mentions = []
    #     for mention_data in mentions_data:
    #         member_id = mention_data["id"]
    #         member = client.cache.get_member(data["guild_id"], member_id)
    #     return data

    async def add_reaction(self, emoji: Union[Emoji, str]):
        """
        Add a reaction to this message.

        :param emoji: the emoji to react with
        """
        if isinstance(emoji, Emoji):
            emoji = emoji.req_format

        await self._client.http.create_reaction(self.channel_id, self.id, emoji)

    async def clear_reaction(self, emoji: Union[Emoji, str]):
        """
        Clear a specific reaction from message

        :param emoji: The emoji to clear
        """
        if isinstance(emoji, Emoji):
            emoji = emoji.req_format

        await self._client.http.clear_reaction(self.channel_id, self.id, emoji)

    async def remove_reaction(self, emoji: Union[Emoji, str], member: Union[Member, Snowflake_Type]):
        """
        Remove a specific reaction that a user reacted with

        :param emoji: Emoji to remove
        :param member: Member to remove reaction of
        """
        if isinstance(emoji, Emoji):
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
