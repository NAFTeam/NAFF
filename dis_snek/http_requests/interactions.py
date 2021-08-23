from typing import Any, Dict, List, Optional, Union

from dis_snek.models.route import Route
from dis_snek.models.snowflake import Snowflake_Type


class InteractionRequests:
    request: Any

    async def get_interaction_element(
        self, application_id: Snowflake_Type, guild_id: Optional[Snowflake_Type] = None
    ) -> List[Dict]:
        """
        Get all interaction elements for this application from discord.

        :param application_id: the what application to query
        :param guild_id: specify a guild to get commands from
        :return:
        """
        if not guild_id:
            return await self.request(Route("GET", f"/applications/{application_id}/commands"))
        return await self.request(Route("GET", f"/applications/{application_id}/guilds/{guild_id}/commands"))

    async def post_interaction_element(self, app_id: Snowflake_Type, data: List[Dict], guild_id: Snowflake_Type = None):
        """
        Register an interaction element.

        :param app_id: The application ID of this bot
        :param guild_id: The ID of the guild this command is for, if this is a guild command
        :param data: List of your interaction data
        """

        endpoint = f"/applications/{app_id}/commands"
        if guild_id:
            endpoint = f"/applications/{app_id}/guilds/{guild_id}/commands"

        return await self.request(Route("PUT", endpoint), data=data)

    async def post_initial_response(self, payload: dict, interaction_id: str, token: str) -> None:
        """
        Post an initial response to an interaction.

        :param payload: the payload to send
        :param interaction_id: the id of the interaction
        :param token: the token of the interaction
        """

        return await self.request(Route("POST", f"/interactions/{interaction_id}/{token}/callback"), data=payload)

    async def post_followup(self, payload: dict, application_id: Snowflake_Type, token: str) -> None:
        """
        Send a followup to an interaction.

        :param payload: the payload to send
        :param application_id: the id of the application
        :param token: the token of the interaction
        """

        return await self.request(Route("POST", f"/webhooks/{application_id}/{token}"), data=payload)

    async def edit_interaction_message(
        self, payload: dict, application_id: Snowflake_Type, token: str, message_id: str = "@original"
    ) -> dict:
        """
        Edits an existing interaction message.

        :param payload: The payload to send.
        :param application_id: The id of the application.
        :param token: The token of the interaction.
        :param message_id: The target message to edit. Defaults to @original which represents the initial response message.

        :return: The edited message data.
        """

        return await self.request(
            Route("PATCH", f"/webhooks/{application_id}/{token}/messages/{message_id}"), data=payload
        )

    async def get_interaction_message(self, application_id: str, token: str, message_id: str = "@original") -> dict:
        """
        Gets an existing interaction message.

        :param payload: The payload to send.
        :param application_id: The id of the application.
        :param token: The token of the interaction.
        :param message_id: The target message to get. Defaults to @original which represents the initial response message.

        :return: The message data.
        """

        return await self.request(Route("GET", f"/webhooks/{application_id}/{token}/messages/{message_id}"))

    async def edit_application_command_permissions(
        self, application_id: Snowflake_Type, scope: Snowflake_Type, cmd_id: Snowflake_Type, permissions: List[dict]
    ) -> dict:
        """
        Edits command permissions for a specific command.

        :param application_id: the id of the application
        :param scope: The scope this command is in
        :param cmd_id: The command id to edit
        :param permissions: The permissions to set to this command
        :return: Guild Application Command Permissions
        """
        return await self.request(
            Route("PUT", f"/applications/{application_id}/guilds/{scope}/commands/{cmd_id}/permissions"),
            data=permissions,
        )

    async def batch_edit_application_command_permissions(
        self, application_id: Snowflake_Type, scope: Snowflake_Type, data: List[dict]
    ) -> dict:
        """
        Edit multiple command permissions within a single scope.

        :param application_id: the id of the application
        :param scope: The scope this command is in
        :param data: The permissions to be set
        :return: array of GuildApplicationCommandPermissions objects
        """
        return await self.request(
            Route("PUT", f"/applications/{application_id}/guilds/{scope}/commands/permissions"),
            data=data,
        )

    async def get_application_command_permissions(
        self, application_id: Snowflake_Type, scope: Snowflake_Type, cmd_id: Snowflake_Type
    ) -> dict:
        """
        Get permission data for a command.

        :param application_id: the id of the application
        :param scope: The scope this command is in
        :param cmd_id: The command id to edit
        :return: guild application command permissions
        """
        return await self.request(
            Route("GET", f"/applications/{application_id}/guilds/{scope}/commands/{cmd_id}/permissions")
        )

    async def batch_get_application_command_permissions(
        self, application_id: Snowflake_Type, scope: Snowflake_Type
    ) -> dict:
        """
        Get permission data for all commands in a scope

        :param application_id: the id of the application
        :param scope: The scope this command is in
        :return: list of guild application command permissions
        """
        return await self.request(Route("GET", f"/applications/{application_id}/guilds/{scope}/commands/permissions"))
