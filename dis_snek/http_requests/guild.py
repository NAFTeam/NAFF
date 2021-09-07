from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from dis_snek.models.route import Route
from dis_snek.utils.serializer import dict_filter_none

if TYPE_CHECKING:
    from dis_snek.models.snowflake import Snowflake_Type


class GuildRequests:
    request: Any

    async def get_guilds(
        self, limit: int = 200, before: Optional["Snowflake_Type"] = None, after: Optional["Snowflake_Type"] = None
    ) -> List[Dict]:
        """
        Get a list of partial guild objects the current user is a member of req. `guilds` scope.

        :param limit: max number of guilds to return (1-200)
        :param before: get guilds before this guild ID
        :param after: get guilds after this guild ID
        :return: List[guilds]
        """
        params: Dict[str, Union[int, str]] = {"limit": limit}

        if before:
            params["before"] = before
        if after:
            params["after"] = after
        return await self.request(Route("GET", "/users/@me/guilds", params=params))

    async def get_guild(self, guild_id: "Snowflake_Type", with_counts: Optional[bool] = True) -> dict:
        """
        Get the guild object for the given ID.

        :param guild_id: the id of the guild
        :param with_counts: when `true`, will return approximate member and presence counts for the guild
        :return: a guild object
        """
        return await self.request(
            Route("GET", f"/guilds/{guild_id}"), params={"with_counts": int(with_counts)}  # type: ignore
        )

    async def get_guild_preview(self, guild_id: "Snowflake_Type") -> dict:
        """
        Get a guild's preview

        :param guild_id: the guilds ID
        :return: guild preview object  # todo: make an object representing this
        """
        return await self.request(Route("GET", f"/guilds/{guild_id}/preview"))

    async def get_channels(self, guild_id: "Snowflake_Type") -> List[Dict]:
        """
        Get a guilds channels.

        :param guild_id: the id of the guild

        :return:
        """
        return await self.request(Route("GET", f"/guilds/{guild_id}/channels"))

    async def get_roles(self, guild_id: "Snowflake_Type") -> List[Dict]:
        """
        Get a guild's roles.

        :param guild_id: The ID of the guild

        :return: List of roles
        """
        return await self.request(Route("GET", f"/guilds/{guild_id}/roles"))

    async def modify_guild(self, guild_id: "Snowflake_Type", reason: str = None, **kwargs) -> None:
        """
        Modify a guild's attributes.

        :param guild_id: The ID of the guild we want to modify
        :param reason: The reason for this change
        :param kwargs: The params to change
        """
        expected = [
            "name",
            "region",
            "verification_level",
            "default_message_notifications",
            "explicit_content_filter",
            "afk_channel_id",
            "afk_timeout",
            "icon",
            "owner_id",
            "splash",
            "discovery_splash",
            "banner",
            "system_channel_id",
            "system_channel_flags",
            "rules_channel_id",
            "public_updates_channel_id",
            "preferred_locale",
            "features",
            "description",
        ]

        for key in kwargs:
            if key not in expected:
                del kwargs[key]

        await self.request(Route("PATCH", f"/guilds/{guild_id}"), data=kwargs, reason=reason)

    async def delete_guild(self, guild_id: "Snowflake_Type") -> None:
        """
        Delete the guild.

        :param guild_id: The ID of the guild that we want to delete
        """
        return await self.request(Route("DELETE", f"/guilds/{guild_id}"))

    async def add_guild_member(
        self,
        guild_id: "Snowflake_Type",
        user_id: "Snowflake_Type",
        access_token: str,
        nick: str = None,
        roles: List["Snowflake_Type"] = None,
        mute: bool = False,
        deaf: bool = False,
    ) -> dict:
        """
        Add a user to the guild.
        All parameters to this endpoint except for `access_token`, `guild_id` and `user_id` are optional.

        :param guild_id: The ID of the guild
        :param user_id: The ID of the user to add
        :param access_token: The access token of the user
        :param nick: value to set users nickname to
        :param roles: array of role ids the member is assigned
        :param mute: whether the user is muted in voice channels
        :param deaf: whether the user is deafened in voice channels
        :return: Guild Member Object
        """
        return await self.request(
            Route("PUT", f"/guilds/{guild_id}/members/{user_id}"),
            data=dict_filter_none(
                {"access_token": access_token, "nick": nick, "roles": roles, "mute": mute, "deaf": deaf}
            ),
        )

    async def remove_guild_member(
        self, guild_id: "Snowflake_Type", user_id: "Snowflake_Type", reason: str = None
    ) -> None:
        """
        Remove a member from a guild.

        :param guild_id: The ID of the guild
        :param user_id: The ID of the user to remove
        :param reason: The reason for this action
        """
        return await self.request(Route("DELETE", f"/guilds/{guild_id}/members/{user_id}"), reaosn=reason)

    async def get_guild_bans(self, guild_id: "Snowflake_Type") -> List[dict]:
        """
        Return a list of ban objects for the users banned from this guild.

        :param guild_id: The ID of the guild to query
        :return: List of ban objects
        """
        return await self.request(Route("GET", f"/guilds/{guild_id}/bans"))

    async def get_guild_ban(self, guild_id: "Snowflake_Type", user_id: "Snowflake_Type") -> Optional[dict]:
        """
        Returns a ban object for the given user or a 404 not found if the ban cannot be found

        :param guild_id: The ID of the guild to query
        :param user_id: The ID of the user to query
        :return: Ban object if exists
        :raises: Not found error if no ban exists
        """
        return await self.request(Route("GET", f"/guilds/{guild_id}/bans/{user_id}"))

    async def create_guild_ban(
        self, guild_id: "Snowflake_Type", user_id: "Snowflake_Type", delete_message_days: int = 0, reason: str = None
    ) -> None:
        """
        Create a guild ban, and optionally delete previous messages sent by the banned user.

        :param guild_id: The ID of the guild to create the ban in
        :param user_id: The ID of the user to ban
        :param delete_message_days: number of days to delete messages for (0-7)
        :param reason: The reason for this action
        """
        return await self.request(
            Route("PUT", f"/guilds/{guild_id}/bans/{user_id}"),
            data={"delete_message_days": delete_message_days},
            reason=reason,
        )

    async def remove_guild_ban(self, guild_id: "Snowflake_Type", user_id: "Snowflake_Type", reason: str = None) -> None:
        """
        Remove a guild ban.

        :param guild_id: The ID of the guild to remove the ban in
        :param user_id: The ID of the user to unban
        :param reason: The reason for this action
        """
        return await self.request(Route("DELETE", f"/guilds/{guild_id}/bans/{user_id}"), reason=reason)

    async def get_guild_prune_count(
        self, guild_id: "Snowflake_Type", days: int = 7, include_roles: List["Snowflake_Type"] = None
    ) -> dict:
        """
        Returns an object with one 'pruned' key indicating the number of members that would be removed in a prune operation.

        :param guild_id: The ID of the guild to query
        :param days: number of days to count prune for (1-30)
        :param include_roles: role(s) to include
        :return: {"pruned": int}
        """
        payload = {"days": days}
        if include_roles:
            payload["include_roles"] = ", ".join(include_roles)

        return await self.request(Route("GET", f"/guilds/{guild_id}/prune"), data=payload)

    async def begin_guild_prune(
        self,
        guild_id: "Snowflake_Type",
        days: int = 7,
        include_roles: List["Snowflake_Type"] = None,
        compute_prune_count: bool = True,
        reason: str = None,
    ) -> dict:
        """
        Begin a prune operation.

        :param guild_id: The ID of the guild to query
        :param days: number of days to count prune for (1-30)
        :param include_roles: role(s) to include
        :param compute_prune_count: whether 'pruned' is returned, discouraged for large guilds
        :param reason: The reason for this action
        :return: {"pruned": int}
        """
        payload = {"days": days, "compute_prune_count": compute_prune_count}
        if include_roles:
            payload["include_roles"] = ", ".join(include_roles)

        return await self.request(Route("POST", f"/guilds/{guild_id}/prune"), data=payload, reason=reason)
