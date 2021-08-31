from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from dis_snek.models.route import Route

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
        await self.request(Route("DELETE", f"/guilds/{guild_id}"))
