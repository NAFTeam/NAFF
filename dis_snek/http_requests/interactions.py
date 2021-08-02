from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

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

        return await self.request(Route("PUT", endpoint), json=data)

    async def post_initial_response(self, payload: dict, interaction_id: str, token: str) -> None:
        """
        Post an initial response to an interaction.

        :param payload: the payload to send
        :param interaction_id: the id of the interaction
        :param token: the token of the interaction
        """

        return await self.request(Route("POST", f"/interactions/{interaction_id}/{token}/callback"), json=payload)

    async def post_followup(self, payload: dict, application_id: str, token: str) -> None:
        """
        Send a followup to an interaction.

        :param payload: the payload to send
        :param application_id: the id of the application
        :param token: the token of the interaction
        """

        return await self.request(Route("POST", f"/webhooks/{application_id}/{token}"), json=payload)

    async def edit(self, payload: dict, application_id: str, token: str, message_id: str = "@original"):

        return await self.request(
            Route("PATCH", f"/webhooks/{application_id}/{token}/messages/{message_id}"), json=payload
        )
