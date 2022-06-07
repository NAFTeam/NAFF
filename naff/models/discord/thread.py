from typing import TYPE_CHECKING, List, Dict, Any, Union, Optional

import naff.models as models
from naff.client.const import MISSING
from naff.client.mixins.send import SendMixin
from naff.client.utils.attr_converters import optional
from naff.client.utils.attr_converters import timestamp_converter
from naff.client.utils.attr_utils import define, field
from naff.models.discord.emoji import PartialEmoji
from naff.models.discord.snowflake import to_snowflake
from naff.models.discord.timestamp import Timestamp
from .base import DiscordObject, ClientObject

if TYPE_CHECKING:
    from aiohttp import FormData

    from naff.client import Client
    from naff.models.discord.user import User
    from naff.models.discord.channel import TYPE_THREAD_CHANNEL
    from naff.models.discord.snowflake import Snowflake_Type
    from naff import UPLOADABLE_TYPE, GuildForum

__all__ = (
    "ThreadMember",
    "ThreadList",
    "ThreadTag",
)


@define()
class ThreadMember(DiscordObject, SendMixin):
    """A thread member is used to indicate whether a user has joined a thread or not."""

    join_timestamp: Timestamp = field(converter=timestamp_converter)
    """The time the current user last joined the thread."""
    flags: int = field()
    """Any user-thread settings, currently only used for notifications."""

    _user_id: "Snowflake_Type" = field(converter=optional(to_snowflake))

    async def fetch_thread(self) -> "TYPE_THREAD_CHANNEL":
        """
        Fetches the thread associated with with this member.

        Returns:
            The thread in question

        """
        return await self._client.cache.fetch_channel(self.id)

    def get_thread(self) -> "TYPE_THREAD_CHANNEL":
        """
        Gets the thread associated with with this member.

        Returns:
            The thread in question

        """
        return self._client.cache.get_channel(self.id)

    async def fetch_user(self) -> "User":
        """
        Fetch the user associated with this thread member.

        Returns:
            The user object

        """
        return await self._client.cache.fetch_user(self._user_id)

    def get_user(self) -> "User":
        """
        Get the user associated with this thread member.

        Returns:
            The user object

        """
        return self._client.cache.get_user(self._user_id)

    async def _send_http_request(
        self, message_payload: Union[dict, "FormData"], files: list["UPLOADABLE_TYPE"] | None = None
    ) -> dict:
        dm_id = await self._client.cache.fetch_dm_channel_id(self._user_id)
        return await self._client.http.create_message(message_payload, dm_id, files=files)


@define()
class ThreadList(ClientObject):
    """Represents a list of one or more threads."""

    threads: List["TYPE_THREAD_CHANNEL"] = field(factory=list)  # TODO Reference the cache or store actual object?
    """The active threads."""
    members: List[ThreadMember] = field(factory=list)
    """A thread member object for each returned thread the current user has joined."""
    has_more: bool = field(default=False)
    """Whether there are potentially additional threads that could be returned on a subsequent call."""

    @classmethod
    def _process_dict(cls, data: Dict[str, Any], client: "Client") -> Dict[str, Any]:
        threads = []
        for thread_data in data["threads"]:
            threads.append(client.cache.place_channel_data(thread_data))
        data["threads"] = threads

        data["members"] = ThreadMember.from_list(data["members"], client)

        return data


@define()
class ThreadTag(DiscordObject):
    name: str = field()
    emoji_id: "Snowflake_Type" = field(default=None)
    emoji_name: str | None = field(default=None)

    _parent_channel_id: "Snowflake_Type" = field(default=MISSING)

    @property
    def parent_channel(self) -> "GuildForum":
        """The parent forum for this tag."""
        return self._client.get_channel(self._parent_channel_id)

    async def edit(
        self, *, name: Optional[str] = None, emoji: Union["models.PartialEmoji", dict, str, None] = None
    ) -> "ThreadTag":
        """
        Edit this tag

        Args:
            name: The name for this tag
            emoji: The emoji for this tag

        Returns:
            This object
        """
        if isinstance(emoji, str):
            emoji = PartialEmoji.from_str(emoji)
        elif isinstance(emoji, dict):
            emoji = PartialEmoji.from_dict(emoji)

        if emoji.id:
            data = await self._client.http.edit_tag(self._parent_channel_id, self.id, name, emoji_id=emoji.id)
        else:
            data = await self._client.http.edit_tag(self._parent_channel_id, self.id, name, emoji_name=emoji.name)

        self._client.cache.place_channel_data(data)

        for tag in data["available_tags"]:
            if tag.id == self.id:
                self.name = tag.name
                self.emoji_id = tag.emoji_id
                self.emoji_name = tag.emoji_name
                break

        return self

    async def delete(self) -> None:
        """Delete this tag."""
        data = await self._client.http.delete_tag(self._parent_channel_id, self.id)
        self._client.cache.place_channel_data(data)
