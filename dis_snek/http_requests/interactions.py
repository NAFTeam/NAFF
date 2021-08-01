from typing import List, Dict, Any

from dis_snek.models.route import Route
from dis_snek.models.snowflake import Snowflake_Type


class InteractionRequests:
    request: Any

    async def get_slash_commands(
        self, application_id: Snowflake_Type, guild_id: Optional[Snowflake_Type] = None
    ) -> List[Dict]:
        """
        Get all SlashCommands for this application from discord.

        :param application_id: the what application to query
        :param guild_id: specify a guild to get commands from
        :return:
        """
        if not guild_id:
            return await self.request(Route("GET", f"/applications/{application_id}/commands"))
        return await self.request(Route("GET", f"/applications/{application_id}/guilds/{guild_id}/commands"))
