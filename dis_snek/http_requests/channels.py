from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from dis_snek.const import MISSING
from dis_snek.models.enums import ChannelTypes, StagePrivacyLevel
from dis_snek.models.route import Route
from dis_snek.utils.serializer import dict_filter_none, dict_filter_missing

if TYPE_CHECKING:
    from dis_snek.models.discord_objects.channel import PermissionOverwrite
    from dis_snek.models.snowflake import Snowflake_Type


class ChannelRequests:
    request: Any

    async def get_channel(self, channel_id: "Snowflake_Type") -> dict:
        """
        Get a channel by ID. Returns a channel object. If the channel is a thread, a thread member object is included.

        parameters:
            channel_id: The id of the channel
        returns:
            channel
        """
        return await self.request(Route("GET", f"/channels/{channel_id}"))

    async def get_channel_messages(
        self,
        channel_id: "Snowflake_Type",
        limit: int = 50,
        around: Optional["Snowflake_Type"] = None,
        before: Optional["Snowflake_Type"] = None,
        after: Optional["Snowflake_Type"] = None,
    ) -> List[dict]:
        """
        Get the messages for a channel.

        parameters:
            channel_id: The channel to get messages from
            limit: How many messages to get (default 50, max 100)
            around: Get messages around this snowflake
            before: Get messages before this snowflake
            after: Get messages after this snowflake

        returns:
            List of message dicts
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
        guild_id: "Snowflake_Type",
        name: str,
        channel_type: Union["ChannelTypes", int],
        topic: Optional[str] = MISSING,
        position: int = 0,
        permission_overwrites: List[Union["PermissionOverwrite", dict]] = MISSING,
        parent_id: "Snowflake_Type" = MISSING,
        nsfw: bool = False,
        bitrate: int = 64000,
        user_limit: int = 0,
        rate_limit_per_user: int = 0,
        reason: str = MISSING,
    ) -> Dict:
        """"""
        payload = dict(
            name=name,
            type=channel_type,
            topic=topic,
            position=position,
            rate_limit_per_user=rate_limit_per_user,
            nsfw=nsfw,
            parent_id=parent_id,
            permission_overwrites=permission_overwrites,
        )

        if channel_type in (2, 13):
            payload.update(
                bitrate=bitrate,
                user_limit=user_limit,
            )

        # clean up payload
        payload = dict_filter_missing(payload)
        return await self.request(Route("POST", f"/guilds/{guild_id}/channels"), data=payload, reason=reason)

    async def move_channel(
        self,
        guild_id: "Snowflake_Type",
        channel_id: "Snowflake_Type",
        new_pos: int,
        parent_id: "Snowflake_Type" = None,
        lock_perms: bool = False,
        reason: str = MISSING,
    ) -> None:
        """
        Move a channel.

        parameters:
            guild_id: The ID of the guild this affects
            channel_id: The ID of the channel to move
            new_pos: The new position of this channel
            parent_id: The parent ID if needed
            lock_perms: Sync permissions with the new parent
            reason: An optional reason for the audit log
        """
        payload = dict(id=channel_id, position=new_pos, lock_permissions=lock_perms)
        if parent_id:
            payload["parent_id"] = parent_id

        return await self.request(Route("PATCH", f"/guilds/{guild_id}/channels"), data=payload, reason=reason)

    async def modify_channel(self, channel_id: "Snowflake_Type", data: dict, reason: str = MISSING) -> dict:
        """
        Update a channel's settings, returns the updated channel object on success.

        parameters:
            channel_id: The ID of the channel to update
            data: The data to update with
            reason: An optional reason for the audit log

        returns:
            Channel object on success
        """
        return await self.request(Route("PATCH", f"/channels/{channel_id}"), data=data, reason=reason)

    async def delete_channel(self, channel_id: "Snowflake_Type", reason: str = MISSING):
        """
        Delete the channel

        parameters:
            channel_id: The ID of the channel to delete
            reason: An optional reason for the audit log
        """
        return await self.request(Route("DELETE", f"/channels/{channel_id}"), reason=reason)

    async def get_channel_invites(self, channel_id: "Snowflake_Type") -> List[dict]:
        """
        Get the invites for the channel.

        parameters:
            channel_id: The ID of the channel to retrieve from

        returns:
            List of invite objects
        """
        return await self.request(Route("GET", f"/channels/{channel_id}/invites"))

    async def create_channel_invite(
        self,
        channel_id: "Snowflake_Type",
        max_age: int = 86400,
        max_uses: int = 0,
        temporary: bool = False,
        unique: bool = False,
        target_type: int = None,
        target_user_id: "Snowflake_Type" = None,
        target_application_id: "Snowflake_Type" = None,
        reason: str = MISSING,
    ) -> dict:
        """
        Create an invite for the given channel.

        parameters:
            channel_id: The ID of the channel to create an invite for
            max_age: duration of invite in seconds before expiry, or 0 for never. between 0 and 604800 (7 days) (default 24 hours)
            max_uses: max number of uses or 0 for unlimited. between 0 and 100
            temporary: whether this invite only grants temporary membership
            unique: if true, don't try to reuse a similar invite (useful for creating many unique one time use invites)
            target_type: the type of target for this voice channel invite
            target_user_id: the id of the user whose stream to display for this invite, required if target_type is 1, the user must be streaming in the channel
            target_application_id: the id of the embedded application to open for this invite, required if target_type is 2, the application must have the EMBEDDED flag
            reason: An optional reason for the audit log

        returns:
            an invite object
        """
        payload = dict(max_age=max_age, max_uses=max_uses, temporary=temporary, unique=unique)
        if target_type:
            payload["target_type"] = target_type
        if target_user_id:
            payload["target_user_id"] = target_user_id
        if target_application_id:
            payload["target_application_id"] = target_application_id

        return await self.request(Route("POST", f"/channels/{channel_id}/invites"), data=payload, reason=reason)

    async def get_invite(
        self,
        invite_code: str,
        with_counts: bool = False,
        with_expiration: bool = True,
        scheduled_event_id: "Snowflake_Type" = None,
    ):
        """
        Get an invite object for a given code

        Args:
            invite_code: The code of the invite
            with_counts: whether the invite should contain approximate member counts
            with_expiration: whether the invite should contain the expiration date
            scheduled_event_id: the guild scheduled event to include with the invite

        Returns:
            an invite object
        """
        params = dict_filter_none(
            dict(with_counts=with_counts, with_expiration=with_expiration, guild_scheduled_event_id=scheduled_event_id)
        )
        return await self.request(Route("GET", f"/invites/{invite_code}", params=params))

    async def delete_invite(self, invite_code: str, reason: str = MISSING) -> dict:
        """
        Delete an invite.


        parameters:
            invite_code: The code of the invite to delete
            reason: The reason to delete the invite

        returns:
            The deleted invite object
        """
        return await self.request(Route("DELETE", f"/invites/{invite_code}"))

    async def edit_channel_permission(
        self,
        channel_id: "Snowflake_Type",
        overwrite_id: "Snowflake_Type",
        allow: str,
        deny: str,
        perm_type: int,
        reason: str = MISSING,
    ) -> None:
        """
        Edit the channel permission overwrites for a user or role in a channel.

        parameters:
            channel_id: The id of the channel
            overwrite_id: The id of the object to override
            allow: the bitwise value of all allowed permissions
            deny: the bitwise value of all disallowed permissions
            perm_type: 0 for a role or 1 for a member
            reason: The reason for this action
        """
        return await self.request(
            Route("PUT", f"/channels/{channel_id}/permissions/{overwrite_id}"),
            data={"allow": allow, "deny": deny, "type": perm_type},
            reason=reason,
        )

    async def delete_channel_permission(
        self, channel_id: "Snowflake_Type", overwrite_id: int, reason: str = MISSING
    ) -> None:
        """
        Delete a channel permission overwrite for a user or role in a channel.

        parameters:
            channel_id: The ID of the channel.
            overwrite_id: The ID of the overwrite
            reason: An optional reason for the audit log
        """
        return await self.request(Route("DELETE", f"/channels/{channel_id}/{overwrite_id}"), reason=reason)

    async def follow_news_channel(self, channel_id: "Snowflake_Type", webhook_channel_id: "Snowflake_Type") -> dict:
        """
        Follow a news channel to send messages to the target channel.

        parameters:
            channel_id: The channel to follow
            webhook_channel_id: ID of the target channel

        returns:
            Followed channel object
        """
        return await self.request(
            Route("POST", f"/channels/{channel_id}/followers"), data={"webhook_channel_id": webhook_channel_id}
        )

    async def trigger_typing_indicator(self, channel_id: "Snowflake_Type") -> None:
        """
        Post a typing indicator for the specified channel. Generally bots should not implement this route.

        parameters:
            channel_id: The id of the channel to "type" in
        """
        return await self.request(Route("POST", f"/channels/{channel_id}/typing"))

    async def get_pinned_messages(self, channel_id: "Snowflake_Type") -> List[dict]:
        """
        Get all pinned messages from a channel.

        parameters:
            channel_id: The ID of the channel to get pins from

        returns:
            A list of pinned message objects
        """
        return await self.request(Route("GET", f"/channels/{channel_id}/pins"))

    async def create_stage_instance(
        self, channel_id: "Snowflake_Type", topic: str, privacy_level: StagePrivacyLevel = 1, reason: str = MISSING
    ) -> dict:
        """
        Create a new stage instance.

        parameters:
            channel_id: The ID of the stage channel
            topic: The topic of the stage instance (1-120 characters)
            privacy_level: Them privacy_level of the stage instance (default guild only)
            reason: The reason for the creating the stage instance

        returns:
            The stage instance
        """
        return await self.request(
            Route("POST", "/stage-instances"),
            data={
                "channel_id": channel_id,
                "topic": topic,
                "privacy_level": StagePrivacyLevel(privacy_level),
            },
            reason=reason,
        )

    async def get_stage_instance(self, channel_id: "Snowflake_Type") -> dict:
        """
        Get the stage instance associated with a given channel, if it exists.

        parameters:
            channel_id: The ID of the channel to retrieve the instance for.

        returns:
            A stage instance.
        """
        return await self.request(Route("GET", f"/stage-instances/{channel_id}"))

    async def modify_stage_instance(
        self, channel_id: "Snowflake_Type", topic: str = None, privacy_level: int = None, reason: str = MISSING
    ) -> dict:
        """
        Update the fields of a given stage instance.

        parameters:
            channel_id: The id of the stage channel.
            topic: The new topic for the stage instance
            privacy_level: The privacy level for the stage instance
            reason: The reason for the change

        returns:
            The updated stage instance.
        """
        return await self.request(
            Route("PATCH", f"/stage-instances/{channel_id}"),
            data=dict_filter_none({"topic": topic, "privacy_level": privacy_level}),
            reason=reason,
        )

    async def delete_stage_instance(self, channel_id: "Snowflake_Type", reason: str = MISSING) -> None:
        """
        Delete a stage instance.

        parameters:
            channel_id: The ID of the channel to delete the stage instance for.
            reason: The reason for the deletion
        """
        return await self.request(Route("DELETE", f"/stage-instances/{channel_id}"), reason=reason)
