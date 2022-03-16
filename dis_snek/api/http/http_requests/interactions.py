from typing import TYPE_CHECKING, Any, Dict, List

import discord_typings

from dis_snek.client.const import GLOBAL_SCOPE
from ..route import Route

__all__ = ["InteractionRequests"]


if TYPE_CHECKING:
    from dis_snek.models.discord.snowflake import Snowflake_Type


class InteractionRequests:
    request: Any

    async def delete_application_command(
        self, application_id: "Snowflake_Type", guild_id: "Snowflake_Type", command_id: "Snowflake_Type"
    ) -> None:
        """
        Delete an existing application command for this application.

        Attributes:
            application_id: the what application to delete for
            guild_id: specify a guild to delete commands from
            command_id The command to delete

        """
        if guild_id == GLOBAL_SCOPE:
            return await self.request(Route("DELETE", f"/applications/{application_id}/commands/{command_id}"))
        return await self.request(
            Route("DELETE", f"/applications/{application_id}/guilds/{guild_id}/commands/{command_id}")
        )

    async def get_application_commands(
        self, application_id: "Snowflake_Type", guild_id: "Snowflake_Type"
    ) -> List[discord_typings.ApplicationCommandData]:
        """
        Get all application commands for this application from discord.

        parameters:
            application_id: the what application to query
            guild_id: specify a guild to get commands from

        returns:
            Application command data

        """
        if guild_id == GLOBAL_SCOPE:
            return await self.request(Route("GET", f"/applications/{application_id}/commands"))
        return await self.request(Route("GET", f"/applications/{application_id}/guilds/{guild_id}/commands"))

    async def overwrite_application_commands(
        self, app_id: "Snowflake_Type", data: List[Dict], guild_id: "Snowflake_Type" = None
    ) -> List[discord_typings.ApplicationCommandData]:
        """
        Take a list of commands and overwrite the existing command list within the given scope

        parameters:
            app_id: The application ID of this bot
            guild_id: The ID of the guild this command is for, if this is a guild command
            data: List of your interaction data

        """
        if guild_id == GLOBAL_SCOPE:
            return await self.request(Route("PUT", f"/applications/{app_id}/commands"), data=data)
        return await self.request(Route("PUT", f"/applications/{app_id}/guilds/{guild_id}/commands"), data=data)

    async def create_application_command(
        self, app_id: "Snowflake_Type", command: Dict, guild_id: "Snowflake_Type"
    ) -> discord_typings.ApplicationCommandData:
        """
        Add a given command to scope.

        Args:
            app_id: The application ID of this bot
            command: A dictionary representing a command to be created
            guild_id: The ID of the guild this command is for, if this is a guild command

        Returns:
            An application command object
        """
        if guild_id == GLOBAL_SCOPE:
            return await self.request(Route("POST", f"/applications/{app_id}/commands"), data=command)
        return await self.request(Route("POST", f"/applications/{app_id}/guilds/{guild_id}/commands"), data=command)

    async def post_initial_response(self, payload: dict, interaction_id: str, token: str) -> None:
        """
        Post an initial response to an interaction.

        parameters:
            payload: the payload to send
            interaction_id: the id of the interaction
            token: the token of the interaction

        """
        return await self.request(Route("POST", f"/interactions/{interaction_id}/{token}/callback"), data=payload)

    async def post_followup(self, payload: dict, application_id: "Snowflake_Type", token: str) -> None:
        """
        Send a followup to an interaction.

        parameters:
            payload: the payload to send
            application_id: the id of the application
            token: the token of the interaction

        """
        return await self.request(Route("POST", f"/webhooks/{application_id}/{token}"), data=payload)

    async def edit_interaction_message(
        self, payload: dict, application_id: "Snowflake_Type", token: str, message_id: str = "@original"
    ) -> discord_typings.MessageData:
        """
        Edits an existing interaction message.

        parameters:
            payload: The payload to send.
            application_id: The id of the application.
            token: The token of the interaction.
            message_id: The target message to edit. Defaults to @original which represents the initial response message.

        returns:
            The edited message data.

        """
        return await self.request(
            Route("PATCH", f"/webhooks/{application_id}/{token}/messages/{message_id}"), data=payload
        )

    async def get_interaction_message(
        self, application_id: str, token: str, message_id: str = "@original"
    ) -> discord_typings.MessageData:
        """
        Gets an existing interaction message.

        parameters:
            payload: The payload to send.
            application_id: The id of the application.
            token: The token of the interaction.
            message_id: The target message to get. Defaults to @original which represents the initial response message.

        returns:
            The message data.

        """
        return await self.request(Route("GET", f"/webhooks/{application_id}/{token}/messages/{message_id}"))

    async def edit_application_command_permissions(
        self,
        application_id: "Snowflake_Type",
        scope: "Snowflake_Type",
        cmd_id: "Snowflake_Type",
        permissions: List[dict],
    ) -> discord_typings.ApplicationCommandPermissionsData:
        """
        Edits command permissions for a specific command.

        parameters:
            application_id: the id of the application
            scope: The scope this command is in
            cmd_id: The command id to edit
            permissions: The permissions to set to this command
        returns:
            Guild Application Command Permissions

        """
        return await self.request(
            Route("PUT", f"/applications/{application_id}/guilds/{scope}/commands/{cmd_id}/permissions"),
            data=permissions,
        )

    async def batch_edit_application_command_permissions(
        self, application_id: "Snowflake_Type", scope: "Snowflake_Type", data: List[dict]
    ) -> List[discord_typings.ApplicationCommandPermissionsData]:
        """
        Edit multiple command permissions within a single scope.

        parameters:
            application_id: the id of the application
            scope: The scope this command is in
            data: The permissions to be set
        returns:
            array of GuildApplicationCommandPermissions objects

        """
        return await self.request(
            Route("PUT", f"/applications/{application_id}/guilds/{scope}/commands/permissions"),
            data=data,
        )

    async def get_application_command_permissions(
        self, application_id: "Snowflake_Type", scope: "Snowflake_Type", cmd_id: "Snowflake_Type"
    ) -> List[discord_typings.ApplicationCommandPermissionsData]:
        """
        Get permission data for a command.

        parameters:
            application_id: the id of the application
            scope: The scope this command is in
            cmd_id: The command id to edit
        returns:
            guild application command permissions

        """
        return await self.request(
            Route("GET", f"/applications/{application_id}/guilds/{scope}/commands/{cmd_id}/permissions")
        )

    async def batch_get_application_command_permissions(
        self, application_id: "Snowflake_Type", scope: "Snowflake_Type"
    ) -> List[discord_typings.ApplicationCommandPermissionsData]:
        """
        Get permission data for all commands in a scope.

        parameters:
            application_id: the id of the application
            scope: The scope this command is in
        returns:
            list of guild application command permissions

        """
        return await self.request(Route("GET", f"/applications/{application_id}/guilds/{scope}/commands/permissions"))
