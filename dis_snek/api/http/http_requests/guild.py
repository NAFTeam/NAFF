from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

import discord_typings

from dis_snek.client.const import Absent, MISSING
from dis_snek.client.utils.serializer import dict_filter_missing, dict_filter_none


from ..route import Route

__all__ = ("GuildRequests",)


if TYPE_CHECKING:
    from dis_snek.models.discord.snowflake import Snowflake_Type
    from dis_snek.models.discord.enums import AuditLogEventType


class GuildRequests:
    request: Any

    async def get_guilds(
        self, limit: int = 200, before: Optional["Snowflake_Type"] = None, after: Optional["Snowflake_Type"] = None
    ) -> List[discord_typings.GuildData]:
        """
        Get a list of partial guild objects the current user is a member of req. `guilds` scope.

        Args:
            limit: max number of guilds to return (1-200)
            before: get guilds before this guild ID
            after: get guilds after this guild ID

        Returns:
            List of guild objects

        """
        params: Dict[str, Union[int, str]] = {"limit": limit}

        if before:
            params["before"] = before
        if after:
            params["after"] = after
        return await self.request(Route("GET", "/users/@me/guilds", params=params))

    async def get_guild(
        self, guild_id: "Snowflake_Type", with_counts: Optional[bool] = True
    ) -> discord_typings.GuildData:
        """
        Get the guild object for the given ID.

        Args:
            guild_id: the id of the guild
            with_counts: when `true`, will return approximate member and presence counts for the guild
        Returns:
            a guild object

        """
        return await self.request(
            Route("GET", f"/guilds/{guild_id}"), params={"with_counts": int(with_counts)}  # type: ignore
        )

    async def get_guild_preview(self, guild_id: "Snowflake_Type") -> discord_typings.GuildPreviewData:
        """
        Get a guild's preview.

        Args:
            guild_id: the guilds ID

        Returns:
            guild preview object

        """
        return await self.request(Route("GET", f"/guilds/{guild_id}/preview"))

    async def get_channels(self, guild_id: "Snowflake_Type") -> List[discord_typings.ChannelData]:
        """
        Get a guilds channels.

        Args:
            guild_id: the id of the guild

        Returns:
            List of channels

        """
        return await self.request(Route("GET", f"/guilds/{guild_id}/channels"))

    async def get_roles(self, guild_id: "Snowflake_Type") -> List[discord_typings.RoleData]:
        """
        Get a guild's roles.

        Args:
            guild_id: The ID of the guild

        Returns:
            List of roles

        """
        return await self.request(Route("GET", f"/guilds/{guild_id}/roles"))

    async def modify_guild(self, guild_id: "Snowflake_Type", reason: Absent[str] = MISSING, **kwargs) -> None:
        """
        Modify a guild's attributes.

        Args:
            guild_id: The ID of the guild we want to modify
            reason: The reason for this change
            kwargs: The params to change

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
        kwargs_copy = kwargs.copy()
        for key, value in kwargs.items():
            if key not in expected or value is MISSING:
                del kwargs_copy[key]

        # only do the request if there is something to modify
        if kwargs_copy:
            await self.request(Route("PATCH", f"/guilds/{guild_id}"), data=kwargs_copy, reason=reason)

    async def delete_guild(self, guild_id: "Snowflake_Type") -> None:
        """
        Delete the guild.

        Args:
            guild_id: The ID of the guild that we want to delete

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
    ) -> discord_typings.GuildMemberData:
        """
        Add a user to the guild. All parameters to this endpoint except for `access_token`, `guild_id` and `user_id` are optional.

        Args:
            guild_id: The ID of the guild
            user_id: The ID of the user to add
            access_token: The access token of the user
            nick: value to set users nickname to
            roles: array of role ids the member is assigned
            mute: whether the user is muted in voice channels
            deaf: whether the user is deafened in voice channels
        Returns:
            Guild Member Object

        """
        return await self.request(
            Route("PUT", f"/guilds/{guild_id}/members/{user_id}"),
            data=dict_filter_none(
                {"access_token": access_token, "nick": nick, "roles": roles, "mute": mute, "deaf": deaf}
            ),
        )

    async def remove_guild_member(
        self, guild_id: "Snowflake_Type", user_id: "Snowflake_Type", reason: Absent[str] = MISSING
    ) -> None:
        """
        Remove a member from a guild.

        Args:
            guild_id: The ID of the guild
            user_id: The ID of the user to remove
            reason: The reason for this action

        """
        return await self.request(Route("DELETE", f"/guilds/{guild_id}/members/{user_id}"), reason=reason)

    async def get_guild_bans(
        self,
        guild_id: "Snowflake_Type",
        before: Absent["Snowflake_Type"] = MISSING,
        after: Absent["Snowflake_Type"] = MISSING,
        limit: int = 1000,
    ) -> List[discord_typings.BanData]:
        """
        Return a list of ban objects for the users banned from this guild.

        Args:
            guild_id: The ID of the guild to query

        Returns:
            List of ban objects

        """
        params = {
            "limit": limit,
            "before": before,
            "after": after,
        }

        return await self.request(Route("GET", f"/guilds/{guild_id}/bans"), params=params)

    async def get_guild_ban(
        self, guild_id: "Snowflake_Type", user_id: "Snowflake_Type"
    ) -> Optional[discord_typings.BanData]:
        """
        Returns a ban object for the given user or a 404 not found if the ban cannot be found.

        Args:
            guild_id: The ID of the guild to query
            user_id: The ID of the user to query

        Returns:
            Ban object if exists

        Raises:
            NotFound: if no ban exists

        """
        return await self.request(Route("GET", f"/guilds/{guild_id}/bans/{user_id}"))

    async def create_guild_ban(
        self,
        guild_id: "Snowflake_Type",
        user_id: "Snowflake_Type",
        delete_message_days: int = 0,
        reason: Absent[str] = MISSING,
    ) -> None:
        """
        Create a guild ban, and optionally delete previous messages sent by the banned user.

        Args:
            guild_id: The ID of the guild to create the ban in
            user_id: The ID of the user to ban
            delete_message_days: number of days to delete messages for (0-7)
            reason: The reason for this action

        """
        return await self.request(
            Route("PUT", f"/guilds/{guild_id}/bans/{user_id}"),
            data={"delete_message_days": delete_message_days},
            reason=reason,
        )

    async def remove_guild_ban(
        self, guild_id: "Snowflake_Type", user_id: "Snowflake_Type", reason: Absent[str] = MISSING
    ) -> None:
        """
        Remove a guild ban.

        Args:
            guild_id: The ID of the guild to remove the ban in
            user_id: The ID of the user to unban
            reason: The reason for this action

        """
        return await self.request(Route("DELETE", f"/guilds/{guild_id}/bans/{user_id}"), reason=reason)

    async def get_guild_prune_count(
        self, guild_id: "Snowflake_Type", days: int = 7, include_roles: List["Snowflake_Type"] = None
    ) -> dict:
        """
        Returns an object with one 'pruned' key indicating the number of members that would be removed in a prune operation.

        Args:
            guild_id: The ID of the guild to query
            days: number of days to count prune for (1-30)
            include_roles: role(s) to include

        Returns:
            {"pruned": int}

        """
        payload = {"days": days}
        if include_roles:
            payload["include_roles"] = ", ".join(include_roles)

        return await self.request(Route("GET", f"/guilds/{guild_id}/prune"), params=payload)

    async def begin_guild_prune(
        self,
        guild_id: "Snowflake_Type",
        days: int = 7,
        include_roles: Optional[List["Snowflake_Type"]] = None,
        compute_prune_count: bool = True,
        reason: Absent[str] = MISSING,
    ) -> dict:
        """
        Begin a prune operation.

        Args:
            guild_id: The ID of the guild to query
            days: number of days to count prune for (1-30)
            include_roles: role(s) to include
            compute_prune_count: whether 'pruned' is returned, discouraged for large guilds
            reason: The reason for this action

        Returns:
            {"pruned": Optional[int]}

        """
        payload = {"days": days, "compute_prune_count": compute_prune_count}
        if include_roles:
            payload["include_roles"] = ", ".join(include_roles)

        return await self.request(Route("POST", f"/guilds/{guild_id}/prune"), data=payload, reason=reason)

    async def get_guild_invites(self, guild_id: "Snowflake_Type") -> List[discord_typings.InviteData]:
        """
        Returns a list of invite objects (with invite metadata) for the guild.

        Args:
            guild_id: The ID of the guild to query

        Returns:
            List of invite objects

        """
        return await self.request(Route("GET", f"/guilds/{guild_id}/invites"))

    async def create_guild_role(
        self, guild_id: "Snowflake_Type", payload: dict, reason: Absent[str] = MISSING
    ) -> discord_typings.RoleData:
        """
        Create a new role for the guild.

        Args:
            guild_id: The ID of the guild
            payload: A dict representing the role to add
            reason: The reason for this action

        Returns:
            Role object

        """
        return await self.request(Route("POST", f"/guilds/{guild_id}/roles"), data=payload, reason=reason)

    async def modify_guild_role_positions(
        self, guild_id: "Snowflake_Type", role_id: "Snowflake_Type", position: int, reason: Absent[str] = MISSING
    ) -> List[discord_typings.RoleData]:
        """
        Modify the position of a role in the guild.

        Args:
            guild_id: The ID of the guild
            role_id: The ID of the role to move
            position: The new position of this role in the hierarchy
            reason: The reason for this action

        Returns:
            List of guild roles

        """
        return await self.request(
            Route("PATCH", f"/guilds/{guild_id}/roles"), data={"id": role_id, "position": position}, reason=reason
        )

    async def modify_guild_role(
        self, guild_id: "Snowflake_Type", role_id: "Snowflake_Type", payload: dict, reason: Absent[str] = MISSING
    ) -> discord_typings.RoleData:
        """
        Modify an existing role for the guild.

        Args:
            guild_id: The ID of the guild
            role_id: The ID of the role to move
            payload: A dict representing the role to add
            reason: The reason for this action

        Returns:
            Role object

        """
        return await self.request(Route("PATCH", f"/guilds/{guild_id}/roles/{role_id}"), data=payload, reason=reason)

    async def delete_guild_role(
        self, guild_id: "Snowflake_Type", role_id: "Snowflake_Type", reason: Absent[str] = MISSING
    ) -> None:
        """
        Delete a guild role.

        Args:
            role_id: The ID of the role to delete
            reason: The reason for this action
            guild_id: The ID of the guild

        """
        return await self.request(Route("DELETE", f"/guilds/{guild_id}/roles/{role_id}"), reason=reason)

    async def get_audit_log(
        self,
        guild_id: "Snowflake_Type",
        user_id: Absent["Snowflake_Type"] = MISSING,
        action_type: Absent["AuditLogEventType"] = MISSING,
        before: Absent["Snowflake_Type"] = MISSING,
        after: Absent["Snowflake_Type"] = MISSING,
        limit: int = 100,
    ) -> discord_typings.AuditLogData:
        """
        Get the audit log for a guild.

        Args:
            guild_id: The ID of the guild to query
            user_id: filter by user ID
            action_type: filter by action type
            before: snowflake to get entries before
            after: snowflake to get entries after
            limit: max number of entries to get

        Returns:
            audit log object for the guild

        """
        params = {
            "action_type": action_type,
            "user_id": user_id,
            "limit": limit,
            "before": before,
            "after": after,
        }
        return await self.request(Route("GET", f"/guilds/{guild_id}/audit-logs"), params=params)

    async def get_guild_voice_regions(self, guild_id: "Snowflake_Type") -> List[discord_typings.VoiceRegionData]:
        """
        Returns a list of voice region objects for the guild. Unlike the similar /voice route, this returns VIP servers when the guild is VIP- enabled.

        Args:
            guild_id: The ID of the guild to query

        Returns:
            List of voice region objects

        """
        return await self.request(Route("GET", f"/guilds/{guild_id}/regions"))

    async def get_guild_integrations(self, guild_id: "Snowflake_Type") -> List[discord_typings.IntegrationData]:
        """
        Returns a list of integration objects for the guild.

        Args:
            guild_id: The ID of the guild to query

        Returns:
            list of integration objects

        """
        return await self.request(Route("GET", f"/guilds/{guild_id}/integrations"))

    async def delete_guild_integration(
        self, guild_id: "Snowflake_Type", integration_id: "Snowflake_Type", reason: Absent[str] = MISSING
    ) -> None:
        """
        Delete an integration from the guild.

        Args:
            guild_id: The ID of the guild
            integration_id: The ID of the integration to remove

        """
        return await self.request(Route("DELETE", f"/guilds/{guild_id}/integrations/{integration_id}"), reason=reason)

    async def get_guild_widget_settings(self, guild_id: "Snowflake_Type") -> discord_typings.GuildWidgetSettingsData:
        """
        Get guild widget settings.

        Args:
            guild_id: The ID of the guild to query

        Returns:
            guild widget object

        """
        return await self.request(Route("GET", f"/guilds/{guild_id}/widget"))

    async def get_guild_widget(self, guild_id: "Snowflake_Type") -> discord_typings.GuildWidgetData:
        """
        Returns the widget for the guild.

        Args:
            guild_id: The ID of the guild to query

        Returns:
            Guild widget

        """
        return await self.request(Route("GET", f"/guilds/{guild_id}/widget.json"))

    async def get_guild_widget_image(self, guild_id: "Snowflake_Type", style: Optional[str] = None) -> str:
        """
        Get a url representing a png image widget for the guild.

        For styles see: https://discord.com/developers/docs/resources/guild#get-guild-widget-image

        Args:
            guild_id: The guild to query
            style: The style of widget required.

        Returns:
            A url pointing to this image

        """
        route = Route("GET", f"/guilds/{guild_id}/widget.png{f'?style={style}' if style else ''}")
        return route.url

    async def get_guild_welcome_screen(self, guild_id: "Snowflake_Type") -> discord_typings.WelcomeScreenData:
        """
        Get the welcome screen for this guild.

        Args:
            guild_id: The ID of the guild to query
        Returns:
            Welcome screen object

        """
        return await self.request(Route("GET", f"/guilds/{guild_id}/welcome-screen"))

    async def get_guild_vanity_url(self, guild_id: "Snowflake_Type") -> dict:
        """
        Get a partial invite object for the guilds vanity invite url.

        Args:
            guild_id: The ID of the guild to query

        Returns:
            Returns a partial invite object. Code is None if a vanity url for the guild is not set.

        """
        return await self.request(Route("GET", f"/guilds/{guild_id}/vanity-url"))

    async def get_guild_channels(self, guild_id: "Snowflake_Type") -> dict:
        """
        Gets a list of guild channel objects.

        Args:
            guild_id: The ID of the guild

        Returns:
            A list of channels in this guild. Does not include threads.
        """
        return await self.request(Route("GET", f"/guilds/{guild_id}/channels"))

    async def modify_guild_widget(
        self, guild_id: "Snowflake_Type", enabled: bool = None, channel_id: "Snowflake_Type" = None
    ) -> discord_typings.GuildWidgetData:
        """
        Modify a guild widget.

        Args:
            guild_id: The ID of the guild to modify.
            enabled: Should the guild widget be enabled
            channel_id: The widget's channel ID

        Returns:
            Updated guild widget.

        """
        return await self.request(
            Route("PATCH", f"/guilds/{guild_id}/widget"),
            data=dict_filter_none({"enabled": enabled, "channel_id": channel_id}),
        )

    async def modify_guild_welcome_screen(
        self, guild_id: "Snowflake_Type", enabled: bool, welcome_channels: List["Snowflake_Type"], description: str
    ) -> discord_typings.WelcomeScreenData:
        """
        Modify the guild's welcome screen.

        Args:
            guild_id: The ID of the guild.
            enabled: Whether the welcome screen is enabled
            welcome_channels: Channels linked in the welcome screen and their display options
            description: The server description to show in the welcome screen

        Returns:
            Updated welcome screen object

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

        Args:
            guild_id: The ID of the guild to update.
            channel_id: The id of the channel the user is currently in
            suppress: Toggle the user's suppress state.
            request_to_speak_timestamp: Sets the user's request to speak

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

        Args:
            guild_id: The ID of the guild.
            user_id: The ID of the user to modify.
            channel_id: The ID of the channel the user is currently in.
            suppress: Toggles the user's suppress state.

        """
        return await self.request(
            Route("PATCH", f"/guilds/{guild_id}/voice-states/{user_id}"),
            data=dict_filter_none({"channel_id": channel_id, "suppress": suppress}),
        )

    async def create_guild(
        self,
        name: str,
        icon: Absent[str] = MISSING,
        verification_level: Absent[int] = MISSING,
        default_message_notifications: Absent[int] = MISSING,
        explicit_content_filter: Absent[int] = MISSING,
        roles: Absent[list[dict]] = MISSING,
        channels: Absent[list[dict]] = MISSING,
        afk_channel_id: Absent["Snowflake_Type"] = MISSING,
        afk_timeout: Absent[int] = MISSING,
        system_channel_id: Absent["Snowflake_Type"] = MISSING,
        system_channel_flags: Absent[int] = MISSING,
    ) -> dict:
        return await self.request(
            Route("POST", "/guilds"),
            data=dict_filter_missing(
                {
                    "name": name,
                    "icon": icon,
                    "verification_level": verification_level,
                    "default_message_notifications": default_message_notifications,
                    "explicit_content_filter": explicit_content_filter,
                    "roles": roles,
                    "channels": channels,
                    "afk_channel_id": afk_channel_id,
                    "afk_timeout": afk_timeout,
                    "system_channel_id": system_channel_id,
                    "system_channel_flags": system_channel_flags,
                }
            ),
        )

    async def create_guild_from_guild_template(
        self, template_code: str, name: str, icon: str
    ) -> discord_typings.GuildData:
        """
        Creates a new guild based on a template.

        note:
            This endpoint can only be used by bots in less than 10 guilds.

        Args:
            template_code: The code of the template to use.
            name: The name of the guild (2-100 characters)
            icon: Data URI scheme

        Returns:
            The newly created guild object

        """
        return await self.request(
            Route("POST", f"/guilds/templates/{template_code}"), data={"name": name, "icon": icon}
        )

    async def get_guild_templates(self, guild_id: "Snowflake_Type") -> List[discord_typings.GuildTemplateData]:
        """
        Returns an array of guild templates.

        Args:
            guild_id: The ID of the guild to query.

        Returns:
            An array of guild templates

        """
        return await self.request(Route("GET", f"/guilds/{guild_id}/templates"))

    async def create_guild_template(
        self, guild_id: "Snowflake_Type", name: str, description: Absent[str] = MISSING
    ) -> discord_typings.GuildTemplateData:
        """
        Create a guild template for the guild.

        Args:
            guild_id: The ID of the guild to create a template for.
            name: The name of the template
            description: The description of the template

        Returns:
            The created guild template

        """
        return await self.request(
            Route("POST", f"/guilds/{guild_id}/templates"),
            data={"name": name, "description": description},
        )

    async def sync_guild_template(
        self, guild_id: "Snowflake_Type", template_code: str
    ) -> discord_typings.GuildTemplateData:
        """
        Sync the template to the guild's current state.

        Args:
            guild_id: The ID of the guild
            template_code: The code for the template to sync

        Returns:
            The updated guild template

        """
        return await self.request(Route("PUT", f"/guilds/{guild_id}/templates/{template_code}"))

    async def modify_guild_template(
        self,
        guild_id: "Snowflake_Type",
        template_code: str,
        name: Absent[str] = MISSING,
        description: Absent[str] = MISSING,
    ) -> discord_typings.GuildTemplateData:
        """
        Modifies the template's metadata.

        Args:
            guild_id: The ID of the guild
            template_code: The template code
            name: The name of the template
            description: The description of the template

        Returns:
            The updated guild template

        """
        return await self.request(
            Route("PATCH", f"/guilds/{guild_id}/templates/{template_code}"),
            data={"name": name, "description": description},
        )

    async def delete_guild_template(
        self, guild_id: "Snowflake_Type", template_code: str
    ) -> discord_typings.GuildTemplateData:
        """
        Delete the guild template.

        Args:
            guild_id: The ID of the guild
            template_code: The ID of the template

        Returns:
            The deleted template object

        """
        # why on earth does this return the deleted template object?
        return await self.request(Route("DELETE", f"/guilds/{guild_id}/templates/{template_code}"))
