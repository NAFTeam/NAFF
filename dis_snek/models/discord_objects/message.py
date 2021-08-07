from dataclasses import dataclass
from datetime import datetime
from typing import Any
from typing import List
from typing import Optional
from typing import Union

import attr
from attr.converters import optional as optional_c

from dis_snek.models.discord_objects.application import Application
from dis_snek.models.discord_objects.channel import Thread
from dis_snek.models.discord_objects.components import ComponentType
from dis_snek.models.discord_objects.embed import Embed
from dis_snek.models.discord_objects.emoji import Emoji
from dis_snek.models.discord_objects.interactions import InteractionType
from dis_snek.models.discord_objects.reaction import Reaction
from dis_snek.models.discord_objects.role import Role
from dis_snek.models.discord_objects.sticker import Sticker
from dis_snek.models.discord_objects.user import Member
from dis_snek.models.discord_objects.user import User
from dis_snek.models.enums import MessageActivityTypes, ChannelTypes
from dis_snek.models.enums import MessageFlags
from dis_snek.models.enums import MessageTypes
from dis_snek.models.snowflake import Snowflake
from dis_snek.models.snowflake import Snowflake_Type
from dis_snek.models.timestamp import Timestamp
from dis_snek.utils.attr_utils import DictSerializationMixin


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


@attr.s(slots=True, kw_only=True)
class Message(Snowflake, DictSerializationMixin):
    _client: Any = attr.ib(repr=False)
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
    interaction: Optional[InteractionType] = attr.ib(default=None)
    thread: Optional[Thread] = attr.ib(default=None)  # TODO: Validation
    components: Optional[List[ComponentType]] = attr.ib(default=None)
    sticker_items: Optional[List[Sticker]] = attr.ib(default=None)  # TODO: StickerItem -> Sticker

    async def add_reaction(self, emoji: Union[Emoji, str]):
        """
        Add a reaction to this message.

        :param emoji: the emoji to react with
        """
        if isinstance(emoji, Emoji):
            emoji = emoji.req_format

        await self._client.http.create_reaction(self.channel_id, self.id, emoji)
