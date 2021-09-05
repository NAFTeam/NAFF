from typing import Any

from dis_snek.models.route import Route


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
