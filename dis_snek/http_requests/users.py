from typing import List, Dict, Any

from dis_snek.models.route import Route
from dis_snek.models.snowflake import Snowflake_Type


class UserRequests:
    request: Any

    async def get_user(self, user_id: Snowflake_Type) -> dict:
        """
        Get a user object for a given user ID.

        :param user_id: The user to get
        :return: user
        """
        return await self.request(Route("GET", f"/users/{user_id}"))

    async def get_member(self, guild_id: Snowflake_Type, user_id: Snowflake_Type) -> Dict:
        """
        Get a member of a guild by ID.

        :param guild_id: The id of the guild
        :param user_id: The user id to grab
        :return:
        """
        return await self.request(Route("GET", f"/guilds/{guild_id}/members/{user_id}"))

    async def list_members(self, guild_id: Snowflake_Type, limit: int = 1, after: Snowflake_Type = None) -> List[Dict]:
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

        return await self.request(Route("GET", f"/guilds/{guild_id}/members"), json=payload)

    async def search_guild_members(self, guild_id: Snowflake_Type, query: str, limit: int = 1) -> List[Dict]:
        """
        Search a guild for members who's username or nickname starts with provided string.

        :param guild_id: The ID of the guild to search
        :param query: The string to search for
        :param limit: The number of members to return
        :return:
        """

        return await self.request(
            Route("GET", f"/guilds/{guild_id}/members/search"), json=dict(query=query, limit=limit)
        )

    async def modify_guild_member(
        self,
        guild_id: Snowflake_Type,
        user_id: Snowflake_Type,
        nickname: str = None,
        roles: List[Snowflake_Type] = None,
        mute: bool = None,
        deaf: bool = None,
        channel_id: Snowflake_Type = None,
    ) -> Dict:
        """
        Modify attributes of a guild member.

        :param guild_id: The ID of the guild
        :param user_id: The ID of the user we're modifying
        :param nickname: Value to set users nickname to
        :param roles: Array of role ids the member is assigned
        :param mute: Whether the user is muted in voice channels. Will throw a 400 if the user is not in a voice channel
        :param deaf: Whether the user is deafened in voice channels
        :param channel_id: 	id of channel to move user to (if they are connected to voice)
        :return: The updated member object
        """
        payload = dict(nick=nickname, roles=roles, mute=mute, deaf=deaf, channel_id=channel_id)
        # clean up payload
        payload = {key: value for key, value in payload.items() if value is not None}
        return await self.request(Route("PATCH", f"/guilds/{guild_id}/members/{user_id}"), json=payload)
