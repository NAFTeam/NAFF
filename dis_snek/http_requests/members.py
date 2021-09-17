from typing import TYPE_CHECKING, Any, Dict, List

from dis_snek.models.route import Route

if TYPE_CHECKING:
    from dis_snek.models.snowflake import Snowflake_Type


class MemberRequests:
    request: Any

    async def get_member(self, guild_id: "Snowflake_Type", user_id: "Snowflake_Type") -> Dict:
        """
        Get a member of a guild by ID.

        parameters:
            guild_id: The id of the guild
            user_id: The user id to grab

        """
        return await self.request(Route("GET", f"/guilds/{guild_id}/members/{user_id}"))

    async def list_members(
        self, guild_id: "Snowflake_Type", limit: int = 1, after: "Snowflake_Type" = None
    ) -> List[Dict]:
        """
        List the members of a guild.

        parameters:
            guild_id: The ID of the guild
            limit: How many members to get (max 1000)
            after: Get IDs after this snowflake

        """
        payload = dict(limit=limit)
        if after:
            payload["after"] = after

        return await self.request(Route("GET", f"/guilds/{guild_id}/members"), params=payload)

    async def search_guild_members(self, guild_id: "Snowflake_Type", query: str, limit: int = 1) -> List[Dict]:
        """
        Search a guild for members who's username or nickname starts with provided string.

        parameters:
            guild_id: The ID of the guild to search
            query: The string to search for
            limit: The number of members to return

        """

        return await self.request(
            Route("GET", f"/guilds/{guild_id}/members/search"), params=dict(query=query, limit=limit)
        )

    async def modify_guild_member(
        self,
        guild_id: "Snowflake_Type",
        user_id: "Snowflake_Type",
        nickname: str = None,
        roles: List["Snowflake_Type"] = None,
        mute: bool = None,
        deaf: bool = None,
        channel_id: "Snowflake_Type" = None,
        reason: str = None,
    ) -> Dict:
        """
        Modify attributes of a guild member.

        parameters:
            guild_id: The ID of the guild
            user_id: The ID of the user we're modifying
            nickname: Value to set users nickname to
            roles: Array of role ids the member is assigned
            mute: Whether the user is muted in voice channels. Will throw a 400 if the user is not in a voice channel
            deaf: Whether the user is deafened in voice channels
            channel_id: id of channel to move user to (if they are connected to voice)
            reason: An optional reason for the audit log
        returns:
            The updated member object
        """
        payload = dict(nick=nickname, roles=roles, mute=mute, deaf=deaf, channel_id=channel_id)
        # clean up payload
        payload = {key: value for key, value in payload.items() if value is not None}
        return await self.request(Route("PATCH", f"/guilds/{guild_id}/members/{user_id}"), data=payload, reason=reason)

    async def add_guild_member_role(
        self, guild_id: "Snowflake_Type", user_id: "Snowflake_Type", role_id: "Snowflake_Type", reason: str = None
    ) -> None:
        """
        Adds a role to a guild member.

        parameters:
            guild_id: The ID of the guild
            user_id: The ID of the user
            role_id: The ID of the role to add
            reason: The reason for this action
        """
        return await self.request(Route("PUT", f"/guilds/{guild_id}/members/{user_id}/roles/{role_id}"))

    async def remove_guild_member_role(
        self, guild_id: "Snowflake_Type", user_id: "Snowflake_Type", role_id: "Snowflake_Type", reason: str = None
    ) -> None:
        """
        Remove a role from a guild member.

        parameters:
            guild_id: The ID of the guild
            user_id: The ID of the user
            role_id: The ID of the role to remove
            reason: The reason for this action
        """
        return await self.request(Route("DELETE", f"/guilds/{guild_id}/members/{user_id}/roles/{role_id}"))
