from typing import TYPE_CHECKING, List, Dict, Any, Optional, Union, Awaitable

from dis_snek.mixins.send import SendMixin
from dis_snek.models.discord import DiscordObject
from dis_snek.models.timestamp import Timestamp
from dis_snek.utils.attr_utils import define, field
from dis_snek.utils.converters import timestamp_converter
from dis_snek.utils.proxy import CacheProxy
from dis_snek.models.snowflake import to_snowflake

if TYPE_CHECKING:
    from aiohttp import FormData

    from dis_snek.client import Snake
    from dis_snek.models.discord_objects.user import User
    from dis_snek.models.discord_objects.channel import ThreadChannel
    from dis_snek.models.snowflake import Snowflake_Type


@define()
class ThreadMember(DiscordObject, SendMixin):
    join_timestamp: Timestamp = field(converter=timestamp_converter)

    flags: int = field()
    _user_id: "Snowflake_Type" = field(converter=to_snowflake)

    @property
    def thread(self) -> Optional[Union[CacheProxy, Awaitable["ThreadChannel"], "ThreadChannel"]]:
        return CacheProxy(id=self.id, method=self._client.cache.get_channel)

    @property
    def user(self) -> Optional[Union[CacheProxy, Awaitable["User"], "User"]]:
        return CacheProxy(id=self.user_id, method=self._client.cache.get_user)

    async def _send_http_request(self, message_payload: Union[dict, "FormData"]) -> dict:
        dm_id = await self._client.cache.get_dm_channel_id(self._user_id)
        return await self._client.http.create_message(message_payload, dm_id)


@define
class ThreadList(DiscordObject):
    threads: List["ThreadChannel"] = field(factory=list)  # TODO Reference the cache or store actual object?
    members: List[ThreadMember] = field(factory=list)
    has_more: bool = field(default=False)

    @classmethod
    def process_dict(cls, data: Dict[str, Any], client: "Snake") -> Dict[str, Any]:
        threads = []
        for thread_data in data["threads"]:
            threads.append(client.cache.place_channel_data(thread_data))
        data["threads"] = threads

        members = []
        for member_data in data["members"]:
            members.append(ThreadMember.from_dict(member_data, client))
        data["members"] = threads

        return data
