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

        return await self.request(Route("GET", f"/guilds/{guild_id}/prune"), params=payload)

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

    async def get_guild_invites(self, guild_id: "Snowflake_Type") -> List[dict]:
        """
        Returns a list of invite objects (with invite metadata) for the guild

        :param guild_id: The ID of the guild to query
        :return: List of invite objects
        """
        return await self.request(Route("GET", f"/guilds/{guild_id}/invites"))

    async def create_guild_role(self, guild_id: "Snowflake_Type", payload: dict, reason: str = None) -> dict:
        """
        Create a new role for the guild.

        :param guild_id: The ID of the guild
        :param payload: A dict representing the role to add
        :param reason: The reason for this action
        :return: Role object
        """
        return await self.request(Route("POST", f"/guilds/{guild_id}/roles"), data=payload, reason=reason)

    async def modify_guild_role_positions(
        self, guild_id: "Snowflake_Type", role_id: "Snowflake_Type", position: int, reason: str = None
    ) -> List[dict]:
        """
        Modify the position of a role in the guild.

        :param guild_id: The ID of the guild
        :param role_id: The ID of the role to move
        :param position: The new position of this role in the hierarchy
        :param reason: The reason for this action
        :return: List of guild roles
        """
        return await self.request(
            Route("PATCH", f"/guilds/{guild_id}/roles"), data={"id": role_id, "position": position}, reason=reason
        )

    async def modify_guild_role(
        self, guild_id: "Snowflake_Type", role_id: "Snowflake_Type", payload: dict, reason: str = None
    ) -> dict:
        """
        Modify an existing role for the guild.

        :param guild_id: The ID of the guild
        :param role_id: The ID of the role to move
        :param payload: A dict representing the role to add
        :param reason: The reason for this action
        :return: Role object
        """
        return await self.request(Route("PATCH", f"/guilds/{guild_id}/roles/{role_id}"), data=payload, reason=reason)

    async def delete_guild_role(self, guild_id: "Snowflake_Type", role_id: "Snowflake_Type", reason: str = None):
        """
        Delete a guild role.

        :param guild_id: The ID of the guild
        :param role_id: The ID of the role to delete
        :param reason: The reason for this action
        """
        return await self.request(Route("DELETE", f"/guilds/{guild_id}/roles/{role_id}"))

    async def get_guild_voice_regions(self, guild_id: "Snowflake_Type") -> List[dict]:
        """
        Returns a list of voice region objects for the guild.
        Unlike the similar /voice route, this returns VIP servers when the guild is VIP-enabled.

        :param guild_id: The ID of the guild to query
        :return: List of voice region objects
        """
        return await self.request(Route("GET", f"/guilds/{guild_id}/regions"))

    async def get_guild_integrations(self, guild_id: "Snowflake_Type") -> List[dict]:
        """
        Returns a list of integration objects for the guild.

        :param guild_id: The ID of the guild to query
        :return: list of integration objects
        """
        return await self.request(Route("GET", f"/guilds/{guild_id}/integrations"))

    async def delete_guild_integration(self, guild_id: "Snowflake_Type", integration_id: "Snowflake_Type") -> None:
        """
        Delete an integration from the guild.

        :param guild_id: The ID of the guild
        :param integration_id: The ID of the integration to remove
        """
        return await self.request(Route("DELETE", f"/guilds/{guild_id}/integrations/{integration_id}"))

    async def get_guild_widget_settings(self, guild_id: "Snowflake_Type") -> dict:
        """
        Get guild widget settings.

        :param guild_id: The ID of the guild to query
        :return: guild widget object
        """
        return await self.request(Route("GET", f"/guilds/{guild_id}/widget"))

    async def get_guild_widget(self, guild_id: "Snowflake_Type") -> dict:
        """
        Returns the widget for the guild.
        :param guild_id: The ID of the guild to query
        :return:Guild widget
        """
        return await self.request(Route("GET", f"/guilds/{guild_id}/widget.json"))

    async def get_guild_widget_image(self, guild_id: "Snowflake_Type", style: str = None) -> str:
        """
        Get a url representing a png image widget for the guild.

        For styles see: https://discord.com/developers/docs/resources/guild#get-guild-widget-image

        :param guild_id: The guild to query
        :param style: The style of widget required.
        :return: A url pointing to this image
        """
        route = Route("GET", f"/guilds/{guild_id}/widget.png{f'?style={style}' if style else ''}")
        return route.url

    async def get_guild_welcome_screen(self, guild_id: "Snowflake_Type") -> dict:
        """
        Get the welcome screen for this guild.

        :param guild_id: The ID of the guild to query
        :return:Welcome screen object
        """
        return await self.request(Route("GET", f"/guilds/{guild_id}/welcome-screen"))

    async def get_guild_vanity_url(self, guild_id: "Snowflake_Type") -> dict:
        """
        Get a partial invite object for the guilds vanity invite url.

        :param guild_id: The ID of the guild to query
        :return: `{"code": "abc", "uses": 420}` or `None`
        """
        return await self.request(Route("GET", f"/guilds/{guild_id}/vanity-url"))

    async def modify_guild_widget(self, guild_id: "Snowflake_Type", **kwargs) -> dict:
        """
        Modify a guild widget.

        :param guild_id: The ID of the guild to modify.
        :return: Updated guild widget.
        """
        # todo: find out if this endpoint works, and what params it expects.
        return await self.request(Route("PATCH", f"/guilds/{guild_id}/widget"), data=kwargs)

    async def modify_guild_welcome_screen(
        self, guild_id: "Snowflake_Type", enabled: bool, welcome_channels: List["Snowflake_Type"], description: str
    ) -> dict:
        """
        Modify the guild's welcome screen.

        :param guild_id: The ID of the guild.
        :param enabled: Whether the welcome screen is enabled
        :param welcome_channels: Channels linked in the welcome screen and their display options
        :param description: The server description to show in the welcome screen
        :return:
        """
        return await self.request(
            Route("PATCH", f"/guilds/{guild_id}/welcome-screen"),
            data={"enabled": enabled, "welcome_channels": welcome_channels, "description": description},
        )

    async def modify_current_user_voice_state(
        self,
        guild_id: "Snowflake_Type",
        channel_id: "Snowflake_Type",
        suppress: bool = None,
        request_to_speak_timestamp: str = None,
    ) -> None:
        """
        Update the current user voice state.

        :param guild_id: The ID of the guild to update.
        :param channel_id: The id of the channel the user is currently in
        :param suppress: Toggle the user's suppress state.
        :param request_to_speak_timestamp: Sets the user's request to speak
        :return:
        """
        return await self.request(
            Route("PATCH", f"/guilds/{guild_id}/voice-states/@me"),
            data=dict_filter_none(
                {
                    "channel_id": channel_id,
                    "suppress": suppress,
                    "request_to_speak_timestamp": request_to_speak_timestamp,
                }
            ),
        )

    async def modify_user_voice_state(
        self, guild_id: "Snowflake_Type", user_id: "Snowflake_Type", channel_id: "Snowflake_Type", suppress: bool = None
    ) -> None:
        """
        Modify the voice state of a user.

        :param guild_id: The ID of the guild.
        :param user_id: The ID of the user to modify.
        :param channel_id: The ID of the channel the user is currently in.
        :param suppress: Toggles the user's suppress state.
        """
        return await self.request(
            Route("PATCH", f"/guilds/{guild_id}/voice-states/{user_id}"),
            data=dict_filter_none({"channel_id": channel_id, "suppress": suppress}),
        )

    async def create_guild_from_guild_template(self, template_code: str, name: str) -> dict:
        """
        Create a a new guild based on a template.

        ..note: This endpoint can only be used by bots in less than 10 guilds.

        :param template_code: The code of the template to use.
        :param name: The name o the guild (2-100 characters)
        :return: The newly created guild object
        """
        # todo: add icon support
        return await self.request(Route("POST", f"/guilds/templates/{template_code}", data={"name": name}))

    async def get_guild_templates(self, guild_id: "Snowflake_Type") -> List[dict]:
        """
        Returns an array of guild templates.

        :param guild_id: The ID of the guild to query.
        :return: An array of guild templates
        """
        return await self.request(Route("GET", f"/guilds/{guild_id}/templates"))

    async def create_guild_template(self, guild_id: "Snowflake_Type", name: str, description: str = None) -> dict:
        """
        Create a guild template for the guild.

        :param guild_id: The ID of the guild to create a template for.
        :param name: The name of the template
        :param description: The description of the template
        :return: The created guild template
        """
        return await self.request(
            Route("POST", f"/guilds/{guild_id}/templates"),
            data=dict_filter_none({"name": name, "description": description}),
        )

    async def sync_guild_template(self, guild_id: "Snowflake_Type", template_code: str) -> dict:
        """
        Sync the template to the guild's current state.

        :param guild_id: The ID of the guild
        :param template_code: The code for the template to sync
        :return: The updated guild template
        """
        return await self.request(Route("PUT", f"/guilds/{guild_id}/templates/{template_code}"))

    async def modify_guild_template(
        self, guild_id: "Snowflake_Type", template_code: str, name: str = None, description: str = None
    ) -> dict:
        """
        Modifies the template's metadata

        :param guild_id: The ID of the guild
        :param template_code: The template code
        :param name: The name of the template
        :param description: The description of the template
        :return: The updated guild template
        """
        return await self.request(
            Route("PATCH", f"/guilds/{guild_id}/templates/{template_code}"),
            data=dict_filter_none({"name": name, "description": description}),
        )

    async def delete_guild_template(self, guild_id: "Snowflake_Type", template_code: str) -> dict:
        """
        Delete the guild template.

        :param guild_id: The ID of the guild
        :param template_code: The ID of the template
        :return: The deleted template object
        """
        # why on earth does this return the deleted template object?
        return await self.request(Route("DELETE", f"/guilds/{guild_id}/templates/{template_code}"))
