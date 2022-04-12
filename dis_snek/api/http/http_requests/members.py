from typing import Any, List, TYPE_CHECKING, Union

import discord_typings

from dis_snek.client.const import MISSING, Absent
from ..route import Route
from dis_snek.models.discord.timestamp import Timestamp

__all__ = ["MemberRequests"]


if TYPE_CHECKING:
    from dis_snek.models.discord.snowflake import Snowflake_Type


class MemberRequests:
    request: Any

    async def get_member(
        self, guild_id: "Snowflake_Type", user_id: "Snowflake_Type"
    ) -> discord_typings.GuildMemberData:
        """
        Get a member of a guild by ID.

        Args:
            guild_id: The id of the guild
            user_id: The user id to grab

        """
        return await self.request(Route("GET", f"/guilds/{guild_id}/members/{user_id}"))

    async def list_members(
        self, guild_id: "Snowflake_Type", limit: int = 1, after: "Snowflake_Type" = MISSING
    ) -> List[discord_typings.GuildMemberData]:
        """
        List the members of a guild.

        Args:
            guild_id: The ID of the guild
            limit: How many members to get (max 1000)
            after: Get IDs after this snowflake

        """
        payload = {"limit": limit, "after": after}
        return await self.request(Route("GET", f"/guilds/{guild_id}/members"), params=payload)

    async def search_guild_members(
        self, guild_id: "Snowflake_Type", query: str, limit: int = 1
    ) -> List[discord_typings.GuildMemberData]:
        """
        Search a guild for members who's username or nickname starts with provided string.

        Args:
            guild_id: The ID of the guild to search
            query: The string to search for
            limit: The number of members to return

        """
        return await self.request(
            Route("GET", f"/guilds/{guild_id}/members/search"), params={"query": query, "limit": limit}
        )

    async def modify_guild_member(
        self,
        guild_id: "Snowflake_Type",
        user_id: "Snowflake_Type",
        nickname: Absent[str] = MISSING,
        roles: List["Snowflake_Type"] = MISSING,
        mute: Absent[bool] = MISSING,
        deaf: Absent[bool] = MISSING,
        channel_id: "Snowflake_Type" = MISSING,
        communication_disabled_until: Absent[Union[Timestamp, None]] = MISSING,
        reason: Absent[str] = MISSING,
    ) -> discord_typings.GuildMemberData:
        """
        Modify attributes of a guild member.

        Args:
            guild_id: The ID of the guild
            user_id: The ID of the user we're modifying
            nickname: Value to set users nickname to
            roles: Array of role ids the member is assigned
            mute: Whether the user is muted in voice channels. Will throw a 400 if the user is not in a voice channel
            deaf: Whether the user is deafened in voice channels
            channel_id: id of channel to move user to (if they are connected to voice)
            reason: An optional reason for the audit log

        Returns:
            The updated member object

        """
        if communication_disabled_until is not MISSING:
            if isinstance(communication_disabled_until, Timestamp):
                communication_disabled_until = communication_disabled_until.isoformat()

        return await self.request(
            Route("PATCH", f"/guilds/{guild_id}/members/{user_id}"),
            data={
                "nick": nickname,
                "roles": roles,
                "mute": mute,
                "deaf": deaf,
                "channel_id": channel_id,
                "communication_disabled_until": communication_disabled_until,
            },
            reason=reason,
        )

    async def modify_current_member(
        self,
        guild_id: "Snowflake_Type",
        nickname: Absent[str] = MISSING,
        reason: Absent[str] = MISSING,
    ) -> None:
        """
        Modify attributes of the user

        Args:
            nickname: The new nickname to apply
            reason: An optional reason for the audit log

        """
        await self.request(
            Route("PATCH", f"/guilds/{guild_id}/members/@me"),
            data={
                "nick": nickname or None,
            },
            reason=reason,
        )

    async def add_guild_member_role(
        self,
        guild_id: "Snowflake_Type",
        user_id: "Snowflake_Type",
        role_id: "Snowflake_Type",
        reason: Absent[str] = MISSING,
    ) -> None:
        """
        Adds a role to a guild member.

        Args:
            guild_id: The ID of the guild
            user_id: The ID of the user
            role_id: The ID of the role to add
            reason: The reason for this action

        """
        return await self.request(Route("PUT", f"/guilds/{guild_id}/members/{user_id}/roles/{role_id}"), reason=reason)

    async def remove_guild_member_role(
        self,
        guild_id: "Snowflake_Type",
        user_id: "Snowflake_Type",
        role_id: "Snowflake_Type",
        reason: Absent[str] = MISSING,
    ) -> None:
        """
        Remove a role from a guild member.

        Args:
            guild_id: The ID of the guild
            user_id: The ID of the user
            role_id: The ID of the role to remove
            reason: The reason for this action

        """
        return await self.request(
            Route("DELETE", f"/guilds/{guild_id}/members/{user_id}/roles/{role_id}"), reason=reason
        )
