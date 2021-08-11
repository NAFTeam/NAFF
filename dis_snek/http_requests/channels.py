from typing import Any, Dict, List, Optional, Union

from dis_snek.models.route import Route
from dis_snek.models.snowflake import Snowflake_Type


class ChannelRequests:
    request: Any

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
        reason: str = None,
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
        return await self.request(Route("POST", f"/guilds/{guild_id}/channels"), json=payload, reason=reason)

    async def move_channel(
        self,
        guild_id: Snowflake_Type,
        channel_id: Snowflake_Type,
        new_pos: int,
        parent_id: Snowflake_Type = None,
        lock_perms: bool = False,
        reason: str = None,
    ) -> None:
        """
        Move a channel.

        :param guild_id: The ID of the guild this affects
        :param channel_id: The ID of the channel to move
        :param new_pos: The new position of this channel
        :param parent_id: The parent ID if needed
        :param lock_perms: Sync permissions with the new parent
        :param reason: An optional reason for the audit log
        :return:
        """
        payload = dict(id=channel_id, position=new_pos, lock_permissions=lock_perms)
        if parent_id:
            payload["parent_id"] = parent_id

        return await self.request(Route("PATCH", f"/guilds/{guild_id}/channels"), json=payload, reason=reason)

    async def modify_channel(self, channel_id: Snowflake_Type, data: dict, reason: str = None) -> dict:
        """
        Update a channel's settings, returns the updated channel object on success.

        :param channel_id: The ID of the channel to update
        :param data: The data to update with
        :param reason: An optional reason for the audit log
        :return: Channel object on success
        """
        return await self.request(Route("PATCH", f"channels/{channel_id}"), json=data, reason=reason)

    async def delete_channel(self, channel_id: Snowflake_Type, reason: str = None):
        """
        Delete the channel
        :param channel_id: The ID of the channel to delete
        :param reason: An optional reason for the audit log
        """
        return await self.request(Route("DELETE", f"channels/{channel_id}"), reason=reason)

    async def get_channel_invites(self, channel_id: Snowflake_Type) -> List[dict]:
        """
        Get the invites for the channel.

        :param channel_id: The ID of the channel to retrieve from
        :return: List of invite objects
        """
        return await self.request(Route("GET", f"/channels/{channel_id}/invites"))

    async def create_channel_invite(
        self,
        channel_id: Snowflake_Type,
        max_age: int = 86400,
        max_uses: int = 0,
        temporary: bool = False,
        unique: bool = False,
        target_type: int = None,
        target_user_id: Snowflake_Type = None,
        target_application_id: Snowflake_Type = None,
        reason: str = None,
    ) -> dict:
        """
        Create an invite for the given channel.

        :param channel_id: The ID of the channel to create an invite for
        :param max_age: duration of invite in seconds before expiry, or 0 for never. between 0 and 604800 (7 days) (default 24 hours)
        :param max_uses: max number of uses or 0 for unlimited. between 0 and 100
        :param temporary: whether this invite only grants temporary membership
        :param unique: if true, don't try to reuse a similar invite (useful for creating many unique one time use invites)
        :param target_type: the type of target for this voice channel invite
        :param target_user_id: the id of the user whose stream to display for this invite, required if target_type is 1, the user must be streaming in the channel
        :param target_application_id: the id of the embedded application to open for this invite, required if target_type is 2, the application must have the EMBEDDED flag
        :param reason: An optional reason for the audit log
        :return: an invite object
        """
        payload = dict(max_age=max_age, max_uses=max_uses, temporary=temporary, unique=unique)
        if target_type:
            payload["target_type"] = target_type
        if target_user_id:
            payload["target_user_id"] = target_user_id
        if target_application_id:
            payload["target_application_id"] = target_application_id

        return await self.request(Route("POST", f"channels/{channel_id}/invites"), json=payload, reason=reason)

    async def delete_channel_permission(
        self, channel_id: Snowflake_Type, overwrite_id: int, reason: str = None
    ) -> None:
        """
        Delete a channel permission overwrite for a user or role in a channel.

        :param channel_id: The ID of the channel.
        :param overwrite_id: The ID of the overwrite
        :param reason: An optional reason for the audit log
        """
        return await self.request(Route("DELETE", f"/channels/{channel_id}/{overwrite_id}"), reason=reason)

    async def follow_news_channel(self, channel_id: Snowflake_Type, webhook_channel_id: Snowflake_Type) -> dict:
        """
        Follow a news channel to send messages to the target channel.

        :param channel_id: The channel to follow
        :param webhook_channel_id: ID of the target channel
        :return: Followed channel object
        """
        return await self.request(
            Route("POST", f"/channels/{channel_id}/followers"), json={"webhook_channel_id": webhook_channel_id}
        )

    async def trigger_typing_indicator(self, channel_id: Snowflake_Type) -> None:
        """
        Post a typing indicator for the specified channel. Generally bots should not implement this route.

        :param channel_id: The id of the channel to "type" in
        """
        return await self.request(Route("POST", f"/channels/{channel_id}/typing"))

    async def get_pinned_messages(self, channel_id: Snowflake_Type) -> List[dict]:
        """
        Get all pinned messages from a channel.
        :param channel_id: The ID of the channel to get pins from
        :return: A list of pinned message objects
        """
        return await self.request(Route("GET", f"/channels/{channel_id}/pins"))
