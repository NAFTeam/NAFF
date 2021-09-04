from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from dis_snek.models.route import Route

if TYPE_CHECKING:
    from dis_snek.models.snowflake import Snowflake_Type


class BotRequests:
    request: Any

    async def get_current_bot_information(self) -> dict:
        """
        Returns the bot's application object without flags.

        :return: application object
        """
        return await self.request(Route("GET", f"/oauth2/applications/@me"))

    async def get_current_authorisation_information(self) -> dict:
        """
        Returns info about the current authorization

        :return: Authorisation information
        """
        return await self.request(Route("GET", f"/oauth2/@me"))
