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

        await self.request(Route("PUT", endpoint), json=data)
