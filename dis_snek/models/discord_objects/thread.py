from typing import TYPE_CHECKING, List, Dict, Any, Union

from attr.converters import optional

from dis_snek.mixins.send import SendMixin
from dis_snek.models.discord import DiscordObject, ClientObject
from dis_snek.models.snowflake import to_snowflake
from dis_snek.models.timestamp import Timestamp
from dis_snek.utils.attr_utils import define, field
from dis_snek.utils.converters import timestamp_converter

if TYPE_CHECKING:
    from aiohttp import FormData

    from dis_snek.client import Snake
    from dis_snek.models.discord_objects.user import User
    from dis_snek.models.discord_objects.channel import TYPE_THREAD_CHANNEL
    from dis_snek.models.snowflake import Snowflake_Type


@define()
class ThreadMember(DiscordObject, SendMixin):
    """A thread member is used to indicate whether a user has joined a thread or not."""

    join_timestamp: Timestamp = field(converter=timestamp_converter)
    """The time the current user last joined the thread."""
    flags: int = field()
    """Any user-thread settings, currently only used for notifications."""

    _user_id: "Snowflake_Type" = field(converter=optional(to_snowflake))

    async def get_thread(self) -> "TYPE_THREAD_CHANNEL":
        """
        Gets the thread associated with with this member.

        Returns:
            The thread in question
        """
        return await self._client.get_channel(self.id)

    async def get_user(self) -> "User":
        """
        Get the user associated with this thread member.

        Returns:
            The user object
        """
        return await self._client.get_user(self._user_id)

    async def _send_http_request(self, message_payload: Union[dict, "FormData"]) -> dict:
        dm_id = await self._client.cache.get_dm_channel_id(self._user_id)
        return await self._client.http.create_message(message_payload, dm_id)


@define
class ThreadList(ClientObject):
    """Represents a list of one or more threads."""

    threads: List["TYPE_THREAD_CHANNEL"] = field(factory=list)  # TODO Reference the cache or store actual object?
    """The active threads."""
    members: List[ThreadMember] = field(factory=list)
    """A thread member object for each returned thread the current user has joined."""
    has_more: bool = field(default=False)
    """Whether there are potentially additional threads that could be returned on a subsequent call."""

    @classmethod
    def _process_dict(cls, data: Dict[str, Any], client: "Snake") -> Dict[str, Any]:
        threads = []
        for thread_data in data["threads"]:
            threads.append(client.cache.place_channel_data(thread_data))
        data["threads"] = threads

        members = []
        for member_data in data["members"]:
            members.append(ThreadMember.from_dict(member_data, client))
        data["members"] = threads

        return data
