from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

import discord_typings

from naff.client.const import MISSING, Absent
from naff.models.discord.enums import ChannelTypes, StagePrivacyLevel, Permissions, OverwriteTypes
from ..route import Route
from naff.client.utils.serializer import dict_filter_none

__all__ = ("ChannelRequests",)


if TYPE_CHECKING:
    from naff.models.discord.channel import PermissionOverwrite
    from naff.models.discord.snowflake import Snowflake_Type


class ChannelRequests:
    request: Any

    async def get_channel(self, channel_id: "Snowflake_Type") -> discord_typings.ChannelData:
        """
        Get a channel by ID. Returns a channel object. If the channel is a thread, a thread member object is included.

        Args:
            channel_id: The id of the channel

        Returns:
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
    ) -> List[discord_typings.MessageData]:
        """
        Get the messages for a channel.

        Args:
            channel_id: The channel to get messages from
            limit: How many messages to get (default 50, max 100)
            around: Get messages around this snowflake
            before: Get messages before this snowflake
            after: Get messages after this snowflake

        Returns:
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
        topic: Absent[Optional[str]] = MISSING,
        position: Absent[Optional[int]] = MISSING,
        permission_overwrites: Absent[Optional[List[Union["PermissionOverwrite", dict]]]] = MISSING,
        parent_id: "Snowflake_Type" = MISSING,
        nsfw: bool = False,
        bitrate: int = 64000,
        user_limit: int = 0,
        rate_limit_per_user: int = 0,
        reason: Absent[str] = MISSING,
    ) -> discord_typings.ChannelData:
        """
        Create a channel in a guild.

        Args:
            guild_id: The ID of the guild to create the channel in
            name: The name of the channel
            channel_type: The type of channel to create
            topic: The topic of the channel
            position: The position of the channel in the channel list
            permission_overwrites: Permission overwrites to apply to the channel
            parent_id: The category this channel should be within
            nsfw: Should this channel be marked nsfw
            bitrate: The bitrate of this channel, only for voice
            user_limit: The max users that can be in this channel, only for voice
            rate_limit_per_user: The time users must wait between sending messages
            reason: The reason for creating this channel

        Returns:
            The created channel object

        """
        payload = {
            "name": name,
            "type": channel_type,
            "topic": topic,
            "position": position,
            "rate_limit_per_user": rate_limit_per_user,
            "nsfw": nsfw,
            "parent_id": parent_id,
            "permission_overwrites": permission_overwrites,
        }

        if channel_type in (2, 13):
            payload.update(
                bitrate=bitrate,
                user_limit=user_limit,
            )

        return await self.request(Route("POST", f"/guilds/{guild_id}/channels"), payload=payload, reason=reason)

    async def move_channel(
        self,
        guild_id: "Snowflake_Type",
        channel_id: "Snowflake_Type",
        new_pos: int,
        parent_id: "Snowflake_Type" = None,
        lock_perms: bool = False,
        reason: Absent[str] = MISSING,
    ) -> None:
        """
        Move a channel.

        Args:
            guild_id: The ID of the guild this affects
            channel_id: The ID of the channel to move
            new_pos: The new position of this channel
            parent_id: The parent ID if needed
            lock_perms: Sync permissions with the new parent
            reason: An optional reason for the audit log

        """
        payload = {"id": channel_id, "position": new_pos, "lock_permissions": lock_perms}
        if parent_id:
            payload["parent_id"] = parent_id

        return await self.request(Route("PATCH", f"/guilds/{guild_id}/channels"), payload=payload, reason=reason)

    async def modify_channel(
        self, channel_id: "Snowflake_Type", data: dict, reason: Absent[str] = MISSING
    ) -> discord_typings.ChannelData:
        """
        Update a channel's settings, returns the updated channel object on success.

        Args:
            channel_id: The ID of the channel to update
            data: The data to update with
            reason: An optional reason for the audit log

        Returns:
            Channel object on success

        """
        return await self.request(Route("PATCH", f"/channels/{channel_id}"), payload=data, reason=reason)

    async def delete_channel(self, channel_id: "Snowflake_Type", reason: Absent[str] = MISSING) -> None:
        """
        Delete the channel.

        Args:
            channel_id: The ID of the channel to delete
            reason: An optional reason for the audit log

        """
        return await self.request(Route("DELETE", f"/channels/{channel_id}"), reason=reason)

    async def get_channel_invites(self, channel_id: "Snowflake_Type") -> List[discord_typings.InviteData]:
        """
        Get the invites for the channel.

        Args:
            channel_id: The ID of the channel to retrieve from

        Returns:
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
        reason: Absent[str] = MISSING,
    ) -> discord_typings.InviteData:
        """
        Create an invite for the given channel.

        Args:
            channel_id: The ID of the channel to create an invite for
            max_age: duration of invite in seconds before expiry, or 0 for never. between 0 and 604800 (7 days) (default 24 hours)
            max_uses: max number of uses or 0 for unlimited. between 0 and 100
            temporary: whether this invite only grants temporary membership
            unique: if true, don't try to reuse a similar invite (useful for creating many unique one time use invites)
            target_type: the type of target for this voice channel invite
            target_user_id: the id of the user whose stream to display for this invite, required if target_type is 1, the user must be streaming in the channel
            target_application_id: the id of the embedded application to open for this invite, required if target_type is 2, the application must have the EMBEDDED flag
            reason: An optional reason for the audit log

        Returns:
            an invite object

        """
        payload = {"max_age": max_age, "max_uses": max_uses, "temporary": temporary, "unique": unique}
        if target_type:
            payload["target_type"] = target_type
        if target_user_id:
            payload["target_user_id"] = target_user_id
        if target_application_id:
            payload["target_application_id"] = target_application_id

        return await self.request(Route("POST", f"/channels/{channel_id}/invites"), payload=payload, reason=reason)

    async def get_invite(
        self,
        invite_code: str,
        with_counts: bool = False,
        with_expiration: bool = True,
        scheduled_event_id: "Snowflake_Type" = None,
    ) -> discord_typings.InviteData:
        """
        Get an invite object for a given code.

        Args:
            invite_code: The code of the invite
            with_counts: whether the invite should contain approximate member counts
            with_expiration: whether the invite should contain the expiration date
            scheduled_event_id: the guild scheduled event to include with the invite

        Returns:
            an invite object

        """
        params = dict_filter_none(
            {
                "with_counts": with_counts,
                "with_expiration": with_expiration,
                "guild_scheduled_event_id": scheduled_event_id,
            }
        )
        return await self.request(Route("GET", f"/invites/{invite_code}", params=params))

    async def delete_invite(self, invite_code: str, reason: Absent[str] = MISSING) -> discord_typings.InviteData:
        """
        Delete an invite.

        Args:
            invite_code: The code of the invite to delete
            reason: The reason to delete the invite

        Returns:
            The deleted invite object

        """
        return await self.request(Route("DELETE", f"/invites/{invite_code}"), reason=reason)

    async def edit_channel_permission(
        self,
        channel_id: "Snowflake_Type",
        overwrite_id: "Snowflake_Type",
        allow: Union["Permissions", int],
        deny: Union["Permissions", int],
        perm_type: Union["OverwriteTypes", int],
        reason: Absent[str] = MISSING,
    ) -> None:
        """
        Edit the channel permission overwrites for a user or role in a channel.

        Args:
            channel_id: The id of the channel
            overwrite_id: The id of the object to override
            allow: the bitwise value of all allowed permissions
            deny: the bitwise value of all disallowed permissions
            perm_type: 0 for a role or 1 for a member
            reason: The reason for this action

        """
        return await self.request(
            Route("PUT", f"/channels/{channel_id}/permissions/{overwrite_id}"),
            payload={"allow": allow, "deny": deny, "type": perm_type},
            reason=reason,
        )

    async def delete_channel_permission(
        self, channel_id: "Snowflake_Type", overwrite_id: int, reason: Absent[str] = MISSING
    ) -> None:
        """
        Delete a channel permission overwrite for a user or role in a channel.

        Args:
            channel_id: The ID of the channel.
            overwrite_id: The ID of the overwrite
            reason: An optional reason for the audit log

        """
        return await self.request(Route("DELETE", f"/channels/{channel_id}/{overwrite_id}"), reason=reason)

    async def follow_news_channel(
        self, channel_id: "Snowflake_Type", webhook_channel_id: "Snowflake_Type"
    ) -> discord_typings.FollowedChannelData:
        """
        Follow a news channel to send messages to the target channel.

        Args:
            channel_id: The channel to follow
            webhook_channel_id: ID of the target channel

        Returns:
            Followed channel object

        """
        return await self.request(
            Route("POST", f"/channels/{channel_id}/followers"), payload={"webhook_channel_id": webhook_channel_id}
        )

    async def trigger_typing_indicator(self, channel_id: "Snowflake_Type") -> None:
        """
        Post a typing indicator for the specified channel. Generally bots should not implement this route.

        Args:
            channel_id: The id of the channel to "type" in

        """
        return await self.request(Route("POST", f"/channels/{channel_id}/typing"))

    async def get_pinned_messages(self, channel_id: "Snowflake_Type") -> List[discord_typings.MessageData]:
        """
        Get all pinned messages from a channel.

        Args:
            channel_id: The ID of the channel to get pins from

        Returns:
            A list of pinned message objects

        """
        return await self.request(Route("GET", f"/channels/{channel_id}/pins"))

    async def create_stage_instance(
        self,
        channel_id: "Snowflake_Type",
        topic: str,
        privacy_level: StagePrivacyLevel = 1,
        reason: Absent[str] = MISSING,
    ) -> discord_typings.StageInstanceData:
        """
        Create a new stage instance.

        Args:
            channel_id: The ID of the stage channel
            topic: The topic of the stage instance (1-120 characters)
            privacy_level: Them privacy_level of the stage instance (default guild only)
            reason: The reason for the creating the stage instance

        Returns:
            The stage instance

        """
        return await self.request(
            Route("POST", "/stage-instances"),
            payload={
                "channel_id": channel_id,
                "topic": topic,
                "privacy_level": StagePrivacyLevel(privacy_level),
            },
            reason=reason,
        )

    async def get_stage_instance(self, channel_id: "Snowflake_Type") -> discord_typings.StageInstanceData:
        """
        Get the stage instance associated with a given channel, if it exists.

        Args:
            channel_id: The ID of the channel to retrieve the instance for.

        Returns:
            A stage instance.

        """
        return await self.request(Route("GET", f"/stage-instances/{channel_id}"))

    async def modify_stage_instance(
        self, channel_id: "Snowflake_Type", topic: str = None, privacy_level: int = None, reason: Absent[str] = MISSING
    ) -> discord_typings.StageInstanceData:
        """
        Update the fields of a given stage instance.

        Args:
            channel_id: The id of the stage channel.
            topic: The new topic for the stage instance
            privacy_level: The privacy level for the stage instance
            reason: The reason for the change

        Returns:
            The updated stage instance.

        """
        return await self.request(
            Route("PATCH", f"/stage-instances/{channel_id}"),
            payload=dict_filter_none({"topic": topic, "privacy_level": privacy_level}),
            reason=reason,
        )

    async def delete_stage_instance(self, channel_id: "Snowflake_Type", reason: Absent[str] = MISSING) -> None:
        """
        Delete a stage instance.

        Args:
            channel_id: The ID of the channel to delete the stage instance for.
            reason: The reason for the deletion

        """
        return await self.request(Route("DELETE", f"/stage-instances/{channel_id}"), reason=reason)
