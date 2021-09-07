from typing import TYPE_CHECKING, Any, Dict, List

from dis_snek.models.route import Route

if TYPE_CHECKING:
    from dis_snek.models.snowflake import Snowflake_Type


class MemberRequests:
    request: Any

    async def get_member(self, guild_id: "Snowflake_Type", user_id: "Snowflake_Type") -> Dict:
        """
        Get a member of a guild by ID.

        :param guild_id: The id of the guild
        :param user_id: The user id to grab
        :return:
        """
        return await self.request(Route("GET", f"/guilds/{guild_id}/members/{user_id}"))

    async def list_members(
        self, guild_id: "Snowflake_Type", limit: int = 1, after: "Snowflake_Type" = None
    ) -> List[Dict]:
        """
        List the members of a guild.

        :param guild_id: The ID of the guild
        :param limit: How many members to get (max 1000)
        :param after: Get IDs after this snowflake
        :return:
        """
        payload = dict(limit=limit)
        if after:
            payload["after"] = after

        return await self.request(Route("GET", f"/guilds/{guild_id}/members"), params=payload)

    async def search_guild_members(self, guild_id: "Snowflake_Type", query: str, limit: int = 1) -> List[Dict]:
        """
        Search a guild for members who's username or nickname starts with provided string.

        :param guild_id: The ID of the guild to search
        :param query: The string to search for
        :param limit: The number of members to return
        :return:
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

        :param guild_id: The ID of the guild
        :param user_id: The ID of the user we're modifying
        :param nickname: Value to set users nickname to
        :param roles: Array of role ids the member is assigned
        :param mute: Whether the user is muted in voice channels. Will throw a 400 if the user is not in a voice channel
        :param deaf: Whether the user is deafened in voice channels
        :param channel_id: id of channel to move user to (if they are connected to voice)
        :param reason: An optional reason for the audit log
        :return: The updated member object
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

        :param guild_id: The ID of the guild
        :param user_id: The ID of the user
        :param role_id: The ID of the role to add
        :param reason: The reason for this action
        """
        return await self.request(Route("PUT", f"/guilds/{guild_id}/members/{user_id}/roles/{role_id}"))

    async def remove_guild_member_role(
        self, guild_id: "Snowflake_Type", user_id: "Snowflake_Type", role_id: "Snowflake_Type", reason: str = None
    ) -> None:
        """
        Remove a role from a guild member.

        :param guild_id: The ID of the guild
        :param user_id: The ID of the user
        :param role_id: The ID of the role to remove
        :param reason: The reason for this action
        """
        return await self.request(Route("DELETE", f"/guilds/{guild_id}/members/{user_id}/roles/{role_id}"))
