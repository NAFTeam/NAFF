from typing import TYPE_CHECKING, Any

from dis_snek.models.route import Route

if TYPE_CHECKING:
    from dis_snek.models.snowflake import Snowflake_Type


class UserRequests:
    request: Any

    async def get_current_user(self):
        """
        Shortcut to get requester's user.
        """
        return self.get_user("@me")

    async def get_user(self, user_id: "Snowflake_Type") -> dict:
        """
        Get a user object for a given user ID.

        parameters:
            user_id: The user to get.
        returns:
            user
        """
        return await self.request(Route("GET", f"/users/{user_id}"))

    async def modify_client_user(self, payload: dict) -> dict:
        """
        Modify the user account settings.

        parameters:
            payload: The data to send.
        """
        return await self.request(Route("PATCH", "/users/@me"), data=payload)

    async def get_user_guilds(self) -> list:
        """
        Returns a list of partial guild objects the current user is a member of. Requires the guilds OAuth2 scope.
        """
        return await self.request(Route("GET", "/users/@me/guilds"))

    async def leave_guild(self, guild_id) -> dict:
        """
        Leave a guild. Returns a 204 empty response on success.

        parameters:
            guild_id: The guild to leave from.
        """
        return await self.request(Route("DELETE", f"/users/@me/guilds/{guild_id}"))

    async def create_dm(self, recipient_id) -> dict:
        """
        Create a new DM channel with a user. Returns a DM channel object.

        parameters:
            recipient_id: The recipient to open a DM channel with.
        """
        return await self.request(Route("POST", "/users/@me/channels"), data=dict(recipient_id=recipient_id))

    async def create_group_dm(self, payload: dict) -> dict:
        """
        Create a new group DM channel with multiple users.

        parameters:
            payload: The data to send.
        """
        return await self.request(Route("POST", "/users/@me/channels"), data=payload)

    async def get_user_connections(self) -> list:
        """
        Returns a list of connection objects. Requires the connections OAuth2 scope.
        """
        return await self.request(Route("GET", "/users/@me/connections"))

    async def group_dm_add_recipient(
        self, channel_id: "Snowflake_Type", user_id: "Snowflake_Type", access_token: str, nick: str = None
    ) -> None:
        """
        Adds a recipient to a Group DM using their access token.

        parameters:
            channel_id: The ID of the group dm
            user_id: The ID of the user to add
            access_token: Access token of a user that has granted your app the gdm.join scope
            nick: Nickname of the user being added
        """
        return await self.request(
            Route("PUT", f"/channels/{channel_id}/recipients/{user_id}"),
            data={"access_token": access_token, "nick": nick},
        )

    async def group_dm_remove_recipient(self, channel_id: "Snowflake_Type", user_id: "Snowflake_Type") -> None:
        """
        Remove a recipient from the group dm.

        parameters:
            channel_id: The ID of the group dm
            user_id: The ID of the user to remove
        """
        return await self.request(Route("DELETE", f"/channels/{channel_id}/recipients/{user_id}"))

    async def modify_current_user_nick(self, guild_id: "Snowflake_Type", nickname: str = None) -> None:
        """
        Modifies the nickname of the current user in a guild

        parameters:
            guild_id: The ID of the guild
            nickname: The new nickname to use
        """
        return await self.request(Route("PATCH", f"/guilds/{guild_id}/members/@me/nick"), data={"nick": nickname})
