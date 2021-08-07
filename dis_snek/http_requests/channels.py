from typing import List, Dict, Any, Optional, Union

from dis_snek.models.route import Route
from dis_snek.models.snowflake import Snowflake_Type


class ChannelRequests:
    request: Any

    async def get_message(self, channel_id: Snowflake_Type, message_id: Snowflake_Type) -> dict:
        """
        Get a specific message in the channel. Returns a message object on success.

        :param channel_id: the channel this message belongs to
        :param message_id: the id of the message
        :return: message or None
        """
        return await self.request(Route("GET", f"/channels/{channel_id}/messages/{message_id}"))

    async def get_channel(self, channel_id: Snowflake_Type) -> dict:
        """
        Get a channel by ID. Returns a channel object. If the channel is a thread, a thread member object is included.

        :param channel_id: The id of the channel
        :return: channel
        """
        return await self.request(Route("GET", f"/channels/{channel_id}"))

    async def get_channel_messages(
        self,
        channel_id: Snowflake_Type,
        limit: int = 50,
        around: Optional[Snowflake_Type] = None,
        before: Optional[Snowflake_Type] = None,
        after: Optional[Snowflake_Type] = None,
    ) -> List[dict]:
        """
        Get the messages for a channel.

        :param channel_id: The channel to get messages from
        :param limit: How many messages to get (default 50, max 100)
        :param around: Get messages around this snowflake
        :param before: Get messages before this snowflake
        :param after: Get messages after this snowflake
        :return: List of message dicts
        """
        params: Dict[str, Union[int, str]] = {"limit": limit}

        params_used = 0

        if before:
            params_used += 1
            params["before"] = before
        if after:
            params_used += 1
            params["after"] = after
        if around:
            params_used += 1
            params["around"] = around

        if params_used > 1:
            raise ValueError("`before` `after` and `around` are mutually exclusive, only one may be passed at a time.")

        return await self.request(Route("GET", f"/channels/{channel_id}/messages"), params=params)

    async def create_guild_channel(
        self,
        guild_id: Snowflake_Type,
        name: str,
        type: int,
        topic: str = "",
        position=0,
        permission_overwrites=List,
        parent_id: Snowflake_Type = None,
        nsfw: bool = False,
        bitrate=64,
        user_limit: int = 0,
        rate_limit_per_user=0,
    ) -> Dict:
        """"""
        payload = dict(
            name=name,
            type=type,
            topic=topic,
            position=position,
            rate_limit_per_user=rate_limit_per_user,
            nsfw=nsfw,
            parent_id=parent_id,
            permission_overwrites=permission_overwrites,
        )

        if type in (2, 13):
            payload.update(
                bitrate=bitrate,
                user_limit=user_limit,
            )

        # clean up payload
        payload = {key: value for key, value in payload.items() if value is not None}
        return await self.request(Route("POST", f"/guilds/{guild_id}/channels", json=payload))

    async def move_channel(
        self,
        guild_id: Snowflake_Type,
        channel_id: Snowflake_Type,
        new_pos: int,
        parent_id: Snowflake_Type = None,
        lock_perms: bool = False,
    ) -> None:
        """
        Move a channel.

        :param guild_id: The ID of the guild this affects
        :param channel_id: The ID of the channel to move
        :param new_pos: The new position of this channel
        :param parent_id: The parent ID if needed
        :param lock_perms: Sync permissions with the new parent
        :return:
        """
        payload = dict(id=channel_id, position=new_pos, lock_permissions=lock_perms)
        if parent_id:
            payload["parent_id"] = parent_id

        return await self.request(Route("PATCH", f"/guilds/{guild_id}/channels"), json=payload)
