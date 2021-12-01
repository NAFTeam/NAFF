from typing import TYPE_CHECKING, Any, Dict, List

from dis_snek.const import GLOBAL_SCOPE
from dis_snek.models.route import Route

if TYPE_CHECKING:
    from dis_snek.models.snowflake import Snowflake_Type


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
    ) -> List[Dict]:
        """
        Get all application commands for this application from discord.

        parameters:
            application_id: the what application to query
            guild_id: specify a guild to get commands from
        returns:
            InteractionCommand
        """
        if guild_id == GLOBAL_SCOPE:
            return await self.request(Route("GET", f"/applications/{application_id}/commands"))
        return await self.request(Route("GET", f"/applications/{application_id}/guilds/{guild_id}/commands"))

    async def post_application_command(
        self, app_id: "Snowflake_Type", data: List[Dict], guild_id: "Snowflake_Type" = None
    ):
        """
        Register an application command.

        parameters:
            app_id: The application ID of this bot
            guild_id: The ID of the guild this command is for, if this is a guild command
            data: List of your interaction data
        """
        if guild_id == GLOBAL_SCOPE:
            return await self.request(Route("PUT", f"/applications/{app_id}/commands"), data=data)
        return await self.request(Route("PUT", f"/applications/{app_id}/guilds/{guild_id}/commands"), data=data)

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
    ) -> dict:
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

    async def get_interaction_message(self, application_id: str, token: str, message_id: str = "@original") -> dict:
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
    ) -> dict:
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
    ) -> dict:
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
    ) -> dict:
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
    ) -> dict:
        """
        Get permission data for all commands in a scope

        parameters:
            application_id: the id of the application
            scope: The scope this command is in
        returns:
            list of guild application command permissions
        """
        return await self.request(Route("GET", f"/applications/{application_id}/guilds/{scope}/commands/permissions"))
